from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from hframe.membrane_bootstrap import (
    AGENTS_APPEND_FILE_ENV,
    _append_agents_md,
    load_bootstrap_env,
    membrane_directory_names,
    repo_slug_from_git_url,
    resolve_agents_append_file,
    write_workspace_devcontainer_if_missing,
)


@pytest.mark.parametrize(
    ("url", "expected_slug"),
    [
        ("git@github.com:org/my-app.git", "my-app"),
        ("https://github.com/org/foo_bar.git", "foo_bar"),
        ("ssh://git@github.com/org/baz.git", "baz"),
        ("git@host:repo.git", "repo"),
    ],
)
def test_repo_slug_from_git_url(url: str, expected_slug: str) -> None:
    assert repo_slug_from_git_url(url) == expected_slug


def test_membrane_directory_names() -> None:
    p, w = membrane_directory_names("git@github.com:acme/widget.git")
    assert p == "widget_repo"
    assert w == "widget_workspace_repo"


def test_repo_slug_file_uri(tmp_path: Path) -> None:
    bare = tmp_path / "upstream.git"
    bare.mkdir()
    uri = bare.resolve().as_uri()
    assert repo_slug_from_git_url(uri) == "upstream"


def test_write_workspace_devcontainer_if_missing_creates_mounts(tmp_path: Path) -> None:
    ws = tmp_path / "podbay_workspace_repo"
    ws.mkdir()
    write_workspace_devcontainer_if_missing(ws)
    data = json.loads(
        (ws / ".devcontainer" / "devcontainer.json").read_text(encoding="utf-8")
    )
    assert data["name"] == "h-frame"
    mounts = data["mounts"]
    assert any("hframe-root" in m for m in mounts)
    assert any("/workspaces/.hframe" in m for m in mounts)
    assert any("readonly" in m and ".hframe" in m for m in mounts)
    assert "safe.directory" in data.get("postCreateCommand", "")


def test_write_workspace_devcontainer_if_missing_skips_existing(tmp_path: Path) -> None:
    ws = tmp_path / "ws"
    dc = ws / ".devcontainer"
    dc.mkdir(parents=True)
    existing = '{"name": "custom"}'
    (dc / "devcontainer.json").write_text(existing, encoding="utf-8")
    write_workspace_devcontainer_if_missing(ws)
    assert (dc / "devcontainer.json").read_text(encoding="utf-8") == existing


