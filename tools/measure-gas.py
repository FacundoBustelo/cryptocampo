#!/usr/bin/env python3
"""Mide recibos de transacciones en un Anvil temporal, sin RPC externo."""

import argparse
import json
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

UNIT = 10**18
LIST_SIZES = (1, 10, 100)
BATCH_SIZES = (1, 10)


def word(value: int | str) -> str:
    number = int(value, 16) if isinstance(value, str) else int(value)
    if not 0 <= number < 2**256:
        raise ValueError("Argumento fuera de rango uint256.")
    return f"{number:064x}"


def calldata(artifact: dict, signature: str, args: tuple) -> str:
    selector = artifact["methodIdentifiers"][signature].removeprefix("0x")
    types = signature.split("(", 1)[1][:-1]
    if types == "uint256[]":
        values = args[0]
        payload = word(32) + word(len(values)) + "".join(word(v) for v in values)
    else:
        payload = "".join(word(value) for value in args)
    return "0x" + selector + payload


def load_artifact(name: str) -> dict:
    artifact = json.loads(Path(f"out/{name}.sol/{name}.json").read_text())
    metadata = artifact.get("metadata") or json.loads(artifact["rawMetadata"])
    if isinstance(metadata, str):
        metadata = json.loads(metadata)
    settings = metadata["settings"]
    if not metadata["compiler"]["version"].startswith("0.8.19+"):
        raise ValueError(f"{name}: se requiere Solidity 0.8.19.")
    optimizer = settings["optimizer"]
    if optimizer.get("enabled") is not True or optimizer.get("runs") != 200:
        raise ValueError(f"{name}: se requiere optimizador habilitado con 200 runs.")
    if settings["evmVersion"] != "paris":
        raise ValueError(f"{name}: se requiere EVM Paris.")
    return artifact


class RPC:
    def __init__(self, port: int):
        self.url = f"http://127.0.0.1:{port}"
        # Ignorar proxies del entorno para mantener todas las llamadas en localhost.
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        self.counter = 0

    def call(self, method: str, params: list):
        self.counter += 1
        request = urllib.request.Request(
            self.url,
            data=json.dumps({"jsonrpc": "2.0", "id": self.counter, "method": method, "params": params}).encode(),
            headers={"Content-Type": "application/json"},
        )
        with self.opener.open(request, timeout=5) as response:
            result = json.load(response)
        if "error" in result:
            raise RuntimeError(f"{method}: {result['error']}")
        return result["result"]

    def send(self, sender: str, data: str, to: str | None = None) -> dict:
        transaction = {"from": sender, "data": data, "gas": hex(20_000_000)}
        if to is not None:
            transaction["to"] = to
        tx_hash = self.call("eth_sendTransaction", [transaction])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            receipt = self.call("eth_getTransactionReceipt", [tx_hash])
            if receipt is not None:
                if int(receipt["status"], 16) != 1:
                    raise RuntimeError(f"Transacción revertida: {tx_hash}")
                return receipt
            time.sleep(0.05)
        raise RuntimeError(f"No se obtuvo el recibo: {tx_hash}")


def prepare(rpc: RPC, artifacts: dict, accounts: list[str], count: int):
    admin, alice, bob, funds, fees = accounts[:5]
    addresses = {}
    for name, artifact in artifacts.items():
        receipt = rpc.send(admin, artifact["bytecode"]["object"])
        addresses[name] = receipt["contractAddress"]

    def send(name: str, signature: str, *args, sender=admin):
        return rpc.send(sender, calldata(artifacts[name], signature, args), addresses[name])

    send("CCNFT", "setFundsToken(address)", addresses["BUSD"])
    send("CCNFT", "setFundsCollector(address)", funds)
    send("CCNFT", "setFeesCollector(address)", fees)
    send("CCNFT", "addValidValues(uint256)", 100 * UNIT)
    send("CCNFT", "setMaxBatchCount(uint16)", 10)
    send("CCNFT", "setMaxValueToRaise(uint256)", 1_000_000 * UNIT)
    send("CCNFT", "setBuyFee(uint16)", 200)
    send("CCNFT", "setTradeFee(uint16)", 100)
    send("CCNFT", "setProfitToPay(uint32)", 500)
    for signature in ("setCanBuy(bool)", "setCanTrade(bool)", "setCanClaim(bool)"):
        send("CCNFT", signature, True)
    for account, amount in ((alice, 100_000), (bob, 100_000), (funds, 1_000)):
        send("BUSD", "transfer(address,uint256)", account, amount * UNIT)
        send("BUSD", "approve(address,uint256)", addresses["CCNFT"], 2**256 - 1, sender=account)

    # Reservar diez NFTs sin publicar para insertar y reclamar lotes completos.
    remaining = count + 10
    while remaining:
        amount = min(remaining, 10)
        send("CCNFT", "buy(uint256,uint256)", 100 * UNIT, amount, sender=alice)
        remaining -= amount
    for token_id in range(count):
        send("CCNFT", "putOnSale(uint256,uint256)", token_id, 120 * UNIT, sender=alice)
    return send


