# Security policy

## Supported versions

H-Frame is in **early public preview**. The documented preview line is **`v2026.6.2`** (see [README](README.md) — Release and stability, and [RELEASES.md](RELEASES.md)).

Security-sensitive fixes are prioritized for **current `main`** and the latest **published Python package** on PyPI (`h-frame`, version **`2026.6.2`** in `pyproject.toml`, release line **`v2026.6.2`** in docs).

Until an explicit stable commitment:

- Bootstrap layout, membrane bundle format, and policy file semantics may evolve between releases.
- Release notes and this document should be updated when a change materially affects the trust boundary or operator guidance.

## Reporting a vulnerability

**Please do not open a public GitHub issue** for undisclosed vulnerabilities (credential exposure, unsafe filesystem or git operations, supply-chain concerns about bootstrap or the zipapp, etc.).

Preferred channels:

1. **GitHub Security Advisories** — use the repository **Security** tab and **Report a vulnerability** if that feature is enabled for this repo.
2. Otherwise, email **Level Up Labs** at security@leveluplabs.ai for coordinated disclosure.

Include where possible:

- affected **`h-frame` package version** (`pyproject.toml` / `pip show h-frame`) or **git commit**
- OS and versions of **git**, **rsync**, and **Python**
- whether the report concerns **operator** (`h-frame-bootstrap`) or **agent** (`./hframe`) surfaces
- minimal reproduction steps and impact assessment (no live customer secrets)

## Trust boundary (what H-Frame is and is not)

H-Frame is a **repository isolation and sync membrane**, not a sandbox runtime (PRD **Non-Goals**; README **H-Frame vs Sandboxes**).

### Operator host (`h-frame-bootstrap`)

Runs as the invoking user and may:

- **`git clone`** the URL you pass (treat URLs like untrusted input until you trust the remote).
- **`rsync`** and **`cp`** between protected and workspace trees according to **host-controlled** policy under **`.hframe/`** (not inside the agent workspace).
- **POSIX:** bootstrap writes a short **`#!/usr/bin/env python3`** workspace script that `execvp`'s `python3` on the membrane zipapp (portable across Linux and macOS, including devcontainers).
- **Windows:** copy a **prebuilt** `hframe-shim-*.exe` from package data (no compiler path).

Policy files **must** remain under operator control. New bootstraps harden `.hframe/` with read-only policy modes (POSIX) and a **read-only** Dev Container bind mount for `../.hframe`; agents should not rewrite policy inside the container. Optional `h-frame-bootstrap --vault` stores encrypted policy on disk with the decryption key embedded only in `hframe-membrane.pyz`—this deters casual edits but does **not** resist a hostile agent with the same UID who can read the zipapp. Git “dubious ownership” is handled by membrane `safe.directory`, not by editing allowlists.

### Agent workspace (`./hframe`)

The workspace launcher resolves **`../.hframe/hframe-membrane.pyz`** and runs **`python3`** on that zipapp (source bundle). It executes **`git`** and **`rsync`** with fixed arguments derived from **embedded layout** frozen at bootstrap (bootstrap-relative paths, with a devcontainer fallback for the mount layout)—not from agent-supplied flags.

Agents are expected to be **semi-trusted** (README / PRD): they can modify the workspace filesystem and local git state, but they should not control membrane policy or the protected repo directly.

### `out` and staging

- **Allowlist mode:** staging uses targeted **`git add`** paths derived from policy.
- **Denylist-only mode:** after rsync, the protected repo may be staged with **`git add -A`** — a **broad** operation by design. Operators must align denylists and review practices with that risk (README).

### What H-Frame does not guarantee

- No cryptographic attestation of sync or git history.
- No SBOM or provenance for third-party git remotes.
- No containment of malicious **code executed** inside the workspace.
- Receipts / diagnostics are not a substitute for audit programs or formal verification.

Operators remain responsible for: **host hardening**, **reviewing policy**, **vetting remotes and branches**, **secrets handling**, and **human review** before pushes from the protected repo.

## Disclosure

We will acknowledge receipt of good-faith reports as capacity allows and coordinate a fix and disclosure timeline when appropriate. This project is provided **as-is** (see README **Disclaimer**); commitments follow maintainer capacity and the severity of the issue.
