# H-Frame releases

## v2026.6.1

**Date:** June 2026  
**Stability:** early public preview  
**Topology / contract:** evolving  
**Production claim:** suitable for **controlled** agent workflows and experimentation—not a substitute for code review, SDLC policy, or execution sandboxing. See [README](README.md) and [PRD](PRD.md).

- **Distribution:** install from GitHub clone (``pip install -e .``; import ``hframe``; executables ``hframe-bootstrap`` / ``hframe-vault``). Repo: **`1eve1Up/h-frame`**.
- **Windows shim:** prebuilt **`h-frame-shim-windows-amd64.exe`** in the wheel built by CI (see ``src/hframe/native/prebuilt/``).
- **Release line:** GitHub tag **`v2026.6.1`**; CI builds and validates wheels via [``.github/workflows/ci.yml``](.github/workflows/ci.yml).

**Packaging note:** The release line is **`v2026.6.1`**. Package version in ``pyproject.toml`` is **`2026.6.1`**. Bump ``pyproject.toml`` and ``src/hframe/__init__.py`` together when shipping.

## v2026.6.0

**Date:** June 2026  
**Stability:** early public preview  
**Topology / contract:** evolving  
**Production claim:** suitable for **controlled** agent workflows and experimentation—not a substitute for code review, SDLC policy, or execution sandboxing. See [README](README.md) and [PRD](PRD.md).

- **Agent sync rules:** default H-Frame sync guidance moved from auto-appended workspace ``AGENTS.md`` to README (**H-Frame Sync Rules**). Operators who want workspace-local snippets can set ``HFRAME_AGENTS_APPEND_FILE`` or ``.hframe/bootstrap.env`` before bootstrap (see README).

## v2026.5.2

**Date:** May 2026  
**Stability:** early public preview  
**Topology / contract:** evolving  
**Production claim:** suitable for **controlled** agent workflows and experimentation—not a substitute for code review, SDLC policy, or execution sandboxing. See [README](README.md) and [PRD](PRD.md).

- **Policy tamper resistance:** bootstrap sets POSIX ``0444`` on policy artifacts under ``.hframe/``; new devcontainers bind-mount ``../.hframe`` **read-only** (repos stay writable via ``hframe-root``). Optional ``hframe-bootstrap --vault`` encrypts ``policy.allowlist`` / ``policy.denylist`` to ``*.vault`` (plaintext removed) with a one-time key embedded only in ``hframe-membrane.pyz`` (``pip install -e '.[vault]'`` from a clone); installs ``./hframe-vault`` for ``HFRAME_VAULT_PASS=… ./hframe-vault decrypt|encrypt allowlist|denylist``. **Migration:** existing devcontainers—add ``,readonly`` to the ``.hframe`` mount line (see README).

## v2026.5.1

**Date:** May 2026  
**Stability:** early public preview  
**Topology / contract:** evolving  
**Production claim:** suitable for **controlled** agent workflows and experimentation—not a substitute for code review, SDLC policy, or execution sandboxing. See [README](README.md) and [PRD](PRD.md).

- **Dev Containers + membrane paths:** new bootstraps embed **bootstrap-relative** paths in the zipapp so ``./hframe in`` / ``out`` resolve ``*_repo`` and ``*_workspace_repo`` under the mounted ``hframe-root`` layout, not only on the host where bootstrap ran. Regenerate ``.hframe/hframe-membrane.pyz`` once after upgrading; zipapps with legacy absolute paths still work on the original host.
- **Git in Dev Containers:** membrane ``git`` subprocesses pass ``-c safe.directory=<resolved-repo>`` so bind mounts are not blocked by “dubious ownership”; bootstrap-generated devcontainers also add global ``safe.directory '*'`` in ``postCreateCommand`` for interactive ``git`` (merge into your own ``postCreateCommand`` with ``&&`` if needed). Regenerate ``hframe-membrane.pyz`` after upgrading so the bundle includes this behavior.

## v2026.5.0

**Date:** May 2026  
**Stability:** early public preview  
**Topology / contract:** evolving  
**Production claim:** suitable for **controlled** agent workflows and experimentation—not a substitute for code review, SDLC policy, or execution sandboxing. See [README](README.md) and [PRD](PRD.md).

This is the first documented public-preview release line for H-Frame as described in the README and PRD.

**Packaging note:** The release line is **`v2026.5.0`**. Package version in ``pyproject.toml`` is **`2026.5.0`**. Bump ``pyproject.toml`` and ``src/hframe/__init__.py`` together when shipping.

### Package `2026.5.0` (May 2026)

