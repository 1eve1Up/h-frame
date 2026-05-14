"""H-Frame configuration types (embedded layout is frozen at bootstrap)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Bytecode zipapp under ``<parent>/.hframe/``; must match ``native/shim.c`` and workspace launcher.
MEMBRANE_PYZ_NAME = "hframe-membrane.pyz"


@dataclass(frozen=True)
class HFrameConfig:
    """Paths for protected repo, agent workspace, and allowlist policy (host-local)."""

    original: Path
    workspace: Path
    policy: Path

    def validate(self) -> None:
        if not self.original.is_dir():
            raise ValueError(f"original repo is not a directory: {self.original}")
        if not (self.original / ".git").is_dir():
            raise ValueError(f"original path is not a git repository: {self.original}")
        if not self.workspace.is_dir():
            raise ValueError(f"workspace is not a directory: {self.workspace}")
        if not (self.workspace / ".git").is_dir():
            raise ValueError(
                f"workspace path is not a git repository: {self.workspace}"
            )
        if not self.policy.is_file():
            raise ValueError(f"policy allowlist file not found: {self.policy}")
