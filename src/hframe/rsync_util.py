"""Rsync execution with generated filter rules."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

from hframe.filters import build_rsync_deny_only_lines, build_rsync_filter_lines


class RsyncError(RuntimeError):
    pass


def rsync_filtered(
    src_dir: Path,
    dst_dir: Path,
    *,
    deny_only: bool = False,
    allow_patterns: list[str],
    user_deny_patterns: list[str] | None = None,
    delete: bool = True,
) -> None:
    """Sync using an rsync filter file (allowlist or denylist-only).

    Uses ``rsync -I`` (ignore times) so same-length edits are not skipped when mtimes match.
    """
    if deny_only:
        lines = build_rsync_deny_only_lines(user_deny_patterns)
    else:
        lines = build_rsync_filter_lines(allow_patterns, extra_deny=user_deny_patterns)
    src = str(src_dir.resolve()) + "/"
    dst = str(dst_dir.resolve()) + "/"
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".rsync-filter",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write("\n".join(lines) + "\n")
        f.flush()
        filter_path = f.name
    try:
        cmd = [
            "rsync",
            "-a",
            "-I",
            *(["--delete"] if delete else []),
            "--filter",
            f"merge {filter_path}",
            src,
            dst,
        ]
        p = subprocess.run(cmd, check=False, text=True, capture_output=True)
        if p.returncode != 0:
            raise RsyncError(
                f"rsync failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr or p.stdout}"
            )
    finally:
        Path(filter_path).unlink(missing_ok=True)
