from __future__ import annotations

import pytest

from hframe.sync_policy import (
    PolicyMode,
    SyncPolicy,
    load_sync_policy,
    parse_allowlist_with_mode,
    validate_sync_policy,
)


def test_parse_mode_default_allowlist() -> None:
    mode, pats = parse_allowlist_with_mode("# intro\nsrc/**\n")
    assert mode == PolicyMode.ALLOWLIST
    assert pats == ["src/**"]


def test_parse_mode_directive_does_not_match_nested_hash() -> None:
    text = "# # hframe-policy: mode denylist-only\nsrc/**\n"
    mode, pats = parse_allowlist_with_mode(text)
    assert mode == PolicyMode.ALLOWLIST
    assert pats == ["src/**"]


def test_parse_denylist_only_directive() -> None:
    text = "# hframe-policy: mode denylist-only\n# only comments\n"
    mode, pats = parse_allowlist_with_mode(text)
    assert mode == PolicyMode.DENYLIST_ONLY
    assert pats == []


def test_validate_denylist_only_rejects_patterns() -> None:
    pol = SyncPolicy(PolicyMode.DENYLIST_ONLY, ("src/**",), ())
    with pytest.raises(ValueError, match="denylist-only"):
        validate_sync_policy(pol)


def test_load_merges_optional_deny_file(tmp_path) -> None:
    allow = tmp_path / "policy.allowlist"
    deny = tmp_path / "policy.denylist"
    allow.write_text("src/**\n", encoding="utf-8")
    deny.write_text("# x\nscratch/**\n", encoding="utf-8")
    pol = load_sync_policy(allow)
    assert pol.mode == PolicyMode.ALLOWLIST
    assert pol.allow_patterns == ("src/**",)
    assert pol.user_deny_patterns == ("scratch/**",)


def test_validate_allowlist_requires_patterns() -> None:
    pol = SyncPolicy(PolicyMode.ALLOWLIST, (), ())
    with pytest.raises(ValueError, match="allowlist mode"):
        validate_sync_policy(pol)
