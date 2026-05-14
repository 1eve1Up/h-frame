from hframe.filters import (
    build_rsync_deny_only_lines,
    build_rsync_filter_lines,
    parse_allowlist_file,
)


def test_parse_allowlist_skips_comments_and_blanks() -> None:
    text = """
# comment
src/**

docs/**
"""
    assert parse_allowlist_file(text) == ["src/**", "docs/**"]


def test_build_filter_contains_git_deny_and_allow() -> None:
    lines = build_rsync_filter_lines(["src/**", "README.md"])
    joined = "\n".join(lines)
    assert "- /.git/" in joined
    assert "+ /src/" in joined
    assert "+ /README.md" in joined
    assert joined.strip().endswith("- *")


def test_build_filter_merges_extra_deny_before_allows() -> None:
    lines = build_rsync_filter_lines(["src/**"], extra_deny=["scratch/**"])
    joined = "\n".join(lines)
    assert "scratch" in joined
    assert "+ /src/" in joined


def test_build_deny_only_includes_remainder() -> None:
    lines = build_rsync_deny_only_lines(["local/**"])
    joined = "\n".join(lines)
    assert "- /.git/" in joined
    assert "local" in joined
    assert "+ /" in joined
    assert "+ /***" in joined
    assert not joined.strip().endswith("- *")
