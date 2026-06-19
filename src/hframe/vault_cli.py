"""Operator CLI: decrypt/encrypt vault policy with ``HFRAME_VAULT_PASS`` (bootstrap password)."""

from __future__ import annotations

import sys
from pathlib import Path

from hframe.policy_fs import harden_hframe_bundle, permit_policy_vault_rewrite
from hframe.policy_vault import (
    ALLOW_VAULT_NAME,
    BOOTSTRAP_DEBUG_ENV,
    DENY_VAULT_NAME,
    VAULT_PASS_ENV,
    assert_vault_password_matches_membrane,
    membrane_vault_key,
    read_vault_file,
    vault_password_from_env,
    write_vault_file,
)

_TARGET_ALIASES: dict[str, str] = {
    "allowlist": "allowlist",
    "allowlist-file": "allowlist",
    "denylist": "denylist",
    "denylist-file": "denylist",
}

_VAULT_FILES = {
    "allowlist": ALLOW_VAULT_NAME,
    "denylist": DENY_VAULT_NAME,
}

_EDIT_FILES = {
    "allowlist": "policy.allowlist.edit",
    "denylist": "policy.denylist.edit",
}


def hframe_dir_from_script(argv0: str) -> Path:
    root = Path(argv0).resolve().parent
    hf = root / ".hframe"
    if not hf.is_dir():
        raise ValueError(f".hframe directory not found next to {root}")
    return hf


def _target_from_vault_path(path: Path) -> str | None:
    name = path.name
    if name == ALLOW_VAULT_NAME or "allowlist" in name and name.endswith(".vault"):
        return "allowlist"
    if name == DENY_VAULT_NAME or "denylist" in name and name.endswith(".vault"):
        return "denylist"
    return None


def resolve_hframe_and_target(argv0: str, target_arg: str) -> tuple[Path, str]:
    raw = target_arg.strip()
    if "/" in raw or raw.startswith("."):
        vault_path = Path(raw).expanduser().resolve()
        if not vault_path.is_file():
            raise ValueError(f"vault file not found: {vault_path}")
        target = _target_from_vault_path(vault_path)
        if target is None:
            raise ValueError(
                f"cannot infer target from vault filename {vault_path.name!r}; "
                "use allowlist or denylist"
            )
        hf = vault_path.parent
        if hf.name != ".hframe":
            raise ValueError(f"vault file must live under .hframe/, got {hf}")
        return hf, target
    return hframe_dir_from_script(argv0), _normalize_target(raw)


def _normalize_target(name: str) -> str:
    t = _TARGET_ALIASES.get(name.strip().lower())
    if t is None:
        raise ValueError(
            f"unknown target {name!r}; use allowlist, denylist, allowlist-file, or denylist-file"
        )
    return t


def cmd_decrypt(hf: Path, target: str, key: bytes) -> None:
    vault = hf / _VAULT_FILES[target]
    edit = hf / _EDIT_FILES[target]
    if not vault.is_file():
        raise ValueError(f"vault file not found: {vault}")
    edit.write_text(read_vault_file(vault, key), encoding="utf-8")
    sys.stdout.write(f"hframe-vault: wrote {edit}\n")


def cmd_encrypt(hf: Path, target: str, key: bytes) -> None:
    vault = hf / _VAULT_FILES[target]
    edit = hf / _EDIT_FILES[target]
    if not edit.is_file():
        raise ValueError(f"edit file not found: {edit} (run decrypt first)")
    plaintext = edit.read_text(encoding="utf-8")
    permit_policy_vault_rewrite(hf)
    write_vault_file(vault, plaintext, key)
    if read_vault_file(vault, membrane_vault_key(hf)) != plaintext:
        raise ValueError("re-seal failed: ./hframe would not read this policy")
    edit.unlink(missing_ok=True)
    harden_hframe_bundle(
        hf,
        policy_paths=[hf / ALLOW_VAULT_NAME, hf / DENY_VAULT_NAME],
    )
    sys.stdout.write(f"hframe-vault: re-sealed {vault}\n")


def cmd_show(hf: Path, target: str | None, key: bytes) -> None:
    targets = ("allowlist", "denylist") if target is None else (target,)
    for t in targets:
        vault = hf / _VAULT_FILES[t]
        if not vault.is_file():
            sys.stderr.write(f"hframe-vault: missing {vault}\n")
            continue
        text = read_vault_file(vault, key)
        sys.stdout.write(f"--- {vault.name} ---\n")
        sys.stdout.write(text)
        if not text.endswith("\n"):
            sys.stdout.write("\n")


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if not args or args[0] not in ("decrypt", "encrypt", "show"):
        sys.stderr.write(
            f"usage: {VAULT_PASS_ENV}=<pw> ./hframe-vault decrypt|encrypt allowlist|denylist\n"
            f"       {VAULT_PASS_ENV}=<pw> ./hframe-vault show [allowlist|denylist]\n"
            f"       password: url-safe base64 from {BOOTSTRAP_DEBUG_ENV}=1 bootstrap\n"
            "       ./hframe in|out uses the compiled password (no env needed)\n"
        )
        return 2
    verb = args[0]
    try:
        if verb == "show":
            hf = hframe_dir_from_script(sys.argv[0])
            target = _normalize_target(args[1]) if len(args) > 1 else None
            if len(args) > 2:
                raise ValueError("too many arguments for show")
            key = assert_vault_password_matches_membrane(hf)
            cmd_show(hf, target, key)
            return 0
        if len(args) != 2:
            raise ValueError(f"{verb} requires exactly one target")
        hf, target = resolve_hframe_and_target(sys.argv[0], args[1])
        if verb == "decrypt":
            key = vault_password_from_env()
            cmd_decrypt(hf, target, key)
        else:
            key = assert_vault_password_matches_membrane(hf)
            cmd_encrypt(hf, target, key)
    except ValueError as e:
        sys.stderr.write(f"hframe-vault: {e}\n")
        return 1
    except Exception as e:
        sys.stderr.write(f"hframe-vault: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
