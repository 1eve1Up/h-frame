"""Operator bootstrap: fixed layout + source membrane zipapp bundle."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from hframe.build_membrane_pyz import build_membrane_pyz
from hframe.config import MEMBRANE_PYZ_NAME
from hframe.git_ops import assert_no_remotes, clone, remove_all_remotes
from hframe.operations import default_policy_template
from hframe.shim_install import install_workspace_shim

POLICY_REL = Path(".hframe") / "policy.allowlist"
POLICY_DENY_REL = Path(".hframe") / "policy.denylist"

DEFAULT_DENYLIST_TEMPLATE = (
    "# Optional: one glob per line (same path syntax as policy.allowlist).\n"
    "# Merged after built-in denies (see hframe.filters.DEFAULT_DENY_GLOBS).\n"
    "# secrets/**\n"
)

AGENTS_APPEND = (
    "\n## H-Frame Sync Rules\n\n"
    "Use:\n"
    "- `./hframe in`\n"
    "- `./hframe out`\n\n"
    "Do not attempt to modify synchronization behavior.\n"
    "Do not create alternative synchronization mechanisms.\n"
)

# Dev Containers: default workspace is only the git repo, so ../.hframe is invisible unless
# we add bind mounts. Two targets match shim_install.resolve_membrane_pyz (direct + hframe-root).
_WORKSPACE_DEVCONTAINER = {
    "name": "hframe",
    "image": "mcr.microsoft.com/devcontainers/base:bookworm",
    "mounts": [
        "source=${localWorkspaceFolder}/..,target=/workspaces/hframe-root,type=bind,consistency=cached",
        "source=${localWorkspaceFolder}/../.hframe,target=/workspaces/.hframe,type=bind,consistency=cached",
    ],
    "postCreateCommand": "git config --global --get-all safe.directory 2>/dev/null | grep -qFx '*' || git config --global --add safe.directory '*'",
}


def write_workspace_devcontainer_if_missing(workspace: Path) -> None:
    """
    If ``workspace/.devcontainer/devcontainer.json`` is absent, create one that bind-mounts
    the bootstrap parent and ``.hframe`` so ``./hframe`` resolves inside Dev Containers.

    If the cloned project already ships a devcontainer, this is a no-op (do not overwrite).
    """
    dc_dir = workspace / ".devcontainer"
    dc_file = dc_dir / "devcontainer.json"
    if dc_file.is_file():
        return
    dc_dir.mkdir(parents=True, exist_ok=True)
    dc_file.write_text(
        json.dumps(_WORKSPACE_DEVCONTAINER, indent=2) + "\n", encoding="utf-8"
    )


def repo_slug_from_git_url(git_url: str) -> str:
    """
    Derive a filesystem-safe directory basename from a clone URL (last path segment, no ``.git``).

    Handles common ``https://``, ``ssh://``, ``git@host:org/repo``, and ``file://`` forms.
    """
    s = git_url.strip().rstrip("/")
    if s.lower().endswith(".git"):
        s = s[:-4]
    path_part: str
    if s.startswith("git@") and ":" in s:
        _, _, rest = s.partition(":")
        path_part = rest
    elif "://" in s:
        without_scheme = s.split("://", 1)[1]
        slash = without_scheme.find("/")
        path_part = without_scheme[slash + 1 :] if slash != -1 else ""
    else:
        path_part = s
    base = path_part.rstrip("/").split("/")[-1] if path_part else ""
    base = base.strip() or "repo"
    safe = re.sub(r"[^0-9A-Za-z._-]+", "_", base).strip("._") or "repo"
    return safe


def membrane_directory_names(git_url: str) -> tuple[str, str]:
    """Return ``<slug>_repo`` and ``<slug>_workspace_repo`` directory basenames."""
    slug = repo_slug_from_git_url(git_url)
    return f"{slug}_repo", f"{slug}_workspace_repo"


def bootstrap_membrane(git_url: str, parent: Path | None = None) -> None:
    """
    Create ``parent/<slug>_repo``, ``parent/<slug>_workspace_repo``,
    ``parent/.hframe/policy.allowlist`` and ``parent/.hframe/policy.denylist`` (templates),
    build ``parent/.hframe/hframe-membrane.pyz`` (source zipapp),
    install ``<slug>_workspace_repo/hframe`` (POSIX: portable ``python3`` launcher;
    Windows: prebuilt ``.exe``),
    add ``<slug>_workspace_repo/.devcontainer/devcontainer.json`` when missing (Dev
    Container bind mounts for ``../.hframe`` and the bootstrap parent),
    and append ``AGENTS.md``.

    ``slug`` is derived from ``git_url`` (see ``repo_slug_from_git_url``).
    """
    root = (parent or Path.cwd()).resolve()
    protected_name, workspace_name = membrane_directory_names(git_url)
    original = root / protected_name
    workspace = root / workspace_name
    policy = root / POLICY_REL

    if original.exists():
        raise ValueError(f"refusing to overwrite existing protected repo: {original}")
    if workspace.exists():
        raise ValueError(f"refusing to overwrite existing workspace: {workspace}")

    policy.parent.mkdir(parents=True, exist_ok=True)
    if not policy.is_file():
        policy.write_text(default_policy_template(), encoding="utf-8")

    deny_policy = root / POLICY_DENY_REL
    if not deny_policy.is_file():
        deny_policy.write_text(DEFAULT_DENYLIST_TEMPLATE, encoding="utf-8")

    clone(git_url, original)
    subprocess.run(
        ["cp", "-a", str(original), str(workspace)],
        check=True,
        capture_output=True,
        text=True,
    )
    remove_all_remotes(workspace)
    assert_no_remotes(workspace)

    bootstrap_root = policy.parent.parent.resolve()
    cfg = {
        "original_rel": str(original.relative_to(bootstrap_root)),
        "workspace_rel": str(workspace.relative_to(bootstrap_root)),
        "policy_rel": str(policy.relative_to(bootstrap_root)),
    }
    pyz = policy.parent / MEMBRANE_PYZ_NAME
    build_membrane_pyz(pyz, config=cfg)
    install_workspace_shim(workspace / "hframe")
    write_workspace_devcontainer_if_missing(workspace)
    _append_agents_md(workspace)


def _append_agents_md(workspace: Path) -> None:
    path = workspace / "AGENTS.md"
    if path.is_file():
        path.write_text(
            path.read_text(encoding="utf-8") + AGENTS_APPEND, encoding="utf-8"
        )
    else:
        path.write_text(AGENTS_APPEND.lstrip("\n"), encoding="utf-8")
