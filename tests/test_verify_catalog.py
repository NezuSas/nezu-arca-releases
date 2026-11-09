import base64
import hashlib
import json
import unittest
from pathlib import Path
import sys

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from sign_catalog import canonical_catalog as sign_canonical
from verify_catalog import ARCA_PUBLIC_KEY_HEX, canonical_catalog, verify_icons, verify_signature

ASSETS = Path(__file__).resolve().parents[1] / "assets"


class VerifyCatalogTests(unittest.TestCase):
    def test_canonical_form_matches_the_signer(self):
        catalog = {"schema_version": 1, "catalog_version": "1.0.0", "platforms": [{"name": "A", "icon": "platforms/a.png", "sha256": "00"}], "extra": "ignored"}
        self.assertEqual(canonical_catalog(catalog), sign_canonical(catalog))

    def test_published_catalog_is_signed_with_the_arca_key(self):
        catalog = json.loads((ASSETS / "catalog.json").read_text(encoding="utf-8"))
        signature = (ASSETS / "catalog.json.sig").read_text(encoding="utf-8")
        verify_signature(catalog, signature, ARCA_PUBLIC_KEY_HEX)
        self.assertEqual(verify_icons(catalog, lambda icon: (ASSETS / icon).read_bytes()), [])

    def test_a_modified_catalog_or_another_key_is_rejected(self):
        catalog = json.loads((ASSETS / "catalog.json").read_text(encoding="utf-8"))
        signature = (ASSETS / "catalog.json.sig").read_text(encoding="utf-8")
        tampered = dict(catalog, catalog_version="9.9.9")
        with self.assertRaises(InvalidSignature):
            verify_signature(tampered, signature, ARCA_PUBLIC_KEY_HEX)
        other_key = Ed25519PrivateKey.generate().public_key().public_bytes_raw().hex()
        with self.assertRaises(InvalidSignature):
            verify_signature(catalog, signature, other_key)

    def test_icon_fingerprint_mismatch_is_reported_by_name(self):
        catalog = {"schema_version": 1, "catalog_version": "1.0.0", "platforms": [
            {"name": "Buena", "icon": "platforms/ok.png", "sha256": hashlib.sha256(b"ok").hexdigest()},
            {"name": "Mala", "icon": "platforms/bad.png", "sha256": hashlib.sha256(b"original").hexdigest()},
        ]}
        failures = verify_icons(catalog, lambda icon: b"ok" if icon.endswith("ok.png") else b"changed")
        self.assertEqual(len(failures), 1)
        self.assertTrue(failures[0].startswith("platforms/bad.png"))

    def test_signature_roundtrip_with_a_fresh_key(self):
        private = Ed25519PrivateKey.generate()
        catalog = {"schema_version": 1, "catalog_version": "2.0.0", "platforms": []}
        signature = base64.b64encode(private.sign(canonical_catalog(catalog))).decode("ascii")
        verify_signature(catalog, signature, private.public_key().public_bytes_raw().hex())


if __name__ == "__main__":
    unittest.main()
