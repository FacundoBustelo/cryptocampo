#!/usr/bin/env python3
"""Sepolia: diagnóstico, simulación, publicación reconciliada y evidencia sin secretos."""

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import fcntl
import importlib.util
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('local_demo', ROOT / 'tools/demo.py')
local = importlib.util.module_from_spec(spec)
spec.loader.exec_module(local)
ROLES = ('admin', 'a', 'b', 'funds', 'fees')
CHAIN = 11155111
CURVE_ORDER = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
# Única versión admitida para recuperar el despliegue rechazado por comisiones.
# No permite aceptar cambios de contratos, scripts Solidity ni otros archivos.
FEE_FIX_PREVIOUS = {
    'tools/sepolia.py': '7c4ae849cc9e7fdf8bbfe18d0b134acd01f4f208da60c1a2b0783b4dc6c2150a',
    'tools/test_sepolia.py': 'db7d8bbb1c9b41cc2d41d13c2f7a3bc7573e6d54265664072df23cd0f448ed58',
}
RPC_GAS_FIX_PREVIOUS = {
    'tools/sepolia.py': '0a0dfb2d2e720b19acdc6c2aa58c400e5b42d1b4042a430a4c1e8540ed31c51b',
    'tools/test_sepolia.py': '369757972d298c47726d60aa724ff2e0ecb8502a379a419f7464ddc76d6d506e',
    'Makefile': '7acfa2731e29ec1972f6a9818379dd619e362e3af79037438299ee4888fb681b',
}


def read_environment(path=ROOT / '.env'):
    """Leer valores literales, sin source, interpolación ni ejecución de shell."""
    values = {}
    if path.exists():
        for line in path.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            match = re.fullmatch(r'(?:export\s+)?([A-Z][A-Z0-9_]*)=(.*)', line)
            if not match:
                raise ValueError('Formato .env inválido; usar NOMBRE=valor literal.')
            key, value = match.groups()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[key] = value
    values.update(os.environ)
    required = ['SEPOLIA_RPC_URL', 'ETHERSCAN_API_KEY']
    required += [f'SEPOLIA_{role.upper()}{suffix}' for role in ROLES for suffix in ('_ADDRESS', '_PRIVATE_KEY')]
    missing = [key for key in required if not values.get(key)]
    if missing:
        raise ValueError('Variables pendientes: ' + ', '.join(missing))
    url = urllib.parse.urlparse(values['SEPOLIA_RPC_URL'])
    if url.scheme != 'https' or not url.hostname or url.fragment:
        raise ValueError('SEPOLIA_RPC_URL requiere HTTPS.')
    addresses = []
    for role in ROLES:
        prefix = f'SEPOLIA_{role.upper()}'
        address = values[prefix + '_ADDRESS'].lower()
        if not re.fullmatch(r'0x[0-9a-f]{40}', address) or int(address, 16) == 0:
            raise ValueError(prefix + '_ADDRESS inválida.')
        key = values[prefix + '_PRIVATE_KEY']
        if not re.fullmatch(r'0x[0-9a-fA-F]{64}', key) or not 0 < int(key, 16) < CURVE_ORDER:
            raise ValueError(prefix + '_PRIVATE_KEY inválida.')
        values[prefix + '_ADDRESS'] = address
        addresses.append(address)
    if len(set(addresses)) != 5:
        raise ValueError('Se requieren cinco direcciones distintas.')
    return values


class Redactor:
    def __init__(self, env):
        secrets = [env.get('SEPOLIA_RPC_URL', ''), env.get('ETHERSCAN_API_KEY', '')]
        url = urllib.parse.urlparse(env.get('SEPOLIA_RPC_URL', ''))
        secrets += [url.username or '', url.password or '']
        secrets += [part for part in url.path.split('/') if len(part) >= 12]
        secrets += list(urllib.parse.parse_qs(url.query).values())
        flat = []
        for secret in secrets:
            flat.extend(secret if isinstance(secret, list) else [secret])
        for key, value in env.items():
            if key.endswith('_PRIVATE_KEY') or key == 'DEMO_SIGNING_KEY':
                flat += [value, value.removeprefix('0x')] if value else []
                if value and re.fullmatch(r'0x[0-9a-fA-F]{64}', value):
                    decimal = str(int(value, 16))
                    if len(decimal) >= 20:
                        flat.append(decimal)
        self.secrets = sorted({v for v in flat if v}, key=len, reverse=True)

    def __call__(self, value):
        for secret in self.secrets:
            value = re.sub(re.escape(secret), '[REDACTED]', value, flags=re.IGNORECASE)
            encoded = urllib.parse.quote(secret, safe='')
            value = re.sub(re.escape(encoded), '[REDACTED]', value, flags=re.IGNORECASE)
        return value


