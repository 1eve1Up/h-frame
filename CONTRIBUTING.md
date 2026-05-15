# Contributing to H-Frame

Thanks for helping improve H-Frame.

H-Frame is a **repository isolation topology** for AI-assisted delivery: a protected git clone, a workspace copy without remotes, and a small `./hframe` bridge (`in` / `out` only). Keep contributions scoped, tested, and honest about what the membrane guarantees versus what remains operator responsibility (see [README](README.md) and [PRD](PRD.md)). The current release line is **`v2026.5.0`**; the Python package version in `pyproject.toml` is **`2026.5.0`** (see `RELEASES.md` for package-level notes).

## Prerequisites

- **Python** 3.11+ for `hframe-bootstrap` and for running the membrane zipapp (source bundle; see README)
- **git** and **rsync** on `PATH` (integration tests exercise both)
- **Windows:** a prebuilt `hframe-shim-windows-amd64.exe` under `src/hframe/native/prebuilt/` when packaging the wheel (see that directory’s README). POSIX workspace bootstrap installs a **portable `python3` launcher**; optional reference native build: `native/shim.c`.

## Local verification

Install the package and dev dependencies from the repository root:

```bash
pip install -e '.[dev]'
```

Run the linter and tests:

```bash
ruff check src tests
pytest
```

Integration tests are marked and require git and rsync; they use local `file://` remotes.

## Development workflow

1. Open or choose an issue (or a short design note in a PR) with a clear scope.
2. Prefer small, reviewable changes; avoid unrelated refactors.
3. Add or update tests when sync behavior, policy parsing, bootstrap layout, or git staging changes.
4. Update [README](README.md) when user-facing behavior changes (bootstrap paths, policy modes, `./hframe` contract). Update [RELEASES.md](RELEASES.md) when cutting a documented preview or release. Update [PRD](PRD.md) only when the **intended product contract** changes, not for every implementation detail.
5. Run `ruff check src tests` and `pytest` before opening a pull request.

## Policy and membrane constraints

- **Policy files** (`.hframe/policy.allowlist`, `.hframe/policy.denylist`) are host-local and should remain outside agent-only writable areas; see PRD policy model and README.
- The **zipapp** embeds **bootstrap-relative** path segments at build time (legacy builds may still embed absolute paths); behavior changes that affect the agent bundle belong in tests that exercise `embedded` / membrane build paths where practical.

## Stability expectations

H-Frame is in **early public preview** (see [README](README.md) — Release and stability, and [RELEASES.md](RELEASES.md)).

Until an explicit stable commitment:

- Bootstrap directory naming, policy file format, and receipt JSON fields may evolve.
- `./hframe` remains intentionally minimal (`in` / `out` only, no flags); breaking that surface should be rare and called out in release notes.

## License compliance (optional)

Full inbound license scanning (ScanCode + YAML allowlist) lives under [tools/licensing](tools/licensing/README.md). From the repo root:

```bash
pip install -r tools/licensing/requirements.txt
# Debian/Ubuntu: sudo apt-get install -y libarchive13
bash tools/run-license-compliance.sh
```

Use `--skip-scancode` for fast policy unit tests only; CI runs the full script on Ubuntu (see [.github/workflows/ci.yml](.github/workflows/ci.yml)).

## Security

Do not open public issues for suspected vulnerabilities. Follow [SECURITY.md](SECURITY.md).

## License

Inbound contributions should be compatible with the project’s **Apache-2.0** license (see `pyproject.toml` and [README](README.md)).
