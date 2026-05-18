"""Encrypt host-local policy files at bootstrap; key embedded only in the membrane zipapp."""

from __future__ import annotations

import base64
import secrets
from pathlib import Path

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
        raise ValueError("vault key must decode to 32 bytes")
    return key


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
