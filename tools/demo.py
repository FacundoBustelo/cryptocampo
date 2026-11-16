#!/usr/bin/env python3
"""Publica scripts Solidity por etapas y verifica recibos/estado con Cast en Anvil."""

import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess
import sys
import time
from urllib.parse import urlparse
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gas_rpc", ROOT / "tools/measure-gas.py")
gas = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gas)
STAGES = {
    "deploy": ("Deploy.s.sol", "Deploy", "admin", 2),
    "configure": ("Configure.s.sol", "Configure", "admin", 11),
    "fund": ("Prepare.s.sol", "Fund", "admin", 3),
    "approve-a": ("Prepare.s.sol", "Approve", "a", 1),
    "approve-b": ("Prepare.s.sol", "Approve", "b", 1),
    "approve-funds": ("Prepare.s.sol", "Approve", "funds", 1),
    "enable": ("Prepare.s.sol", "Enable", "admin", 3),
    "buy": ("Operations.s.sol", "Buy", "a", 1),
    "list": ("Operations.s.sol", "List", "a", 1),
    "trade": ("Operations.s.sol", "Trade", "b", 1),
    "claim": ("Operations.s.sol", "Claim", "b", 1),
}


def now():
    return datetime.now(timezone.utc).isoformat()


def parameters():
    """Una sola fuente de parámetros económicos: DemoBase.sol."""
    source = (ROOT / "script/DemoBase.sol").read_text()
    values = {}
    for name, value in re.findall(r'public constant (\w+) = ([^;]+);', source):
        if value.startswith('"'):
            values[name] = json.loads(value)
        elif value.endswith(" ether"):
            values[name] = int(Decimal(value[:-6].replace("_", "")) * 10**18)
        else:
            values[name] = int(value.replace("_", ""))
    publication = json.loads((ROOT / "docs/ipfs-publication.json").read_text())
    if values["URI"] != publication["resources"]["metadata"]["uri"]:
        raise ValueError("La URI del script difiere de la publicación definitiva.")
    return values


def source_hashes():
    paths = [ROOT / "foundry.toml", ROOT / "Makefile", ROOT / "README.md"]
    for folder in ("src", "test", "script", "tools", "assets", ".github/workflows"):
        paths.extend(p for p in (ROOT / folder).rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)}


def loopback_url(value):
    url = urlparse(value)
    if (url.scheme != "http" or url.hostname != "127.0.0.1" or not url.port
            or url.username or url.password or url.path not in ("", "/") or url.query or url.fragment):
        raise ValueError("Usar http://127.0.0.1:PUERTO para esta demostración local.")
    return url.port


