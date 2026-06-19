"""Operator environment variable names (``H_FRAME_*``) with legacy ``HFRAME_*`` fallback."""

from __future__ import annotations

import os

H_FRAME_VAULT_PASS = "H_FRAME_VAULT_PASS"
H_FRAME_BOOTSTRAP_DEBUG = "H_FRAME_BOOTSTRAP_DEBUG"
H_FRAME_AGENTS_APPEND_FILE = "H_FRAME_AGENTS_APPEND_FILE"

LEGACY_HFRAME_VAULT_PASS = "HFRAME_VAULT_PASS"
LEGACY_HFRAME_BOOTSTRAP_DEBUG = "HFRAME_BOOTSTRAP_DEBUG"
LEGACY_HFRAME_AGENTS_APPEND_FILE = "HFRAME_AGENTS_APPEND_FILE"
H_FRAME_SRC = "H_FRAME_SRC"
LEGACY_HFRAME_SRC = "HFRAME_SRC"

# Keys in ``.hframe/bootstrap.env`` may use legacy names; they normalize to canonical.
BOOTSTRAP_ENV_ALIASES: dict[str, str] = {
    LEGACY_HFRAME_VAULT_PASS: H_FRAME_VAULT_PASS,
    LEGACY_HFRAME_BOOTSTRAP_DEBUG: H_FRAME_BOOTSTRAP_DEBUG,
    LEGACY_HFRAME_AGENTS_APPEND_FILE: H_FRAME_AGENTS_APPEND_FILE,
}


def normalize_bootstrap_env_key(key: str) -> str:
    return BOOTSTRAP_ENV_ALIASES.get(key, key)


def env_value(primary: str, legacy: str) -> str | None:
    """Return the first non-empty value for ``primary`` or ``legacy``."""
    for name in (primary, legacy):
        raw = os.environ.get(name)
        if raw is not None and raw.strip() != "":
            return raw.strip()
    return None


def env_flag(primary: str, legacy: str) -> bool:
    return os.environ.get(primary) == "1" or os.environ.get(legacy) == "1"