def test_append_agents_md_noop_when_unconfigured(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    _append_agents_md(ws, None)
    assert not (ws / "AGENTS.md").exists()


def test_append_agents_md_writes_snippet(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    snippet = tmp_path / "snippet.md"
    snippet.write_text("## Team rules\n\nBe nice.\n", encoding="utf-8")
    _append_agents_md(ws, snippet)
    assert (ws / "AGENTS.md").read_text(
        encoding="utf-8"
    ) == "## Team rules\n\nBe nice.\n"


def test_append_agents_md_appends_to_existing(tmp_path: Path) -> None:
    ws = tmp_path / "workspace"
    ws.mkdir()
    (ws / "AGENTS.md").write_text("# Existing\n", encoding="utf-8")
    snippet = tmp_path / "snippet.md"
    snippet.write_text("## More\n", encoding="utf-8")
    _append_agents_md(ws, snippet)
    assert (ws / "AGENTS.md").read_text(encoding="utf-8") == "# Existing\n## More\n"


def test_load_bootstrap_env_sets_unset_keys_only(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hframe_dir = tmp_path / ".hframe"
    hframe_dir.mkdir()
    (hframe_dir / "bootstrap.env").write_text(
        f"{AGENTS_APPEND_FILE_ENV}=./from-env-file.md\n" "ALREADY_SET=from-file\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("ALREADY_SET", "from-shell")
    monkeypatch.delenv(AGENTS_APPEND_FILE_ENV, raising=False)
    load_bootstrap_env(tmp_path)
    assert os.environ[AGENTS_APPEND_FILE_ENV] == "./from-env-file.md"
    assert os.environ["ALREADY_SET"] == "from-shell"
    os.environ.pop(AGENTS_APPEND_FILE_ENV, None)


def test_resolve_agents_append_file_from_bootstrap_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    hframe_dir = tmp_path / ".hframe"
    hframe_dir.mkdir()
    snippet = tmp_path / "snippet.md"
    snippet.write_text("custom rules\n", encoding="utf-8")
    (hframe_dir / "bootstrap.env").write_text(
        f"{AGENTS_APPEND_FILE_ENV}=./snippet.md\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(AGENTS_APPEND_FILE_ENV, raising=False)
    assert resolve_agents_append_file(tmp_path, cwd=tmp_path) == snippet.resolve()
    os.environ.pop(AGENTS_APPEND_FILE_ENV, None)


def test_load_bootstrap_env_from_layout_parent_scratch_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "hframe-scratch-workspaces"
    layout = scratch / "podbay-parent"
    layout.mkdir(parents=True)
    (scratch / ".hframe").mkdir()
    (scratch / ".hframe" / "bootstrap.env").write_text(
        f"{AGENTS_APPEND_FILE_ENV}=../MYAGENTS.md\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(AGENTS_APPEND_FILE_ENV, raising=False)
    load_bootstrap_env(layout, cwd=layout)
    assert os.environ[AGENTS_APPEND_FILE_ENV] == "../MYAGENTS.md"
    os.environ.pop(AGENTS_APPEND_FILE_ENV, None)


def test_load_bootstrap_env_layout_overrides_parent_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "scratch"
    layout = scratch / "podbay-parent"
    layout.mkdir(parents=True)
    (scratch / ".hframe").mkdir()
    (layout / ".hframe").mkdir(parents=True)
    (scratch / ".hframe" / "bootstrap.env").write_text(
        f"{AGENTS_APPEND_FILE_ENV}=../parent.md\n",
        encoding="utf-8",
    )
    (layout / ".hframe" / "bootstrap.env").write_text(
        f"{AGENTS_APPEND_FILE_ENV}=../layout.md\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(AGENTS_APPEND_FILE_ENV, raising=False)
    load_bootstrap_env(layout, cwd=layout)
    assert os.environ[AGENTS_APPEND_FILE_ENV] == "../layout.md"
    os.environ.pop(AGENTS_APPEND_FILE_ENV, None)


def test_resolve_agents_append_file_from_parent_scratch_bootstrap_env(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scratch = tmp_path / "hframe-scratch-workspaces"
    layout = scratch / "podbay-parent"
    layout.mkdir(parents=True)
    agents = scratch / "MYAGENTS.md"
    agents.write_text("team rules\n", encoding="utf-8")
    (scratch / ".hframe").mkdir()
    (scratch / ".hframe" / "bootstrap.env").write_text(
        f"{AGENTS_APPEND_FILE_ENV}=../MYAGENTS.md\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(AGENTS_APPEND_FILE_ENV, raising=False)
    assert resolve_agents_append_file(layout, cwd=layout) == agents.resolve()
    os.environ.pop(AGENTS_APPEND_FILE_ENV, None)


def test_resolve_agents_append_file_relative_to_cwd_not_bootstrap_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outer = tmp_path / "scratch"
    layout = outer / "podbay-parent"
    layout.mkdir(parents=True)
    snippet = outer / "sampleagents.md"
    snippet.write_text("team rules\n", encoding="utf-8")
    monkeypatch.setenv(AGENTS_APPEND_FILE_ENV, "sampleagents.md")
    assert resolve_agents_append_file(layout, cwd=outer) == snippet.resolve()


def test_resolve_agents_append_file_missing_raises(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv(AGENTS_APPEND_FILE_ENV, "./missing.md")
    with pytest.raises(ValueError, match="does not resolve to a readable file"):
        resolve_agents_append_file(tmp_path, cwd=tmp_path)


def test_resolve_agents_append_file_unset_returns_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv(AGENTS_APPEND_FILE_ENV, raising=False)
    assert resolve_agents_append_file(tmp_path, cwd=tmp_path) is None