- **POSIX workspace `./hframe`:** bootstrap now installs a **portable `#!/usr/bin/env python3` launcher** (stdlib only) instead of a native Mach-O/ELF binary, so the same workspace tree works on **macOS and Linux** (including devcontainers) without exec-format mismatches. Optional reference native launcher remains in `src/hframe/native/shim.c`.
- **Default policy files:** **`hframe-bootstrap`** writes **allowlist** lines in ``policy.allowlist`` (one pattern per repo-root path Git does not ignore, via ``git check-ignore``; directories as ``name/**``). **``policy.denylist``** is seeded from the protected clone’s root **``.gitignore``** (``!`` negation lines omitted). If no root paths qualify, bootstrap falls back to **denylist-only** (see README / PRD).
- **Membrane zipapp:** `hframe-membrane.pyz` is now a **source** zipapp (``.py`` under ``.hframe/``), not bytecode-only, so it runs under any supported ``python3`` minor (e.g. bootstrap on 3.11, devcontainer on 3.12) without `can't find '__main__'` from magic skew. Re-bootstrap once to regenerate `.hframe/hframe-membrane.pyz`.
- **Workspace launcher:** if ``<workspace-parent>/.hframe/`` is absent, resolves the zipapp when **exactly one** subdirectory of that parent contains ``.hframe/hframe-membrane.pyz`` (flat ``/workspaces/<slug>_workspace_repo`` next to ``/workspaces/hframe-root/.hframe``). Reinstall the workspace ``./hframe`` script after upgrading the ``hframe`` package.

### Shipped scope (preview)

- **Bootstrap** (`hframe-bootstrap <git-url>`): parent layout with **`<slug>_repo`** (protected clone, keeps `origin`), **`<slug>_workspace_repo`** (workspace, remotes removed), **`.hframe/`** (policy templates, source `hframe-membrane.pyz`, optional denylist file).
- **Workspace bridge** `<slug>_workspace_repo/hframe`: **POSIX:** portable `python3` script; **Windows:** prebuilt `h-frame-shim-*.exe` from package data; runs `python3` on the membrane zipapp (canonical ``../.hframe/`` or a unique sibling ``*/.hframe/`` under the workspace parent; see README).
- **Sync surface:** `./hframe in` and `./hframe out` only (no paths, flags, or env-based policy in the agent helper).
- **Policy:** default **allowlist** via `.hframe/policy.allowlist` (bootstrap-generated root paths); **`.hframe/policy.denylist`** from root `.gitignore`; optional **denylist-only** mode (see README). **`git add -A`** on export only in denylist-only mode.
- **Built-in denylist** for common agent/orchestration paths (`src/hframe/filters.py` — `DEFAULT_DENY_GLOBS`).
- **Git behavior:** workspace must be clean (tracked) before `out`; protected commit uses **full workspace `HEAD` message**; push from protected repo only.
- **Docs / trust baseline:** Apache-2.0, README narrative aligned with PRD, `CONTRIBUTING.md`, `SECURITY.md`, this file.

### Install and verify

From a clone:

```bash
pip install -e '.[dev]'
ruff check src tests
pytest
```

Operator install (bootstrap only; agents use `./hframe` in the workspace):

```bash
git clone https://github.com/1eve1Up/h-frame.git
cd h-frame
pip install -e .
# vault: pip install -e '.[vault]'
```

### Stability statement

Until a future **stable** commitment called out in README / PRD:

- **Policy files** (allowlist / denylist / mode directive) may gain options or stricter validation; migration notes belong in this file when behavior changes.
- **Embedded paths** in the zipapp are fixed at bootstrap; changing layout or policy location may require re-bootstrap or explicit operator migration.
- **Receipt JSON** from sync operations may gain fields; treat as diagnostic, not a long-term external API unless documented.

### Known limitations (by design)

- **Not a sandbox:** H-Frame does not isolate syscall-level execution; agents can run arbitrary code inside the workspace. Safety is **topology + sync policy**, not VM/container guarantees (PRD non-goals).
- **Not a git replacement:** remotes, review, and CI remain customer responsibilities; the protected repo is the only tree that should push upstream.
- **Source membrane zipapp** is portable across **Python 3.11+** minors used at bootstrap vs in the agent environment; re-bootstrap regenerates `.hframe/hframe-membrane.pyz` when upgrading `hframe`.
- **`./hframe out` in denylist-only mode** stages with **`git add -A`** on the protected repo after rsync—broad by intent; operators must size denylists and reviews accordingly (README).

### Non-goals

H-Frame is not: a Kubernetes/deploy orchestrator, a secrets manager, a universal policy DSL, cryptographic provenance, or a replacement for human review. See PRD **Non-Goals** and README **Current non-goals**.

### Maintainer

[H-Frame](README.md) is maintained by [Level Up Labs](https://levelupla.io) as open source (Apache-2.0).
