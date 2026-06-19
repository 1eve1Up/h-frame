from __future__ import annotations

from pathlib import Path

import pytest

cryptography = pytest.importorskip("cryptography")

from hframe.env_vars import (  # noqa: E402
    H_FRAME_BOOTSTRAP_DEBUG,
    H_FRAME_VAULT_PASS,
    LEGACY_HFRAME_BOOTSTRAP_DEBUG,
    LEGACY_HFRAME_VAULT_PASS,
)
from hframe.policy_vault import (  # noqa: E402
    bootstrap_debug_enabled,
    decrypt_policy_blob,
    emit_vault_password_debug,
    encrypt_policy_plaintext,
    generate_vault_key,
    key_from_b64,
    key_to_b64,
    membrane_vault_key,
    read_vault_file,
    vault_password_from_env,
    write_vault_file,
)


def test_round_trip_encrypt_decrypt() -> None:
    key = generate_vault_key()
    plain = "# hframe-policy: mode allowlist\nsrc/**\n"
    blob = encrypt_policy_plaintext(plain, key)
    assert blob.startswith("HFV1\n")
    assert decrypt_policy_blob(blob, key) == plain


def test_wrong_key_fails() -> None:
    key = generate_vault_key()
    blob = encrypt_policy_plaintext("x\n", key)
    with pytest.raises(Exception):
        decrypt_policy_blob(blob, generate_vault_key())


def test_corrupt_blob_fails() -> None:
    key = generate_vault_key()
    with pytest.raises(ValueError, match="HFV1"):
        decrypt_policy_blob("NOPE\n", key)


def test_key_b64_round_trip() -> None:
    key = generate_vault_key()
    assert key_from_b64(key_to_b64(key)) == key


def test_vault_password_from_env_required(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(H_FRAME_VAULT_PASS, raising=False)
    monkeypatch.delenv(LEGACY_HFRAME_VAULT_PASS, raising=False)
    with pytest.raises(ValueError, match=H_FRAME_VAULT_PASS):
        vault_password_from_env()


def test_vault_password_from_env_legacy_name(monkeypatch: pytest.MonkeyPatch) -> None:
    key = generate_vault_key()
    monkeypatch.delenv(H_FRAME_VAULT_PASS, raising=False)
    monkeypatch.setenv(LEGACY_HFRAME_VAULT_PASS, key_to_b64(key))
    assert vault_password_from_env() == key


def test_emit_vault_password_debug(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    key = generate_vault_key()
    monkeypatch.delenv(H_FRAME_BOOTSTRAP_DEBUG, raising=False)
    monkeypatch.delenv(LEGACY_HFRAME_BOOTSTRAP_DEBUG, raising=False)
    emit_vault_password_debug(key)
    assert capsys.readouterr().out == ""
    monkeypatch.setenv(H_FRAME_BOOTSTRAP_DEBUG, "1")
    assert bootstrap_debug_enabled()
    emit_vault_password_debug(key)
    out = capsys.readouterr().out
    assert H_FRAME_VAULT_PASS in out
    assert key_to_b64(key) in out


def test_bootstrap_debug_legacy_env_name(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(H_FRAME_BOOTSTRAP_DEBUG, raising=False)
    monkeypatch.setenv(LEGACY_HFRAME_BOOTSTRAP_DEBUG, "1")
    assert bootstrap_debug_enabled()


def test_write_read_vault_file(tmp_path: Path) -> None:
    key = generate_vault_key()
    path = tmp_path / "policy.allowlist.vault"
    write_vault_file(path, "a\n", key)
    assert read_vault_file(path, key) == "a\n"


def test_membrane_vault_key_from_stub_pyz(tmp_path: Path) -> None:
    import json
    import zipfile

    key = b"m" * 32
    hf = tmp_path / ".hframe"
    hf.mkdir()
    cfg = json.dumps(
        {"policy_vault": {"key_b64": key_to_b64(key)}},
        separators=(",", ":"),
    )
    pyz = hf / "hframe-membrane.pyz"
    with zipfile.ZipFile(pyz, "w") as zf:
        zf.writestr("__main__.py", f"import json\n_CFG=json.loads({cfg!r})\n")
    assert membrane_vault_key(hf) == key
