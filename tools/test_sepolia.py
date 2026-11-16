"""Guardas del perfil público, reconciliación tras interrupciones y filtrado de evidencia."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location('sepolia', Path(__file__).with_name('sepolia.py'))
public = importlib.util.module_from_spec(spec)
spec.loader.exec_module(public)


def environment():
    env = {'SEPOLIA_RPC_URL': 'https://rpc.example/v2/credential-1234567890?token=rpc-secret',
           'ETHERSCAN_API_KEY': 'etherscan-secret'}
    for i, role in enumerate(public.ROLES, 1):
        env[f'SEPOLIA_{role.upper()}_ADDRESS'] = f'0x{i:040x}'
        env[f'SEPOLIA_{role.upper()}_PRIVATE_KEY'] = f'0x{2**240+i:064x}'
    return env


class PublicTest(unittest.TestCase):
    def test_environment_is_literal_and_requires_every_credential(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            env = environment()
            path.write_text('\n'.join(f'{key}={value}' for key, value in env.items()))
            self.assertEqual(public.read_environment(path), env)
            path.write_text('SEPOLIA_RPC_URL=$(touch /tmp/never-execute-this)')
            with self.assertRaisesRegex(ValueError, 'Variables pendientes:'):
                public.read_environment(path)
            for key in env:
                bad = dict(env, **{key: ''})
                path.write_text('\n'.join(f'{k}={v}' for k, v in bad.items()))
                with self.subTest(key=key), self.assertRaises(ValueError):
                    public.read_environment(path)

    def test_duplicate_accounts_bad_key_and_non_https_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ, {}, clear=True):
            path = Path(directory) / '.env'
            env = environment()
            for changes in ({'SEPOLIA_B_ADDRESS': env['SEPOLIA_A_ADDRESS']},
                            {'SEPOLIA_ADMIN_PRIVATE_KEY': '0x' + '0'*64},
                            {'SEPOLIA_ADMIN_PRIVATE_KEY': hex(public.CURVE_ORDER)},
                            {'SEPOLIA_A_ADDRESS': 'invalid'}, {'SEPOLIA_RPC_URL': 'http://rpc.example'}):
                path.write_text('\n'.join(f'{k}={v}' for k, v in dict(env, **changes).items()))
                with self.subTest(changes=changes), self.assertRaises(ValueError):
                    public.read_environment(path)

    def test_wrong_network_rejected_before_any_script(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.rpc = MagicMock()
            runner.rpc.call.return_value = '0x1'
            runner.command = MagicMock()
            with self.assertRaises(ValueError):
                runner.preflight()
            runner.command.assert_not_called()

    def test_logs_and_reports_exclude_rpc_api_and_all_key_representations(self):
        env = environment()
        key = env['SEPOLIA_A_PRIVATE_KEY']
        message = ' '.join([env['SEPOLIA_RPC_URL'], env['ETHERSCAN_API_KEY'], key,
                            key[2:], str(int(key, 16)), 'credential-1234567890', 'rpc-secret'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', env)
            with patch.object(public.subprocess, 'run', return_value=MagicMock(
                    returncode=1, stdout=message, stderr=message)):
                with self.assertRaises(RuntimeError):
                    runner.command(['forge', 'script'])
            output = ''.join(path.read_text() for path in root.rglob('*.txt')) + (root / 'result.json').read_text()
            for secret in message.split():
                self.assertNotIn(secret, output)
            self.assertIn('[REDACTED]', output)
            child = runner.environment('a')
            self.assertEqual(child['DEMO_PROFILE'], 'sepolia')
            self.assertEqual(child['DEMO_SIGNING_KEY'], key)
            self.assertNotIn('--private-key', output)

    def test_unrelated_nonhex_private_variable_is_also_redacted_without_parse_error(self):
        env = dict(environment(), OTHER_PRIVATE_KEY='foreign-secret-value')
        self.assertEqual(public.Redactor(env)('error: foreign-secret-value'), 'error: [REDACTED]')

    def test_low_gas_price_with_high_priority_cannot_make_an_invalid_max_fee(self):
        rpc = MagicMock()
        rpc.call.side_effect = lambda method, args: {
            'eth_getBlockByNumber': {'baseFeePerGas': '0x19'},
            'eth_maxPriorityFeePerGas': hex(10**9), 'eth_gasPrice': '0x19'}[method]
        fees = public.estimate_fees(rpc)
        self.assertEqual(fees['max_priority_fee_wei'], 10**9)
        self.assertEqual(fees['max_fee_wei'], 10**9 + 50)
        self.assertGreaterEqual(fees['max_fee_wei'], fees['base_fee_wei'] + fees['max_priority_fee_wei'])

    def test_fee_estimate_handles_zero_and_rejects_invalid_rpc_values(self):
        rpc = MagicMock()
        for base, priority, suggested in ((0, 0, 0), (10, 3, 200)):
            rpc.call.side_effect = lambda method, args: {
                'eth_getBlockByNumber': {'baseFeePerGas': hex(base)},
                'eth_maxPriorityFeePerGas': hex(priority), 'eth_gasPrice': hex(suggested)}[method]
            fees = public.estimate_fees(rpc)
            self.assertEqual(fees['max_fee_wei'], max(2*base + priority, 2*suggested, 1))
        rpc.call.side_effect = lambda method, args: {
            'eth_getBlockByNumber': {'baseFeePerGas': '0x1'},
            'eth_maxPriorityFeePerGas': '-0x1', 'eth_gasPrice': '0x1'}[method]
        with self.assertRaises(ValueError):
            public.estimate_fees(rpc)

    def test_broadcast_explicitly_pins_both_fees_without_signing_keys_in_arguments(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.command = MagicMock()
            path = runner.raw / 'Publish.s.sol/11155111/run-latest.json'
            path.parent.mkdir(parents=True)
            path.write_text('{"transactions": []}')
            runner.script('Publish.s.sol', 'Publish', 'admin', broadcast=True,
                          extra={'ETH_GAS_PRICE': '1000000050', 'ETH_PRIORITY_GAS_PRICE': '1000000000'})
            args = runner.command.call_args.args[0]
            self.assertIn('--skip-simulation', args)
            self.assertEqual(args[args.index('--gas-estimate-multiplier')+1], '150')
            self.assertEqual(args[args.index('--with-gas-price')+1], '1000000050')
            self.assertEqual(args[args.index('--priority-gas-price')+1], '1000000000')
            self.assertNotIn(environment()['SEPOLIA_ADMIN_PRIVATE_KEY'], args)
            runner.command.reset_mock()
            with self.assertRaisesRegex(ValueError, 'inconsistentes'):
                runner.script('Publish.s.sol', 'Publish', 'admin', broadcast=True,
                              extra={'ETH_GAS_PRICE': '50', 'ETH_PRIORITY_GAS_PRICE': '1000000000'})
            runner.command.assert_not_called()

    def fee_recovery(self, runner):
        previous = dict(public.FEE_FIX_PREVIOUS, **{'src/CCNFT.sol': 'unchanged'})
        current = dict(previous, **{name: 'new-version' for name in public.FEE_FIX_PREVIOUS})
        runner.context['source_sha256'] = previous
        sender = runner.context['actors']['admin']
        runner.context['pending'] = {'name': 'deploy', 'start_block': 10, 'transactions': [], 'plan': [
            {'from': sender, 'to': None, 'input': '0x1234', 'nonce': nonce, 'value': 0} for nonce in (4, 5)]}
        runner.rpc = MagicMock()
        runner.rpc.call.return_value = '0x4'
        return previous, current

    def test_fee_recovery_preserves_intent_and_backs_up_state_after_nonce_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            previous, current = self.fee_recovery(runner)
            before = json.loads(json.dumps(runner.context))
            with patch.object(public, 'reconcile', return_value=[]) as reconcile, \
                    patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                runner.check_source_version(current)
            reconcile.assert_called_once()
            self.assertEqual(runner.context['pending'], before['pending'])
            self.assertEqual(runner.context['source_sha256'], current)
            self.assertEqual(json.loads((root / 'state-before-fee-fix.json').read_text()), before)
            self.assertEqual(runner.context['source_upgrades'][0]['preserved_nonces'], [4, 5])

    def test_fee_recovery_rejects_unrelated_changes_or_unknown_previous_runner(self):
        for mutation in ({'src/CCNFT.sol': 'modified'}, {'tools/unknown.py': 'new-file'}):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                runner = public.Sepolia(root, root / 'state.json', environment())
                previous, current = self.fee_recovery(runner)
                current.update(mutation)
                with self.assertRaisesRegex(ValueError, 'supported fee-only recovery'):
                    runner.check_source_version(current)
                self.assertEqual(runner.context['source_sha256'], previous)
                runner.rpc.call.assert_not_called()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            previous, current = self.fee_recovery(runner)
            previous['tools/sepolia.py'] = 'unknown-version'
            with self.assertRaisesRegex(ValueError, 'supported fee-only recovery'):
                runner.check_source_version(current)
            runner.rpc.call.assert_not_called()

    def test_fee_recovery_rejects_confirmed_or_pending_nonce_without_updating_state(self):
        for confirmed, nonce in (([{'hash': '0xconfirmed'}], '0x5'), ([], '0x5')):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                runner = public.Sepolia(root, root / 'state.json', environment())
                previous, current = self.fee_recovery(runner)
                runner.rpc.call.return_value = nonce
                with patch.object(public, 'reconcile', return_value=confirmed), \
                        patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                    with self.assertRaises(ValueError):
                        runner.check_source_version(current)
                self.assertEqual(runner.context['source_sha256'], previous)
                self.assertNotIn('source_upgrades', runner.context)
                self.assertFalse((root / 'state-before-fee-fix.json').exists())

    def test_pending_nonce_during_fee_recovery_stops_before_state_update(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            previous, current = self.fee_recovery(runner)
            with patch.object(public, 'reconcile', side_effect=RuntimeError('Nonce pendiente')), \
                    patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                with self.assertRaisesRegex(RuntimeError, 'Nonce pendiente'):
                    runner.check_source_version(current)
            self.assertEqual(runner.context['source_sha256'], previous)
            self.assertFalse((root / 'state.json').exists())

    def gas_recovery(self, runner):
        previous = dict(public.RPC_GAS_FIX_PREVIOUS, **{'src/CCNFT.sol': 'unchanged'})
        current = dict(previous, **{name: 'new-version' for name in public.RPC_GAS_FIX_PREVIOUS})
        runner.context['source_sha256'] = previous
        sender = runner.context['actors']['admin']
        tx_hash = '0x' + 'a'*64
        runner.context['pending'] = {'name': 'deploy', 'start_block': 10, 'transactions': [], 'plan': [
            {'from': sender, 'to': None, 'input': '0x1234', 'nonce': nonce, 'value': 0} for nonce in (4, 5)]}
        tx = dict(runner.context['pending']['plan'][0], nonce='0x4', value='0x0', gas='0xcb588', hash=tx_hash)
        receipt = {'transactionHash': tx_hash, 'from': sender, 'to': None, 'status': '0x0',
                   'gasUsed': '0xcb588', 'logs': [], 'blockHash': '0xcanonical', 'blockNumber': '0xb',
                   'contractAddress': '0x' + 'f'*40}
        control = {'code': '0x', 'latest_nonce': 5, 'pending_nonce': 5, 'estimate': 4165136,
                   'balance': 10**18, 'head': 13, 'tx': tx, 'receipt': receipt}
        def call(method, args):
            if method == 'eth_getTransactionByHash':
                return control['tx']
            if method == 'eth_getTransactionReceipt':
                return control['receipt']
            if method == 'eth_getBlockByNumber':
                return {'baseFeePerGas': '0x15'} if args[0] == 'latest' else {'hash': '0xcanonical'}
            if method == 'eth_getTransactionCount':
                return hex(control[args[1] + '_nonce'])
            return {'eth_blockNumber': hex(control['head']), 'eth_getCode': control['code'],
                    'eth_estimateGas': hex(control['estimate']), 'eth_getBalance': hex(control['balance']),
                    'eth_maxPriorityFeePerGas': '0x6', 'eth_gasPrice': '0x1b'}[method]
        runner.rpc = MagicMock()
        runner.rpc.call.side_effect = call
        return previous, current, tx_hash, control

    def test_gas_recovery_prepares_new_nonces_and_preserves_failed_receipt_without_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            previous, current, tx_hash, control = self.gas_recovery(runner)
            before = json.loads(json.dumps(runner.context))
            runner.command = MagicMock()
            with patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                runner.recover_failed_deploy(tx_hash, current)
            runner.command.assert_not_called()
            self.assertEqual(runner.context['completed'], [])
            self.assertEqual(runner.context['addresses'], {})
            self.assertEqual([item['nonce'] for item in runner.context['pending']['plan']], [5, 6])
            self.assertEqual(runner.context['failed_deployments'][0]['original_pending'], before['pending'])
            self.assertEqual(runner.context['failed_deployments'][0]['receipt'], control['receipt'])
            self.assertEqual(json.loads((root / 'state-before-gas-recovery.json').read_text()), before)
            self.assertEqual(runner.context['pending']['recovered_from'], tx_hash)
            self.assertEqual(runner.context['source_sha256'], current)
            runner.rpc.call.reset_mock()
            runner.recover_failed_deploy(tx_hash, current)
            runner.rpc.call.assert_not_called()
            self.assertEqual(len(runner.context['failed_deployments']), 1)
            self.assertEqual([item['nonce'] for item in runner.context['pending']['plan']], [5, 6])

    def test_gas_recovery_rejects_successful_missing_or_reorganized_receipt(self):
        for mutation in ('success', 'missing', 'reorganized', 'wrong_sender', 'wrong_hash', 'unconfirmed'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                runner = public.Sepolia(root, root / 'state.json', environment())
                previous, current, tx_hash, control = self.gas_recovery(runner)
                if mutation == 'success': control['receipt']['status'] = '0x1'
                if mutation == 'missing': control['receipt'] = None
                if mutation == 'reorganized': control['receipt']['blockHash'] = '0xorphaned'
                if mutation == 'wrong_sender': control['receipt']['from'] = '0xother'
                if mutation == 'wrong_hash': control['receipt']['transactionHash'] = '0xother'
                if mutation == 'unconfirmed': control['head'] = 11
                with patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        runner.recover_failed_deploy(tx_hash, current)
                self.assertEqual(runner.context['source_sha256'], previous)
                self.assertNotIn('failed_deployments', runner.context)
                self.assertFalse((root / 'state-before-gas-recovery.json').exists())

    def test_gas_recovery_rejects_occupied_nonce_code_logs_and_unexplained_failure(self):
        for mutation in ('pending_nonce', 'latest_nonce', 'code', 'logs', 'unused_gas', 'estimate', 'balance', 'input'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                runner = public.Sepolia(root, root / 'state.json', environment())
                previous, current, tx_hash, control = self.gas_recovery(runner)
                if mutation.endswith('_nonce'): control[mutation] = 6
                if mutation == 'code': control['code'] = '0x6000'
                if mutation == 'logs': control['receipt']['logs'] = [{'data': '0x'}]
                if mutation == 'unused_gas': control['receipt']['gasUsed'] = '0x1234'
                if mutation == 'estimate': control['estimate'] = 640000
                if mutation == 'balance': control['balance'] = 0
                if mutation == 'input': control['tx']['input'] = '0xother'
                with patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                    with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                        runner.recover_failed_deploy(tx_hash, current)
                self.assertEqual(runner.context['source_sha256'], previous)
                self.assertNotIn('failed_deployments', runner.context)
                self.assertFalse((root / 'state.json').exists())

    def test_gas_recovery_rejects_unrelated_source_changes_or_completed_business_stages(self):
        for mutation in ('source', 'completed', 'addresses', 'other_stage'):
            with tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                runner = public.Sepolia(root, root / 'state.json', environment())
                previous, current, tx_hash, control = self.gas_recovery(runner)
                if mutation == 'source': current['src/CCNFT.sol'] = 'modified'
                if mutation == 'completed': runner.context['completed'] = ['deploy']
                if mutation == 'addresses': runner.context['addresses']['BUSD'] = '0xdeployed'
                if mutation == 'other_stage': runner.context['pending']['name'] = 'buy'
                with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                    runner.recover_failed_deploy(tx_hash, current)
                runner.rpc.call.assert_not_called()
                self.assertEqual(runner.context['source_sha256'], previous)

    def test_gas_recovery_does_not_change_state_when_rpc_estimation_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            previous, current, tx_hash, control = self.gas_recovery(runner)
            original = runner.rpc.call.side_effect
            def call(method, args):
                if method == 'eth_estimateGas':
                    raise RuntimeError('RPC estimate failed')
                return original(method, args)
            runner.rpc.call.side_effect = call
            with patch.object(public.local.gas, 'load_artifact', return_value={'bytecode': {'object': '0x1234'}}):
                with self.assertRaisesRegex(RuntimeError, 'RPC estimate failed'):
                    runner.recover_failed_deploy(tx_hash, current)
            self.assertEqual(runner.context['source_sha256'], previous)
            self.assertFalse((root / 'state.json').exists())

    def test_failed_broadcast_collects_failed_receipt_before_returning_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.identity = MagicMock()
            runner.context['pending'] = {'name': 'deploy', 'plan': [{'from': '0xadmin', 'nonce': 4,
                'to': None, 'input': '0x1234', 'value': 0}], 'start_block': 10}
            runner.confirmed = MagicMock(return_value=[])
            runner.rpc = MagicMock()
            runner.rpc.call.side_effect = lambda method, args: {
                'eth_getTransactionCount': '0x4', 'eth_estimateGas': hex(4165136),
                'eth_getBlockByNumber': {'baseFeePerGas': '0x15'}, 'eth_maxPriorityFeePerGas': '0x6',
                'eth_gasPrice': '0x1b', 'eth_getBalance': hex(10**18)}[method]
            runner.script = MagicMock(side_effect=RuntimeError('broadcast failed'))
            observed = [{'hash': '0xfailed', 'receipt': {'status': '0x0'}}]
            with patch.object(public, 'reconcile', side_effect=public.ReconciliationError('failed receipt', observed)):
                with self.assertRaisesRegex(RuntimeError, 'broadcast failed'):
                    runner.stage('deploy')
            self.assertEqual(json.loads((root / 'state.json').read_text())['pending']['transactions'], observed)

    def test_transaction_normalizes_create_and_public_fixture(self):
        self.assertEqual(public.transaction({'transaction': {'from': '0xAB', 'to': None,
            'input': '0xCD', 'nonce': '0x2', 'value': '0x0'}}),
            {'from': '0xab', 'to': None, 'input': '0xcd', 'nonce': 2, 'value': 0})
        data = json.loads((public.ROOT / 'docs/evidence/local-demo-complete-2026-11-15/run-1/deploy-broadcast.json').read_text())
        self.assertEqual(len([public.transaction(tx) for tx in data['transactions']]), 2)

    def rpc(self, confirmed=1, pending=None, status='0x1', confirmations=2, mismatch=False):
        tx = {'from': '0xabc', 'to': '0xdef', 'input': '0x1234', 'nonce': '0x0', 'value': '0x0', 'hash': '0xhash'}
        plan = [public.transaction(tx)]
        receipt = {'from': '0xabc', 'status': status, 'blockHash': '0xblock', 'blockNumber': '0xb'}
        def call(method, args):
            if method == 'eth_blockNumber':
                return hex(10 + confirmations)
            if method == 'eth_getTransactionCount':
                return hex((pending if pending is not None else confirmed) if args[1] == 'pending' else confirmed)
            if method == 'eth_getBlockByNumber':
                return {'hash': '0xblock', 'transactions': [dict(tx, input='0x9999') if mismatch else tx]}
            if method == 'eth_getTransactionReceipt':
                return receipt
            raise AssertionError(method)
        rpc = MagicMock()
        rpc.call.side_effect = call
        return rpc, plan

    def test_interruption_before_hash_save_finds_confirmed_nonce(self):
        rpc, plan = self.rpc()
        receipts = public.reconcile(rpc, plan, 10)
        self.assertEqual(receipts[0]['hash'], '0xhash')
        self.assertTrue(receipts[0]['url'].endswith('/tx/0xhash'))

    def test_unsent_nonce_can_proceed_but_pending_cannot_repeat(self):
        rpc, plan = self.rpc(confirmed=0)
        self.assertEqual(public.reconcile(rpc, plan, 10), [])
        rpc, plan = self.rpc(confirmed=0, pending=1)
        with self.assertRaisesRegex(RuntimeError, 'Nonce pendiente'):
            public.reconcile(rpc, plan, 10)

    def test_failed_receipt_replacement_and_unconfirmed_are_rejected(self):
        for args, error in (({'status': '0x0'}, 'Recibo fallido'),
                            ({'mismatch': True}, 'otra transacción'),
                            ({'confirmations': 1}, 'Confirmaciones insuficientes')):
            rpc, plan = self.rpc(**args)
            with self.subTest(args=args), self.assertRaisesRegex(RuntimeError, error):
                public.reconcile(rpc, plan, 10)

    def test_completed_stage_is_audited_without_new_publication(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.context['completed'] = ['deploy']
            runner.identity = MagicMock()
            runner.audit = MagicMock()
            runner.script = MagicMock()
            runner.stage('deploy')
            runner.audit.assert_called_once()
            runner.script.assert_not_called()

    def test_configuration_requires_two_verified_contracts(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.context['completed'] = ['deploy']
            runner.identity = MagicMock()
            runner.script = MagicMock()
            with self.assertRaisesRegex(ValueError, 'both contracts verified'):
                runner.stage('configure')
            runner.script.assert_not_called()

    def test_failed_receipt_is_saved_for_diagnosis(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.rpc, plan = self.rpc(status='0x0')
            pending = {'name': 'buy', 'plan': plan, 'start_block': 10}
            runner.context['pending'] = pending
            with self.assertRaises(public.ReconciliationError):
                runner.confirmed(pending)
            state = json.loads((root / 'state.json').read_text())
            self.assertEqual(state['pending']['transactions'][0]['receipt']['status'], '0x0')

    def test_missing_receipt_and_reorganized_block_stop_reconciliation(self):
        for receipt in (None, {'blockHash': '0xorphaned'}):
            rpc, plan = self.rpc()
            original = rpc.call.side_effect
            rpc.call.side_effect = lambda method, args: receipt if method == 'eth_getTransactionReceipt' else original(method, args)
            with self.subTest(receipt=receipt), self.assertRaisesRegex(RuntimeError, 'Recibo ausente'):
                public.reconcile(rpc, plan, 10)

    def test_audit_restores_prior_balances_without_applying_delta_twice(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.context.update(completed=['deploy', 'configure', 'fund'], balances={'a': 1000},
                allowances={'a': 0}, history=[{'plan': [], 'start_block': 10,
                    'before_verification': {'balances': {'a': 0}, 'allowances': {'a': 0}}}])
            runner.rpc = MagicMock()
            runner.rpc.call.return_value = '0xc'
            def check(stage):
                self.assertEqual(stage, 'fund')
                self.assertEqual(runner.context['balances']['a'], 0)
                runner.context['balances']['a'] += 1000
            runner.verify = check
            runner.audit()
            self.assertEqual(runner.context['balances']['a'], 1000)

    def test_reverts_require_rpc_revert_data_and_reject_transport_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.context['addresses']['CCNFT'] = '0xnft'
            runner.rpc = MagicMock()
            for error, accepted in ((public.RPCError('eth_call', {'code': -32000, 'data': '0x'}), True),
                                    (public.RPCError('eth_call', {'code': 3, 'data': '0xdeadbeef'}), False),
                                    (RuntimeError('connection failed'), False)):
                runner.rpc.call.side_effect = error
                if accepted:
                    runner.reverts('listTokensOnSale(uint256)(uint256)', 0)
                else:
                    with self.assertRaises((ValueError, RuntimeError)):
                        runner.reverts('listTokensOnSale(uint256)(uint256)', 0)

    def test_etherscan_settings_are_checked_beyond_forge_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', environment())
            runner.context.update(completed=['deploy'], addresses={'BUSD': '0xbusd'})
            runner.command = MagicMock()
            source = {'ContractName': 'BUSD', 'CompilerVersion': 'v0.8.19+commit.7dd6d404',
                      'OptimizationUsed': '1', 'Runs': '200', 'EVMVersion': 'paris',
                      'ConstructorArguments': '', 'SourceCode': 'verified source', 'ABI': '[]'}
            response = MagicMock()
            response.__enter__.return_value = response
            with patch.object(public.urllib.request, 'urlopen', return_value=response), \
                    patch.object(public.json, 'load', return_value={'status': '1', 'result': [source]}):
                runner.verify_contracts()
                self.assertIn('BUSD', runner.context['verified'])
                source['Runs'] = '999'
                with self.assertRaisesRegex(ValueError, 'Runs'):
                    runner.verify_contracts()
            args = runner.command.call_args.args[0]
            self.assertNotIn(environment()['ETHERSCAN_API_KEY'], args)

    def test_partial_stage_continues_only_remaining_nonce(self):
        env = environment()
        rpc, plan = self.rpc()
        plan[0]['from'] = env['SEPOLIA_ADMIN_ADDRESS']
        plan[0]['to'] = None
        second = dict(plan[0], nonce=1, input='0x5678')
        first = {'hash': '0xfirst', 'receipt': {'contractAddress': '0x111'}}
        last = {'hash': '0xsecond', 'receipt': {'contractAddress': '0x222'}}
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', env)
            runner.context['pending'] = {'name': 'deploy', 'plan': plan + [second], 'start_block': 10}
            runner.identity = MagicMock()
            runner.confirmed = MagicMock(side_effect=[[first], [first, last]])
            runner.rpc = MagicMock()
            runner.rpc.call.side_effect = lambda method, args: {
                'eth_getTransactionCount': '0x1', 'eth_estimateGas': '0x100',
                'eth_gasPrice': '0x1', 'eth_maxPriorityFeePerGas': '0x1',
                'eth_getBlockByNumber': {'baseFeePerGas': '0x1'}, 'eth_getBalance': hex(10**18)}[method]
            runner.script = MagicMock()
            runner.verify = MagicMock()
            runner.stage('deploy')
            runner.script.assert_called_once()
            self.assertEqual(runner.script.call_args.kwargs['extra']['DEMO_TX_NONCE'], '1')
            self.assertEqual(runner.script.call_args.kwargs['extra']['DEMO_TX_KIND'], '2')
            self.assertEqual(runner.context['completed'], ['deploy'])
            self.assertNotIn('pending', runner.context)

    def test_partial_intent_survives_publication_exception(self):
        env = environment()
        rpc, plan = self.rpc()
        plan[0]['from'] = env['SEPOLIA_ADMIN_ADDRESS']
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runner = public.Sepolia(root, root / 'state.json', env)
            runner.context['pending'] = {'name': 'buy', 'plan': plan, 'start_block': 10}
            runner.context['completed'] = list(public.local.STAGES)[:7]
            runner.identity = MagicMock()
            runner.confirmed = MagicMock(return_value=[])
            runner.rpc = MagicMock()
            runner.rpc.call.side_effect = lambda method, args: {
                'eth_getTransactionCount': '0x0', 'eth_estimateGas': '0x100',
                'eth_gasPrice': '0x1', 'eth_maxPriorityFeePerGas': '0x1',
                'eth_getBlockByNumber': {'baseFeePerGas': '0x1'}, 'eth_getBalance': hex(10**18)}[method]
            runner.script = MagicMock(side_effect=RuntimeError('interrupted'))
            with self.assertRaisesRegex(RuntimeError, 'interrupted'):
                runner.stage('buy')
            state = json.loads((root / 'state.json').read_text())
            self.assertEqual(state['pending']['plan'], plan)
            self.assertNotIn('buy', state['completed'])


if __name__ == '__main__':
    unittest.main()
