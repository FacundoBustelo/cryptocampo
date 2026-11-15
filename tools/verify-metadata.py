#!/usr/bin/env python3
"""Verifica bytes IPFS y la URI compartida en un Anvil temporal (Python estándar)."""

import argparse
import base64
import hashlib
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GATEWAYS = ("https://gateway.pinata.cloud/ipfs/", "https://ipfs.io/ipfs/")
PATHS = {"image": "assets/certificate.svg", "metadata": "assets/metadata.json"}
UNIT = 10**18


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_cid(cid):
    """CIDv0 o CIDv1 base32 con multihash sha2-256, sin rutas ni carpetas."""
    require(isinstance(cid, str) and cid, "Falta el CID público del archivo individual.")
    if cid.startswith("Qm"):
        alphabet = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        require(len(cid) == 46 and all(c in alphabet for c in cid), "CIDv0 inválido.")
        number = 0
        for char in cid:
            number = number * 58 + alphabet.index(char)
        raw = number.to_bytes((number.bit_length() + 7) // 8, "big")
        require(len(raw) == 34 and raw[:2] == b"\x12\x20", "Multihash CIDv0 inválido.")
    else:
        require(cid.startswith("b") and cid == cid.lower(), "Se requiere CIDv0 o CIDv1 base32.")
        try:
            raw = base64.b32decode(cid[1:].upper() + "=" * (-len(cid[1:]) % 8))
        except ValueError as error:
            raise ValueError("CIDv1 base32 inválido.") from error
        require(len(raw) == 36 and raw[0] == 1 and raw[1] in (0x55, 0x70)
                and raw[2:4] == b"\x12\x20", "Se requiere CIDv1 raw/dag-pb con sha2-256.")
        require(base64.b32encode(raw).decode().lower().rstrip("=") == cid[1:], "CID no canónico.")
    return cid


def validate_svg(data):
    root = ET.fromstring(data)
    require(root.tag == "{http://www.w3.org/2000/svg}svg", "La imagen no es un SVG válido.")
    require(root.get("viewBox") == "0 0 1200 800", "Dimensiones SVG inesperadas.")


def validate_metadata(data, image_uri=None):
    def unique_keys(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, f"Clave JSON duplicada: {key}.")
            result[key] = value
        return result

    value = json.loads(data.decode("utf-8"), object_pairs_hook=unique_keys)
    require(isinstance(value, dict) and set(value) == {"name", "description", "image"},
            "El JSON debe contener únicamente name, description e image.")
    require(all(isinstance(v, str) and v.strip() for v in value.values()), "Campos JSON vacíos o inválidos.")
    require("demostración" in value["name"].lower(), "Falta el nombre de demostración.")
    require("no acredita existencias físicas verificadas" in value["description"].lower(),
            "Falta la descripción de demostración.")
    if image_uri is not None:
        require(value["image"] == image_uri, "metadata.image no coincide con la URI IPFS de la imagen.")
        require("local" not in value["description"].lower(), "La descripción todavía menciona pruebas locales.")
    return value


def check_date(value, label):
    require(isinstance(value, str), f"Falta fecha de {label}.")
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    require(parsed.tzinfo is not None and parsed <= datetime.now(timezone.utc), f"Fecha inválida de {label}.")


def publication_reference(resource):
    cid = validate_cid(resource.get("cid"))
    require(resource.get("uri") == f"ipfs://{cid}", "URI distinta del CID registrado.")
    return cid


def publication(resource):
    cid = publication_reference(resource)
    if resource.get("published_at") is not None:
        check_date(resource["published_at"], "publicación")
    else:
        published_on = resource.get("published_on")
        require(isinstance(published_on, str), "Falta fecha de publicación.")
        parsed = date.fromisoformat(published_on)
        require(parsed.isoformat() == published_on and parsed <= datetime.now(timezone.utc).date(),
                "Fecha de publicación inválida.")
    return cid


def pinning(resource):
    pin = resource.get("pinning", {})
    require(pin.get("status") == "confirmed_by_user" and pin.get("provider") == "Pinata",
            "Falta confirmación del usuario de pinning en Pinata.")
    check_date(pin.get("confirmed_at"), "pinning")
    require(bool(pin.get("evidence")), "Falta evidencia o declaración del usuario sobre el pinning.")


def download(resource, data, gateway, output, timeout):
    url = gateway + resource["cid"]
    result = {"url": url, "checked_at": now(), "status": "pending"}
    try:
        output.unlink(missing_ok=True)
        request = urllib.request.Request(url, headers={"User-Agent": "CryptoCampo-metadata-verifier/1.0"})
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result.update(http_status=response.status, resolved_url=response.url)
            require(response.status == 200, f"HTTP {response.status}")
            received = response.read(len(data) + 1)
        require(len(received) <= len(data), "La respuesta supera el tamaño del archivo local.")
        result["sha256"] = digest(received)
        require(received == data, "Los bytes descargados difieren del archivo local (o se recibió una carpeta/HTML).")
        if resource["path"].endswith(".svg"):
            validate_svg(received)
        else:
            validate_metadata(received)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(received)
        result.update(status="verified", downloaded_file=str(output))
    except (OSError, ValueError, ET.ParseError) as error:
        result["error"] = str(error)
    return result


def word(value):
    return f"{int(value, 16) if isinstance(value, str) else int(value):064x}"


def encode(artifact, signature, args):
    selector = artifact["methodIdentifiers"][signature].removeprefix("0x")
    if signature == "setMetadataURI(string)":
        value = args[0].encode()
        payload = word(32) + word(len(value)) + value.hex().ljust((len(value) + 31) // 32 * 64, "0")
    elif signature == "claim(uint256[])":
        payload = word(32) + word(len(args[0])) + "".join(word(v) for v in args[0])
    else:
        payload = "".join(word(v) for v in args)
    return "0x" + selector + payload


def decode_string(value):
    data = bytes.fromhex(value.removeprefix("0x"))
    offset = int.from_bytes(data[:32], "big")
    require(len(data) >= 64 and offset == 32, "Respuesta ABI string inválida.")
    size = int.from_bytes(data[offset:offset + 32], "big")
    require(len(data) >= offset + 32 + size, "Respuesta ABI string truncada.")
    return data[offset + 32:offset + 32 + size].decode()


class RevertError(RuntimeError):
    def __init__(self, error):
        self.error = error
        super().__init__(str(error))


class RPC:
    def __init__(self, port):
        self.url = f"http://127.0.0.1:{port}"
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

    def call(self, method, params):
        request = urllib.request.Request(self.url, data=json.dumps(
            {"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode(),
            headers={"Content-Type": "application/json"})
        with self.opener.open(request, timeout=5) as response:
            result = json.load(response)
        if "error" in result:
            raise RevertError(result["error"])
        return result["result"]

    def send(self, sender, data, to=None):
        tx = {"from": sender, "data": data, "gas": hex(20_000_000)}
        if to is not None:
            tx["to"] = to
        tx_hash = self.call("eth_sendTransaction", [tx])
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            receipt = self.call("eth_getTransactionReceipt", [tx_hash])
            if receipt is not None:
                require(int(receipt["status"], 16) == 1, f"Transacción revertida: {tx_hash}")
                return receipt
            time.sleep(0.05)
        raise ValueError(f"Recibo pendiente: {tx_hash}")


def expect_revert(rpc, transaction, reason):
    try:
        rpc.call("eth_call", [transaction, "latest"])
    except RevertError as error:
        data = error.error.get("data")
        require(isinstance(data, str) and data.startswith("0x08c379a0"),
                f"No se recibió una reversión Error(string): {error}")
        require(decode_string("0x" + data[10:]) == reason, f"Reversión inesperada: {error}")
        return
    raise ValueError(f"La llamada no revirtió: se esperaba {reason}.")


def anvil_scenario(rpc, artifacts, uri, result):
    admin, alice, bob, funds, fees = rpc.call("eth_accounts", [])[:5]
    addresses = {}
    receipts = []
    result.update(addresses=addresses, transactions=receipts, checks=[])
    for name, artifact in artifacts.items():
        receipt = rpc.send(admin, artifact["bytecode"]["object"])
        addresses[name] = receipt["contractAddress"]
        receipts.append({"operation": f"deploy {name}", "hash": receipt["transactionHash"]})

    def tx(name, signature, *args, sender=admin):
        receipt = rpc.send(sender, encode(artifacts[name], signature, args), addresses[name])
        receipts.append({"operation": signature, "hash": receipt["transactionHash"]})

    def read(signature, *args):
        return rpc.call("eth_call", [{"to": addresses["CCNFT"],
                        "data": encode(artifacts["CCNFT"], signature, args)}, "latest"])

    tx("CCNFT", "setFundsToken(address)", addresses["BUSD"])
    tx("CCNFT", "setFundsCollector(address)", funds)
    tx("CCNFT", "setFeesCollector(address)", fees)
    for value in (100, 500):
        tx("CCNFT", "addValidValues(uint256)", value * UNIT)
    for signature, value in (("setMaxBatchCount(uint16)", 10), ("setMaxValueToRaise(uint256)", 10_000 * UNIT),
                             ("setBuyFee(uint16)", 200), ("setTradeFee(uint16)", 100),
                             ("setProfitToPay(uint32)", 500), ("setCanBuy(bool)", True),
                             ("setCanTrade(bool)", True), ("setCanClaim(bool)", True)):
        tx("CCNFT", signature, value)
    for account in (alice, bob):
        tx("BUSD", "transfer(address,uint256)", account, 100_000 * UNIT)
    for account in (alice, bob, funds):
        tx("BUSD", "approve(address,uint256)", addresses["CCNFT"], 2**256 - 1, sender=account)
    tx("CCNFT", "setMetadataURI(string)", uri)
    tx("CCNFT", "buy(uint256,uint256)", 100 * UNIT, 2, sender=alice)
    for token_id in (0, 1):
        require(decode_string(read("tokenURI(uint256)", token_id)) == uri, f"URI incorrecta: NFT {token_id}.")
    result["checks"].append("two_tokens_share_published_uri")
    tx("CCNFT", "putOnSale(uint256,uint256)", 0, 120 * UNIT, sender=alice)
    tx("CCNFT", "trade(uint256)", 0, sender=bob)
    require(int(read("ownerOf(uint256)", 0), 16) == int(bob, 16), "No cambió el propietario.")
    for token_id in (0, 1):
        require(decode_string(read("tokenURI(uint256)", token_id)) == uri, "Cambió la URI tras la reventa.")
    result["checks"].append("resale_preserves_uri")
    tx("CCNFT", "claim(uint256[])", [0], sender=bob)
    for token_id in (0, 999):
        expect_revert(rpc, {"to": addresses["CCNFT"], "data": encode(
            artifacts["CCNFT"], "tokenURI(uint256)", (token_id,))}, "Token does not exist")
    result["checks"].extend(("burned_token_reverts", "nonexistent_token_reverts"))
    expect_revert(rpc, {"from": bob, "to": addresses["CCNFT"], "data": encode(
        artifacts["CCNFT"], "setMetadataURI(string)", ("https://metadata.example.invalid/unauthorized.json",))},
        "Ownable: caller is not the owner")
    require(decode_string(read("tokenURI(uint256)", 1)) == uri, "Se modificó la URI compartida.")
    require(int(read("totalValue()"), 16) == 100 * UNIT, "Nominal final incorrecto.")
    result["checks"].append("third_party_cannot_update_uri")


def verify_anvil(uri, result):
    result.update(status="pending", uri=uri)
    binary = ROOT / ".tools/bin/anvil"
    forge = ROOT / ".tools/bin/forge"
    require(binary.is_file() and forge.is_file(), "Falta Foundry: ejecutar bash tools/setup.sh.")
    subprocess.run([str(forge), "build"], cwd=ROOT, check=True, stdout=sys.stderr, timeout=120)
    artifacts = {name: json.loads((ROOT / f"out/{name}.sol/{name}.json").read_text())
                 for name in ("BUSD", "CCNFT")}
    for name, artifact in artifacts.items():
        metadata = artifact["metadata"]
        if isinstance(metadata, str):
            metadata = json.loads(metadata)
        settings = metadata["settings"]
        require(metadata["compiler"]["version"].startswith("0.8.19+") and settings["evmVersion"] == "paris"
                and settings["optimizer"] == {"enabled": True, "runs": 200}, f"Compilación inesperada de {name}.")
    result["versions"] = {name: subprocess.check_output([str(ROOT / f".tools/bin/{name}"), "--version"],
                          text=True).splitlines()[0] for name in ("forge", "anvil")}
    result["libraries"] = {name: subprocess.check_output(["git", "-C", str(ROOT / f"lib/{name}"),
                           "rev-parse", "HEAD"], text=True).strip()
                           for name in ("openzeppelin-contracts", "forge-std")}
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        port = probe.getsockname()[1]
    rpc = RPC(port)
    with tempfile.TemporaryFile(mode="w+") as log:
        process = subprocess.Popen([str(binary), "--host", "127.0.0.1", "--port", str(port),
                                    "--hardfork", "paris", "--chain-id", "31337"], stdout=log, stderr=log)
        try:
            deadline = time.monotonic() + 10
            while True:
                require(process.poll() is None, "Anvil terminó durante el inicio.")
                try:
                    require(int(rpc.call("eth_chainId", []), 16) == 31337, "Chain ID inesperado.")
                    break
                except (urllib.error.URLError, TimeoutError):
                    require(time.monotonic() < deadline, "Anvil no respondió durante el inicio.")
                    time.sleep(0.1)
            anvil_scenario(rpc, artifacts, uri, result)
            require(process.poll() is None, "Anvil terminó antes de completar las comprobaciones.")
            result.update(status="verified", checked_at=now(), chain_id=31337, hardfork="paris")
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


def verify(manifest, mode, output_dir, timeout):
    require(manifest.get("schema_version") == 1, "Versión de manifiesto no compatible.")
    result = {"checked_at": now(), "status": "pending", "mode": mode, "resources": {},
              "anvil": {"status": "pending"}, "pending": []}
    resources = manifest["resources"]
    for name, path in PATHS.items():
        resource = resources[name]
        require(resource["path"] == path, f"Ruta inesperada para {name}.")
        data = (ROOT / path).read_bytes()
        require(resource["sha256"] == digest(data), f"{path}: SHA-256 distinto del registrado.")
        validate_svg(data) if name == "image" else validate_metadata(data)
        result["resources"][name] = {"sha256": digest(data), "local": "verified", "gateways": []}
    if mode == "local":
        if resources["image"].get("cid") is not None:
            validate_metadata((ROOT / PATHS["metadata"]).read_bytes(),
                              "ipfs://" + validate_cid(resources["image"]["cid"]))
        result["pending"].append("Solo validación local; IPFS, pinning, presentación y Anvil pendientes.")
        return result
    names = ("image",) if mode == "image" else tuple(PATHS)
    public_ok = True
    for name in names:
        resource = resources[name]
        try:
            publication_reference(resource)
        except (ValueError, TypeError) as error:
            result["pending"].append(f"{name}: {error}")
            public_ok = False
            continue
        try:
            publication(resource)
        except (ValueError, TypeError) as error:
            result["pending"].append(f"{name}: {error}")
        data = (ROOT / resource["path"]).read_bytes()
        for index, gateway in enumerate(GATEWAYS):
            checked = download(resource, data, gateway, output_dir / str(index) / Path(resource["path"]).name, timeout)
            result["resources"][name]["gateways"].append(checked)
            if checked["status"] != "verified":
                public_ok = False
                result["pending"].append(f"{name}: {checked['url']}: {checked['error']}")
        try:
            pinning(resource)
        except (ValueError, TypeError) as error:
            result["pending"].append(f"{name}: {error}")
    if mode == "image":
        result["image_publication"] = "verified" if public_ok and not result["pending"] else "pending"
        result["pending"].append("Faltan el JSON definitivo y la prueba de su URI en Anvil.")
        return result
    try:
        require(resources["image"].get("cid") is not None,
                "El JSON definitivo espera el CID real de la imagen.")
        image_uri = "ipfs://" + validate_cid(resources["image"]["cid"])
        validate_metadata((ROOT / PATHS["metadata"]).read_bytes(), image_uri)
    except (ValueError, TypeError) as error:
        public_ok = False
        result["pending"].append(f"metadata: {error}")
    if public_ok:
        try:
            verify_anvil(resources["metadata"]["uri"], result["anvil"])
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError, KeyError) as error:
            result["anvil"]["error"] = str(error)
            result["pending"].append(f"Anvil: {error}")
    else:
        result["pending"].append("Anvil: pendiente de recuperación pública de ambos archivos y JSON definitivo.")
    try:
        visual = manifest["visual_review"]
        require(visual["status"] == "verified" and visual["sha256"] == resources["image"]["sha256"]
                and bool(visual.get("reviewed_by")) and bool(visual["evidence"]),
                "Falta revisar visualmente la imagen recuperada.")
        check_date(visual["reviewed_at"], "revisión visual")
    except (ValueError, TypeError, KeyError) as error:
        result["pending"].append(f"Presentación: {error}")
    if not result["pending"] and result["anvil"]["status"] == "verified":
        result["status"] = "verified"
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--local-only", action="store_true", help="Sin red ni Foundry; acepta JSON de borrador.")
    mode.add_argument("--image-only", action="store_true", help="Recupera solo la imagen antes de publicar el JSON.")
    parser.add_argument("--record", action="store_true", help="Registra el resultado real en el manifiesto, aun si falla.")
    parser.add_argument("--manifest", type=Path, default=ROOT / "docs/ipfs-publication.json")
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".tools/metadata-verification")
    parser.add_argument("--timeout", type=int, choices=range(1, 61), default=15, metavar="1..60")
    args = parser.parse_args()
    mode = "local" if args.local_only else "image" if args.image_only else "full"
    manifest = None
    try:
        manifest = json.loads(args.manifest.read_text())
        result = verify(manifest, mode, args.output_dir, args.timeout)
    except (OSError, ValueError, TypeError, KeyError, ET.ParseError) as error:
        result = {"checked_at": now(), "status": "pending", "mode": mode, "pending": [str(error)]}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    (args.output_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    if args.record and manifest is not None:
        manifest["verification"] = result
        args.manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if mode == "local" and all(r.get("local") == "verified" for r in result.get("resources", {}).values()) \
            and len(result.get("resources", {})) == 2:
        return 0
    if mode == "image" and result.get("image_publication") == "verified":
        return 0
    return 0 if result["status"] == "verified" else 1


if __name__ == "__main__":
    sys.exit(main())
