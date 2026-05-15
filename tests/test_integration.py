from __future__ import annotations

import os
import subprocess
import zipfile
from pathlib import Path

import pytest

from hframe.config import HFrameConfig
from hframe.git_ops import list_remotes
from hframe.membrane_bootstrap import (
    MEMBRANE_PYZ_NAME,
    bootstrap_membrane,
    membrane_directory_names,
)
from hframe.operations import verify
from hframe.sync_policy import PolicyMode, load_sync_policy, validate_sync_policy


def _run(cmd: list[str], cwd: Path | None = None) -> None:
    subprocess.run(
        cmd, cwd=str(cwd) if cwd else None, check=True, capture_output=True, text=True
    )


def _git(repo: Path, *args: str) -> None:
    _run(["git", "-C", str(repo), *args])


def _init_identity(repo: Path) -> None:
    _git(repo, "config", "user.email", "hframe-test@example.com")
    _git(repo, "config", "user.name", "hframe-test")


def _make_upstream_bare(tmp: Path) -> Path:
    """Create a non-bare repo with an initial commit, then return path to a bare clone."""
    upstream = tmp / "upstream"
    upstream.mkdir()
    _run(["git", "init", "-b", "main"], cwd=upstream)
    _init_identity(upstream)
    (upstream / "src").mkdir()
    (upstream / "src" / "hello.txt").write_text("v0\n", encoding="utf-8")
    (upstream / "README.md").write_text("readme\n", encoding="utf-8")
    (upstream / ".gitignore").write_text(
        "# build artifacts\n" "dist/\n" "node_modules/\n" "!ignored_but_negated/**\n",
        encoding="utf-8",
    )
    _git(upstream, "add", ".")
    _git(upstream, "commit", "-m", "init")
    bare = tmp / "upstream.git"
    _run(["git", "clone", "--bare", str(upstream), str(bare)])
    return bare


@pytest.mark.integration
def test_membrane_bootstrap_and_embedded_bridge(tmp_path: Path) -> None:
    bare = _make_upstream_bare(tmp_path)
    remote_url = bare.resolve().as_uri()
    bootstrap_membrane(remote_url, tmp_path)

    protected_name, workspace_name = membrane_directory_names(remote_url)
    original = tmp_path / protected_name
    workspace = tmp_path / workspace_name
    bridge = workspace / "hframe"
    pyz = tmp_path / ".hframe" / MEMBRANE_PYZ_NAME

    assert (original / ".git").is_dir()
    assert (workspace / ".git").is_dir()
    assert bridge.is_file()
    assert pyz.is_file()
    assert not (workspace / ".hframe_runtime").exists()
    assert bridge.read_bytes().startswith(
        b"#!/usr/bin/env python3\n"
    ), "workspace hframe should be the portable POSIX python3 launcher"
    with zipfile.ZipFile(pyz) as zf:
        names = zf.namelist()
    assert any(n == "__main__.py" for n in names), names
    assert any(n.startswith("hframe/") and n.endswith(".py") for n in names), names
    assert not any(n.endswith(".pyc") for n in names), names
    assert list_remotes(workspace) == []
    assert "origin" in list_remotes(original)
    assert "H-Frame Sync Rules" in (workspace / "AGENTS.md").read_text(encoding="utf-8")

    policy_allow = tmp_path / ".hframe" / "policy.allowlist"
    policy_deny = tmp_path / ".hframe" / "policy.denylist"
    pol = load_sync_policy(policy_allow)
    validate_sync_policy(pol)
    assert pol.mode == PolicyMode.ALLOWLIST
    deny_text = policy_deny.read_text(encoding="utf-8")
    assert "dist/" in deny_text
    assert "node_modules/" in deny_text
    assert "!ignored_but_negated" not in deny_text
    assert pol.user_deny_patterns == ("dist/", "node_modules/")
    assert "src/**" in pol.allow_patterns
    assert "README.md" in pol.allow_patterns

    dc = workspace / ".devcontainer" / "devcontainer.json"
    assert dc.is_file()
    raw = dc.read_text(encoding="utf-8")
    assert (
        "hframe-root" in raw
        and "/workspaces/.hframe" in raw
        and "safe.directory" in raw
    )

    cfg = HFrameConfig(
        original=original,
        workspace=workspace,
        policy=tmp_path / ".hframe" / "policy.allowlist",
    )
    verify(cfg)
    _init_identity(original)
    _init_identity(workspace)

    # No PYTHONPATH: launcher execs membrane zipapp under .hframe/
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    subprocess.run(
        [str(bridge), "in"],
        cwd=str(workspace),
        check=True,
        env=env,
        capture_output=True,
    )

    assert (workspace / "src" / "hello.txt").read_text(encoding="utf-8") == "v0\n"

    (workspace / "src" / "hello.txt").write_text("v1\n", encoding="utf-8")
    _git(workspace, "add", "src/hello.txt")
    _git(
        workspace,
        "commit",
        "-m",
        "agent: bump hello to v1\n\nExport body line.",
    )
    subprocess.run(
        [str(bridge), "out"],
        cwd=str(workspace),
        check=True,
        env=env,
        capture_output=True,
    )

    assert (original / "src" / "hello.txt").read_text(encoding="utf-8") == "v1\n"

    proc = subprocess.run(
        ["git", "-C", str(original), "log", "-1", "--format=%B"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert "agent: bump hello to v1" in proc.stdout
    assert "Export body line." in proc.stdout

    check = tmp_path / "verify_clone"
    subprocess.run(
        ["git", "clone", str(bare), str(check)], check=True, capture_output=True
    )
    assert (check / "src" / "hello.txt").read_text(encoding="utf-8") == "v1\n"
