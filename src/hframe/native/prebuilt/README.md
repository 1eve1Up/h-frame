# Prebuilt `hframe` Windows shim (optional)

Bootstrap installs the workspace bridge as follows:

| OS | Workspace `hframe` |
|----|---------------------|
| Linux / macOS | Portable **`#!/usr/bin/env python3`** script (stdlib only); no prebuilt binary required |
| Windows x64 | Prebuilt **`hframe-shim-windows-amd64.exe`** copied from this directory into the wheel |

## Windows file name

Place a **chmod +x** is not applicable for `.exe`; ship the file as:

| Tag | File |
|-----|------|
| Windows x64 | `hframe-shim-windows-amd64.exe` |

Tags are chosen from `platform.machine()` and `sys.platform` at bootstrap time.

## Reference native launcher (POSIX)

Optional **manual** compile of [`../shim.c`](../shim.c) produces a tiny ELF/Mach-O binary with the same behavior as the default Python launcher. It is **not** installed by bootstrap on POSIX anymore (as of package `2026.5.0`).
