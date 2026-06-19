# PRD: H-Frame (repository isolation membrane)

## Document control

This document is the **canonical product requirements specification** for H-Frame. Material that previously lived in `REVISION-TO-PRD.md` (membrane appliance model, compile-time embedding, revised CLI) is merged here. **Operational truth** for commands and layout is also described in [README.md](README.md); this PRD states intent, invariants, and acceptance-oriented detail.

---

## Overview

H-Frame is a **repository isolation and synchronization membrane** for safely operationalizing AI coding agents against customer repositories: it limits what can leave a **stochastic workspace** and reach a **canonical remote**, without exposing operator sync policy to the agent as a configurable runtime surface.

The hardened workflow:

```text
Customer Remote Repo
          |
      git pull / git push
          |
Protected Repo (<slug>_repo)
          |
   deterministic membrane
 (policy outside agent control)
          |
Workspace Repo (<slug>_workspace_repo)
          |
      Agents / automation
```

Under the intended workflow, agents do not use the protected clone as their working tree and do not use it for day-to-day edits; they use the workspace copy, which has no remotes configured for upstream push.

Instead:

* Agents operate only on disposable workspace copies.
* Workspace copies have **all git remotes removed** before agent use.
* Synchronization is mediated through **operator-controlled policy** (**allowlist** paths at bootstrap: non-ignored repo-root entries; **`.hframe/policy.denylist`** from root **`.gitignore`**; optional **denylist-only** mode) plus **built-in deny globs**.
* Only **sanitized filesystem deltas** propagate back to the protected repo (per policy).
* **Only the protected repo** may push to the remote (`./hframe out` performs push from the protected tree).

This architecture treats agent environments as intentionally **contaminated** execution zones while preserving a clean export boundary for customer-owned source code.

### Revision thesis (membrane appliance)

H-Frame is intentionally **not** a general-purpose configurable sync utility. It is a **bootstrapped, deterministic repository membrane appliance**:

* Synchronization behavior and paths are **fixed at bootstrap** into a **source zipapp** (`.hframe/hframe-membrane.pyz`) plus a **workspace-local launcher** (`./hframe`: POSIX uses a portable `python3` script; Windows uses a prebuilt shim).
* Agents receive **no** sync paths, flags, alternate destinations, or environment-based overrides for membrane behavior.
* Agents invoke exactly **`./hframe in`** and **`./hframe out`**—nothing else on the bridge CLI.

Philosophical shift:

| Earlier framing | Current framing |
| ----------------- | ----------------- |
| Agents should follow sync rules | Agents should have **no meaningful control** over synchronization |
| Runtime-configurable helper | **Compile-time / bootstrap-time** configured membrane |
| Prompt-dependent boundaries | **Topology-enforced**, appliance-like boundary |

The boundary must tolerate agents that are stochastic, over-creative, and instruction-sensitive; therefore the **membrane itself** is boring, minimal, and externally controlled (see [README.md](README.md)).

---

## Problem statement

AI coding agents routinely:

* create temporary artifacts
* leak orchestration files
* modify unrelated directories
* create hidden metadata
* over-broaden git adds
* accidentally commit internal tooling
* mutate deployment/runtime state unexpectedly

Current mitigations rely heavily on:

* prompting discipline
* `.gitignore`
* AGENTS.md conventions
* human review

These approaches are **soft** constraints. H-Frame targets a **stronger operational boundary**: export and repo layout are governed by topology and host-side policy, so teams can rely on something more repeatable than prompt text alone. It is still **not** execution sandboxing, cryptographic provenance, or a replacement for review.

---

## Goals

### 1. Prevent internal / orchestration leakage

Reduce the chance that paths such as the following are promoted **to customer remotes**, subject to **policy** and **built-in denies**:

* `.pinion/`, `pinion/`, agent scratch dirs (see built-in deny list)
* sprint or work-graph artifacts where applicable
* orchestration state and operational metadata

### 2. Enforce repository roles and constrained promotion

Under the **intended** workflow, agents should not:

* push directly to customer remotes from the workspace (workspace remotes are removed at bootstrap)
* mutate the protected working tree except through the **`./hframe in` / `./hframe out`** bridge semantics described in this PRD
* widen or reconfigure synchronization policy through the agent bridge CLI (policy is host-local)

A compromised host, mis-placed policy files, or operator mistakes can still violate these expectations—this document describes **design intent**, not a kernel-level guarantee.

### 3. Preserve normal git workflows

Customers continue using GitHub, GitLab, Bitbucket, branching, CI/CD, and review practices **unchanged** at the remote; H-Frame only inserts a **local topology** and promotion path.

### 4. Keep agent UX simple

Agents:

