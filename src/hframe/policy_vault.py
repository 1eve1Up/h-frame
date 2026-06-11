"""Encrypt host-local policy; one-time vault password compiled into hframe-membrane.pyz."""

from __future__ import annotations

import base64
import os
import secrets
import sys
from pathlib import Path

BOOTSTRAP_DEBUG_ENV = "HFRAME_BOOTSTRAP_DEBUG"
VAULT_PASS_ENV = "HFRAME_VAULT_PASS"

VAULT_MAGIC = "HFV1"
ALLOW_VAULT_NAME = "policy.allowlist.vault"
DENY_VAULT_NAME = "policy.denylist.vault"


def require_cryptography():
    """Import ``cryptography`` or raise with install hint."""
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as e:
        raise ImportError(
            "policy vault requires the cryptography package; "
            "install with: pip install 'hframe[vault]'"
        ) from e
    return AESGCM


def generate_vault_key() -> bytes:
    return secrets.token_bytes(32)


def key_to_b64(key: bytes) -> str:
    return base64.urlsafe_b64encode(key).decode("ascii")


def key_from_b64(token: str) -> bytes:
    key = base64.urlsafe_b64decode(token.encode("ascii"))
    if len(key) != 32:
        raise ValueError("vault password must decode to 32 bytes (url-safe base64)")
    return key


def bootstrap_debug_enabled() -> bool:
    return os.environ.get(BOOTSTRAP_DEBUG_ENV) == "1"


def emit_vault_password_debug(key: bytes) -> None:
    """Print compiled vault password when ``HFRAME_BOOTSTRAP_DEBUG=1`` at bootstrap."""
    if not bootstrap_debug_enabled():
        return
    sys.stdout.write(
        "hframe-bootstrap: vault password "
        f"(export {VAULT_PASS_ENV}={key_to_b64(key)!r} for ./hframe-vault)\n"
    )
    sys.stdout.flush()


def vault_password_from_env() -> bytes:
    """Operator-supplied vault password (must match the value compiled into the zipapp)."""
    token = os.environ.get(VAULT_PASS_ENV, "").strip()
    if not token:
        raise ValueError(
            f"{VAULT_PASS_ENV} must be set to the vault password "
            "(printed at bootstrap when HFRAME_BOOTSTRAP_DEBUG=1, or from your records)"
        )
    return key_from_b64(token)


def embedded_vault_key_b64_from_hframe(hframe_dir: Path) -> str:
    """Read compiled ``policy_vault.key_b64`` from ``hframe-membrane.pyz``."""
    import re
    import zipfile

    from hframe.config import MEMBRANE_PYZ_NAME

    pyz = hframe_dir / MEMBRANE_PYZ_NAME
    if not pyz.is_file():
        raise ValueError(f"membrane zipapp not found: {pyz}")
    src = zipfile.ZipFile(pyz).read("__main__.py").decode()
    m = re.search(r'"key_b64":"([^"]+)"', src.replace(" ", ""))
    if not m:
        raise ValueError(
            "hframe-membrane.pyz has no policy_vault.key_b64 (not a --vault bootstrap?)"
        )
    return m.group(1)


def membrane_vault_key(hframe_dir: Path) -> bytes:
    """Password compiled into ``hframe-membrane.pyz``; used by ``./hframe in|out``."""
    return key_from_b64(embedded_vault_key_b64_from_hframe(hframe_dir))


def assert_vault_password_matches_membrane(hframe_dir: Path) -> bytes:
    """Return env password after checking it matches the compiled membrane password."""
    operator_key = vault_password_from_env()
    if operator_key != membrane_vault_key(hframe_dir):
        raise ValueError(
            f"{VAULT_PASS_ENV} does not match the vault password compiled into "
            "hframe-membrane.pyz"
        )
    return operator_key


def encrypt_policy_plaintext(plaintext: str, key: bytes) -> str:
    AESGCM = require_cryptography()
    nonce = secrets.token_bytes(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext.encode("utf-8"), None)
    payload = base64.b64encode(nonce + ciphertext).decode("ascii")
    return f"{VAULT_MAGIC}\n{payload}\n"


def decrypt_policy_blob(blob: str, key: bytes) -> str:
    AESGCM = require_cryptography()
    lines = blob.splitlines()
    if len(lines) < 2 or lines[0].strip() != VAULT_MAGIC:
        raise ValueError("invalid policy vault envelope (expected HFV1 header)")
    raw = base64.b64decode(lines[1].encode("ascii"))
    if len(raw) < 13:
        raise ValueError("invalid policy vault payload")
    nonce, ciphertext = raw[:12], raw[12:]
    return AESGCM(key).decrypt(nonce, ciphertext, None).decode("utf-8")


def write_vault_file(path: Path, plaintext: str, key: bytes) -> None:
    path.write_text(encrypt_policy_plaintext(plaintext, key), encoding="utf-8")


def read_vault_file(path: Path, key: bytes) -> str:
    return decrypt_policy_blob(path.read_text(encoding="utf-8"), key)


def seal_policy_files(
    hframe_dir: Path,
    *,
    allow_plain: Path,
    deny_plain: Path,
    key: bytes,
) -> tuple[Path, Path]:
    """Encrypt plaintext policy files, delete plaintext, return vault paths."""
    allow_vault = hframe_dir / ALLOW_VAULT_NAME
    deny_vault = hframe_dir / DENY_VAULT_NAME
    write_vault_file(allow_vault, allow_plain.read_text(encoding="utf-8"), key)
    write_vault_file(deny_vault, deny_plain.read_text(encoding="utf-8"), key)
    allow_plain.unlink(missing_ok=True)
    deny_plain.unlink(missing_ok=True)
    return allow_vault, deny_vault
