"""H-Frame configuration types (embedded layout is frozen at bootstrap)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

# Bytecode zipapp under ``<parent>/.hframe/``; must match ``native/shim.c`` and workspace launcher.
MEMBRANE_PYZ_NAME = "hframe-membrane.pyz"


@dataclass(frozen=True)
class PolicyVaultConfig:
    """Vault-encrypted policy blobs; key is compiled into hframe-membrane.pyz."""

    allow: Path
    deny: Path
    key: bytes


@dataclass(frozen=True)
class HFrameConfig:
    """Paths for protected repo, agent workspace, and sync policy (host-local)."""

    original: Path
    workspace: Path
    policy: Path | None = None
    policy_vault: PolicyVaultConfig | None = None

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
        if self.policy_vault is not None:
            if not self.policy_vault.allow.is_file():
                raise ValueError(
                    f"vault allowlist file not found: {self.policy_vault.allow}"
                )
            if not self.policy_vault.deny.is_file():
                raise ValueError(
                    f"vault denylist file not found: {self.policy_vault.deny}"
                )
            return
        if self.policy is None or not self.policy.is_file():
            raise ValueError(
                "policy allowlist file not found: "
                f"{self.policy if self.policy else '(not configured)'}"
            )

    def policy_reference_path(self) -> Path:
        """Path recorded in sync receipts (never exposes vault key)."""
        if self.policy_vault is not None:
            return self.policy_vault.allow
        assert self.policy is not None
        return self.policy