class RPCError(RuntimeError):
    def __init__(self, method, error):
        super().__init__(f'RPC {method}: respuesta de error.')
        self.code = error.get('code')
        self.data = error.get('data')


class ReconciliationError(RuntimeError):
    def __init__(self, message, transactions):
        super().__init__(message)
        self.transactions = transactions


class RPC:
    def __init__(self, url):
        self.url = url

    def call(self, method, params):
        request = urllib.request.Request(self.url, data=json.dumps({
            'jsonrpc': '2.0', 'id': 1, 'method': method, 'params': params}).encode(),
            headers={'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                result = json.load(response)
        except Exception:
            raise RuntimeError(f'RPC {method}: conexión fallida.') from None
        if 'error' in result:
            # No incluir respuestas arbitrarias del proveedor ni su URL.
            raise RPCError(method, result['error'])
        return result['result']


def transaction(raw):
    tx = raw.get('transaction', raw)
    data = tx.get('input', tx.get('data', '0x')).lower()
    return {'from': tx['from'].lower(), 'to': (tx.get('to') or '').lower() or None,
            'input': data, 'nonce': int(tx['nonce'], 16) if isinstance(tx['nonce'], str) else tx['nonce'],
            'value': int(tx.get('value', '0x0'), 16) if isinstance(tx.get('value', '0x0'), str) else tx['value']}


def estimate_fees(rpc):
    """Mantener coherentes base, propina y máximo EIP-1559, incluso con gasPrice muy bajo."""
    block = rpc.call('eth_getBlockByNumber', ['latest', False])
    base = int(block['baseFeePerGas'], 16)
    priority = int(rpc.call('eth_maxPriorityFeePerGas', []), 16)
    suggested = int(rpc.call('eth_gasPrice', []), 16)
    if min(base, priority, suggested) < 0:
        raise ValueError('RPC devolvió comisiones negativas.')
    return {'base_fee_wei': base, 'max_priority_fee_wei': priority,
            'max_fee_wei': max(2 * base + priority, 2 * suggested, 1)}


def reconcile(rpc, plan, start_block, confirmations=2):
    """Encontrar por nonce incluso si se interrumpió antes de guardar el hash de Forge."""
    head = int(rpc.call('eth_blockNumber', []), 16)
    receipts = []
    gap = False
    for expected in plan:
        sender, nonce = expected['from'], expected['nonce']
        latest = int(rpc.call('eth_getTransactionCount', [sender, 'latest']), 16)
        if latest <= nonce:
            pending = int(rpc.call('eth_getTransactionCount', [sender, 'pending']), 16)
            if pending > nonce:
                raise RuntimeError('Nonce pendiente: esperar confirmación antes de continuar.')
            gap = True
            continue
        if gap:
            raise RuntimeError('Secuencia de nonces inconsistente.')
        # Búsqueda por bloque: evita escanear todo Sepolia después de una interrupción larga.
        lo, hi = start_block + 1, head
        while lo < hi:
            mid = (lo + hi) // 2
            count = int(rpc.call('eth_getTransactionCount', [sender, hex(mid)]), 16)
            if count > nonce:
                hi = mid
            else:
                lo = mid + 1
        block = rpc.call('eth_getBlockByNumber', [hex(lo), True])
        matches = [tx for tx in block['transactions'] if tx['from'].lower() == sender
                   and int(tx['nonce'], 16) == nonce]
        if len(matches) != 1 or transaction(matches[0]) != expected:
            raise RuntimeError('Nonce utilizado por otra transacción; detener y revisar.')
        tx = matches[0]
        receipt = rpc.call('eth_getTransactionReceipt', [tx['hash']])
        if not receipt or receipt['blockHash'] != block['hash']:
            raise RuntimeError('Recibo ausente o reorganización: reconciliar de nuevo.')
        observed = {'hash': tx['hash'], 'receipt': receipt,
                    'url': f"https://sepolia.etherscan.io/tx/{tx['hash']}"}
        if int(receipt['status'], 16) != 1:
            raise ReconciliationError('Recibo fallido; no repetir automáticamente.', receipts + [observed])
        if receipt['from'].lower() != sender:
            raise RuntimeError('Firmante del recibo incorrecto.')
        if head - int(receipt['blockNumber'], 16) + 1 < confirmations:
            raise RuntimeError('Confirmaciones insuficientes; volver a reconciliar.')
        receipts.append({'hash': tx['hash'], 'receipt': receipt,
                         'url': f"https://sepolia.etherscan.io/tx/{tx['hash']}"})
    return receipts


class Sepolia(local.Demo):
    def __init__(self, output, state_path, env):
        self.env = env
        self.redact = Redactor(env)
        self.state_path = state_path
        private_root = ROOT / '.tools/sepolia-private'
        private_root.mkdir(parents=True, mode=0o700, exist_ok=True)
        self.raw = private_root / output.name
        self.raw.mkdir(mode=0o700)
        super().__init__(output)
        self.p = local.parameters()
        self.rpc = RPC(env['SEPOLIA_RPC_URL'])
        self.context = json.loads(state_path.read_text()) if state_path.exists() else {
            'profile': 'sepolia', 'chain_id': CHAIN, 'rpc_url': 'sepolia',
            'actors': {role: env[f'SEPOLIA_{role.upper()}_ADDRESS'] for role in ROLES},
            'addresses': {}, 'completed': []}
        self.report['network'] = 'sepolia'

    def save(self):
        self.report['context'] = self.context
        self.write(self.output / 'result.json', self.report)

    def write(self, path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        temp = path.with_suffix('.tmp')
        temp.write_text(self.redact(json.dumps(data, indent=2, ensure_ascii=False)) + '\n')
        temp.replace(path)

    def checkpoint(self):
        self.write(self.state_path, self.context)
        self.save()

    def command(self, args, env=None, allow_failure=False):
        # stdout se filtra en memoria antes de persistirlo. Las claves y RPC solo viajan por entorno.
        record = {'command': args, 'started_at': local.now(), 'log': f"{len(self.report['commands']):03d}.txt"}
        self.report['commands'].append(record)
        self.save()
        try:
            result = subprocess.run(args, cwd=ROOT, env=env or self.environment(), capture_output=True,
                                    text=True, timeout=240)
            code, output = result.returncode, result.stdout + result.stderr
        except subprocess.TimeoutExpired:
            code, output = 124, 'Tiempo máximo excedido; reconciliar antes de reintentar.'
        except OSError:
            code, output = 127, 'No se pudo ejecutar la herramienta.'
        output = self.redact(output)
        (self.output / record['log']).write_text(output)
        record.update(exit_code=code, finished_at=local.now())
        # Los archivos internos de Forge quedan privados y excluidos de Git.
        for path in self.raw.rglob('*.json'):
            path.write_text(self.redact(path.read_text()))
        self.save()
        if code and not allow_failure:
            raise RuntimeError(f"Falló {args[1] if len(args)>1 else args[0]}; ver {record['log']}.")
        return code, output.strip()

    def environment(self, role='admin'):
        env = dict(self.env)
        # Evitar overrides de perfiles/compilación/URLs que alteren los parámetros fijados.
        for key in list(env):
            if key.startswith(('FOUNDRY_', 'DAPP_', 'DEMO_', 'ETH_')):
                del env[key]
        env.update(DEMO_PROFILE='sepolia', FOUNDRY_PROFILE='default',
                   FOUNDRY_BROADCAST=str(self.raw), FOUNDRY_DISABLE_NIGHTLY_WARNING='1',
                   ETH_RPC_URL=self.env['SEPOLIA_RPC_URL'],
                   DEMO_SIGNING_KEY=self.env[f'SEPOLIA_{role.upper()}_PRIVATE_KEY'])
        for actor, address in self.context['actors'].items():
            env[f'DEMO_{actor.upper()}'] = address
        for name, address in self.context['addresses'].items():
            env[f'DEMO_{name}'] = address
        env['DEMO_APPROVER'] = self.context['actors'][role]
        return env

    def reverts(self, signature, *args):
        artifact = local.gas.load_artifact('CCNFT')
        data = local.gas.calldata(artifact, signature.split(')(')[0] + ')', args)
        expected = '0x'
        if not signature.startswith('listTokensOnSale'):
            reason = ('ERC721: owner query for nonexistent token' if signature.startswith('ownerOf')
                      else 'Token does not exist')
            payload = reason.encode().hex()
            expected = '0x08c379a0' + f'{32:064x}{len(reason.encode()):064x}' + payload.ljust((len(payload)+63)//64*64, '0')
        try:
            self.rpc.call('eth_call', [{'to': self.context['addresses']['CCNFT'], 'data': data}, 'latest'])
        except RPCError as error:
            self.expect(f'revert ABI: {signature}', error.data, expected)
        else:
            self.expect(f'revert required: {signature}', False, True)

    def identity(self):
        self.expect('Sepolia chain', int(self.rpc.call('eth_chainId', []), 16), CHAIN)
        self.expect('explicit public profile', self.context.get('profile'), 'sepolia')
        self.expect('stored chain', self.context.get('chain_id'), CHAIN)
        expected = {role: self.env[f'SEPOLIA_{role.upper()}_ADDRESS'] for role in ROLES}
        self.expect('same five actors', self.context['actors'], expected)
        self.expect('five distinct actors', len(set(expected.values())), 5)
        for role, address in expected.items():
            self.expect(f'{role}: EOA', self.rpc.call('eth_getCode', [address, 'latest']), '0x')

    def preflight(self, recovery_tx=None):
        self.identity()
        for binary in ('forge', 'cast', 'anvil'):
            _, version = self.command([f'.tools/bin/{binary}', '--version'])
            self.expect(f'{binary} version', 'Version: 1.4.4' in version, True)
        revisions = {'openzeppelin-contracts': 'a5445b0afb8b350417b6e6ab3160554967bc151f',
                     'forge-std': '77041d2ce690e692d6e03cc812b57d1ddaa4d505'}
        for name, revision in revisions.items():
            _, value = self.command(['git', '-C', f'lib/{name}', 'rev-parse', 'HEAD'])
            self.expect(f'{name}: revision', value, revision)
            _, changes = self.command(['git', '-C', f'lib/{name}', 'status', '--porcelain'])
            self.expect(f'{name}: clean', changes, '')
        self.command(['.tools/bin/forge', 'build', '--color', 'never'])
        for name in ('BUSD', 'CCNFT'):
            local.gas.load_artifact(name)
        # Identity ejecuta actors() en Solidity y compara las cinco claves con las cinco direcciones.
        self.command(['.tools/bin/forge', 'script', 'script/Identity.s.sol:Identity',
                      '--rpc-url', 'sepolia', '--color', 'never'])
        current_hashes = local.source_hashes()
        if recovery_tx:
            self.recover_failed_deploy(recovery_tx, current_hashes)
        elif 'source_sha256' in self.context:
            self.check_source_version(current_hashes)
        self.context['source_sha256'] = current_hashes
        # Reserva inicial orientativa basada en el recorrido real de fase 6; cada etapa se simula de nuevo.
        historical = json.loads((ROOT / 'docs/evidence/local-demo-complete-2026-11-15/run-1/result.json').read_text())
        totals = dict.fromkeys(ROLES, 0)
        for stage in historical['stages']:
            role = local.STAGES[stage['name']][2]
            totals[role] += sum(int(tx['receipt']['gasUsed'], 16) for tx in stage['transactions'])
        self.report['fee_estimate'] = estimate_fees(self.rpc)
        price = self.report['fee_estimate']['max_fee_wei']
        self.report['eth_budget'] = {role: {'gas_local_reference': units,
            'suggested_wei': (units * 150 // 100) * price,
            'balance_wei': int(self.rpc.call('eth_getBalance', [self.context['actors'][role], 'latest']), 16)}
            for role, units in totals.items()}
        self.save()
        if not self.context['completed'] and not self.context.get('pending'):
            for role, budget in self.report['eth_budget'].items():
                self.expect(f'{role}: initial ETH reserve', budget['balance_wei'] >= budget['suggested_wei'], True)

    def check_source_version(self, current):
        previous = self.context['source_sha256']
        changed = {name for name in set(previous) | set(current) if previous.get(name) != current.get(name)}
        if not changed:
            return
        pending = self.context.get('pending', {})
        supported = (changed == set(FEE_FIX_PREVIOUS)
                     and all(previous.get(name) == value for name, value in FEE_FIX_PREVIOUS.items())
                     and not self.context['completed'] and not self.context['addresses']
                     and not self.context.get('history') and pending.get('name') == 'deploy')
        self.expect('supported fee-only recovery', supported, True)
        plan = pending['plan']
        self.expect('original two deployment intentions', len(plan), 2)
        sender = self.context['actors']['admin']
        for index, name in enumerate(('BUSD', 'CCNFT')):
            tx = plan[index]
            self.expect(f'{name}: preserved creation code', tx['input'],
                        local.gas.load_artifact(name)['bytecode']['object'].lower())
            self.expect(f'{name}: preserved sender', tx['from'], sender)
            self.expect(f'{name}: no target', tx['to'], None)
            self.expect(f'{name}: no native payment', tx['value'], 0)
        self.expect('consecutive deployment nonces', plan[1]['nonce'], plan[0]['nonce'] + 1)
        receipts = reconcile(self.rpc, plan, pending['start_block'])
        self.expect('fee-rejected deployment has no confirmed transactions', len(receipts), 0)
        for tag in ('latest', 'pending'):
            self.expect(f'fee recovery: {tag} nonce untouched',
                        int(self.rpc.call('eth_getTransactionCount', [sender, tag]), 16), plan[0]['nonce'])
        self.write(self.output / 'state-before-fee-fix.json', self.context)
        self.context.setdefault('source_upgrades', []).append({
            'reason': 'EIP-1559 max fee and priority fee correction before first accepted deployment',
            'checked_at': local.now(), 'previous_sha256': {name: previous[name] for name in sorted(changed)},
            'current_sha256': {name: current[name] for name in sorted(changed)},
            'confirmed_transactions': 0, 'preserved_nonces': [tx['nonce'] for tx in plan]})
        self.context['source_sha256'] = current
        self.checkpoint()

    def recover_failed_deploy(self, tx_hash, current):
        """Preparar, sin publicar, el reintento explícito de un CREATE fallido por límite de gas."""
        previous = self.context.get('source_sha256', {})
        if any(item['hash'] == tx_hash for item in self.context.get('failed_deployments', [])):
            self.expect('recovery already applied: same sources', current, previous)
            self.report['recovery_already_prepared'] = tx_hash
            return
        changed = {name for name in set(previous) | set(current) if previous.get(name) != current.get(name)}
        supported = (changed == set(RPC_GAS_FIX_PREVIOUS)
                     and all(previous.get(name) == value for name, value in RPC_GAS_FIX_PREVIOUS.items())
                     and not self.context['completed'] and not self.context['addresses']
                     and not self.context.get('history') and self.context.get('pending', {}).get('name') == 'deploy')
        self.expect('supported RPC gas recovery before successful deployment', supported, True)
        original = self.context['pending']
        plan = original['plan']
        self.expect('two original deployment intentions', len(plan), 2)
        sender = self.context['actors']['admin']
        for index, name in enumerate(('BUSD', 'CCNFT')):
            self.expect(f'{name}: unchanged CREATE intention',
                        {k: v for k, v in plan[index].items() if k != 'nonce'},
                        {'from': sender, 'to': None, 'input': local.gas.load_artifact(name)['bytecode']['object'].lower(), 'value': 0})
        self.expect('original consecutive nonces', plan[1]['nonce'], plan[0]['nonce'] + 1)
        tx = self.rpc.call('eth_getTransactionByHash', [tx_hash])
        receipt = self.rpc.call('eth_getTransactionReceipt', [tx_hash])
        self.expect('failed transaction and receipt available', bool(tx) and bool(receipt), True)
        self.expect('same failed transaction hash', tx['hash'].lower(), tx_hash)
        self.expect('same receipt transaction hash', receipt['transactionHash'].lower(), tx_hash)
        self.expect('failed first CREATE matches original plan', transaction(tx), plan[0])
        self.expect('receipt sender', receipt['from'].lower(), sender)
        self.expect('receipt is failed', int(receipt['status'], 16), 0)
        self.expect('failed CREATE has no logs', receipt['logs'], [])
        self.expect('failed CREATE has no recipient', receipt['to'], None)
        block = self.rpc.call('eth_getBlockByNumber', [receipt['blockNumber'], False])
        self.expect('failed receipt is canonical', receipt['blockHash'], block['hash'])
        head = int(self.rpc.call('eth_blockNumber', []), 16)
        self.expect('failed receipt has two confirmations', head - int(receipt['blockNumber'], 16) + 1 >= 2, True)
        limit = int(tx['gas'], 16)
        self.expect('failed transaction consumed its assigned gas', int(receipt['gasUsed'], 16), limit)
        failed_address = receipt['contractAddress']
        self.expect('failed CREATE address recorded', bool(failed_address), True)
        self.expect('failed deployment left no code', self.rpc.call('eth_getCode', [failed_address, 'latest']), '0x')
        nonce = plan[0]['nonce'] + 1
        for tag in ('latest', 'pending'):
            self.expect(f'only failed deployment consumed a nonce: {tag}',
                        int(self.rpc.call('eth_getTransactionCount', [sender, tag]), 16), nonce)
        # Simulación por RPC de ambas creaciones antes de preparar un nuevo plan.
        estimates = [int(self.rpc.call('eth_estimateGas', [{'from': sender, 'data': item['input']}]), 16) for item in plan]
        self.expect('RPC estimate exceeds failed gas limit', estimates[0] > limit, True)
        fees = estimate_fees(self.rpc)
        balance = int(self.rpc.call('eth_getBalance', [sender, 'latest']), 16)
        required = sum((units * 150 + 99) // 100 for units in estimates) * fees['max_fee_wei']
        self.expect('ETH for both recovered deployments', balance >= required, True)
        self.write(self.output / 'state-before-gas-recovery.json', self.context)
        new_plan = deepcopy(plan)
        for index, item in enumerate(new_plan):
            item['nonce'] = nonce + index
        self.context.setdefault('failed_deployments', []).append({
            'hash': tx_hash, 'receipt': receipt, 'transaction': tx, 'original_pending': deepcopy(original),
            'reason': 'First CREATE failed after consuming all assigned gas; prepare explicit RPC gas retry',
            'checked_at': local.now(), 'rpc_gas_estimates': estimates, 'new_nonces': [item['nonce'] for item in new_plan]})
        self.context['pending'] = {'name': 'deploy', 'plan': new_plan, 'start_block': head, 'transactions': [],
                                   'recovered_from': tx_hash}
        self.context.setdefault('source_upgrades', []).append({
            'reason': 'Use RPC gas estimation for broadcast after failed first CREATE',
            'checked_at': local.now(), 'failed_transaction': tx_hash,
            'previous_sha256': {name: previous[name] for name in sorted(changed)},
            'current_sha256': {name: current[name] for name in sorted(changed)}})
        self.context['source_sha256'] = current
        self.checkpoint()

    def script(self, filename, target, role, broadcast=False, extra=None):
        env = self.environment(role)
        env.update(extra or {})
        args = ['.tools/bin/forge', 'script', f'script/{filename}:{target}', '--rpc-url', 'sepolia',
                '--sender', self.context['actors'][role], '--slow', '--non-interactive', '--color', 'never']
        if broadcast:
            maximum, priority = int(env['ETH_GAS_PRICE']), int(env['ETH_PRIORITY_GAS_PRICE'])
            if maximum < priority or min(maximum, priority) < 0:
                raise ValueError('Comisiones EIP-1559 inconsistentes; no publicar.')
            # Fijar ambos valores: Forge no debe elegir una propina por encima del máximo presupuestado.
            # En Forge 1.4.4 skip-simulation fuerza eth_estimateGas antes de firmar/enviar.
            # La etapa completa ya se simuló; Publish conserva sus guardas y ejecuta una sola transacción.
            args += ['--broadcast', '--skip-simulation', '--gas-estimate-multiplier', '150',
                     '--with-gas-price', str(maximum), '--priority-gas-price', str(priority)]
        self.command(args, env=env)
        folder = self.raw / filename / str(CHAIN)
        path = folder / ('run-latest.json' if broadcast else 'dry-run/run-latest.json')
        if not path.exists():
            raise RuntimeError('Forge no guardó el plan esperado; no publicar.')
        return json.loads(path.read_text())

    def confirmed(self, pending):
        deadline = time.monotonic() + 120
        while True:
            try:
                return reconcile(self.rpc, pending['plan'], pending['start_block'])
            except RuntimeError as error:
                if isinstance(error, ReconciliationError):
                    pending['transactions'] = error.transactions
                    self.checkpoint()
                waiting = str(error).startswith(('Nonce pendiente:', 'Confirmaciones insuficientes;'))
                if not waiting or time.monotonic() >= deadline:
                    raise
                print('Esperando recibos y dos confirmaciones en Sepolia…', flush=True)
                time.sleep(12)

    def stage(self, name):
        self.identity()
        # Revalidar recibos históricos antes de publicar una etapa posterior, incluida una posible reorganización.
        for history in self.context.get('history', []):
            reconcile(self.rpc, history['plan'], history['start_block'])
        completed = self.context['completed']
        if name in completed:
            if name != completed[-1]:
                raise ValueError('Etapa ya confirmada; continuar por la próxima etapa.')
            self.audit()
            return
        self.expect('stage order', name, list(local.STAGES)[len(completed)] if len(completed) < len(local.STAGES) else 'done')
        filename, target, role, count = local.STAGES[name]
        if name == 'configure':
            self.expect('both contracts verified before configuration', sorted(self.context.get('verified', {})), ['BUSD', 'CCNFT'])
        pending = self.context.get('pending')
        if pending:
            self.expect('same interrupted stage', pending['name'], name)
        else:
            if completed:
                self.audit()
            # Sin --broadcast: Foundry simula la etapa completa y genera las transacciones sin firmarlas en disco.
            data = self.script(filename, target, role)
            plan = [transaction(tx) for tx in data['transactions']]
            self.expect('simulation transaction count', len(plan), count)
            nonce = int(self.rpc.call('eth_getTransactionCount', [self.context['actors'][role], 'latest']), 16)
            for i, tx in enumerate(plan):
                self.expect('planned sender', tx['from'], self.context['actors'][role])
                self.expect('planned nonce', tx['nonce'], nonce + i)
                self.expect('no native payment', tx['value'], 0)
            gas_units = sum(int(raw['transaction']['gas'], 16) if isinstance(raw['transaction']['gas'], str)
                            else raw['transaction']['gas'] for raw in data['transactions'])
            cap = estimate_fees(self.rpc)['max_fee_wei']
            balance = int(self.rpc.call('eth_getBalance', [self.context['actors'][role], 'latest']), 16)
            self.expect('ETH for complete simulated stage', balance >= gas_units * cap * 150 // 100, True)
            pending = {'name': name, 'plan': plan, 'start_block': int(self.rpc.call('eth_blockNumber', []), 16),
                       'transactions': []}
            self.context['pending'] = pending
            # Guardar la intención antes del primer envío, incluso para los dos CREATE.
            self.checkpoint()
        while True:
            receipts = self.confirmed(pending)
            pending['transactions'] = receipts
            if name == 'deploy':
                for contract, tx in zip(('BUSD', 'CCNFT'), receipts):
                    self.context['addresses'][contract] = tx['receipt']['contractAddress'].lower()
            self.checkpoint()
            if len(receipts) == count:
                break
            tx = pending['plan'][len(receipts)]
            sender = tx['from']
            self.expect('no pending nonce', int(self.rpc.call('eth_getTransactionCount', [sender, 'pending']), 16), tx['nonce'])
            estimate_tx = {key: tx[key] for key in ('from', 'to', 'input') if tx[key] is not None}
            estimate = int(self.rpc.call('eth_estimateGas', [estimate_tx]), 16)
            fees = estimate_fees(self.rpc)
            price = fees['max_fee_wei']
            required = (estimate * 150 // 100) * price
            balance = int(self.rpc.call('eth_getBalance', [sender, 'latest']), 16)
            pending['gas_estimate'] = dict(fees, units=estimate, required_wei=required, balance_wei=balance)
            self.checkpoint()
            self.expect('ETH for simulated transaction', balance >= required, True)
            kind = 1 + len(receipts) if name == 'deploy' else 0
            try:
                self.script('Publish.s.sol', 'Publish', role, broadcast=True, extra={
                    'DEMO_TX_KIND': str(kind), 'DEMO_TX_NONCE': str(tx['nonce']), 'DEMO_TX_DATA': tx['input'],
                    'DEMO_TX_TO': tx['to'] or '0x0000000000000000000000000000000000000000',
                    'ETH_GAS_PRICE': str(price), 'ETH_PRIORITY_GAS_PRICE': str(fees['max_priority_fee_wei'])})
            except Exception:
                # Guardar también un recibo fallido si Forge termina antes de escribirlo en su broadcast.
                try:
                    pending['transactions'] = reconcile(self.rpc, pending['plan'], pending['start_block'])
                except ReconciliationError as error:
                    pending['transactions'] = error.transactions
                except Exception:
                    pass  # La intención anterior se conserva si la RPC tampoco responde.
                self.checkpoint()
                raise
            # Se requieren dos confirmaciones. Si aún falta la segunda, se detiene sin reenviar.
        before = deepcopy(self.context)
        pending['before_verification'] = {key: deepcopy(self.context[key])
            for key in ('balances', 'allowances', 'baseline', 'sold_id', 'kept_id') if key in self.context}
        try:
            self.verify(name)
        except Exception:
            self.context = before
            self.checkpoint()
            raise
        record = deepcopy(pending)
        record['status'] = 'passed'
        self.context.setdefault('history', []).append(record)
        self.context['completed'].append(name)
        del self.context['pending']
        self.checkpoint()
        print(f'{name}: confirmado y verificado', flush=True)

    def audit(self):
        if self.context.get('pending'):
            pending = self.context['pending']
            pending['transactions'] = reconcile(self.rpc, pending['plan'], pending['start_block'])
            self.checkpoint()
            if len(pending['transactions']) == len(pending['plan']):
                self.stage(pending['name'])
            return
        for stage in self.context.get('history', []):
            reconcile(self.rpc, stage['plan'], stage['start_block'])
        if self.context['completed']:
            last = self.context['completed'][-1]
            # verify modela el cambio desde la etapa previa; reconstruirla para consultas repetidas.
            current = deepcopy(self.context)
            previous = self.context['history'][-1].get('before_verification')
            if previous:
                self.context.update(previous)
            else:
                # Reutilizar balances anteriores conservados en el historial.
                history = self.context['history']
                if len(history) > 1:
                    self.context.update(deepcopy(history[-2]['after_verification']))
            try:
                self.verify(last)
            finally:
                self.context = current
            self.checkpoint()

    def verify(self, stage):
        super().verify(stage)
        snapshot = {
            key: deepcopy(self.context[key]) for key in ('balances', 'allowances', 'baseline', 'sold_id', 'kept_id')
            if key in self.context}
        if self.context.get('pending'):
            self.context['pending']['after_verification'] = snapshot

    def verify_contracts(self):
        if 'deploy' not in self.context['completed'] or self.context.get('pending'):
            raise ValueError('Completar y reconciliar deploy antes de verificar.')
        for name, address in self.context['addresses'].items():
            self.command(['.tools/bin/forge', 'verify-contract', address, f'src/{name}.sol:{name}',
                          '--chain', str(CHAIN), '--verifier', 'etherscan', '--watch',
                          '--compiler-version', 'v0.8.19+commit.7dd6d404', '--num-of-optimizations', '200',
                          '--evm-version', 'paris', '--verifier-url', 'https://api.etherscan.io/v2/api?chainid=11155111'])
            query = urllib.parse.urlencode({'chainid': CHAIN, 'module': 'contract', 'action': 'getsourcecode',
                                            'address': address, 'apikey': self.env['ETHERSCAN_API_KEY']})
            try:
                with urllib.request.urlopen('https://api.etherscan.io/v2/api?' + query, timeout=45) as response:
                    result = json.load(response)
            except Exception:
                raise RuntimeError('Etherscan no respondió; repetir verificación sin desplegar de nuevo.') from None
            self.expect('Etherscan status', result.get('status'), '1')
            source = result['result'][0]
            for key, expected in {'ContractName': name, 'CompilerVersion': 'v0.8.19+commit.7dd6d404',
                                  'OptimizationUsed': '1', 'Runs': '200', 'EVMVersion': 'paris',
                                  'ConstructorArguments': ''}.items():
                self.expect(f'{name}: {key}', source.get(key), expected)
            self.expect(f'{name}: source verified', bool(source.get('SourceCode')) and source.get('ABI') != 'Contract source code not verified', True)
            self.write(self.output / f'{name}-etherscan.json', result)
            self.context.setdefault('verified', {})[name] = {'address': address, 'checked_at': local.now(),
                'url': f'https://sepolia.etherscan.io/address/{address}#code'}
            self.checkpoint()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--stage', choices=[*local.STAGES, 'doctor', 'verify', 'reconcile', 'check', 'demo', 'recover-deploy'], required=True)
    parser.add_argument('--state', type=Path, default=ROOT / '.tools/sepolia/state.json')
    parser.add_argument('--failed-tx', help='Hash público del primer CREATE fallido; solo para recover-deploy')
    args = parser.parse_args()
    if args.stage == 'recover-deploy':
        if not args.failed_tx or not re.fullmatch(r'0x[0-9a-fA-F]{64}', args.failed_tx):
            parser.error('recover-deploy requiere --failed-tx con un hash de transacción válido.')
        args.failed_tx = args.failed_tx.lower()
    elif args.failed_tx:
        parser.error('--failed-tx solo corresponde a recover-deploy.')
    output = ROOT / '.tools/sepolia' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True, mode=0o700)
    instance = None
    try:
        args.state.parent.mkdir(parents=True, exist_ok=True)
        # Impide dos publicaciones simultáneas del mismo estado.
        with args.state.with_suffix('.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            env = read_environment()
            instance = Sepolia(output, args.state, env)
            instance.preflight(recovery_tx=args.failed_tx)
            if args.stage in ('doctor', 'recover-deploy'):
                pass
            elif args.stage == 'verify':
                instance.verify_contracts()
            elif args.stage in ('reconcile', 'check'):
                instance.audit()
                if args.stage == 'check':
                    instance.expect('full public journey', instance.context['completed'], list(local.STAGES))
                    instance.expect('two verified contracts', sorted(instance.context.get('verified', {})), ['BUSD', 'CCNFT'])
            elif args.stage == 'demo':
                while len(instance.context['completed']) < len(local.STAGES):
                    name = list(local.STAGES)[len(instance.context['completed'])]
                    if name == 'configure':
                        instance.verify_contracts()
                    instance.stage(name)
                instance.audit()
            else:
                instance.stage(args.stage)
            instance.report['status'] = 'passed'
            instance.report['finished_at'] = local.now()
            instance.save()
    except Exception as error:
        message = instance.redact(str(error)) if instance else str(error)
        if instance:
            instance.report.update(status='failed', error=message, finished_at=local.now())
            instance.save()
        else:
            (output / 'result.json').write_text(json.dumps({'status': 'blocked', 'error': message}, indent=2) + '\n')
        print(f'Sepolia: {message} Evidencia: {output}', file=sys.stderr)
        return 1
    print(f'Sepolia: controles aprobados. Evidencia: {output}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
