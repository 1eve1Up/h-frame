from __future__ import annotations

import stat
import subprocess
import sys
from pathlib import Path

import pytest

from hframe.shim_install import install_workspace_shim, resolve_membrane_pyz


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX layout")
def test_resolve_membrane_pyz_canonical(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    ws = parent / "my_workspace_repo"
    hf = parent / ".hframe"
    ws.mkdir(parents=True)
    hf.mkdir()
    pyz = hf / "hframe-membrane.pyz"
    pyz.write_text("x", encoding="utf-8")
    assert resolve_membrane_pyz(ws) == pyz.resolve()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX layout")
def test_resolve_membrane_pyz_unique_sibling_hframe_root(tmp_path: Path) -> None:
    workspaces = tmp_path / "workspaces"
    workspaces.mkdir()
    ws = workspaces / "podbay_workspace_repo"
    mount = workspaces / "hframe-root"
    hf = mount / ".hframe"
    ws.mkdir()
    hf.mkdir(parents=True)
    pyz = hf / "hframe-membrane.pyz"
    pyz.write_text("x", encoding="utf-8")
    assert resolve_membrane_pyz(ws) == pyz.resolve()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX layout")
def test_resolve_membrane_pyz_nonstandard_sibling_dir_name(tmp_path: Path) -> None:
    root = tmp_path / "workspaces"
    root.mkdir()
    ws = root / "podbay_workspace_repo"
    acme = root / "acme"
    hf = acme / ".hframe"
    ws.mkdir(parents=True)
    hf.mkdir(parents=True)
    pyz = hf / "hframe-membrane.pyz"
    pyz.write_text("x", encoding="utf-8")
    assert resolve_membrane_pyz(ws) == pyz.resolve()


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX layout")
def test_resolve_membrane_pyz_explicit_hframe_root_beats_other_siblings(
    tmp_path: Path,
) -> None:
    """README ``hframe-root`` path wins when multiple siblings ship a membrane."""
    root = tmp_path / "workspaces"
    root.mkdir()
    ws = root / "podbay_workspace_repo"
    ws.mkdir()
    for name in ("noise", "hframe-root"):
        d = root / name / ".hframe"
        d.mkdir(parents=True)
        (d / "hframe-membrane.pyz").write_text("x", encoding="utf-8")
    expected = (root / "hframe-root" / ".hframe" / "hframe-membrane.pyz").resolve()
    assert resolve_membrane_pyz(ws) == expected


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX layout")
def test_resolve_membrane_pyz_ambiguous_returns_none(tmp_path: Path) -> None:
    parent = tmp_path / "workspaces"
    parent.mkdir()
    ws = parent / "ws"
    ws.mkdir()
    for name in ("a", "b"):
        d = parent / name / ".hframe"
        d.mkdir(parents=True)
        (d / "hframe-membrane.pyz").write_text("x", encoding="utf-8")
    assert resolve_membrane_pyz(ws) is None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX layout")
def test_resolve_membrane_pyz_missing_returns_none(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    assert resolve_membrane_pyz(ws) is None


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX launcher is a Python script")
def test_posix_workspace_bridge_is_executable_python_script(tmp_path: Path) -> None:
    dest = tmp_path / "hframe"
    install_workspace_shim(dest)
    text = dest.read_text(encoding="utf-8")
    assert text.startswith("#!/usr/bin/env python3\n")
    assert "os.execvp" in text
    assert "hframe-membrane.pyz" in text
    assert "_resolve_pyz" in text
    mode = dest.stat().st_mode
    assert mode & stat.S_IXUSR


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX launcher")
def test_posix_launcher_rejects_bad_argv(tmp_path: Path) -> None:
    dest = tmp_path / "hframe"
    install_workspace_shim(dest)
    proc = subprocess.run(
        [sys.executable, str(dest), "nope"],
        cwd=str(tmp_path),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "usage:" in proc.stderr


@pytest.mark.skipif(sys.platform == "win32", reason="POSIX launcher")
def test_posix_launcher_missing_membrane_exits_nonzero(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    ws.mkdir()
    dest = ws / "hframe"
    install_workspace_shim(dest)
    proc = subprocess.run(
        [sys.executable, str(dest), "in"],
        cwd=str(ws),
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2
    assert "missing membrane" in proc.stderr
    assert "Tried:" in proc.stderr