class Demo:
    def __init__(self, output):
        self.output = output
        self.report = {"schema_version": 1, "started_at": now(), "status": "running",
                       "source_sha256": source_hashes(), "commands": [], "checks": [], "stages": [],
                       "ci": {k: os.environ.get(k) for k in ("GITHUB_SHA", "GITHUB_RUN_ID", "GITHUB_RUN_ATTEMPT")}}
        self.context = {}
        self.rpc = None
        self.p = None
        self.save()

    def save(self):
        self.report["context"] = self.context
        (self.output / "result.json").write_text(json.dumps(self.report, indent=2, ensure_ascii=False) + "\n")

    def command(self, args, env=None, allow_failure=False):
        log = f"{len(self.report['commands']):03d}.txt"
        record = {"command": args, "log": log, "started_at": now()}
        self.report["commands"].append(record)
        self.save()
        with (self.output / log).open("w") as stream:
            try:
                result = subprocess.run(args, cwd=ROOT, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                        text=True, timeout=180)
                code = result.returncode
            except (OSError, subprocess.TimeoutExpired) as error:
                stream.write(f"{type(error).__name__}: {error}\n")
                code = 124 if isinstance(error, subprocess.TimeoutExpired) else 127
        record.update(exit_code=code, finished_at=now())
        self.save()
        text = (self.output / log).read_text()
        if code and not allow_failure:
            raise RuntimeError(f"Falló {args[0]} (exit {code}); ver {log}")
        return code, text.strip()

    def expect(self, name, actual, expected):
        self.report["checks"].append({"name": name, "actual": actual, "expected": expected,
                                      "status": "passed" if actual == expected else "failed"})
        self.save()
        if actual != expected:
            raise ValueError(f"{name}: {actual!r} != {expected!r}")

    def call(self, contract, signature, *args):
        _, text = self.command([".tools/bin/cast", "call", self.context["addresses"][contract], signature,
                                *map(str, args), "--rpc-url", self.context["rpc_url"]])
        result = signature.split(")(")[1][:-1]
        if result.startswith("uint") and "," not in result:
            return int(text.split()[0])
        if result == "bool":
            return text == "true"
        if result == "address":
            return text.lower()
        if result == "string":
            return json.loads(text)
        return text

    def reverts(self, signature, *args):
        code, text = self.command([".tools/bin/cast", "call", self.context["addresses"]["CCNFT"], signature,
                                   *map(str, args), "--rpc-url", self.context["rpc_url"]], allow_failure=True)
        if signature.startswith("listTokensOnSale"):
            # El getter público generado por Solidity 0.8.19 usa revert(0, 0)
            # al exceder el índice; no devuelve Panic(uint256).
            expected = "0x"
        else:
            reason = ("ERC721: owner query for nonexistent token" if signature.startswith("ownerOf")
                      else "Token does not exist")
            payload = reason.encode().hex()
            expected = "0x08c379a0" + f"{32:064x}{len(reason.encode()):064x}" + payload.ljust((len(payload) + 63) // 64 * 64, "0")
        data = re.search(r'\bdata:\s*"(0x[0-9a-fA-F]*)"', text)
        reverted = re.search(r"\berror code 3: execution reverted\b", text) is not None
        self.expect(f"reverts: {signature} {args}",
                    code != 0 and reverted and data is not None and data[1].lower() == expected, True)

    def identity(self):
        self.expect("chain ID", int(self.rpc.call("eth_chainId", []), 16), 31337)
        self.expect("node is Anvil", "anvil" in self.rpc.call("web3_clientVersion", []).lower(), True)
        self.expect("genesis", self.rpc.call("eth_getBlockByNumber", ["0x0", False])["hash"], self.context["genesis"])
        unlocked = [a.lower() for a in self.rpc.call("eth_accounts", [])]
        actors = list(self.context["actors"].values())
        self.expect("five distinct actors", len(set(actors)), 5)
        self.expect("unlocked nonzero EOAs", all(a in unlocked and int(a, 16) != 0
                    and self.rpc.call("eth_getCode", [a, "latest"]) == "0x" for a in actors), True)

    def stage(self, name):
        self.identity()
        completed = self.context["completed"]
        self.expect("stage order", name, list(STAGES)[len(completed)] if len(completed) < len(STAGES) else "done")
        filename, target, actor, count = STAGES[name]
        sender = self.context["actors"][actor]
        env = os.environ.copy()
        # Estas variables explícitas prevalecen sobre cualquier .env que lea Forge.
        env["FOUNDRY_DISABLE_NIGHTLY_WARNING"] = "1"
        env["DEMO_PROFILE"] = "anvil"
        for key, address in self.context["actors"].items():
            env[f"DEMO_{key.upper()}"] = address
        for key, address in self.context["addresses"].items():
            env[f"DEMO_{key.upper()}"] = address
        env["DEMO_APPROVER"] = sender
        record = {"name": name, "sender": sender, "status": "running", "transactions": []}
        self.report["stages"].append(record)
        self.save()
        command = [".tools/bin/forge", "script", f"script/{filename}:{target}", "--rpc-url", self.context["rpc_url"],
                   "--sender", sender, "--unlocked", "--broadcast", "--slow", "--non-interactive", "--color", "never"]
        try:
            self.command(command, env=env)
        finally:
            # Conservar también recibos parciales si Forge falla después de publicar.
            path = ROOT / "broadcast" / filename / "31337/run-latest.json"
            if path.exists():
                data = json.loads(path.read_text())
                # Solo transacciones de esta ejecución: el inicio registra el bloque previo.
                transactions = data.get("transactions", [])
                for tx in transactions:
                    receipt = self.rpc.call("eth_getTransactionReceipt", [tx["hash"]]) if tx.get("hash") else None
                    if receipt and int(receipt["blockNumber"], 16) > self.context["last_block"]:
                        record["transactions"].append({"hash": tx["hash"], "receipt": receipt,
                                                        "contract_name": tx.get("contractName")})
                (self.output / f"{name}-broadcast.json").write_text(json.dumps(data, indent=2) + "\n")
                self.save()
        self.expect(f"{name}: transaction count", len(record["transactions"]), count)
        for tx in record["transactions"]:
            receipt = tx["receipt"]
            self.expect(f"{name}: receipt {tx['hash']}", int(receipt["status"], 16), 1)
            self.expect(f"{name}: sender {tx['hash']}", receipt["from"].lower(), sender)
        if name == "deploy":
            for tx in record["transactions"]:
                contract = tx["contract_name"]
                self.expect("deployment contract", contract in ("BUSD", "CCNFT"), True)
                self.context["addresses"][contract] = tx["receipt"]["contractAddress"].lower()
            self.expect("two deployed contracts", len(self.context["addresses"]), 2)
        self.verify(name)
        self.context["last_block"] = int(self.rpc.call("eth_blockNumber", []), 16)
        completed.append(name)
        record["status"] = "passed"
        self.save()
        print(f"{name}: recibos y estado verificados", flush=True)

    def verify(self, stage):
        p, ctx = self.p, self.context
        a, addresses = ctx["actors"], ctx["addresses"]
        nft = lambda signature, *args: self.call("CCNFT", signature, *args)
        busd = lambda signature, *args: self.call("BUSD", signature, *args)
        self.expect("owner", nft("owner()(address)"), a["admin"])
        for contract in ("BUSD", "CCNFT"):
            artifact = gas.load_artifact(contract)
            self.expect(f"{contract} runtime bytecode", self.rpc.call("eth_getCode", [addresses[contract], "latest"]).lower(),
                        artifact["deployedBytecode"]["object"].lower())
        balances = {key: busd("balanceOf(address)(uint256)", address) for key, address in a.items()}
        allowances = {key: busd("allowance(address,address)(uint256)", a[key], addresses["CCNFT"])
                      for key in ("a", "b", "funds")}
        self.expect("no BUSD custody", busd("balanceOf(address)(uint256)", addresses["CCNFT"]), 0)
        # Modelar únicamente los cambios esperados desde la etapa anterior.
        expected_balances = dict(ctx.get("balances", balances))
        expected_allowances = dict(ctx.get("allowances", {key: 0 for key in allowances}))
        if stage == "deploy":
            expected_balances = {key: 10_000_000 * 10**18 if key == "admin" else 0 for key in a}
        elif stage == "fund":
            expected_balances.update(a=p["START_BALANCE"], b=p["START_BALANCE"], funds=p["RESERVE"])
            expected_balances["admin"] -= 2 * p["START_BALANCE"] + p["RESERVE"]
        elif stage.startswith("approve-"):
            key = stage.removeprefix("approve-")
            expected_allowances[key] = p[{"a": "BUY_PAYMENT", "b": "TRADE_PAYMENT", "funds": "CLAIM_PAYMENT"}[key]]
        elif stage == "buy":
            principal = 2 * p["NOMINAL"]
            expected_balances["a"] -= p["BUY_PAYMENT"]
            expected_balances["funds"] += principal
            expected_balances["fees"] += p["BUY_PAYMENT"] - principal
            expected_allowances["a"] = 0
        elif stage == "trade":
            expected_balances["a"] += p["PRICE"]
            expected_balances["b"] -= p["TRADE_PAYMENT"]
            expected_balances["fees"] += p["TRADE_PAYMENT"] - p["PRICE"]
            expected_allowances["b"] = 0
        elif stage == "claim":
            expected_balances["b"] += p["CLAIM_PAYMENT"]
            expected_balances["funds"] -= p["CLAIM_PAYMENT"]
            expected_allowances["funds"] = 0
        self.expect(f"{stage}: balances", balances, expected_balances)
        self.expect(f"{stage}: exact allowances", allowances, expected_allowances)
        ctx.update(balances=balances, allowances=allowances)
        if stage == "fund":
            ctx["baseline"] = dict(balances)
        index = list(STAGES).index(stage)
        if index >= list(STAGES).index("configure"):
            for signature, expected in (("fundsToken()(address)", addresses["BUSD"]),
                    ("fundsCollector()(address)", a["funds"]), ("feesCollector()(address)", a["fees"]),
                    ("buyFee()(uint16)", p["BUY_FEE"]), ("tradeFee()(uint16)", p["TRADE_FEE"]),
                    ("profitToPay()(uint32)", p["PROFIT"]), ("maxBatchCount()(uint16)", p["BATCH"]),
                    ("maxValueToRaise()(uint256)", p["LIMIT"])):
                self.expect(signature, nft(signature), expected)
            for nominal in (p["NOMINAL"], p["OTHER_NOMINAL"]):
                self.expect("valid nominal", nft("validValues(uint256)(bool)", nominal), True)
        for flag in ("canBuy", "canTrade", "canClaim"):
            self.expect(flag, nft(f"{flag}()(bool)"), index >= list(STAGES).index("enable"))
        supply = 0 if index < list(STAGES).index("buy") else 1 if stage == "claim" else 2
        self.expect("totalSupply", nft("totalSupply()(uint256)"), supply)
        self.expect("totalValue", nft("totalValue()(uint256)"), supply * p["NOMINAL"])
        if stage == "buy":
            ctx["sold_id"] = nft("tokenOfOwnerByIndex(address,uint256)(uint256)", a["a"], 0)
            ctx["kept_id"] = nft("tokenOfOwnerByIndex(address,uint256)(uint256)", a["a"], 1)
            self.expect("distinct enumerated IDs", ctx["sold_id"] != ctx["kept_id"], True)
        if supply:
            ids = [ctx["kept_id"]] if stage == "claim" else [ctx["sold_id"], ctx["kept_id"]]
            actual_ids = [nft("tokenByIndex(uint256)(uint256)", i) for i in range(supply)]
            self.expect("global enumeration", sorted(actual_ids), sorted(ids))
            for token_id in ids:
                owner = a["b"] if stage == "trade" and token_id == ctx["sold_id"] else a["a"]
                self.expect("NFT owner", nft("ownerOf(uint256)(address)", token_id), owner)
                self.expect("NFT nominal", nft("values(uint256)(uint256)", token_id), p["NOMINAL"])
                self.expect("NFT metadata", nft("tokenURI(uint256)(string)", token_id), p["URI"])
                sale = nft("tokensOnSale(uint256)(bool,uint256)", token_id).splitlines()
                self.expect("listing active", sale[0], "true" if stage == "list" and token_id == ctx["sold_id"] else "false")
                self.expect("listing price", int(sale[1].split()[0]), p["PRICE"] if stage == "list" and token_id == ctx["sold_id"] else 0)
            for key in ("a", "b"):
                expected = 1 if stage == "trade" else (1 if key == "a" else 0) if stage == "claim" else (2 if key == "a" else 0)
                self.expect(f"{key}: NFT balance", nft("balanceOf(address)(uint256)", a[key]), expected)
        if stage == "list":
            self.expect("sale enumeration", nft("listTokensOnSale(uint256)(uint256)", 0), ctx["sold_id"])
            self.reverts("listTokensOnSale(uint256)(uint256)", 1)
        else:
            self.reverts("listTokensOnSale(uint256)(uint256)", 0)
        if stage == "claim":
            burned = ctx["sold_id"]
            self.expect("burned nominal", nft("values(uint256)(uint256)", burned), 0)
            self.expect("burned listing", nft("tokensOnSale(uint256)(bool,uint256)", burned).splitlines(), ["false", "0"])
            self.reverts("ownerOf(uint256)(address)", burned)
            self.reverts("tokenURI(uint256)(string)", burned)
            deltas = {key: balances[key] - ctx["baseline"][key] for key in ("a", "b", "funds", "fees")}
            self.expect("final BUSD deltas", deltas, {"a": -84 * 10**18, "b": -162 * 10**17,
                                                       "funds": 95 * 10**18, "fees": 52 * 10**17})
            self.expect("remaining collector reserve", balances["funds"], p["CLAIM_PAYMENT"])
            ctx["deltas"] = deltas
            ctx["reserve_note"] = "Saldo suficiente para el NFT conservado; requiere nueva aprobación exacta de 105 BUSD."


def execute(output, rpc_url=None, stage=None, state=None):
    output.mkdir(parents=True, exist_ok=False)
    demo = Demo(output)
    process = None
    node_log = None
    try:
        demo.p = parameters()
        for command in (["git", "rev-parse", "HEAD"], ["git", "status", "--short"], ["git", "diff", "HEAD"],
                        *[[f".tools/bin/{binary}", "--version"] for binary in ("forge", "cast", "anvil")],
                        *[["git", "-C", f"lib/{lib}", "rev-parse", "HEAD"] for lib in ("openzeppelin-contracts", "forge-std")],
                        *[["git", "-C", f"lib/{lib}", "status", "--porcelain"] for lib in ("openzeppelin-contracts", "forge-std")]):
            demo.command(command)
        demo.command([".tools/bin/forge", "build", "--color", "never"])
        for contract in ("BUSD", "CCNFT"):
            gas.load_artifact(contract)
        if rpc_url:
            port = loopback_url(rpc_url)
        else:
            # Fallar antes de iniciar si no se pueden crear sockets; usar un puerto libre.
            with socket.socket() as probe:
                probe.bind(("127.0.0.1", 0))
                port = probe.getsockname()[1]
            rpc_url = f"http://127.0.0.1:{port}"
            node_log = (output / "anvil.txt").open("w")
            cmd = [str(ROOT / ".tools/bin/anvil"), "--host", "127.0.0.1", "--port", str(port),
                   "--chain-id", "31337", "--hardfork", "paris", "--silent"]
            demo.report["node_command"] = cmd
            # --silent impide guardar las claves de desarrollo que imprime Anvil por defecto.
            process = subprocess.Popen(cmd, stdout=node_log, stderr=node_log, cwd=ROOT)
            demo.report["owned_anvil_pid"] = process.pid
            demo.save()
        demo.rpc = gas.RPC(port)
        deadline = time.monotonic() + 10
        while True:
            if process and process.poll() is not None:
                raise RuntimeError("Anvil terminó antes de estar disponible; ver anvil.txt")
            try:
                accounts = demo.rpc.call("eth_accounts", [])
                break
            except (urllib.error.URLError, TimeoutError):
                if time.monotonic() >= deadline:
                    raise RuntimeError("Anvil no respondió")
                time.sleep(0.1)
        if stage and stage != "deploy":
            demo.context = json.loads(state.read_text())
            demo.expect("same RPC URL", demo.context["rpc_url"], rpc_url)
        else:
            if state and state.exists():
                raise ValueError("El archivo de estado ya existe; usar otro para una nueva demostración.")
            if len(accounts) < 5:
                raise ValueError("Anvil requiere cinco cuentas desbloqueadas")
            demo.context = {"rpc_url": rpc_url, "actors": dict(zip(("admin", "a", "b", "funds", "fees"),
                            (address.lower() for address in accounts[:5]))), "addresses": {}, "completed": [],
                            "genesis": demo.rpc.call("eth_getBlockByNumber", ["0x0", False])["hash"],
                            "last_block": int(demo.rpc.call("eth_blockNumber", []), 16)}
        for name in ([stage] if stage else STAGES):
            demo.stage(name)
            if state:
                state.parent.mkdir(parents=True, exist_ok=True)
                temporary = state.with_suffix(".tmp")
                temporary.write_text(json.dumps(demo.context, indent=2) + "\n")
                temporary.replace(state)
        demo.report["status"] = "passed"
    except Exception as error:
        for record in demo.report["stages"]:
            if record["status"] == "running":
                record["status"] = "failed"
        demo.report.update(status="failed", error=f"{type(error).__name__}: {error}")
        print(f"Demostración fallida: {error}; evidencia: {output}", file=sys.stderr, flush=True)
    finally:
        if process:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            demo.report["owned_anvil_exit_code"] = process.returncode
        if node_log:
            node_log.close()
        demo.report["finished_at"] = now()
        demo.save()
    return demo.report["status"] == "passed"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".tools/demo" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    parser.add_argument("--rpc-url", help="Anvil existente; obligatorio para etapas individuales")
    parser.add_argument("--stage", choices=STAGES)
    parser.add_argument("--state", type=Path, default=ROOT / ".tools/demo-state.json")
    parser.add_argument("--repeat", type=int, default=2, help="Redes nuevas para el recorrido completo (predeterminado: 2)")
    args = parser.parse_args()
    if args.stage and not args.rpc_url:
        parser.error("--stage requiere --rpc-url; iniciar Anvil con make anvil")
    if args.rpc_url and not args.stage:
        parser.error("Para el recorrido completo se crean redes nuevas; usar --stage con un Anvil existente")
    if args.repeat < 1:
        parser.error("--repeat debe ser positivo")
    output = args.output_dir.resolve()
    if args.stage:
        return 0 if execute(output, args.rpc_url, args.stage, args.state.resolve()) else 1
    output.mkdir(parents=True, exist_ok=False)
    results = []
    # Ejecutar ambas redes incluso si la primera falla, conservando cada intento.
    for index in range(args.repeat):
        results.append(execute(output / f"run-{index + 1}"))
    report = {"status": "passed" if all(results) else "failed", "runs": results, "finished_at": now()}
    (output / "result.json").write_text(json.dumps(report, indent=2) + "\n")
    print(f"{report['status']}: {output}", flush=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
