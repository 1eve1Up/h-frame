from __future__ import annotations

import json
from pathlib import Path

import pytest

from hframe.membrane_bootstrap import (
    membrane_directory_names,
    repo_slug_from_git_url,
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
    assert data["name"] == "hframe"
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
