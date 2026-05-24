#!/usr/bin/env bash
set -eo pipefail

ZCC_COMPILER_BIN="${ZCC_BIN:-../zcc/zcc}"
ML64_BIN="${ML64_BIN:-}"

echo "========================================================================="
echo "ZKAEDI VMAX: ZCC TWO-STAGE BUILD"
echo "========================================================================="

if [ ! -f "${ZCC_COMPILER_BIN}" ]; then
    echo "[FATAL] ZCC binary not found at: ${ZCC_COMPILER_BIN}"
    exit 1
fi

if [ -z "${ML64_BIN}" ]; then
    ML64_CANDIDATES=(
        "/mnt/c/Program Files/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/ml64.exe"
        "/mnt/c/Program Files (x86)/Microsoft Visual Studio/2022/BuildTools/VC/Tools/MSVC/14.44.35207/bin/Hostx64/x64/ml64.exe"
    )
    for candidate in "${ML64_CANDIDATES[@]}"; do
        [ -f "${candidate}" ] && ML64_BIN="${candidate}" && break
    done
fi

[ -z "${ML64_BIN}" ] && echo "[FATAL] ml64.exe not found. Set ML64_BIN." && exit 1

mkdir -p bin

echo "[1/3] ZCC compile -> assembly..."
ZCC_EMIT_IR=1 "${ZCC_COMPILER_BIN}" \
    -D_WIN32_WINNT=0x0A00 \
    -DNTDDI_VERSION=0x0A000007 \
    -DUNICODE -D_UNICODE \
    src/zcc_win32_host.c \
    -S -o bin/zcc_win32_host.s

echo "[2/3] ml64.exe assemble -> object..."
"${ML64_BIN}" /c /Fo bin/zcc_win32_host.obj bin/zcc_win32_host.s

echo "[3/3] link.exe -> executable..."
link.exe \
    bin/zcc_win32_host.obj \
    d3d12.lib dxgi.lib dstorage.lib user32.lib kernel32.lib \
    /OUT:bin/zkaedi_win32_monolith.exe \
    /SUBSYSTEM:WINDOWS /MACHINE:X64

echo "Build complete: bin/zkaedi_win32_monolith.exe"
echo "IR telemetry:   out.ir"
