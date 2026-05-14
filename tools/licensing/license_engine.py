"""Inbound ScanCode license validation (stdlib + license_expression only).

validate_report.py loads YAML policy and delegates here.
"""

from __future__ import annotations

import fnmatch

from license_expression import ExpressionParseError, Licensing


def path_matches_any_glob(rel_path: str, globs: list[str]) -> bool:
    """True if ``rel_path`` matches any glob (POSIX slashes, ``**`` globstar)."""
    normalized = rel_path.replace("\\", "/").lstrip("/")
    if not normalized:
        return False
    parts = tuple(normalized.split("/"))
    for raw in globs:
        pattern = raw.replace("\\", "/").lstrip("/")
        pat_parts = tuple(pattern.split("/")) if pattern else ()
        if _globstar_match(parts, pat_parts):
            return True
    return False


def _globstar_match(path_parts: tuple[str, ...], pat_parts: tuple[str, ...]) -> bool:
    """Match split path to split pattern; ``**`` matches zero or more whole segments."""

    def rec(pi: int, pj: int) -> bool:
        if pj == len(pat_parts):
            return pi == len(path_parts)
        if pat_parts[pj] == "**":
            if pj + 1 == len(pat_parts):
                return True
            if rec(pi, pj + 1):
                return True
            if pi < len(path_parts) and rec(pi + 1, pj):
                return True
            return False
        if pi == len(path_parts):
            return False
        if not fnmatch.fnmatch(path_parts[pi], pat_parts[pj]):
            return False
        return rec(pi + 1, pj + 1)

    return rec(0, 0)


def symbols_from_expression(expr: str) -> list[str]:
    licensing = Licensing()
    parsed = licensing.parse(expr)
    return [str(sym) for sym in parsed.symbols]


def validate_scan_code_json(data: dict, policy: dict) -> list[tuple[str, str, str]]:
    """Return list of (path, expression, reason) violations."""
    approved = {str(x) for x in policy["approved_spdx_license_identifiers"]}
    first_party_globs = list(policy["first_party_path_globs"])
    ref_prefixes = tuple(policy.get("allowed_license_ref_prefixes", []))
    options = policy.get("options") or {}
    allow_ref_on_fp = bool(
        options.get("allow_unknown_license_ref_tokens_on_first_party_paths", True)
    )
    allow_ref_outside_fp = bool(
        options.get("allow_license_ref_tokens_outside_first_party", False)
    )

    violations: list[tuple[str, str, str]] = []
    files = data.get("files") or []
    for entry in files:
        if entry.get("type") != "file":
            continue
        path = entry.get("path") or ""
        expr_spdx = entry.get("detected_license_expression_spdx")
        expr_raw = entry.get("detected_license_expression")
        expr = (expr_spdx or expr_raw or "").strip()
        if not expr:
            continue

        first_party = path_matches_any_glob(path, first_party_globs)

        try:
            symbols = symbols_from_expression(expr)
        except ExpressionParseError:
            violations.append((path, expr, "unparseable license expression"))
            continue

        for sym in symbols:
            if sym in approved:
                continue
            if any(sym.startswith(prefix) for prefix in ref_prefixes):
                if first_party and allow_ref_on_fp:
                    continue
                if allow_ref_outside_fp:
                    continue
                violations.append(
                    (
                        path,
                        expr,
                        f"disallowed ScanCode license ref token {sym!r} "
                        f"(first_party={first_party})",
                    )
                )
                continue
            violations.append(
                (
                    path,
                    expr,
                    f"license symbol {sym!r} not in approved_spdx_license_identifiers",
                )
            )

    return violations
