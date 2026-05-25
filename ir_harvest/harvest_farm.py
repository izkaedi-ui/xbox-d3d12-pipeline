#!/usr/bin/env python3
# =========================================================================
# 🔱 ZKAEDI VMAX: TB-SCALE PARALLEL COMPILATION & IR HARVEST ORCHESTRATOR
# Spawns N parallel ZCC instances, schedules source shards, and merges IR.
# =========================================================================
import os
import sys
import json
import time
import subprocess
from concurrent.futures import ProcessPoolExecutor, as_completed
import argparse

ZCC_BIN_DEFAULT = "../zcc/zcc"
DEFAULT_WORKERS = 8  # Matched to Ryzen AI 7 350 cores
OUTPUT_IR_MERGED = "out.ir"

def load_priority_queue(queue_path: str) -> list:
    """Loads pre-classified source files from priority queue."""
    if not os.path.exists(queue_path):
        print(f"⚠️ [WARNING] Priority queue '{queue_path}' not found. Falling back to default scanning.")
        return []
    try:
        with open(queue_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"🔴 [ERROR] Failed to load priority queue: {e}")
        return []

def scan_raw_source_files(source_dir: str) -> list:
    """Fallback scanner to locate all C source files recursively."""
    print(f"[*] Scanning source directory for C files: {source_dir}")
    c_files = []
    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith((".c", ".cpp", ".cc")):
                c_files.append(os.path.join(root, file))
    return c_files

def compile_source_shard(zcc_bin: str, file_path: str) -> tuple[str, bool, float]:
    """
    Compiles a single C source file using ZCC with telemetry activated.
    Returns: (output_ir_content, success, elapsed_time)
    """
    start_time = time.perf_counter()
    env = os.environ.copy()
    env["ZCC_EMIT_IR"] = "1"
    
    # We output a temporary assembly file in the bin directory
    filename_hash = hashlib.sha256(file_path.encode()).hexdigest()[:8]
    temp_asm = f"bin/telemetry_{filename_hash}.s"
    
    # Run ZCC with ZCC_EMIT_IR=1
    cmd = [
        zcc_bin,
        file_path,
        "-o",
        temp_asm
    ]
    
    try:
        # Run compiler subprocess and capture output directly from stdout
        res = subprocess.run(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        elapsed = time.perf_counter() - start_time
        
        # ZCC outputs IR directly to stdout when ZCC_EMIT_IR is enabled
        ir_content = res.stdout
        
        # Clean up temp assembly file
        if os.path.exists(temp_asm):
            try:
                os.remove(temp_asm)
            except OSError:
                pass
                
        return ir_content, (res.returncode == 0 or len(ir_content) > 0), elapsed
        
    except subprocess.TimeoutExpired:
        print(f"⚠️ [TIMEOUT] Compilation expired on: {file_path}")
        return "", False, time.perf_counter() - start_time
    except Exception as e:
        return "", False, time.perf_counter() - start_time

import hashlib

def main():
    parser = argparse.ArgumentParser(description="🔱 ZKAEDI VMAX Parallel IR Farm")
    parser.add_argument("--source", required=True, help="Path to source directory or codebase shard")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="Number of parallel compiler threads")
    parser.add_argument("--queue", default="priority_queue.json", help="Path to pre-pass priority queue")
    parser.add_argument("--zcc", default=ZCC_BIN_DEFAULT, help="Path to ZCC binary")
    args = parser.parse_args()

    print("=========================================================================")
    print("          🔱 ZKAEDI VMAX: PARALLEL ZCC COMPILATION FARM")
    print("=========================================================================")
    print(f"[*] Ryzen Core Count  : {args.workers}")
    print(f"[*] Base Compiler Path: {args.zcc}")
    
    os.makedirs("bin", exist_ok=True)
    
    # 1. Load priority queue or fall back to scanning directory
    queue = load_priority_queue(args.queue)
    if not queue:
        raw_files = scan_raw_source_files(args.source)
        queue = [{"path": f, "score": 100} for f in raw_files]
    else:
        # Pre-pend path prefix if not fully resolved
        pass
        
    total_files = len(queue)
    print(f"[*] Orchestrating {total_files} source files through parallel pipeline...")
    
    # 2. Spawn multi-core compiler workers
    compiled_count = 0
    failure_count = 0
    total_time = 0.0
    
    with open(OUTPUT_IR_MERGED, "w", encoding="utf-8") as out_f:
        out_f.write(f"; 🔱 ZKAEDI VMAX: UNIFIED TELEMETRY STREAM\n; Created: {time.asctime()}\n; =========================================================================\n\n")
        
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            # Submit all tasks
            futures = {
                executor.submit(compile_source_shard, args.zcc, item["path"]): item 
                for item in queue
            }
            
            for future in as_completed(futures):
                item = futures[future]
                file_path = item["path"]
                try:
                    ir_content, success, elapsed = future.result()
                    total_time += elapsed
                    compiled_count += 1
                    
                    if success and len(ir_content) > 0:
                        out_f.write(ir_content + "\n")
                        print(f"   ✓ [COMPILED] {os.path.basename(file_path):<30} | Telemetry Size: {len(ir_content):<6} bytes | {elapsed:.2f}s")
                    else:
                        failure_count += 1
                        print(f"   ❌ [FAILED]   {os.path.basename(file_path):<30} | {elapsed:.2f}s")
                        
                except Exception as e:
                    failure_count += 1
                    print(f"   🚨 [CRITICAL] Exception compiling {file_path}: {e}")
                    
    print("=========================================================================")
    print(f"🔱 PARALLEL FARM COMPLETED")
    print(f"   Successfully compiled : {compiled_count - failure_count}/{total_files}")
    print(f"   Skipped / Failed      : {failure_count}")
    print(f"   Total CPU core-time   : {total_time:.2f}s")
    print(f"   Merged IR written to  : {OUTPUT_IR_MERGED}")
    print("=========================================================================")

if __name__ == "__main__":
    main()
