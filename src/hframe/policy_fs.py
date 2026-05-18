"""POSIX permission helpers for host-local ``.hframe/`` policy artifacts."""

from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

MODE_HFRAME_DIR = (
    stat.S_IRUSR | stat.S_IWUSR | stat.S_IXUSR | stat.S_IRGRP | stat.S_IXGRP
)
MODE_POLICY_FILE = stat.S_IRUSR | stat.S_IRGRP | stat.S_IROTH
# Owner-writable for operator re-seal; harden_hframe_bundle restores MODE_POLICY_FILE.
MODE_POLICY_FILE_OPERATOR_WRITE = (
    stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH
)


def _chmod(path: Path, mode: int) -> None:
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def permit_policy_vault_rewrite(hframe_dir: Path) -> None:
    """
    Allow the operator to overwrite ``*.vault`` blobs (bootstrap sets ``0444``).

    Call before ``write_vault_file`` during manual re-seal; follow with
    ``harden_hframe_bundle`` to restore read-only policy artifacts.
    """
    if sys.platform == "win32":
        return
    hf = hframe_dir.resolve()
    for name in ("policy.allowlist.vault", "policy.denylist.vault"):
        p = hf / name
        if p.is_file():
            _chmod(p, MODE_POLICY_FILE_OPERATOR_WRITE)


def harden_hframe_bundle(hframe_dir: Path, *, policy_paths: list[Path]) -> None:
    """
    Apply operator-oriented modes under ``.hframe/``.

    On Windows this is a no-op (same pattern as ``build_membrane_pyz``).
    """
    if sys.platform == "win32":
        return
    hframe_dir = hframe_dir.resolve()
    if hframe_dir.is_dir():
        _chmod(hframe_dir, MODE_HFRAME_DIR)
    for p in policy_paths:
        p = p.resolve()
        if p.is_file():
            _chmod(p, MODE_POLICY_FILE)
