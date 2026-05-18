"""Load and validate host-local sync policy (allowlist vs denylist-only)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from hframe.config import HFrameConfig
from hframe.filters import parse_allowlist_file

# Only a top-level ``# hframe-policy: …`` line sets mode (not ``# # …`` documentation).
_POLICY_DIRECTIVE_RE = re.compile(
    r"^\s*#\s*hframe-policy:\s*mode\s+(\S+)",
    re.IGNORECASE,
)


class PolicyMode(StrEnum):
    ALLOWLIST = "allowlist"
    DENYLIST_ONLY = "denylist-only"


@dataclass(frozen=True)
class SyncPolicy:
    """Effective policy after reading ``policy.allowlist`` and optional ``policy.denylist``."""

    mode: PolicyMode
    allow_patterns: tuple[str, ...]
    user_deny_patterns: tuple[str, ...]


def parse_allowlist_with_mode(text: str) -> tuple[PolicyMode, list[str]]:
    """Parse ``policy.allowlist`` body: optional ``# hframe-policy: mode …`` plus path patterns."""
    mode = PolicyMode.ALLOWLIST
    patterns: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        m = _POLICY_DIRECTIVE_RE.match(line)
        if m:
            mode = _coerce_mode(m.group(1))
            continue
        if s.startswith("#"):
            continue
        patterns.append(s)
    return mode, patterns


def _coerce_mode(token: str) -> PolicyMode:
    t = token.strip().lower().replace(" ", "").replace("_", "-")
    if t in ("allowlist", "allowlist+denylist", "allow+deny"):
        return PolicyMode.ALLOWLIST
    if t in ("denylist-only", "denyonly"):
        return PolicyMode.DENYLIST_ONLY
    raise ValueError(
        f"unknown policy mode {token!r}; use allowlist or denylist-only (see README)."
    )


def load_sync_policy(policy_allowlist_path: Path) -> SyncPolicy:
    text = policy_allowlist_path.read_text(encoding="utf-8")
    return _sync_policy_from_text(
        text, policy_allowlist_path.parent / "policy.denylist"
    )


def _sync_policy_from_text(allow_text: str, deny_path: Path) -> SyncPolicy:
    mode, allows = parse_allowlist_with_mode(allow_text)
    denies: list[str] = []
    if deny_path.is_file():
        denies = parse_allowlist_file(deny_path.read_text(encoding="utf-8"))
    return SyncPolicy(mode, tuple(allows), tuple(denies))


def _sync_policy_from_vault_text(allow_text: str, deny_text: str | None) -> SyncPolicy:
    mode, allows = parse_allowlist_with_mode(allow_text)
    denies: list[str] = []
    if deny_text:
        denies = parse_allowlist_file(deny_text)
    return SyncPolicy(mode, tuple(allows), tuple(denies))


def load_sync_policy_for_config(cfg: HFrameConfig) -> SyncPolicy:
    if cfg.policy_vault is not None:
        from hframe.policy_vault import read_vault_file

        vault = cfg.policy_vault
        allow_text = read_vault_file(vault.allow, vault.key)
        deny_text: str | None = None
        if vault.deny.is_file():
            deny_text = read_vault_file(vault.deny, vault.key)
        return _sync_policy_from_vault_text(allow_text, deny_text)
    assert cfg.policy is not None
    return load_sync_policy(cfg.policy)


def validate_sync_policy(p: SyncPolicy) -> None:
    if p.mode == PolicyMode.ALLOWLIST:
        if not p.allow_patterns:
            raise ValueError(
                "allowlist mode requires at least one allow pattern in .hframe/policy.allowlist"
            )
        return
    if p.allow_patterns:
        raise ValueError(
            "denylist-only mode: remove non-comment path lines from .hframe/policy.allowlist "
            "(keep only the mode comment and blank or comment lines)."
        )
