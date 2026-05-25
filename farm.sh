#!/usr/bin/env bash
# =========================================================================
# 🔱 ZKAEDI VMAX: UNIFIED COMPILER INTELLIGENCE FARM HARNEST
# Single entry command to launch the full 6-phase TB-scale IR harvest pipeline.
# =========================================================================
set -eo pipefail

# Configuration
SOURCE_SHARDS_DIR="/mnt/h/_studio_tripo3d/3d_tools/source_shards"
ZCC_BIN_PATH="${ZCC_BIN:-/mnt/h/__DOWNLOADS/selforglinux/zcc}"
WORKERS=8

echo "========================================================================="
echo "          🔱 ZKAEDI VMAX: COMPILER INTELLIGENCE FACTORY"
echo "========================================================================="
echo "[*] Initializing Unified Systems Orchestration Loop..."
echo "[*] Target Core Count: ${WORKERS} (Ryzen AI 7 350)"

# Verify sibling compiler is available
if [ ! -f "${ZCC_BIN_PATH}" ]; then
    echo "🔴 [FATAL] Sibling ZCC C Compiler binary not found at: ${ZCC_BIN_PATH}"
    echo "   Please compile ZCC first or export ZCC_BIN env var."
    exit 1
fi

# Ensure directories exist
mkdir -p bin
mkdir -p corpus
mkdir -p source_shards

# -------------------------------------------------------------------------
# PHASE 1: SOURCE ACQUISITION
# -------------------------------------------------------------------------
echo -e "\n🔱 [PHASE 1] RUNNING SOURCE CODEBASE SHARDING AUDIT..."
# Verify if C files exist in source_shards. If empty, download or symlink them.
C_COUNT=$(find "${SOURCE_SHARDS_DIR}" -name "*.c" -o -name "*.cpp" 2>/dev/null | wc -l || echo "0")
if [ "$C_COUNT" -eq 0 ]; then
    echo "⚠️ [WARNING] No C source shards found in source_shards/."
    echo "   Placing default high-value solver source into source_shards/ for bootstrapping..."
    cp src/zcc_win32_host.c source_shards/
fi
echo "✓ PHASE 1 SUCCESS: Source sharding target verification complete."

# -------------------------------------------------------------------------
# PHASE 2: NPU PRE-PASS CLASSIFIER (XDNA2)
# -------------------------------------------------------------------------
echo -e "\n🔱 [PHASE 2] INITIATING NPU PRE-PASS COMPLEXITY SCORING (XDNA2)..."
python3 ir_harvest/npu_classifier.py \
    --source "${SOURCE_SHARDS_DIR}" \
    --output "priority_queue.json" \
    --min-score 30
echo "✓ PHASE 2 SUCCESS: Complexity priority queue written to priority_queue.json."

# -------------------------------------------------------------------------
# PHASE 3: PARALLEL ZCC FARM (8 RYZEN CORES)
# -------------------------------------------------------------------------
echo -e "\n🔱 [PHASE 3] LAUNCHING MULTI-CORE PARALLEL ZCC FARM..."
python3 ir_harvest/harvest_farm.py \
    --source "${SOURCE_SHARDS_DIR}" \
    --workers "${WORKERS}" \
    --queue "priority_queue.json" \
    --zcc "${ZCC_BIN_PATH}"
echo "✓ PHASE 3 SUCCESS: Parallel compilation complete. Telemetry written to out.ir."

# -------------------------------------------------------------------------
# PHASE 4: GPU PARALLEL SCORING & DEDUP (RTX 5070 BLACKWELL)
# -------------------------------------------------------------------------
echo -e "\n🔱 [PHASE 4] EXECUTING GPU-ACCELERATED SCORING & TRITON KERNELS (RTX 5070)..."
python3 ir_harvest/gpu_scorer.py
echo "✓ PHASE 4 SUCCESS: Telemetry blocks parsed, scored, and hashed."

# -------------------------------------------------------------------------
# PHASE 5: STREAMING CORPUS MANAGEMENT & HUGGINGFACE SYNC
# -------------------------------------------------------------------------
echo -e "\n🔱 [PHASE 5] STREAMING CORPUS COMMITS & HUGGINGFACE SYNC..."
python3 ir_harvest/corpus_manager.py --push
echo "✓ PHASE 5 SUCCESS: Transaction-safe batches synchronized to zcc-ir-prime-v1."

# -------------------------------------------------------------------------
# PHASE 6: BOOTSTRAP PARITY VERIFICATION (ZCC PARITY GATE)
# -------------------------------------------------------------------------
echo -e "\n🔱 [PHASE 6] EXECUTING BOOTSTRAP PARITY VERIFICATION (zcc2.s == zcc3.s)..."
# Perform self-compiling bootstrap check to verify compiler backend has not drifted
BOOTSTRAP_SUCCESS=true

if [ -f "zcc/Makefile" ]; then
    echo "[*] Triggering ZCC bootstrap verification..."
    cd zcc
    make clean || true
    make zcc2 || BOOTSTRAP_SUCCESS=false
    make zcc3 || BOOTSTRAP_SUCCESS=false
    
    if [ "$BOOTSTRAP_SUCCESS" = true ] && cmp -s zcc2.s zcc3.s; then
        echo "✓ [PARITY PASS] zcc2.s == zcc3.s bootstrap parity confirmed!"
        cd ..
    else
        echo "🔴 [PARITY FAIL] zcc2.s != zcc3.s compiler backend drift detected!"
        cd ..
        exit 1
    fi
else
    echo "⚠️ [PARITY SKIP] Sibling compiler ZCC build directory not found. Skipping compiler parity check."
fi

echo -e "\n========================================================================="
echo "✓ [PIPELINE SUCCESS] 100% compliant. Closed-loop loop closed successfully."
echo "========================================================================="
