# Prebuilt `hframe` Windows shim

Bootstrap installs the workspace bridge as follows:

| OS | Workspace `hframe` |
|----|---------------------|
| Linux / macOS | Portable **`#!/usr/bin/env python3`** script (stdlib only); no prebuilt binary required |
| Windows x64 | Prebuilt **`hframe-shim-windows-amd64.exe`** copied from this directory into the wheel |

## Windows file name

| Tag | File |
|-----|------|
| Windows x64 | `hframe-shim-windows-amd64.exe` |

Tags are chosen from `platform.machine()` and `sys.platform` at bootstrap time.

## Rebuilding the Windows shim

Source: [`../shim_windows.c`](../shim_windows.c). From the repository root (requires `gcc-mingw-w64-x86-64` on Linux, or MSVC on Windows):

```bash
bash tools/build_windows_shim.sh
```

The resulting executable must be committed under this directory before publishing the `h-frame` wheel.

## Reference native launcher (POSIX)

Optional **manual** compile of [`../shim.c`](../shim.c) produces a tiny ELF/Mach-O binary with the same behavior as the default Python launcher. It is **not** installed by bootstrap on POSIX anymore (as of package `2026.5.0`).
