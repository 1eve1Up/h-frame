from __future__ import annotations

import json
import os
import stat
import sys
import zipfile
from pathlib import Path

import pytest

pytest.importorskip("cryptography")

from hframe.policy_vault import (
    VAULT_PASS_ENV,
    assert_vault_password_matches_membrane,
    key_to_b64,
    membrane_vault_key,
    read_vault_file,
    write_vault_file,
)
from hframe.shim_install import install_bootstrap_vault_cli
from hframe.vault_cli import cmd_decrypt, cmd_encrypt, main


def _write_stub_pyz(hf: Path, key: bytes) -> None:
    cfg = json.dumps(
        {"policy_vault": {"key_b64": key_to_b64(key)}}, separators=(",", ":")
    )
    with zipfile.ZipFile(hf / "hframe-membrane.pyz", "w") as zf:
        zf.writestr("__main__.py", f"import json\n_CFG=json.loads({cfg!r})\n")


def _layout(tmp_path: Path, key: bytes) -> Path:
    root = tmp_path / "parent"
    hf = root / ".hframe"
    hf.mkdir(parents=True)
    write_vault_file(hf / "policy.allowlist.vault", "src/**\n", key)
    write_vault_file(hf / "policy.denylist.vault", "#\n", key)
    _write_stub_pyz(hf, key)
    (root / "hframe-vault").write_text("#!/usr/bin/env python3\n", encoding="utf-8")
    return root


def test_encrypt_requires_matching_env_password(tmp_path: Path) -> None:
    key = b"k" * 32
    root = _layout(tmp_path, key)
    hf = root / ".hframe"
    os.environ[VAULT_PASS_ENV] = key_to_b64(b"z" * 32)
    try:
        with pytest.raises(ValueError, match="does not match"):
            assert_vault_password_matches_membrane(hf)
    finally:
        os.environ.pop(VAULT_PASS_ENV, None)


def test_decrypt_encrypt_roundtrip(tmp_path: Path) -> None:
    key = b"x" * 32
    root = _layout(tmp_path, key)
    hf = root / ".hframe"
    os.environ[VAULT_PASS_ENV] = key_to_b64(key)
    try:
        cmd_decrypt(hf, "allowlist", key)
        edit = hf / "policy.allowlist.edit"
        edit.write_text("lib/**\n", encoding="utf-8")
        cmd_encrypt(hf, "allowlist", assert_vault_password_matches_membrane(hf))
        assert not edit.exists()
        assert "lib/**" in read_vault_file(
            hf / "policy.allowlist.vault", membrane_vault_key(hf)
        )
    finally:
        os.environ.pop(VAULT_PASS_ENV, None)


def test_main_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    key = b"z" * 32
    root = _layout(tmp_path, key)
    script = str(root / "hframe-vault")
    monkeypatch.setenv(VAULT_PASS_ENV, key_to_b64(key))
    monkeypatch.setattr(sys, "argv", [script, "decrypt", "allowlist"])
    assert main() == 0
    monkeypatch.setattr(sys, "argv", [script, "encrypt", "allowlist"])
    assert main() == 0


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX vault script install")
def test_install_bootstrap_vault_cli(tmp_path: Path) -> None:
    root = tmp_path / "parent"
    root.mkdir()
    dest = install_bootstrap_vault_cli(root)
    assert dest.read_text(encoding="utf-8").startswith(f"#!{sys.executable}")
    assert stat.S_IMODE(dest.stat().st_mode) & stat.S_IXUSR