* work in a normal git checkout (workspace)
* commit locally
* run **`./hframe in`** and **`./hframe out`** only

…without needing to understand allowlists, denylists, or internal path layout.

### 5. Support deterministic synchronization

Synchronization must be reproducible, auditable, scriptable, automatable, and **policy-driven** on the operator side.

---

## Non-goals

* **Not a sandbox runtime** — no syscall virtualization; arbitrary code in the workspace is out of scope to “secure.”
* **Not a git replacement** — git remains the source of truth.
* **Not a deployment orchestrator** — repository sync only.
* **Not a secrets manager, cryptographic provenance system, or universal policy DSL** — see [README.md](README.md) non-goals.

---

## Core design principles

1. **Topology over prompting** — risk reduction and export discipline come from layout and sync architecture, not from assuming agents always follow instructions.
2. **Export boundary model** — the protected repo is an **export target**, not the agent workspace.
3. **Agent ignorance is a feature** — agents do not manage policy, topology, or rsync rules via the bridge.
4. **Workspace contamination is acceptable** — the system assumes contamination and **filters exports** accordingly.

---

## Architecture

### Repository roles

#### 1. Remote repository

Canonical customer-owned git remote (GitHub, GitLab, Bitbucket, etc.).

#### 2. Protected repository

Local directory **`<slug>_repo/`** (name derived from clone URL basename at bootstrap):

* Retains **`origin`** (or equivalent) and is **push-capable**.
* **Never** the agent working tree under normal operations.
* Receives exports from the workspace only through **`./hframe out`** semantics.

#### 3. Agent workspace copy

Local directory **`<slug>_workspace_repo/`**:

* **Copy** of the clone; **all remotes removed** immediately after bootstrap.
* Fully writable by agents; may accumulate orchestration and experimental artifacts.
* Contains the **workspace-local `./hframe` launcher** only (no global `hframe` install required for agents).

#### 4. Host policy bundle (`.hframe/`)

Sibling of the two repos under the same parent:

* **`policy.allowlist`** — default from bootstrap: **allowlist** path lines, one per **non-ignored** top-level entry in the protected clone (see `git check-ignore` in implementation), unless none qualify (then **denylist-only** fallback). Operators may replace or edit on the **host** (not from agent prompts).
* **`policy.denylist`** — extra deny globs merged **after** built-in denies. On a fresh bootstrap (when this file did not exist beforehand), it is **seeded from the protected clone’s root `.gitignore`** (pattern lines only; `!` negation lines are omitted).
* **`policy.allowlist.vault` / `policy.denylist.vault`** — when bootstrap uses **`--vault`**, plaintext policy files are removed after encryption; decryption key is embedded only in the zipapp (optional `h-frame[vault]` dependency).
* **`hframe-membrane.pyz`** — source zipapp built at bootstrap; embeds **paths relative to the bootstrap parent** (plus runtime resolution so the same bundle can run in Dev Containers when the parent is bind-mounted).
* **POSIX modes:** bootstrap sets policy artifacts to `0444` and `.hframe/` to `0755` where supported.
* Optional templates / docs as shipped by bootstrap.

**Critical requirement:** policy files **MUST** remain under operator control—typically **outside** the agent-only writable tree (same parent as repos; agents confined to `<slug>_workspace_repo/`). Generated devcontainers bind-mount `.hframe` **read-only**; do not place authoritative policy only inside paths the agent owns unconditionally.

---

## Membrane appliance model

### Operator surface: `h-frame-bootstrap`

```bash
h-frame-bootstrap [--vault] '<git_url>'
```

* **Exactly one argument:** the git URL to clone.
* **`--vault` (optional):** encrypt policy on disk; key embedded only in the membrane zipapp (`pip install 'h-frame[vault]'`).
* No other flags on the operator surface for the standard agent workflow.
* Creates `<slug>_repo/`, `<slug>_workspace_repo/`, seeds `.hframe/` policy templates, builds the zipapp, installs **`./hframe`** into the workspace; default sync rules are in README; optional operator append to **AGENTS.md** via `HFRAME_AGENTS_APPEND_FILE`.

### Agent surface: `./hframe`

From **inside** `<slug>_workspace_repo/`:

```bash
./hframe in
./hframe out
```

* **Exactly one** subcommand; **no** extra arguments, paths, or env-based reconfiguration.
* The launcher resolves **`../.hframe/hframe-membrane.pyz`** and runs **`python3`** on it (source bundle; portable across supported Python minors per project `requires-python`).

### Embedded configuration

At zipapp build time, the membrane embeds a small JSON mapping including:

* `original_rel` — path to protected repo **relative to the bootstrap parent** (same directory as `.hframe/`)
* `workspace_rel` — path to workspace repo **relative to the bootstrap parent**
* `policy_rel` — path to `policy.allowlist` **relative to the bootstrap parent** (typically under `.hframe/`)

