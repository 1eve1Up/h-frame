from __future__ import annotations

import subprocess
from pathlib import Path

from hframe.gitignore_policy import (
    format_bootstrap_allowlist_body,
    format_seeded_denylist_body,
    parse_gitignore_for_denylist,
    read_gitignore_deny_patterns,
    root_allow_patterns_from_protected_repo,
)


def test_parse_gitignore_skips_comments_blanks_negation() -> None:
    text = "\n" "# comment\n" "dist/\n" "\n" "!dist/keep\n" "*.log\n"
    assert parse_gitignore_for_denylist(text) == ["dist/", "*.log"]


def test_read_gitignore_deny_patterns_missing_file(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    assert read_gitignore_deny_patterns(repo) == []


def test_read_gitignore_deny_patterns_reads_root_file(tmp_path: Path) -> None:
    repo = tmp_path / "r"
    repo.mkdir()
    (repo / ".gitignore").write_text("node_modules/\n", encoding="utf-8")
    assert read_gitignore_deny_patterns(repo) == ["node_modules/"]


def test_format_seeded_denylist_body_empty_patterns() -> None:
    body = format_seeded_denylist_body([])
    assert "root .gitignore" in body
    assert "!" in body and "negation" in body


def test_format_bootstrap_allowlist_body_lists_patterns() -> None:
    body = format_bootstrap_allowlist_body(["README.md", "src/**"])
    assert "git check-ignore" in body
    assert "README.md" in body
    assert "src/**" in body


def test_root_allow_patterns_respects_gitignore(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(
        ["git", "init", "-b", "main"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "t@e.co"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "t"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    (repo / ".gitignore").write_text("build/\n", encoding="utf-8")
    (repo / "README.md").write_text("x", encoding="utf-8")
    (repo / "src").mkdir()
    (repo / "src" / "a.txt").write_text("a", encoding="utf-8")
    (repo / "build").mkdir()
    (repo / "build" / "b.txt").write_text("b", encoding="utf-8")
    subprocess.run(
        ["git", "add", ".gitignore", "README.md", "src"],
        cwd=repo,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    pats = root_allow_patterns_from_protected_repo(repo)
    assert "README.md" in pats
    assert "src/**" in pats
    assert ".gitignore" in pats
    assert not any(p.startswith("build") for p in pats)
