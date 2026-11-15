"""Verifica evidencias, fallos y ciclo de vida del ejecutor sin requerir sockets."""

import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch

spec = importlib.util.spec_from_file_location("demo", Path(__file__).with_name("demo.py"))
demo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(demo)


class DemoTest(unittest.TestCase):
    def test_parameters_use_definitive_publication_and_exact_payments(self):
        p = demo.parameters()
        self.assertEqual(p["BUY_PAYMENT"], 204 * 10**18)
        self.assertEqual(p["TRADE_PAYMENT"], 1212 * 10**17)
        self.assertEqual(p["CLAIM_PAYMENT"], 105 * 10**18)
        self.assertEqual(p["URI"], json.loads((demo.ROOT / "docs/ipfs-publication.json").read_text())["resources"]["metadata"]["uri"])

    def test_only_loopback_without_credentials_is_accepted(self):
        self.assertEqual(demo.loopback_url("http://127.0.0.1:8545"), 8545)
        for url in ("https://example.com:8545", "http://0.0.0.0:8545", "http://localhost:8545",
                    "http://user:secret@127.0.0.1:8545", "http://127.0.0.1:8545/path"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                demo.loopback_url(url)

    def test_hash_manifest_includes_scripts_and_makefile(self):
        paths = demo.source_hashes()
        self.assertIn("Makefile", paths)
        for path in (demo.ROOT / "script").glob("*.sol"):
            self.assertIn(str(path.relative_to(demo.ROOT)), paths)

    def test_failed_command_records_log_and_exit_code(self):
        with tempfile.TemporaryDirectory() as directory:
            instance = demo.Demo(Path(directory))
            with self.assertRaises(RuntimeError):
                instance.command(["python3", "-c", "print('partial evidence'); raise SystemExit(9)"])
            report = json.loads((Path(directory) / "result.json").read_text())
            self.assertEqual(report["commands"][0]["exit_code"], 9)
            self.assertIn("partial evidence", (Path(directory) / "000.txt").read_text())

    def test_failed_state_check_is_persisted_before_raise(self):
        with tempfile.TemporaryDirectory() as directory:
            instance = demo.Demo(Path(directory))
            with self.assertRaises(ValueError):
                instance.expect("totalValue", 200, 100)
            report = json.loads((Path(directory) / "result.json").read_text())
            self.assertEqual(report["checks"][-1]["status"], "failed")

    def test_existing_evidence_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            sentinel = Path(directory) / "result.json"
            sentinel.write_text("historical")
            with self.assertRaises(FileExistsError):
                demo.execute(Path(directory))
            self.assertEqual(sentinel.read_text(), "historical")

    def test_socket_failure_preserves_result_and_creates_no_process(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(demo.Demo, "command"), \
                patch.object(demo.gas, "load_artifact"), \
                patch.object(demo.socket, "socket", side_effect=PermissionError("socket denied")), \
                patch.object(demo.subprocess, "Popen") as process:
            output = Path(directory) / "attempt"
            self.assertFalse(demo.execute(output))
            report = json.loads((output / "result.json").read_text())
            self.assertEqual(report["status"], "failed")
            self.assertIn("socket denied", report["error"])
            process.assert_not_called()

    def test_owned_node_is_stopped_after_stage_failure(self):
        rpc = MagicMock()
        rpc.call.side_effect = lambda method, params: {
            "eth_accounts": [f"0x{i:040x}" for i in range(1, 6)],
            "eth_getBlockByNumber": {"hash": "0xgenesis"}, "eth_blockNumber": "0x0"}[method]
        with tempfile.TemporaryDirectory() as directory, patch.object(demo.Demo, "command"), \
                patch.object(demo.Demo, "stage", side_effect=ValueError("bad state")), \
                patch.object(demo.gas, "load_artifact"), patch.object(demo.gas, "RPC", return_value=rpc), \
                patch.object(demo.socket, "socket"), patch.object(demo.subprocess, "Popen") as factory:
            process = factory.return_value
            process.pid = 12345
            process.returncode = -15
            process.poll.return_value = None
            self.assertFalse(demo.execute(Path(directory) / "attempt"))
            process.terminate.assert_called_once()
            process.wait.assert_called_once_with(timeout=5)
            self.assertIn("--silent", factory.call_args.args[0])

    def test_external_node_is_never_stopped(self):
        rpc = MagicMock()
        rpc.call.return_value = [f"0x{i:040x}" for i in range(1, 6)]
        with tempfile.TemporaryDirectory() as directory, patch.object(demo.Demo, "command"), \
                patch.object(demo.gas, "load_artifact"), patch.object(demo.gas, "RPC", return_value=rpc), \
                patch.object(demo.subprocess, "Popen") as factory:
            state = Path(directory) / "state.json"
            state.write_text(json.dumps({"rpc_url": "http://127.0.0.1:9999"}))
            self.assertFalse(demo.execute(Path(directory) / "attempt", "http://127.0.0.1:8545", "buy", state))
            factory.assert_not_called()

    def test_expected_revert_requires_exact_abi_data_and_rejects_network_errors(self):
        with tempfile.TemporaryDirectory() as directory:
            instance = demo.Demo(Path(directory))
            instance.context = {"addresses": {"CCNFT": "0xnft"}, "rpc_url": "http://127.0.0.1:8545"}
            # Respuesta real de Cast/Anvil 1.4.4 para el getter público vacío.
            message = 'Error: server returned an error response: error code 3: execution reverted, data: "0x"'
            instance.command = MagicMock(return_value=(1, message))
            instance.reverts("listTokensOnSale(uint256)(uint256)", 0)
            panic = "0x4e487b71" + f"{0x32:064x}"
            for code, message in ((0, message), (1, "network connection refused"),
                    (1, 'network connection refused, data: "0x"'),
                    (1, 'error code 3: execution reverted: different reason'),
                    (1, 'error code 3: execution reverted, data: "0xdeadbeef"'),
                    (1, f'error code 3: execution reverted, data: "{panic}"')):
                instance.command.return_value = (code, message)
                with self.subTest(code=code, message=message), self.assertRaises(ValueError):
                    instance.reverts("listTokensOnSale(uint256)(uint256)", 0)

    def test_burned_token_queries_require_their_exact_revert_reason(self):
        with tempfile.TemporaryDirectory() as directory:
            instance = demo.Demo(Path(directory))
            instance.context = {"addresses": {"CCNFT": "0xnft"}, "rpc_url": "http://127.0.0.1:8545"}
            for signature, reason in (("ownerOf(uint256)(address)", "ERC721: owner query for nonexistent token"),
                                      ("tokenURI(uint256)(string)", "Token does not exist")):
                payload = reason.encode().hex()
                expected = "0x08c379a0" + f"{32:064x}{len(reason):064x}" + payload.ljust(64 if len(reason) <= 32 else 128, "0")
                instance.command = MagicMock(return_value=(1, f'error code 3: execution reverted, data: "{expected}"'))
                instance.reverts(signature, 0)
                for data in ("0x", "0xdeadbeef"):
                    instance.command.return_value = (1, f'error code 3: execution reverted, data: "{data}"')
                    with self.subTest(signature=signature, data=data), self.assertRaises(ValueError):
                        instance.reverts(signature, 0)

    def test_final_state_verifier_detects_broken_accounting_cleanup_and_metadata(self):
        # Valores externos al modelo del ejecutor, expresados en unidades mínimas.
        unit = 10**18
        with tempfile.TemporaryDirectory() as directory:
            instance = demo.Demo(Path(directory))
            instance.p = demo.parameters()
            a = {key: key for key in ("admin", "a", "b", "funds", "fees")}
            preclaim = {"admin": 9_997_990 * unit, "a": 916 * unit, "b": 8788 * 10**17,
                        "funds": 210 * unit, "fees": 52 * 10**17}
            final = dict(preclaim, b=9838 * 10**17, funds=105 * unit)
            initial = dict(preclaim, a=1000 * unit, b=1000 * unit, funds=10 * unit, fees=0)
            state = {"metadata": instance.p["URI"], "nominal": 100 * unit, "sale": "false\n0",
                     "funds_allowance": 0, "owner": "a", "balances": final}
            instance.rpc = MagicMock()
            instance.rpc.call.return_value = "0xab"
            instance.reverts = MagicMock()

            def read(contract, signature, *args):
                if contract == "BUSD":
                    if signature.startswith("balanceOf"):
                        return state["balances"].get(args[0], 0)
                    return state["funds_allowance"] if args[0] == "funds" else 0
                scalar = {"owner()(address)": "admin", "fundsToken()(address)": "busd",
                          "fundsCollector()(address)": "funds", "feesCollector()(address)": "fees",
                          "buyFee()(uint16)": 200, "tradeFee()(uint16)": 100, "profitToPay()(uint32)": 500,
                          "maxBatchCount()(uint16)": 10, "maxValueToRaise()(uint256)": 10_000 * unit,
                          "totalSupply()(uint256)": 1, "totalValue()(uint256)": 100 * unit}
                if signature in scalar:
                    return scalar[signature]
                if signature.startswith(("validValues", "can")):
                    return True
                if signature.startswith("tokenByIndex"):
                    return 17
                if signature.startswith("ownerOf"):
                    return state["owner"]
                if signature.startswith("values"):
                    return state["nominal"] if args[0] == 17 else 0
                if signature.startswith("tokenURI"):
                    return state["metadata"]
                if signature.startswith("tokensOnSale"):
                    return state["sale"]
                if signature.startswith("balanceOf"):
                    return 1 if args[0] == "a" else 0
                raise AssertionError(signature)

            instance.call = read
            for mutation in ({}, {"metadata": "ipfs://wrong"}, {"nominal": 0}, {"sale": "true\n120"},
                             {"funds_allowance": 105 * unit}, {"owner": "b"},
                             {"balances": dict(final, funds=104 * unit)}):
                with self.subTest(mutation=mutation):
                    instance.context = {"actors": a, "addresses": {"BUSD": "busd", "CCNFT": "nft"},
                                        "balances": dict(preclaim), "allowances": {"a": 0, "b": 0, "funds": 105 * unit},
                                        "baseline": initial, "kept_id": 17, "sold_id": 3}
                    original = dict(state)
                    state.update(mutation)
                    with patch.object(demo.gas, "load_artifact", return_value={"deployedBytecode": {"object": "0xab"}}):
                        if mutation:
                            with self.assertRaises(ValueError):
                                instance.verify("claim")
                        else:
                            instance.verify("claim")
                    state.clear()
                    state.update(original)

    def test_partial_broadcast_receipts_survive_forge_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output = root / "evidence"
            output.mkdir()
            instance = demo.Demo(output)
            instance.context = {"completed": [], "actors": {"admin": "0xadmin"}, "addresses": {},
                                "rpc_url": "http://127.0.0.1:8545", "last_block": 0}
            instance.identity = MagicMock()
            instance.command = MagicMock(side_effect=RuntimeError("Forge failed after publishing"))
            instance.rpc = MagicMock()
            instance.rpc.call.return_value = {"status": "0x1", "blockNumber": "0x1"}
            broadcast = root / "broadcast/Deploy.s.sol/31337/run-latest.json"
            broadcast.parent.mkdir(parents=True)
            broadcast.write_text(json.dumps({"transactions": [{"hash": "0xtx", "contractName": "BUSD"}]}))
            with patch.object(demo, "ROOT", root), self.assertRaises(RuntimeError):
                instance.stage("deploy")
            report = json.loads((output / "result.json").read_text())
            self.assertEqual(report["stages"][0]["transactions"][0]["hash"], "0xtx")
            self.assertTrue((output / "deploy-broadcast.json").exists())


if __name__ == "__main__":
    unittest.main()
