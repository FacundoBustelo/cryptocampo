"""Pruebas sin red del verificador; no acreditan publicación IPFS ni ejecución EVM."""

import base64
import copy
import importlib.util
import json
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("verify_metadata", Path(__file__).with_name("verify-metadata.py"))
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class Response:
    def __init__(self, data, url):
        self.data, self.url, self.status = data, url, 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self, size):
        return self.data[:size]


class MetadataVerifierTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.output = self.root / "downloads"
        self.manifest = json.loads((verifier.ROOT / "docs/ipfs-publication.json").read_text())
        self.content = {}
        for name, path in verifier.PATHS.items():
            data = (verifier.ROOT / path).read_bytes()
            target = self.root / path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            self.content[name] = data
        self.patch_root = patch.object(verifier, "ROOT", self.root)
        self.patch_root.start()
        self.addCleanup(self.patch_root.stop)
        # CIDs sintéticos solo para fixtures: jamás se usan para descargas públicas.
        for index, resource in enumerate(self.manifest["resources"].values()):
            cid = "b" + base64.b32encode(b"\x01\x55\x12\x20" + bytes([index]) * 32).decode().lower().rstrip("=")
            resource.update(cid=cid, uri=f"ipfs://{cid}", published_at="2026-01-01T00:00:00Z")
            resource["pinning"].update(status="confirmed_by_user", confirmed_at="2026-01-01T00:00:00Z",
                                       evidence="Declaración de prueba, sin publicación real.")
        metadata = json.loads(self.content["metadata"])
        metadata["image"] = self.manifest["resources"]["image"]["uri"]
        metadata["description"] = metadata["description"].split(" La imagen usa")[0]
        self.write_metadata(json.dumps(metadata, ensure_ascii=False).encode())
        self.manifest["visual_review"].update(status="verified", reviewed_by="Fixture de prueba", reviewed_at="2026-01-01T00:00:00Z",
            sha256=verifier.digest(self.content["image"]), evidence="Revisión de prueba.")

    def write_metadata(self, data):
        self.content["metadata"] = data
        (self.root / verifier.PATHS["metadata"]).write_bytes(data)
        self.manifest["resources"]["metadata"]["sha256"] = verifier.digest(data)

    def respond(self, request, timeout):
        for name, resource in self.manifest["resources"].items():
            if request.full_url.endswith(resource["cid"]):
                return Response(self.content[name], request.full_url)
        raise AssertionError("URL inesperada")

    @staticmethod
    def anvil_passes(uri, result):
        result.update(status="verified", uri=uri)

    def test_local_validation_never_uses_network_or_anvil(self):
        with patch.object(verifier.urllib.request, "urlopen") as network, \
                patch.object(verifier, "verify_anvil") as anvil:
            result = verifier.verify(self.manifest, "local", self.output, 1)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["resources"]["metadata"]["local"], "verified")
        network.assert_not_called()
        anvil.assert_not_called()

    def test_missing_cids_do_not_download_or_run_anvil(self):
        for resource in self.manifest["resources"].values():
            resource["cid"] = None
        with patch.object(verifier.urllib.request, "urlopen") as network, \
                patch.object(verifier, "verify_anvil") as anvil:
            result = verifier.verify(self.manifest, "full", self.output, 1)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(any("image:" in message for message in result["pending"]))
        network.assert_not_called()
        anvil.assert_not_called()

    def test_all_four_downloads_and_anvil_are_required(self):
        with patch.object(verifier.urllib.request, "urlopen", side_effect=self.respond) as network, \
                patch.object(verifier, "verify_anvil", side_effect=self.anvil_passes) as anvil:
            result = verifier.verify(self.manifest, "full", self.output, 1)
        self.assertEqual(result["status"], "verified")
        self.assertEqual(network.call_count, 4)
        anvil.assert_called_once_with(self.manifest["resources"]["metadata"]["uri"], result["anvil"])
        self.assertEqual((self.output / "0/certificate.svg").read_bytes(), self.content["image"])

    def test_failed_gateway_invalidates_stale_success_and_reports_resource(self):
        self.manifest["verification"] = {"status": "verified"}

        def fail_one(request, timeout):
            if request.full_url.startswith(verifier.GATEWAYS[1]) and request.full_url.endswith(
                    self.manifest["resources"]["image"]["cid"]):
                raise urllib.error.URLError("Fixture: gateway no disponible")
            return self.respond(request, timeout)

        with patch.object(verifier.urllib.request, "urlopen", side_effect=fail_one) as network, \
                patch.object(verifier, "verify_anvil") as anvil:
            result = verifier.verify(self.manifest, "full", self.output, 1)
        self.assertEqual(result["status"], "pending")
        self.assertEqual(network.call_count, 4)
        self.assertTrue(any("image:" in p and verifier.GATEWAYS[1] in p for p in result["pending"]))
        anvil.assert_not_called()

    def test_directory_or_mismatched_content_is_not_accepted(self):
        self.output.mkdir()
        (self.output / "image.svg").write_bytes(b"evidencia anterior")
        with patch.object(verifier.urllib.request, "urlopen", return_value=Response(b"<html>folder</html>", "https://example.invalid")):
            result = verifier.download(self.manifest["resources"]["image"], self.content["image"],
                                       verifier.GATEWAYS[0], self.output / "image.svg", 1)
        self.assertEqual(result["status"], "pending")
        self.assertIn("bytes", result["error"])
        self.assertFalse((self.output / "image.svg").exists())

    def test_wrong_image_reference_blocks_anvil_even_if_bytes_match(self):
        value = json.loads(self.content["metadata"])
        value["image"] = "http://127.0.0.1:8000/certificate.svg"
        self.write_metadata(json.dumps(value).encode())
        with patch.object(verifier.urllib.request, "urlopen", side_effect=self.respond), \
                patch.object(verifier, "verify_anvil") as anvil:
            result = verifier.verify(self.manifest, "full", self.output, 1)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(any("metadata.image" in p for p in result["pending"]))
        anvil.assert_not_called()

    def test_downloads_do_not_prove_pinning_or_visual_review(self):
        for field in ("pinning", "visual_review"):
            manifest = copy.deepcopy(self.manifest)
            if field == "pinning":
                manifest["resources"]["image"]["pinning"]["status"] = "pending"
            else:
                manifest["visual_review"]["status"] = "pending"
            with self.subTest(field=field), \
                    patch.object(verifier.urllib.request, "urlopen", side_effect=self.respond), \
                    patch.object(verifier, "verify_anvil", side_effect=self.anvil_passes):
                result = verifier.verify(manifest, "full", self.output, 1)
                self.assertEqual(result["status"], "pending")

    def test_anvil_failure_is_pending(self):
        with patch.object(verifier.urllib.request, "urlopen", side_effect=self.respond), \
                patch.object(verifier, "verify_anvil", side_effect=ValueError("URI incorrecta: NFT 1")):
            result = verifier.verify(self.manifest, "full", self.output, 1)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(any("Anvil: URI incorrecta" in p for p in result["pending"]))

    def test_image_stage_never_claims_full_verification(self):
        with patch.object(verifier.urllib.request, "urlopen", side_effect=self.respond) as network, \
                patch.object(verifier, "verify_anvil") as anvil:
            result = verifier.verify(self.manifest, "image", self.output, 1)
        self.assertEqual(result["image_publication"], "verified")
        self.assertEqual(result["status"], "pending")
        self.assertEqual(network.call_count, 2)
        anvil.assert_not_called()

    def test_local_file_change_requires_updating_evidence(self):
        (self.root / verifier.PATHS["image"]).write_bytes(self.content["image"] + b"\n")
        with self.assertRaisesRegex(ValueError, "SHA-256"):
            verifier.verify(self.manifest, "local", self.output, 1)

    def test_cids_must_be_individual_content_identifiers(self):
        cid = self.manifest["resources"]["image"]["cid"]
        self.assertEqual(verifier.validate_cid(cid), cid)
        for bad in (None, "<CID_REAL>", "ipfs://" + cid, cid + "/certificate.svg", cid + "?key=secret", "b1234"):
            with self.subTest(cid=bad), self.assertRaises(ValueError):
                verifier.validate_cid(bad)

    def test_publication_accepts_a_visible_date_without_inventing_a_time(self):
        resource = copy.deepcopy(self.manifest["resources"]["image"])
        resource.update(published_at=None, published_on="2026-01-01")
        self.assertEqual(verifier.publication(resource), resource["cid"])
        self.assertIsNone(resource["published_at"])
        for bad in (None, "2026-99-99", "9999-01-01"):
            resource["published_on"] = bad
            with self.subTest(date=bad), self.assertRaises(ValueError):
                verifier.publication(resource)

    def test_missing_publication_date_does_not_skip_downloads_or_claim_success(self):
        metadata = self.manifest["resources"]["metadata"]
        metadata["published_at"] = None
        metadata.pop("published_on", None)
        with patch.object(verifier.urllib.request, "urlopen", side_effect=self.respond) as network, \
                patch.object(verifier, "verify_anvil", side_effect=self.anvil_passes):
            result = verifier.verify(self.manifest, "full", self.output, 1)
        self.assertEqual(network.call_count, 4)
        self.assertEqual(result["status"], "pending")
        self.assertTrue(any("metadata: Falta fecha de publicación" in p for p in result["pending"]))

    def test_duplicate_keys_and_extra_fields_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicada"):
            verifier.validate_metadata(b'{"image":"a","image":"b"}')
        value = json.loads(self.content["metadata"])
        value["tokenId"] = "1"
        with self.assertRaisesRegex(ValueError, "únicamente"):
            verifier.validate_metadata(json.dumps(value).encode())

    def test_network_errors_are_not_treated_as_expected_reverts(self):
        class BrokenRPC:
            def call(self, *_):
                raise urllib.error.URLError("Fixture: RPC desconectado")

        with self.assertRaises(urllib.error.URLError):
            verifier.expect_revert(BrokenRPC(), {}, "Token does not exist")

    def test_revert_reason_must_be_exact(self):
        class WrongRevertRPC:
            def call(self, *_):
                reason = b"Wrong reason"
                payload = verifier.word(32) + verifier.word(len(reason)) + reason.hex().ljust(64, "0")
                raise verifier.RevertError({"data": "0x08c379a0" + payload})

        with self.assertRaisesRegex(ValueError, "inesperada"):
            verifier.expect_revert(WrongRevertRPC(), {}, "Token does not exist")


if __name__ == "__main__":
    unittest.main()
