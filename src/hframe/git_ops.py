"""Git subprocess helpers."""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path


class GitError(RuntimeError):
    pass


def _run(
    repo: Path, *args: str, check: bool = True
) -> subprocess.CompletedProcess[str]:
    # Dev Containers / Docker bind mounts often trigger "dubious ownership"; treat the
    # resolved repo path as safe for this subprocess only (no global git config).
    rp = repo.resolve()
    cmd = ("git", "-c", f"safe.directory={rp}", "-C", str(rp), *args)
    p = subprocess.run(
        cmd,
        check=False,
        text=True,
        capture_output=True,
    )
    if check and p.returncode != 0:
        raise GitError(
            f"git failed ({p.returncode}): {' '.join(cmd)}\n{p.stderr or p.stdout}"
        )
    return p


def list_remotes(repo: Path) -> list[str]:
    p = _run(repo, "remote", check=True)
    names = [line.strip() for line in p.stdout.splitlines() if line.strip()]
    return names


def remove_all_remotes(repo: Path) -> None:
    for name in list_remotes(repo):
        _run(repo, "remote", "remove", name)


def git_pull(repo: Path) -> None:
    _run(repo, "pull")


def git_push(repo: Path, remote: str = "origin", ref: str | None = None) -> None:
    args = ["push", remote]
    if ref:
        args.append(ref)
    _run(repo, *args)


def assert_no_remotes(repo: Path, label: str = "workspace") -> None:
    remotes = list_remotes(repo)
    if remotes:
        raise GitError(
            f"{label} must not have git remotes (invariant); found: {', '.join(remotes)}"
        )


def clone(remote_url: str, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(
        (
            "git",
            "-c",
            "safe.directory=*",
            "clone",
            remote_url,
            str(target),
        ),
        check=False,
        text=True,
        capture_output=True,
    )
    if p.returncode != 0:
        raise GitError(f"git clone failed: {remote_url}\n{p.stderr or p.stdout}")


def git_add_all(repo: Path) -> None:
    """Stage all changes under ``repo`` (denylist-only ``hframe out`` after rsync)."""
    _run(repo, "add", "-A")


def git_add_paths(repo: Path, paths: list[str]) -> None:
    """Stage paths that exist in the working tree (allowlist may name dirs not yet present)."""
    existing = [p for p in paths if (repo / p).exists()]
    if not existing:
        return
    _run(repo, "add", "--", *existing)


def has_staged_changes(repo: Path) -> bool:
    """Return True if the index differs from HEAD for staged paths."""
    p = _run(repo, "diff", "--cached", "--quiet", check=False)
    return p.returncode != 0


def assert_workspace_tracked_clean(workspace: Path) -> None:
    """Require no pending changes to tracked files (commit before ``hframe out``)."""
    if _run(workspace, "diff", "--quiet", check=False).returncode != 0:
        raise GitError(
            "workspace has unstaged changes to tracked files; commit before hframe out."
        )
    if _run(workspace, "diff", "--cached", "--quiet", check=False).returncode != 0:
        raise GitError("workspace has staged changes; commit before hframe out.")


def workspace_head_commit_message(workspace: Path) -> str:
    """Return the full ``HEAD`` commit message body (``git log -1 --format=%B``)."""
    p = _run(workspace, "log", "-1", "--format=%B", check=True)
    body = p.stdout.replace("\x00", "")
    if not body.strip():
        raise GitError(
            "workspace HEAD has an empty commit message; set a non-empty message before hframe out."
        )
    return body.rstrip("\n")


def git_commit_staged(repo: Path, message: str) -> bool:
    """Create a commit if there are staged changes. Message may be multiline (uses ``-F``)."""
    if not has_staged_changes(repo):
        return False
    msg = message.replace("\x00", "").rstrip("\n")
    if not msg.strip():
        raise GitError(
            "refusing to create an empty commit message on the protected repo"
        )
    if len(msg) > 100_000:
        msg = msg[:100_000]
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".git-msg",
        delete=False,
        encoding="utf-8",
    ) as f:
        f.write(msg)
        if not msg.endswith("\n"):
            f.write("\n")
        msg_path = Path(f.name)
    try:
        _run(repo, "commit", "-F", str(msg_path))
    finally:
        msg_path.unlink(missing_ok=True)
    return True
