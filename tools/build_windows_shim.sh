#!/usr/bin/env bash
# Build hframe-shim-windows-amd64.exe for src/hframe/native/prebuilt/.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SRC="${ROOT}/src/hframe/native/shim_windows.c"
OUT="${ROOT}/src/hframe/native/prebuilt/hframe-shim-windows-amd64.exe"

CC="${MINGW_CC:-x86_64-w64-mingw32-gcc}"
if ! command -v "${CC}" >/dev/null 2>&1; then
  echo "error: ${CC} not found; install gcc-mingw-w64-x86-64 (Debian/Ubuntu) or set MINGW_CC" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUT}")"
"${CC}" -O2 -s -o "${OUT}" "${SRC}" -municode -mconsole
echo "built ${OUT}"