def scenarios(count: int):
    for batch in BATCH_SIZES:
        yield "buy", batch, "alice", "buy(uint256,uint256)", (100 * UNIT, batch)
    for label, token_id in (("list_new", count), ("list_update_first", 0), ("list_update_last", count - 1)):
        yield label, 1, "alice", "putOnSale(uint256,uint256)", (token_id, 121 * UNIT)
    for label, token_id in (("trade_first", 0), ("trade_middle", count // 2), ("trade_last", count - 1)):
        yield label, 1, "bob", "trade(uint256)", (token_id,)
    for batch in BATCH_SIZES:
        yield "claim_unlisted", batch, "alice", "claim(uint256[])", (list(range(count, count + batch)),)
        if batch <= count:
            # IDs al final: cada eliminación recorre la lista hasta su último elemento.
            ids = list(range(count - 1, count - batch - 1, -1))
            yield "claim_listed_last", batch, "alice", "claim(uint256[])", (ids,)


def measure(rpc: RPC, artifacts: dict, accounts: list[str]) -> list[dict]:
    rows = []
    actors = {"alice": accounts[1], "bob": accounts[2]}
    print("| Publicaciones | Operación | Lote | Gas del recibo |", flush=True)
    print("| ---: | --- | ---: | ---: |", flush=True)
    for count in LIST_SIZES:
        send = prepare(rpc, artifacts, accounts, count)
        for label, batch, actor, signature, args in scenarios(count):
            snapshot = rpc.call("evm_snapshot", [])
            try:
                receipt = send("CCNFT", signature, *args, sender=actors[actor])
                used = int(receipt["gasUsed"], 16)
            finally:
                if not rpc.call("evm_revert", [snapshot]):
                    raise RuntimeError("No se pudo restaurar el estado entre mediciones.")
            rows.append({"list_size": count, "operation": label, "batch_size": batch, "gas_used": used})
            print(f"| {count} | {label} | {batch} | {used} |", flush=True)
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=18545)
    args = parser.parse_args()
    artifacts = {name: load_artifact(name) for name in ("BUSD", "CCNFT")}
    binary = str(Path(".tools/bin/anvil").resolve())
    rpc = RPC(args.port)
    # Rechazar un puerto ocupado antes de crear el proceso, incluso si no es un RPC.
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", args.port))
    with tempfile.TemporaryFile(mode="w+") as node_log:
        process = subprocess.Popen(
            [binary, "--host", "127.0.0.1", "--port", str(args.port), "--hardfork", "paris",
             "--chain-id", "31337", "--gas-limit", "30000000"],
            stdout=node_log, stderr=node_log,
        )
        try:
            deadline = time.monotonic() + 10
            while True:
                if process.poll() is not None:
                    node_log.seek(0)
                    raise RuntimeError(f"Anvil no pudo iniciar: {node_log.read()}")
                try:
                    accounts = rpc.call("eth_accounts", [])
                    break
                except (urllib.error.URLError, TimeoutError):
                    if time.monotonic() >= deadline:
                        raise RuntimeError("Anvil no respondió durante el inicio.")
                    time.sleep(0.1)
            if len(accounts) < 5 or int(rpc.call("eth_chainId", []), 16) != 31337:
                raise RuntimeError("Se requiere la red Anvil local con cinco cuentas de desarrollo.")
            commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
            print(f"Commit: {commit}", flush=True)
            for name in ("openzeppelin-contracts", "forge-std"):
                revision = subprocess.check_output(["git", "-C", f"lib/{name}", "rev-parse", "HEAD"], text=True).strip()
                print(f"{name}: {revision}", flush=True)
            for tool in ("forge", "anvil"):
                version = subprocess.check_output([f".tools/bin/{tool}", "--version"], text=True).splitlines()[0]
                print(version, flush=True)
            print("Solidity 0.8.19; optimizador: 200 runs; compilación y red: Paris.", flush=True)
            rows = measure(rpc, artifacts, accounts)
            result = {"commit": commit, "hardfork": "paris", "optimizer_runs": 200, "measurements": rows}
            Path(".tools/gas-scenarios.json").write_text(json.dumps(result, indent=2) + "\n")
            print(f"Medición completa: {len(rows)} transacciones exitosas; resultado en .tools/gas-scenarios.json.")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    main()
