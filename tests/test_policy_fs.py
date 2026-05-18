from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

import pytest

from hframe.policy_fs import (
    MODE_HFRAME_DIR,
    MODE_POLICY_FILE,
    MODE_POLICY_FILE_OPERATOR_WRITE,
    harden_hframe_bundle,
    permit_policy_vault_rewrite,
)


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX chmod only")
def test_harden_hframe_bundle_sets_modes(tmp_path: Path) -> None:
    hf = tmp_path / ".hframe"
    hf.mkdir()
    allow = hf / "policy.allowlist"
    allow.write_text("src/**\n", encoding="utf-8")
    harden_hframe_bundle(hf, policy_paths=[allow])
    assert stat.S_IMODE(os.stat(hf).st_mode) == MODE_HFRAME_DIR
    assert stat.S_IMODE(os.stat(allow).st_mode) == MODE_POLICY_FILE


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX chmod only")
def test_permit_policy_vault_rewrite_allows_owner_write(tmp_path: Path) -> None:
    hf = tmp_path / ".hframe"
    hf.mkdir()
    vault = hf / "policy.allowlist.vault"
    vault.write_text("x", encoding="utf-8")
    harden_hframe_bundle(hf, policy_paths=[vault])
    assert not (stat.S_IMODE(os.stat(vault).st_mode) & stat.S_IWUSR)
    permit_policy_vault_rewrite(hf)
    assert stat.S_IMODE(os.stat(vault).st_mode) == MODE_POLICY_FILE_OPERATOR_WRITE