At runtime, the membrane resolves those segments against the bootstrap parent inferred from the zipapp path (and, when needed, the standard Dev Container `hframe-root` mount). **Legacy** zipapps may still embed absolute `original` / `workspace` / `policy` keys from older builds; those behave as before on the host where they were produced.

Optional denylist paths are resolved relative to the same `.hframe/` directory on the host when loaded (see implementation: `policy.denylist` sibling file).

### Trust boundary summary

* **Deterministic** — `in` / `out` behavior is code-defined; not prompt-negotiated.
* **Immutable during agent execution** — embedded layout is fixed in the shipped zipapp / workspace launcher; changing it means replacing those artifacts or editing host files outside the normal agent workflow.
* **Topology-oriented** — the workspace clone has no git remotes for fetch/push; the protected repo keeps the remote used for `git push` after `out`.

---

## Bootstrap workflow (normative)

High-level steps performed by **`h-frame-bootstrap`** (see [README.md](README.md)):

1. **Clone** the URL into **`<slug>_repo/`** (protected).
2. **Copy** tree to **`<slug>_workspace_repo/`** (workspace).
3. **Remove all remotes** from the workspace; assert workspace has no remotes.
4. Ensure **`.hframe/policy.allowlist`** and **`.hframe/policy.denylist`**: after the protected clone exists, bootstrap writes defaults when those files were absent (allowlist from non-ignored root paths, or denylist-only if none; denylist from **`<slug>_repo/.gitignore`**).
5. **Build** `.hframe/hframe-membrane.pyz` (source zipapp with `hframe` `.py` under `.hframe/`; not shipped inside the workspace git tree).
6. **Install** the **`./hframe`** workspace launcher (POSIX: portable `python3` script; Windows: prebuilt `hframe-shim-*.exe`).
7. **Write** a minimal **`.devcontainer/devcontainer.json`** into the workspace when none exists (Dev Container bind mounts for `./hframe`; see README).
8. **Optionally** append operator-provided content to workspace **AGENTS.md** when `HFRAME_AGENTS_APPEND_FILE` is set (shell env or `.hframe/bootstrap.env`); default H-Frame sync rules are documented in README.

---

## Policy model

### Allowlist mode (default from `h-frame-bootstrap`)

* **Path lines** in **`.hframe/policy.allowlist`** (repo-root-relative globs/paths; see README for directive syntax). Bootstrap seeds one line per **top-level** clone path that Git does not ignore (directories as `name/**`, files as `name`), using **`git check-ignore`** so nested ignore rules apply.
* **Optional** **`.hframe/policy.denylist`** — user globs merged **after** built-in denies and **before** allow rules. Bootstrap seeds this from the protected clone’s **root `.gitignore`** (pattern lines only; `!` negation omitted).
* **`./hframe out`** uses path-limited `git add` for tracked paths implied by the allowlist.
* Operators may replace bootstrap-generated lines with a hand-maintained list (see README).

### Denylist-only mode (fallback or operator-selected)

* Selected by **`# hframe-policy: mode denylist-only`** in `policy.allowlist` with **no** other path lines. Bootstrap uses this only when **no** non-ignored root paths were found for an allowlist.
* Rsync includes the **whole tree** except built-in denies, the repo-root **`./hframe`** launcher (never mirrored between repos), and user deny globs from **`.hframe/policy.denylist`**.
* **`./hframe out`** stages with **`git add -A`** (broader than allowlist mode).

### Built-in deny globs (always on)

Authoritative list in source: `hframe.filters.DEFAULT_DENY_GLOBS` (as of this PRD revision), **plus** anchored rsync excludes for **`.git/`** and the repo-root **`hframe`** launcher (see `hframe.filters.build_rsync_filter_lines` / `build_rsync_deny_only_lines`):

```text
.pinion/**
pinion/**
.agent/**
tmp/**
.cursor/**
.claude/**
```

(Additional built-in patterns may be added in minor releases; release notes should call out material changes.)

### Example allowlist body (opt-in)

When using **allowlist** mode, paths might include:

```text
.devcontainer/**
.devcontainer.json
src/**
tests/**
docs/**
pyproject.toml
package.json
Dockerfile
README.md
```

---

## Synchronization model

### Sync-in (`./hframe in`)

**Purpose:** refresh the workspace from upstream customer state.

**Flow:**

```text
remote → protected repo (git pull) → workspace (rsync per policy)
```

**Implementation requirements:**

1. Validate config and assert workspace has **no remotes**.
2. Load and validate policy.
3. **`git pull`** in the **protected** repo.
4. **`rsync`** from protected → workspace using generated filter rules (allowlist or denylist-only per policy).
5. Emit a **sync receipt** payload (at minimum: direction, policy path, mode, counts—see § Receipts).

