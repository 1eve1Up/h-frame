"""Build rsync filter rules from allowlist and denylist."""

from __future__ import annotations

# PRD default deny patterns (always applied).
DEFAULT_DENY_GLOBS: tuple[str, ...] = (
    ".pinion/**",
    "pinion/**",
    ".agent/**",
    "tmp/**",
    ".cursor/**",
    ".claude/**",
)


def parse_allowlist_file(text: str) -> list[str]:
    """Read one pattern per line; strip comments and blanks."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        out.append(s)
    return out


def _deny_to_rsync_rules(glob: str) -> list[str]:
    g = glob.strip().rstrip("/")
    if g.endswith("/**"):
        base = g[: -len("/**")].lstrip("/")
        if "*" in base:
            return [f"- /{base}/***", f"- {base}/***"]
        return [f"- /{base}/", f"- /{base}/***"]
    if "*" in g:
        return [f"- /{g}", f"- {g}"]
    if "/" in g:
        return [f"- /{g}", f"- /{g}/***", f"- {g}", f"- {g}/***"]
    return [f"- /{g}", f"- /{g}/***", f"- {g}", f"- {g}/***"]


def _allow_to_rsync_rules(pattern: str) -> list[str]:
    p = pattern.strip().rstrip("/")
    if p.endswith("/**"):
        base = p[: -len("/**")].lstrip("/")
        if not base or "**" in base:
            raise ValueError(f"invalid allow pattern: {pattern!r}")
        return [f"+ /{base}/", f"+ /{base}/***"]
    if "**" in p:
        raise ValueError(f"unsupported allow pattern (use dir/** only): {pattern!r}")
    if p.endswith("/"):
        base = p.rstrip("/").lstrip("/")
        return [f"+ /{base}/", f"+ /{base}/***"]
    base = p.lstrip("/")
    if "/" in base:
        return [f"+ /{base}"]
    # Single path segment: treat dotted names and common extensionless files as files.
    root_files = frozenset(
        {
            "Dockerfile",
            "Makefile",
            "Rakefile",
            "Gemfile",
            "LICENSE",
            "README",
        }
    )
    if "." in base or base in root_files:
        return [f"+ /{base}"]
    return [f"+ /{base}/", f"+ /{base}/***"]


def build_rsync_filter_lines(
    allow_patterns: list[str],
    extra_deny: list[str] | None = None,
) -> list[str]:
    """Produce rsync --filter merge lines: deny defaults, optional user denies, allows, ``- *``."""
    lines: list[str] = [
        "# never sync .git between repos",
        "- /.git/",
        "- /.git/***",
        "# repo-root workspace launcher (bootstrap install; not in protected clone)",
        "- /hframe",
        "- /hframe/***",
    ]
    for g in DEFAULT_DENY_GLOBS:
        lines.extend(_deny_to_rsync_rules(g))
    for g in extra_deny or []:
        lines.extend(_deny_to_rsync_rules(g))
    lines.append("# allowlist")
    for a in allow_patterns:
        lines.extend(_allow_to_rsync_rules(a))
    lines.append("- *")
    return lines


def build_rsync_deny_only_lines(extra_deny: list[str] | None = None) -> list[str]:
    """Rsync filter: built-in denies, optional user denies, then include the rest of the tree."""
    lines: list[str] = [
        "# never sync .git between repos",
        "- /.git/",
        "- /.git/***",
        "# repo-root workspace launcher (bootstrap install; not in protected clone)",
        "- /hframe",
        "- /hframe/***",
    ]
    for g in DEFAULT_DENY_GLOBS:
        lines.extend(_deny_to_rsync_rules(g))
    for g in extra_deny or []:
        lines.extend(_deny_to_rsync_rules(g))
    lines.extend(["# include everything not denied above", "+ /", "+ /***"])
    return lines
