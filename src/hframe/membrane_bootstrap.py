"""Operator bootstrap: fixed layout + source membrane zipapp bundle."""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
from pathlib import Path

from hframe.build_membrane_pyz import build_membrane_pyz
from hframe.config import MEMBRANE_PYZ_NAME
from hframe.git_ops import assert_no_remotes, clone, remove_all_remotes
from hframe.gitignore_policy import (
    format_bootstrap_allowlist_body,
    format_seeded_denylist_body,
    read_gitignore_deny_patterns,
    root_allow_patterns_from_protected_repo,
)
from hframe.operations import default_policy_template
from hframe.policy_fs import harden_hframe_bundle
from hframe.policy_vault import (
    emit_vault_password_debug,
    generate_vault_key,
    key_to_b64,
    seal_policy_files,
)
from hframe.shim_install import install_bootstrap_vault_cli, install_workspace_shim

POLICY_REL = Path(".hframe") / "policy.allowlist"
POLICY_DENY_REL = Path(".hframe") / "policy.denylist"

DEFAULT_DENYLIST_TEMPLATE = (
    "# Optional: one glob per line (same path syntax as policy.allowlist).\n"
    "# Merged after built-in denies (see hframe.filters.DEFAULT_DENY_GLOBS).\n"
    "# secrets/**\n"
)

BOOTSTRAP_ENV_REL = Path(".hframe") / "bootstrap.env"
AGENTS_APPEND_FILE_ENV = "HFRAME_AGENTS_APPEND_FILE"