### Sync-out (`./hframe out`)

**Purpose:** export approved workspace deltas to the protected repo and push upstream.

**Flow:**

```text
workspace → protected repo (rsync + git stage + commit + push) → remote
```

**Implementation requirements:**

1. Validate config; assert workspace has **no remotes**.
2. Assert workspace **tracked tree is clean** (no unstaged or staged changes to tracked files)—agents must **commit** work in the workspace before `out`.
3. Load policy; **read full workspace `HEAD` commit message** (`git log -1 --format=%B`) for the **protected-repo commit** message.
4. **`rsync`** workspace → protected per policy.
5. **Stage** in protected repo: **path-limited `git add`** for allowlist mode, or **`git add -A`** in denylist-only mode.
6. **`git commit`** when there are staged changes, using the workspace message.
7. **`git push`** from protected repo to **`origin`** (or configured remote as implemented).

---

## Agent interaction model

Agents interact only with:

```bash
./hframe in
./hframe out
```

Agents are not required to know:

* absolute paths to protected repo or policy files
* rsync filter construction
* full built-in deny list

…reducing accidental or intentional **policy manipulation** via the bridge (host filesystem permissions remain an operator responsibility).

---

## Git workflow

### Workspace repo

**Allowed:** local commits, branches, experimentation.  
**Forbidden in the intended setup:** remotes that allow fetch/push to customer upstream (workspace must stay remote-free).

### Protected repo

**Responsible for:** `git pull`, merge/rebase as needed, **`git push`** after `out`, and hosting the remote that points to customer canonical history.

---

## Safety invariants

1. **Workspace repos MUST NOT contain git remotes** — `git remote -v` in the workspace must be empty before/after `in`/`out` as enforced by the implementation.
2. **Export scope is policy-bound** — only paths permitted by **allowlist + deny rules**, or by **denylist-only** rules including built-in denies, are copied to the protected repo during `out`. The `./hframe` bridge does not expose flags or knobs to widen that scope at runtime.
3. **Protected repo is the only push-capable participant** in the topology for customer upstream.
4. **Synchronization policy is not agent-configurable** via `./hframe` (no flags, paths, or env overrides).
5. **Internal/orchestration artifacts should not reach customer remotes** when policy, built-in denies, and human review are aligned—**operators** must keep policy files accurate and review pushes.

---

## Failure modes

| Risk | Mitigation |
| ---- | ---------- |
| Workspace corruption | Recreate workspace from protected repo (operator tooling / fresh bootstrap). |
| Bad agent commits in workspace | `out` exports **filesystem state** filtered by policy—not “trust” of commit messages. Review before merge to customer branches. |
| Upstream drift | Run `./hframe in` before work cycles; resolve conflicts in **protected** repo with normal git. |
| Partial sync / conflicts | Standard git conflict resolution in protected repo. |

---

## Receipts

The implementation returns a minimal machine-readable **receipt dict** per sync (example shape):

```json
{
  "sync_id": "sync-1715620800",
  "direction": "out",
  "policy": "/path/to/.hframe/policy.allowlist",
  "policy_mode": "allowlist",
  "allow_rules": 7,
  "user_deny_rules": 2,
  "timestamp": "2026-05-13T18:12:00Z"
}
```

**Future / enterprise:** richer receipts (file counts, blocked paths, policy profile id), drift summaries, and audit pipelines may extend this shape—call out breaking changes in [RELEASES.md](RELEASES.md).

---

## Enterprise features (future)

* **Multi-agent workspaces** — multiple workspace directories fanning into one protected repo.
* **Policy profiles** — strict / enterprise / OSS-safe templates.
* **Drift analysis** — summarize contamination vs exports (metrics product surface, not core membrane).

---

## Release and stability

See [README.md](README.md) (Release and stability) and [RELEASES.md](RELEASES.md). Until a stable commitment, policy file formats, receipt fields, and bootstrap layout may evolve.

---

## Success metrics

* **Safety:** zero direct workspace pushes; no widening of export scope via `./hframe`.
* **Operational:** workspace rebuild / bootstrap within operator SLO; sync latency acceptable for typical repos.
* **Adoption:** minimal disruption to existing CI/CD; agents use two commands only.

---

## Strategic importance

H-Frame establishes a **trust boundary** for enterprise-grade agentic delivery: repository safety becomes **enforced architecture** (topology + deterministic promotion), not only behavioral convention.

---

## License and maintenance

Open source under **Apache-2.0** (see `pyproject.toml`). Maintenance and roadmap communication: see [README.md](README.md) and [Level Up Labs](https://levelupla.io).
