"""Build a source zipapp for agent sync (``.py`` inside ``.hframe/``, host-local)."""

from __future__ import annotations

import compileall
import json
import shutil
import stat
import tempfile
import zipfile
from pathlib import Path

# Not needed inside the agent runtime bundle (operator host only).
_EXCLUDE_PACKAGE_FILES = frozenset(
    {
        "bootstrap_cli.py",
        "build_membrane_pyz.py",
        "membrane_bootstrap.py",
        "shim_install.py",
    }
)


def _ignore_copy(_dir: str, names: list[str]) -> list[str]:
    return [n for n in names if n in _EXCLUDE_PACKAGE_FILES or n == "native"]


def build_membrane_pyz(output: Path, *, config: dict[str, str]) -> None:
    """
    Write a zipapp at ``output`` containing:

    * ``hframe/`` package as ``.py`` (operator-only modules excluded at copy)
    * ``__main__.py`` with embedded JSON; calls ``embedded.main``

    The bundle is **source**, not minor-specific bytecode, so the same zipapp runs
    under any ``python3`` satisfying ``requires-python`` (e.g. bootstrap on 3.11,
    devcontainer on 3.12). ``compileall`` is used only to validate the tree compiles
    on the **bootstrap** interpreter; ``.pyc`` / ``__pycache__`` are not shipped.
    """
    import hframe

    src_pkg = Path(hframe.__file__).resolve().parent
    tmp = Path(tempfile.mkdtemp(prefix="hframe-pyz-"))
    try:
        dest_pkg = tmp / "hframe"
        shutil.copytree(src_pkg, dest_pkg, ignore=_ignore_copy)
        main_py = tmp / "__main__.py"
        cfg_json = json.dumps(config, separators=(",", ":"))
        main_py.write_text(
            "import json\n"
            f"_CFG = json.loads({repr(cfg_json)})\n"
            "from hframe.embedded import main\n"
            "raise SystemExit(main(_CFG))\n",
            encoding="utf-8",
        )
        if not compileall.compile_dir(tmp, legacy=True, quiet=1):
            raise RuntimeError("compileall reported failures")
        for path in tmp.rglob("*.pyc"):
            path.unlink(missing_ok=True)
        for cache in tmp.rglob("__pycache__"):
            if cache.is_dir():
                shutil.rmtree(cache, ignore_errors=True)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            output.unlink()
        with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in tmp.rglob("*"):
                if path.is_file():
                    zf.write(path, path.relative_to(tmp))
        try:
            output.chmod(stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH)
        except OSError:
            pass
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