# Dev Containers: default workspace is only the git repo, so ../.hframe is invisible unless
# we add bind mounts. Two targets match shim_install.resolve_membrane_pyz (direct + hframe-root).
# postCreateCommand: avoid dubious-ownership errors for interactive git in Dev Containers.
_SAFE_DIR_POSTCREATE = (
    "git config --global --get-all safe.directory 2>/dev/null | grep -qFx '*' || "
    "git config --global --add safe.directory '*'"
)
_WORKSPACE_DEVCONTAINER = {
    "name": "h-frame",
    "image": "mcr.microsoft.com/devcontainers/base:bookworm",
    "mounts": [
        "source=${localWorkspaceFolder}/..,target=/workspaces/hframe-root,type=bind,consistency=cached",
        "source=${localWorkspaceFolder}/../.hframe,target=/workspaces/.hframe,type=bind,consistency=cached,readonly",
    ],
    "postCreateCommand": _SAFE_DIR_POSTCREATE,
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


def _require_vault_cli_installed() -> None:
    if importlib.util.find_spec("hframe.vault_cli") is None:
        raise RuntimeError(
            "hframe-bootstrap --vault requires hframe.vault_cli in the active Python "
            f"({sys.executable}). Install from a current tree, e.g.\n"
            "  pip install -e '/path/to/H-Frame[vault]'\n"
            "Then re-run bootstrap."
        )


def bootstrap_membrane(
    git_url: str, parent: Path | None = None, *, use_vault: bool = False
) -> None:
    """
    Create ``parent/<slug>_repo``, ``parent/<slug>_workspace_repo``,
    ``parent/.hframe/policy.allowlist`` and ``parent/.hframe/policy.denylist``
    (defaults when absent: allowlist built from non-ignored root paths via ``git check-ignore``;
    denylist seeded from the protected clone's root ``.gitignore``; if no root paths qualify,
    falls back to denylist-only policy),
    build ``parent/.hframe/hframe-membrane.pyz`` (source zipapp),
    install ``<slug>_workspace_repo/hframe`` (POSIX: portable ``python3`` launcher;
    Windows: prebuilt ``.exe``),
    add ``<slug>_workspace_repo/.devcontainer/devcontainer.json`` when missing (Dev
    Container bind mounts for ``../.hframe`` and the bootstrap parent),
    and optionally append operator-provided content to workspace ``AGENTS.md`` when
    ``HFRAME_AGENTS_APPEND_FILE`` is set (shell env or ``.hframe/bootstrap.env``).

    Default H-Frame sync rules are documented in README, not written to ``AGENTS.md``.

    Relative paths in ``HFRAME_AGENTS_APPEND_FILE`` resolve from the process working
    directory when bootstrap starts, not from the bootstrap parent layout directory.

    ``slug`` is derived from ``git_url`` (see ``repo_slug_from_git_url``).
    """
    bootstrap_cwd = Path.cwd().resolve()
    root = (parent or bootstrap_cwd).resolve()
    protected_name, workspace_name = membrane_directory_names(git_url)
    original = root / protected_name
    workspace = root / workspace_name
    policy = root / POLICY_REL

    if original.exists():
        raise ValueError(f"refusing to overwrite existing protected repo: {original}")
    if workspace.exists():
        raise ValueError(f"refusing to overwrite existing workspace: {workspace}")

    policy.parent.mkdir(parents=True, exist_ok=True)
    deny_policy = root / POLICY_DENY_REL
    seed_allow = not policy.is_file()
    seed_deny = not deny_policy.is_file()

    clone(git_url, original)
    subprocess.run(
        ["cp", "-a", str(original), str(workspace)],
        check=True,
        capture_output=True,
        text=True,
    )
    remove_all_remotes(workspace)
    assert_no_remotes(workspace)

    if seed_allow:
        roots = root_allow_patterns_from_protected_repo(original)
        if roots:
            policy.write_text(format_bootstrap_allowlist_body(roots), encoding="utf-8")
        else:
            policy.write_text(default_policy_template(), encoding="utf-8")
    if seed_deny:
        deny_policy.write_text(
            format_seeded_denylist_body(read_gitignore_deny_patterns(original)),
            encoding="utf-8",
        )
    elif not deny_policy.is_file():
        deny_policy.write_text(DEFAULT_DENYLIST_TEMPLATE, encoding="utf-8")

    hframe_dir = policy.parent
    bootstrap_root = hframe_dir.parent.resolve()
    policy_paths: list[Path] = []
    if use_vault:
        _require_vault_cli_installed()
        vault_key = generate_vault_key()
        emit_vault_password_debug(vault_key)
        allow_vault, deny_vault = seal_policy_files(
            hframe_dir,
            allow_plain=policy,
            deny_plain=deny_policy,
            key=vault_key,
        )
        policy_paths = [allow_vault, deny_vault]
        cfg = {
            "original_rel": str(original.relative_to(bootstrap_root)),
            "workspace_rel": str(workspace.relative_to(bootstrap_root)),
            "policy_vault": {
                "allow_rel": str(allow_vault.relative_to(bootstrap_root)),
                "deny_rel": str(deny_vault.relative_to(bootstrap_root)),
                "key_b64": key_to_b64(vault_key),
            },
        }
    else:
        policy_paths = [p for p in (policy, deny_policy) if p.is_file()]
        cfg = {
            "original_rel": str(original.relative_to(bootstrap_root)),
            "workspace_rel": str(workspace.relative_to(bootstrap_root)),
            "policy_rel": str(policy.relative_to(bootstrap_root)),
        }
    pyz = hframe_dir / MEMBRANE_PYZ_NAME
    build_membrane_pyz(pyz, config=cfg)
    harden_hframe_bundle(hframe_dir, policy_paths=policy_paths)
    install_workspace_shim(workspace / "hframe")
    if use_vault:
        install_bootstrap_vault_cli(bootstrap_root)
    write_workspace_devcontainer_if_missing(workspace)
    append_path = resolve_agents_append_file(bootstrap_root, cwd=bootstrap_cwd)
    _append_agents_md(workspace, append_path)


def _parse_bootstrap_env_file(env_file: Path) -> list[tuple[str, str]]:
    if not env_file.is_file():
        return []
    pairs: list[tuple[str, str]] = []
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        if not key:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        pairs.append((key, value))
    return pairs


def load_bootstrap_env(bootstrap_root: Path, *, cwd: Path | None = None) -> None:
    """
    Load ``.hframe/bootstrap.env`` into ``os.environ``.

    Checks, in order (later files override earlier; shell exports always win):

    1. ``<layout-parent>/.hframe/bootstrap.env`` (scratch workspace above ``*-parent/``)
    2. ``<cwd>/.hframe/bootstrap.env``
    3. ``<bootstrap-root>/.hframe/bootstrap.env``
    """
    base = (cwd or Path.cwd()).resolve()
    root = bootstrap_root.resolve()
    seen: set[Path] = set()
    candidates: list[Path] = []
    for env_file in (
        root.parent / BOOTSTRAP_ENV_REL,
        base / BOOTSTRAP_ENV_REL,
        root / BOOTSTRAP_ENV_REL,
    ):
        resolved = env_file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        candidates.append(resolved)

    initial_keys = frozenset(os.environ)
    merged: dict[str, str] = {}
    for env_file in candidates:
        for key, value in _parse_bootstrap_env_file(env_file):
            merged[key] = value
    for key, value in merged.items():
        if key not in initial_keys:
            os.environ[key] = value


def resolve_agents_append_file(
    bootstrap_root: Path, *, cwd: Path | None = None
) -> Path | None:
    """Return the operator snippet path from env, or ``None`` when unset."""
    load_bootstrap_env(bootstrap_root, cwd=cwd)
    raw = os.environ.get(AGENTS_APPEND_FILE_ENV, "").strip()
    if not raw:
        return None
    base = (cwd or Path.cwd()).resolve()
    path = Path(raw)
    if not path.is_absolute():
        path = base / path
    path = path.resolve()
    if not path.is_file():
        raise ValueError(
            f"{AGENTS_APPEND_FILE_ENV}={raw!r} does not resolve to a readable file: {path}"
        )
    return path


def _append_agents_md(workspace: Path, append_file: Path | None) -> None:
    if append_file is None:
        return
    snippet = append_file.read_text(encoding="utf-8")
    path = workspace / "AGENTS.md"
    if path.is_file():
        existing = path.read_text(encoding="utf-8")
        separator = "" if existing.endswith("\n") or not snippet else "\n"
        path.write_text(existing + separator + snippet, encoding="utf-8")
    else:
        path.write_text(snippet.lstrip("\n"), encoding="utf-8")
