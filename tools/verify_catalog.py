#!/usr/bin/env python3
"""Verify the NEZU Arca platform catalog the same way the application does.

Checks, in order:
  1. the detached Ed25519 signature of ``catalog.json`` against the public key Arca ships with;
  2. that every icon listed in the catalog exists and matches its SHA-256 fingerprint.

Usage:
  python tools/verify_catalog.py                 # verifies assets/catalog.json of this checkout
  python tools/verify_catalog.py --remote        # downloads the published catalog from GitHub and verifies it

Requires: pip install cryptography
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
import urllib.request
from pathlib import Path

try:
    from cryptography.exceptions import InvalidSignature
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
except ImportError:  # pragma: no cover - friendlier message than a traceback
    sys.exit("Falta la dependencia 'cryptography': pip install cryptography")

# The Ed25519 public key embedded in NEZU Arca. Anyone can verify with it; only NEZU holds the private key.
ARCA_PUBLIC_KEY_HEX = "170e1e42525574a7cc3e0cf25af429f0c797978936de5fd22a12e3d80424f921"

ASSET_BASE_URL = "https://raw.githubusercontent.com/NezuSas/nezu-arca-releases/main/assets/"
REPO_ROOT = Path(__file__).resolve().parents[1]
ASSETS_DIR = REPO_ROOT / "assets"


def canonical_catalog(catalog: dict) -> bytes:
    """Serialise the catalog exactly as ``tools/sign_catalog.py`` does, so the bytes under the signature match."""
    payload = {
        "schema_version": catalog["schema_version"],
        "catalog_version": catalog["catalog_version"],
        "platforms": catalog["platforms"],
    }
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")


def verify_signature(catalog: dict, signature_b64: str, public_key_hex: str = ARCA_PUBLIC_KEY_HEX) -> None:
    signature = base64.b64decode(signature_b64.strip(), validate=True)
    key = Ed25519PublicKey.from_public_bytes(bytes.fromhex(public_key_hex))
    key.verify(signature, canonical_catalog(catalog))


def verify_icons(catalog: dict, read_icon) -> list[str]:
    """Return the names of the icons whose SHA-256 does not match (or that cannot be read)."""
    failures: list[str] = []
    for platform in catalog.get("platforms", []):
        icon = platform.get("icon")
        expected = (platform.get("sha256") or "").lower()
        if not icon or not expected:
            failures.append(f"{platform.get('name', '?')}: entrada sin icono o sin huella")
            continue
        try:
            actual = hashlib.sha256(read_icon(icon)).hexdigest()
        except Exception as exc:  # noqa: BLE001 - we report every failure, whatever its cause
            failures.append(f"{icon}: no se pudo leer ({exc})")
            continue
        if actual != expected:
            failures.append(f"{icon}: huella {actual[:12]}… no coincide con {expected[:12]}…")
    return failures


def load_local() -> tuple[dict, str, callable]:
    catalog = json.loads((ASSETS_DIR / "catalog.json").read_text(encoding="utf-8"))
    signature = (ASSETS_DIR / "catalog.json.sig").read_text(encoding="utf-8")
    return catalog, signature, lambda icon: (ASSETS_DIR / icon).read_bytes()


def load_remote() -> tuple[dict, str, callable]:
    def fetch(path: str, limit: int) -> bytes:
        with urllib.request.urlopen(ASSET_BASE_URL + path, timeout=20) as response:  # noqa: S310 - fixed https host
            data = response.read(limit + 1)
        if len(data) > limit:
            raise ValueError(f"{path} supera el tamaño esperado")
        return data

    catalog = json.loads(fetch("catalog.json", 1024 * 1024).decode("utf-8"))
    signature = fetch("catalog.json.sig", 16 * 1024).decode("utf-8")
    return catalog, signature, lambda icon: fetch(icon, 2 * 1024 * 1024)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--remote", action="store_true", help="verificar el catálogo publicado en GitHub en vez del local")
    parser.add_argument("--public-key", default=ARCA_PUBLIC_KEY_HEX, help="clave pública Ed25519 en hexadecimal (por defecto, la de Arca)")
    args = parser.parse_args()

    catalog, signature, read_icon = load_remote() if args.remote else load_local()
    origin = "publicado" if args.remote else "local"

    try:
        verify_signature(catalog, signature, args.public_key)
    except (InvalidSignature, ValueError) as exc:
        reason = str(exc) or "la firma no corresponde a esta clave pública o el catálogo fue modificado"
        print(f"FIRMA INVÁLIDA en el catálogo {origin}: {reason}")
        return 1
    print(f"Firma válida: el catálogo {origin} (versión {catalog.get('catalog_version', '?')}) fue firmado con la clave de NEZU Arca.")

    failures = verify_icons(catalog, read_icon)
    total = len(catalog.get("platforms", []))
    if failures:
        print(f"{len(failures)} de {total} iconos NO coinciden con su huella:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"Huellas correctas: los {total} iconos coinciden con el catálogo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
