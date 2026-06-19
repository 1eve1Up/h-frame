"""Workspace bridge install: portable POSIX launcher; Windows prebuilt .exe only."""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path

from hframe.config import MEMBRANE_PYZ_NAME

# README devcontainer example mounts the bootstrap parent here.
_DEVCONTAINER_PARENT_MOUNT = "hframe-root"


def _package_native_dir() -> Path:
    import hframe

    return Path(hframe.__file__).resolve().parent / "native"


def shim_resource_tag() -> str | None:
    """Return prebuilt Windows artifact tag for this machine, or None if unknown."""
    machine = platform.machine().lower()
    if sys.platform == "win32":
        if machine in ("amd64", "x86_64"):
            return "windows-amd64"
    return None


def resolve_membrane_pyz(workspace_repo: Path) -> Path | None:
    """
    Return ``hframe-membrane.pyz`` for a workspace repo layout.

    Resolution order:

    1. ``<workspace-parent>/.hframe/hframe-membrane.pyz`` (canonical bootstrap layout).
    2. ``<workspace-parent>/hframe-root/.hframe/hframe-membrane.pyz``
       (README devcontainer ``workspaceMount`` target).
    3. Otherwise, if **exactly one** other subdirectory of the workspace parent contains
       ``.hframe/hframe-membrane.pyz``, use that path (skipping the workspace directory itself).
    4. If several such directories exist, return ``None`` (ambiguous).
    """
    here = workspace_repo.resolve()
    direct = (here.parent / ".hframe" / MEMBRANE_PYZ_NAME).resolve()
    if direct.is_file():
        return direct
    root = here.parent
    if not root.is_dir():
        return None
    devc = (root / _DEVCONTAINER_PARENT_MOUNT / ".hframe" / MEMBRANE_PYZ_NAME).resolve()
    if devc.is_file():
        return devc
    hits: list[Path] = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if child.resolve() == here.resolve():
            continue
        p = (child / ".hframe" / MEMBRANE_PYZ_NAME).resolve()
        if p.is_file():
            hits.append(p)
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    return None


def _posix_launcher_source() -> str:
    """Stdlib-only script: same contract as ``native/shim.c`` (python3 + zipapp path)."""
    mount = _DEVCONTAINER_PARENT_MOUNT
    pyz_name = MEMBRANE_PYZ_NAME
    return f"""#!/usr/bin/env python3
import os
import sys
from pathlib import Path

_DEVCONTAINER_PARENT_MOUNT = "{mount}"


def _resolve_pyz(here: Path) -> Path | None:
    direct = (here.parent / ".hframe" / "{pyz_name}").resolve()
    if direct.is_file():
        return direct
    root = here.parent
    if not root.is_dir():
        return None
    devc = (root / _DEVCONTAINER_PARENT_MOUNT / ".hframe" / "{pyz_name}").resolve()
    if devc.is_file():
        return devc
    hits = []
    for child in sorted(root.iterdir(), key=lambda p: p.name):
        if not child.is_dir():
            continue
        if child.resolve() == here.resolve():
            continue
        p = (child / ".hframe" / "{pyz_name}").resolve()
        if p.is_file():
            hits.append(p)
    if not hits:
        return None
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        sys.stderr.write(
            "hframe: multiple sibling .hframe/ bundles under "
            + str(root)
            + "; keep only one or use "
            + str(root / _DEVCONTAINER_PARENT_MOUNT / ".hframe")
            + ".\\n"
        )
    return None


def _main() -> int:
    if len(sys.argv) != 2 or sys.argv[1] not in {{"in", "out"}}:
        sys.stderr.write("usage: ./hframe in\\n       ./hframe out\\n")
        return 2
    here = Path(__file__).resolve().parent
    pyz = _resolve_pyz(here)
    if pyz is None:
        tried = (here.parent / ".hframe" / "{pyz_name}").resolve()
        alt = (here.parent / _DEVCONTAINER_PARENT_MOUNT / ".hframe" / "{pyz_name}").resolve()
        sys.stderr.write(
            "hframe: missing membrane bundle. Tried:\\n  "
            + str(tried)
            + "\\n  "
            + str(alt)
            + "\\n"
            "If those files are missing, add Dev Container bind mounts "
            "(see README Devcontainers); "
            "workspaces bootstrapped without an existing .devcontainer get one "
            "with the needed mounts.\\n"
            "To refresh this launcher, install the hframe package in this environment "
            "(pip install h-frame) then run the install_workspace_shim one-liner from README "
            "Devcontainers.\\n"
        )
        return 2
    os.execvp("python3", ["python3", str(pyz), sys.argv[1]])
    return 127


if __name__ == "__main__":
    raise SystemExit(_main())
"""


def _install_posix_script(dest: Path, body: str) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(body, encoding="utf-8")
    mode = dest.stat().st_mode
    dest.chmod(mode | 0o111)


def _install_posix_python_launcher(dest: Path) -> None:
    _install_posix_script(dest, _posix_launcher_source())


def _vault_cli_launcher_source(python: str) -> str:
    """Launcher uses the interpreter that ran bootstrap (venv), not an arbitrary ``python3``."""
    return f"""#!{python}
import runpy
import sys

try:
    rc = runpy.run_module("hframe.vault_cli", run_name="__main__")
except ModuleNotFoundError:
    sys.stderr.write(
        "hframe-vault: hframe.vault_cli not found for this interpreter.\\n"
        f"  {sys.executable}\\n"
        "  pip install -e '/path/to/H-Frame[vault]'\\n"
    )
    raise SystemExit(1)
raise SystemExit(rc or 0)
"""


def install_bootstrap_vault_cli(bootstrap_root: Path) -> Path:
    """
    Install ``<bootstrap-root>/hframe-vault`` for operator policy decrypt/re-seal.

    Requires ``h-frame[vault]`` in the operator Python environment (same as bootstrap).
    """
    if sys.platform == "win32":
        raise RuntimeError(
            "h-frame-bootstrap --vault: hframe-vault operator script is POSIX-only; "
            "use Python snippets in README on Windows."
        )
    dest = bootstrap_root.resolve() / "hframe-vault"
    _install_posix_script(dest, _vault_cli_launcher_source(sys.executable))
    return dest


def install_workspace_shim(dest: Path) -> None:
    """
    Install the workspace ``hframe`` entrypoint.

    On POSIX, writes a small ``#!/usr/bin/env python3`` script that calls
    ``execvp`` with ``python3`` on ``hframe-membrane.pyz``. The script checks
    ``<workspace-parent>/.hframe/``, then ``<workspace-parent>/hframe-root/.hframe/``
    (README devcontainer mount), then a unique sibling ``*/.hframe/``.

    On Windows, copies ``hframe/native/prebuilt/hframe-shim-<tag>.exe`` into ``dest``.
    """
    if sys.platform != "win32":
        _install_posix_python_launcher(dest)
        return

    tag = shim_resource_tag()
    prebuilt_dir = _package_native_dir() / "prebuilt"
    if tag:
        src = prebuilt_dir / f"hframe-shim-{tag}.exe"
        if src.is_file():
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dest)
            return

    if not tag:
        raise RuntimeError(
            "h-frame-bootstrap: unsupported Windows machine type for prebuilt shims."
        )
    raise RuntimeError(
        "h-frame-bootstrap: no prebuilt Windows shim (hframe-shim-"
        f"{tag}.exe). Add it under hframe/native/prebuilt/; see native/prebuilt/README.md."
    )
