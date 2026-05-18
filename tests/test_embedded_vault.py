from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

import pytest

pytest.importorskip("cryptography")

from hframe.embedded import main
from hframe.policy_vault import key_to_b64, write_vault_file


def test_embedded_relative_vault_cfg(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "parent"
    orig = root / "orig_repo"
    ws = root / "ws_repo"
    hf = root / ".hframe"
    pyz = hf / "hframe-membrane.pyz"
    key = b"x" * 32
    orig.mkdir(parents=True)
    (orig / ".git").mkdir()
    ws.mkdir(parents=True)
    (ws / ".git").mkdir()
    hf.mkdir(parents=True)
    write_vault_file(hf / "policy.allowlist.vault", "src/**\n", key)
    write_vault_file(hf / "policy.denylist.vault", "#\n", key)
    pyz.write_text("x", encoding="utf-8")

    cfg = {
        "original_rel": "orig_repo",
        "workspace_rel": "ws_repo",
        "policy_vault": {
            "allow_rel": ".hframe/policy.allowlist.vault",
            "deny_rel": ".hframe/policy.denylist.vault",
            "key_b64": key_to_b64(key),
        },
    }
    called: dict[str, object] = {}

    def fake_sync_in(c):
        called["cfg"] = c

    monkeypatch.setattr(sys, "argv", [str(pyz), "in"])
    with mock.patch("hframe.embedded.sync_in", fake_sync_in):
        assert main(cfg) == 0
    hcfg = called["cfg"]
    assert hcfg.policy_vault is not None
    assert hcfg.policy_vault.allow.name == "policy.allowlist.vault"
    assert hcfg.policy is None
