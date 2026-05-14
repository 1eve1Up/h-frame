# License compliance (H-Frame)

Inbound license checks for **first-party** paths using [ScanCode](https://github.com/nexB/scancode-toolkit) plus a YAML allowlist (`license_policy.allowlist.yaml`).

## When it runs

- **Locally / CI:** `bash tools/run-license-compliance.sh` from the repository root (see [.github/workflows/ci.yml](../../.github/workflows/ci.yml)).
- **Pull requests:** the `license` job installs ScanCode, runs the scan on `src/`, `tests/`, key docs, `.github/`, and `tools/licensing/`, then validates detected SPDX symbols against the policy.

## Quick local run (no ScanCode)

```bash
pip install -r tools/licensing/requirements.txt
bash tools/run-license-compliance.sh --skip-scancode
```

## Full run (ScanCode)

On Debian/Ubuntu, install the real `libarchive` SONAME ScanCode’s extractor expects:

```bash
sudo apt-get update && sudo apt-get install -y libarchive13
pip install -r tools/licensing/requirements.txt
bash tools/run-license-compliance.sh
```

Use `./tools/run-license-compliance.sh --skip-scancode --pip-report` to print `pip` license metadata without a ScanCode install.

## Policy

Edit **`license_policy.allowlist.yaml`** when adding new first-party trees or when intentionally allowing additional SPDX identifiers. Paths in ScanCode JSON must match one of **`first_party_path_globs`** (segment-wise globs with `**` globstar, e.g. `src/**` matches any depth under `src/`) or detections outside that set can fail the check.
