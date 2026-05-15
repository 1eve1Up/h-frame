"""Bootstrap helpers: ``.gitignore`` → denylist; repo root → allowlist."""

from __future__ import annotations

import subprocess
from pathlib import Path


def parse_gitignore_for_denylist(text: str) -> list[str]:
    """
    Extract pattern lines suitable for ``.hframe/policy.denylist``.

    Uses the same comment convention as ``hframe.filters.parse_allowlist_file``:
    blank lines and ``#`` comments are skipped.

    Lines starting with ``!`` (git negation / un-ignore) are skipped: denylist-only
    rsync rules do not model git's negation ordering without extra include rules.
    Rare escapes (``\\#``, trailing ``\\ ``) are not interpreted; they pass through
    as literal patterns if non-empty after strip.
    """
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        if s.startswith("!"):
            continue
        out.append(s)
    return out


def read_gitignore_deny_patterns(protected_repo: Path) -> list[str]:
    """Load root ``.gitignore`` from a clone; return ``[]`` if missing."""
    gi = protected_repo / ".gitignore"
    if not gi.is_file():
        return []
    return parse_gitignore_for_denylist(gi.read_text(encoding="utf-8"))


def format_seeded_denylist_body(patterns: list[str]) -> str:
    """Human-readable ``policy.denylist`` body: header comments plus one pattern per line."""
    header = (
        "# Generated at bootstrap from the protected repo's root .gitignore.\n"
        "# Merged after built-in denies (see hframe.filters.DEFAULT_DENY_GLOBS).\n"
        "# Lines starting with ! (git negation) are omitted; edit manually if needed.\n"
    )
    if not patterns:
        return header + "\n"
    return header + "\n" + "\n".join(patterns) + "\n"


def root_allow_patterns_from_protected_repo(protected_repo: Path) -> list[str]:
    """
    Build allowlist lines for each **root** path in ``protected_repo`` that Git does not ignore.

    Uses ``git check-ignore`` so nested ``.gitignore`` rules and excludes files are respected.
    Directories become ``name/**``; files become ``name``. Skips ``.git`` and repo-root ``hframe``
    (workspace launcher; not part of the protected clone in normal layouts).
    """
    if not (protected_repo / ".git").is_dir():
        raise ValueError(f"not a git repository: {protected_repo}")
    patterns: list[str] = []
    for entry in sorted(protected_repo.iterdir(), key=lambda p: p.name.casefold()):
        name = entry.name
        if name in (".git", "hframe"):
            continue
        cp = subprocess.run(
            ["git", "-C", str(protected_repo), "check-ignore", "-q", "--", name],
            capture_output=True,
            text=True,
        )
        if cp.returncode == 0:
            continue
        if cp.returncode != 1:
            raise ValueError(
                f"git check-ignore failed in {protected_repo} for {name!r}: "
                f"exit {cp.returncode} stderr={cp.stderr!r}"
            )
        if entry.is_dir():
            patterns.append(f"{name}/**")
        elif entry.is_file() or entry.is_symlink():
            patterns.append(name)
    return patterns


def format_bootstrap_allowlist_body(patterns: list[str]) -> str:
    """Body for ``policy.allowlist``: comments plus one allow pattern per line."""
    header = (
        "# Generated at bootstrap: one pattern per non-ignored root entry "
        "(see git check-ignore).\n"
        "# Directories use name/** ; files use the basename. "
        "policy.denylist still applies.\n"
        "# For full-tree sync except denies, use denylist-only mode (README).\n"
        "\n"
    )
    if not patterns:
        return header
    return header + "\n".join(patterns) + "\n"
