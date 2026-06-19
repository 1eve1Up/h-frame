"""Packaging metadata checks."""

from __future__ import annotations

import tomllib
import zipfile
from pathlib import Path

import hframe

ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
PREBUILT_EXE = (
    ROOT / "src" / "hframe" / "native" / "prebuilt" / "h-frame-shim-windows-amd64.exe"
)


def _pyproject_version() -> str:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    return data["project"]["version"]


def test_version_matches_pyproject() -> None:
    assert hframe.__version__ == _pyproject_version()


def test_pyproject_distribution_name() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert data["project"]["name"] == "h-frame"


def test_bootstrap_console_script_name() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert "hframe-bootstrap" in scripts
    assert "h-frame-bootstrap" not in scripts


def test_vault_console_script_name() -> None:
    data = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    scripts = data["project"]["scripts"]
    assert "hframe-vault" in scripts
    assert "h-frame-vault" not in scripts


def test_windows_shim_prebuilt_exists() -> None:
    assert PREBUILT_EXE.is_file(), f"missing prebuilt Windows shim: {PREBUILT_EXE}"


def test_built_wheel_includes_windows_shim() -> None:
    dist = ROOT / "dist"
    if not dist.is_dir():
        return
    wheels = sorted(dist.glob("h_frame-*.whl"))
    if not wheels:
        return
    with zipfile.ZipFile(wheels[-1]) as zf:
        names = zf.namelist()
    assert any(name.endswith("h-frame-shim-windows-amd64.exe") for name in names)
