from __future__ import annotations

import sys
from pathlib import Path
from unittest import mock

from hframe import embedded
from hframe.embedded import main


def test_embedded_rejects_extra_args(tmp_path: Path, monkeypatch) -> None:
    cfg = {
        "original": str(tmp_path / "o"),
        "workspace": str(tmp_path / "w"),
        "policy": str(tmp_path / "p"),
    }
    monkeypatch.setattr(sys, "argv", ["hframe", "in", "nope"])
    assert main(cfg) == 2


def test_embedded_runs_in_with_mocked_sync(tmp_path: Path, monkeypatch) -> None:
    cfg = {
        "original": str(tmp_path / "o"),
        "workspace": str(tmp_path / "w"),
        "policy": str(tmp_path / "p"),
    }
    (tmp_path / "o").mkdir()
    (tmp_path / "o" / ".git").mkdir()
    (tmp_path / "w").mkdir()
    (tmp_path / "w" / ".git").mkdir()
    (tmp_path / "p").write_text("src/**\n", encoding="utf-8")

    called = {}

    def fake_sync_in(c):
        called["cfg"] = c

    monkeypatch.setattr(sys, "argv", ["hframe", "in"])
    with mock.patch("hframe.embedded.sync_in", fake_sync_in):
        assert main(cfg) == 0
    assert called["cfg"].original == (tmp_path / "o").resolve()


def test_embedded_relative_cfg_from_pyz_parent(tmp_path: Path, monkeypatch) -> None:
    root = tmp_path / "parent"
    orig = root / "orig_repo"
    ws = root / "ws_repo"
    hf = root / ".hframe"
    pyz = hf / "hframe-membrane.pyz"
    orig.mkdir(parents=True)
    (orig / ".git").mkdir()
    ws.mkdir(parents=True)
    (ws / ".git").mkdir()
    hf.mkdir(parents=True)
    (hf / "policy.allowlist").write_text("src/**\n", encoding="utf-8")
    pyz.write_text("not-a-real-zip", encoding="utf-8")

    cfg = {
        "original_rel": "orig_repo",
        "workspace_rel": "ws_repo",
        "policy_rel": ".hframe/policy.allowlist",
    }
    called: dict[str, object] = {}

    def fake_sync_in(c):
        called["cfg"] = c

    monkeypatch.setattr(sys, "argv", [str(pyz), "in"])
    with mock.patch("hframe.embedded.sync_in", fake_sync_in):
        assert main(cfg) == 0
    assert called["cfg"].original == orig.resolve()
    assert called["cfg"].workspace == ws.resolve()


def test_embedded_relative_cfg_uses_devcontainer_mount(
    tmp_path: Path, monkeypatch
) -> None:
    """Simulate zipapp only under .../.hframe while repos live under a sibling hframe-root."""
    flat = tmp_path / "flat"
    hr = tmp_path / "hframe-root"
    pyz = flat / ".hframe" / "hframe-membrane.pyz"
    orig = hr / "orig_repo"
    ws = hr / "ws_repo"
    pyz.parent.mkdir(parents=True)
    orig.mkdir(parents=True)
    (orig / ".git").mkdir()
    ws.mkdir(parents=True)
    (ws / ".git").mkdir()
    (hr / ".hframe").mkdir(parents=True)
    (hr / ".hframe" / "policy.allowlist").write_text("src/**\n", encoding="utf-8")
    pyz.write_text("x", encoding="utf-8")

    cfg = {
        "original_rel": "orig_repo",
        "workspace_rel": "ws_repo",
        "policy_rel": ".hframe/policy.allowlist",
    }
    monkeypatch.setattr(embedded, "DEVCONTAINER_BOOTSTRAP_ROOT", hr)
    called: dict[str, object] = {}

    def fake_sync_in(c):
        called["cfg"] = c

    monkeypatch.setattr(sys, "argv", [str(pyz), "in"])
    with mock.patch("hframe.embedded.sync_in", fake_sync_in):
        assert main(cfg) == 0
    assert called["cfg"].original == orig.resolve()
    assert called["cfg"].workspace == ws.resolve()
