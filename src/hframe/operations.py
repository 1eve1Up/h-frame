"""High-level H-Frame workflows."""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from pathlib import Path

from hframe.config import HFrameConfig
from hframe.git_ops import (
    GitError,
    assert_no_remotes,
    assert_workspace_tracked_clean,
    git_add_all,
    git_add_paths,
    git_commit_staged,
    git_pull,
    git_push,
    list_remotes,
    remove_all_remotes,
    workspace_head_commit_message,
)
from hframe.rsync_util import rsync_filtered
from hframe.sync_policy import (
    PolicyMode,
    SyncPolicy,
    load_sync_policy,
    validate_sync_policy,
)


def default_policy_template() -> str:
    return (
        "# Default: allowlist mode. Optional user deny globs: .hframe/policy.denylist\n"
        "# Switch to denylist-only (sync everything except built-in + user denies):\n"
        "# # hframe-policy: mode denylist-only\n"
        "\n"
        "# Allowlist: paths relative to repo root (see H-Frame PRD).\n"
        "# VS Code / devcontainers: keep so ``./hframe in`` (rsync --delete) does not strip them.\n"
        ".devcontainer/**\n"
        ".devcontainer.json\n"
        "src/**\n"
        "tests/**\n"
        "docs/**\n"
        "pyproject.toml\n"
        "package.json\n"
        "Dockerfile\n"
        "README.md\n"
    )


def allowlist_pathspecs(patterns: list[str]) -> list[str]:
    """Map allow patterns to arguments for `git add --`."""
    specs: list[str] = []
    for p in patterns:
        p = p.strip()
        if p.endswith("/**"):
            specs.append(p[: -len("/**")].lstrip("/"))
        elif p.endswith("/"):
            specs.append(p.rstrip("/").lstrip("/"))
        else:
            specs.append(p.lstrip("/"))
    seen: set[str] = set()
    out: list[str] = []
    for s in specs:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def sync_in(cfg: HFrameConfig) -> dict:
    """Pull upstream in protected repo, then rsync allowlisted paths into workspace."""
    cfg.validate()
    assert_no_remotes(cfg.workspace)
    sync_policy = load_sync_policy(cfg.policy)
    validate_sync_policy(sync_policy)
    git_pull(cfg.original)
    deny_only = sync_policy.mode == PolicyMode.DENYLIST_ONLY
    rsync_filtered(
        cfg.original,
        cfg.workspace,
        deny_only=deny_only,
        allow_patterns=list(sync_policy.allow_patterns),
        user_deny_patterns=list(sync_policy.user_deny_patterns) or None,
        delete=True,
    )
    return _receipt("in", cfg.policy, sync_policy)


def sync_out(cfg: HFrameConfig) -> dict:
    """Rsync allowlisted paths workspace → original, then stage those paths in original."""
    cfg.validate()
    assert_no_remotes(cfg.workspace)
    sync_policy = load_sync_policy(cfg.policy)
    validate_sync_policy(sync_policy)
    deny_only = sync_policy.mode == PolicyMode.DENYLIST_ONLY
    rsync_filtered(
        cfg.workspace,
        cfg.original,
        deny_only=deny_only,
        allow_patterns=list(sync_policy.allow_patterns),
        user_deny_patterns=list(sync_policy.user_deny_patterns) or None,
        delete=True,
    )
    if deny_only:
        git_add_all(cfg.original)
    else:
        git_add_paths(
            cfg.original, allowlist_pathspecs(list(sync_policy.allow_patterns))
        )
    return _receipt("out", cfg.policy, sync_policy)


def sync_out_and_push(cfg: HFrameConfig, *, remote: str = "origin") -> dict:
    """Rsync allowlisted paths to protected repo, commit with workspace HEAD message, push."""
    cfg.validate()
    assert_no_remotes(cfg.workspace)
    assert_workspace_tracked_clean(cfg.workspace)
    export_msg = workspace_head_commit_message(cfg.workspace)
    rec = sync_out(cfg)
    git_commit_staged(cfg.original, export_msg)
    git_push(cfg.original, remote=remote)
    return rec


def rebuild_workspace(cfg: HFrameConfig) -> None:
    """Recreate workspace from protected repo copy; remotes removed."""
    cfg.validate()
    if cfg.workspace.resolve() == cfg.original.resolve():
        raise ValueError("workspace and original paths must differ")
    if cfg.workspace.is_dir():
        shutil.rmtree(cfg.workspace)
    subprocess.run(
        ["cp", "-a", str(cfg.original), str(cfg.workspace)],
        check=True,
        capture_output=True,
        text=True,
    )
    remove_all_remotes(cfg.workspace)
    assert_no_remotes(cfg.workspace)


def verify(cfg: HFrameConfig) -> None:
    """Check invariants: workspace has no remotes; paths are git dirs."""
    cfg.validate()
    assert_no_remotes(cfg.workspace)
    if not list_remotes(cfg.original):
        raise GitError(
            "protected repo has no remotes configured (expected at least origin)"
        )


def _receipt(direction: str, policy: Path, sync_policy: SyncPolicy) -> dict:
    return {
        "sync_id": f"sync-{int(time.time())}",
        "direction": direction,
        "policy": str(policy),
        "policy_mode": sync_policy.mode.value,
        "allow_rules": len(sync_policy.allow_patterns),
        "user_deny_rules": len(sync_policy.user_deny_patterns),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def write_receipt_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
