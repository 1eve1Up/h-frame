"""Workspace-local bridge: only ``hframe in`` and ``hframe out``; config is compile-time only."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from hframe.config import HFrameConfig, PolicyVaultConfig
from hframe.operations import sync_in, sync_out_and_push
from hframe.policy_vault import key_from_b64

# When the zipapp is only bind-mounted at ``/workspaces/.hframe``, ``sys.argv[0]`` resolves
# under ``/workspaces/.hframe/`` and ``Path.parent.parent`` is ``/workspaces``, not the
# bootstrap parent. Try this mount next (same name as ``shim_install._DEVCONTAINER_PARENT_MOUNT``).
DEVCONTAINER_BOOTSTRAP_ROOT = Path("/workspaces/hframe-root")


def _membrane_pyz_path() -> Path:
    """Locate this zipapp on disk from ``sys.argv``.

    Zipapp invocations use ``argv[0]`` as the path to the ``.pyz`` file.
    """
    if not sys.argv:
        raise ValueError("missing sys.argv")
    arg0 = Path(sys.argv[0])
    if arg0.suffix.lower() == ".pyz" or arg0.name.lower().endswith(".pyz"):
        return arg0.resolve()
    raise ValueError(f"membrane argv[0] must be the .pyz path, got {sys.argv[0]!r}")


def _resolve_bootstrap_root(pyz: Path, original_rel: Path) -> Path:
    """
    Directory that contains ``original_rel``, ``workspace_rel``, and ``.hframe/``.

    Tries the path implied by the zipapp location first, then the devcontainer
    ``hframe-root`` mount, so the same zipapp works on the host and in a container.
    """
    pyz = pyz.resolve()
    candidates: list[Path] = []
    seen: set[Path] = set()

    def add(p: Path) -> None:
        try:
            r = p.resolve()
        except OSError:
            return
        if r in seen:
            return
        seen.add(r)
        candidates.append(r)

    add(pyz.parent.parent)
    add(DEVCONTAINER_BOOTSTRAP_ROOT)

    for root in candidates:
        orig = root / original_rel
        if orig.is_dir() and (orig / ".git").is_dir():
            return root
    return pyz.parent.parent.resolve()


def _policy_vault_from_embedded(
    root: Path, vault_cfg: dict[str, Any]
) -> PolicyVaultConfig:
    for key in ("allow_rel", "deny_rel", "key_b64"):
        if key not in vault_cfg:
            raise KeyError(key)
    return PolicyVaultConfig(
        allow=(root / str(vault_cfg["allow_rel"])).resolve(),
        deny=(root / str(vault_cfg["deny_rel"])).resolve(),
        key=key_from_b64(str(vault_cfg["key_b64"])),
    )


def _cfg_from_embedded_relative(cfg: dict[str, Any], *, pyz: Path) -> HFrameConfig:
    for key in ("original_rel", "workspace_rel"):
        if key not in cfg:
            raise KeyError(key)
    root = _resolve_bootstrap_root(pyz, Path(cfg["original_rel"]))
    original = (root / cfg["original_rel"]).resolve()
    workspace = (root / cfg["workspace_rel"]).resolve()
    if "policy_vault" in cfg:
        vault = _policy_vault_from_embedded(root, cfg["policy_vault"])
        return HFrameConfig(original=original, workspace=workspace, policy_vault=vault)
    if "policy_rel" not in cfg:
        raise KeyError("policy_rel")
    policy = (root / cfg["policy_rel"]).resolve()
    return HFrameConfig(original=original, workspace=workspace, policy=policy)


def _cfg_from_embedded_absolute(cfg: dict[str, Any]) -> HFrameConfig:
    for key in ("original", "workspace"):
        if key not in cfg:
            raise KeyError(key)
    original = Path(str(cfg["original"])).resolve()
    workspace = Path(str(cfg["workspace"])).resolve()
    if "policy_vault" in cfg:
        vault_cfg = cfg["policy_vault"]
        for key in ("allow", "deny", "key_b64"):
            if key not in vault_cfg:
                raise KeyError(key)
        return HFrameConfig(
            original=original,
            workspace=workspace,
            policy_vault=PolicyVaultConfig(
                allow=Path(str(vault_cfg["allow"])).resolve(),
                deny=Path(str(vault_cfg["deny"])).resolve(),
                key=key_from_b64(str(vault_cfg["key_b64"])),
            ),
        )
    if "policy" not in cfg:
        raise KeyError("policy")
    policy = Path(str(cfg["policy"])).resolve()
    return HFrameConfig(original=original, workspace=workspace, policy=policy)


def _cfg_from_embedded(cfg: dict[str, Any]) -> HFrameConfig:
    if not isinstance(cfg, dict):
        raise TypeError("configuration must be a mapping")
    if "original_rel" in cfg:
        pyz = _membrane_pyz_path()
        return _cfg_from_embedded_relative(cfg, pyz=pyz)
    if "original" in cfg:
        return _cfg_from_embedded_absolute(cfg)
    raise KeyError("original")


def main(cfg: dict[str, Any]) -> int:
    """
    Entry for the generated ``<slug>_workspace_repo/hframe`` executable.

    Accepts exactly one subcommand: ``in`` or ``out``. No paths, flags, or env-based config.
    """
    argv = sys.argv
    if len(argv) != 2 or argv[1] not in {"in", "out"}:
        sys.stderr.write("usage: ./hframe in\n       ./hframe out\n")
        return 2

    try:
        hcfg = _cfg_from_embedded(cfg)
    except (KeyError, TypeError, ValueError) as e:
        sys.stderr.write(f"hframe: invalid embedded configuration: {e}\n")
        return 2

    cmd = argv[1]
    try:
        if cmd == "in":
            sync_in(hcfg)
        else:
            sync_out_and_push(hcfg)
    except Exception as e:
        sys.stderr.write(f"hframe: {e}\n")
        return 1
    return 0
