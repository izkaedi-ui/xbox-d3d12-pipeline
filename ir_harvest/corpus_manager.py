#!/usr/bin/env python3
# =========================================================================
# 🔱 ZKAEDI VMAX: STREAMING CORPUS MANAGER & HF BATCH PUSHER
# Manages TB-scale data streaming, dynamic deduplication, and HuggingFace sync.
# =========================================================================
import os
import sys
import re
import json
import hashlib
import time
import argparse
from typing import Generator

try:
    from huggingface_hub import HfApi
    HF_HUB_AVAILABLE = True
except ImportError:
    HF_HUB_AVAILABLE = False

CORPUS_DIR = "corpus"
HF_DATASET_ID = "zkaedi/zcc-ir-prime-v1"
TRANSACTION_LOG = "bin/corpus_transactions.json"

# Regex patterns for ZCC IR Schema (Verified)
FUNC_START_RE = re.compile(r"^\s*;\s*func\s+([a-zA-Z0-9_]+)\s*->")
# Matches ZCC schema footer: "; end transform_vertex_4x4  nodes=164"
FUNC_END_RE = re.compile(r"^\s*;\s*end\s+([a-zA-Z0-9_]+)")

def stream_ir_functions(file_path: str) -> Generator[tuple[str, str], None, None]:
    """
    Generator that streams individual ZCC IR functions from out.ir.
    Avoids loading TB-scale flat telemetry files into CPU RAM.
    """
    if not os.path.exists(file_path):
        return
        
    current_func = None
    current_body = []
    
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            start_match = FUNC_START_RE.match(line)
            if start_match:
                current_func = start_match.group(1)
                current_body = [line]
                continue
                
            if current_func:
                current_body.append(line)
                end_match = func_end_re_match(line)
                if end_match and end_match.group(1) == current_func:
                    yield current_func, "".join(current_body)
                    current_func = None
                    current_body = []
                    
def func_end_re_match(line: str):
    """Helper matcher for function end bounds."""
    return FUNC_END_RE.match(line)

class CorpusManager:
    def __init__(self, token: str = None):
        self.token = token or os.environ.get("HF_TOKEN")
        self.api = HfApi(token=self.token) if (HF_HUB_AVAILABLE and self.token) else None
        self.known_hashes = set()
        self.stats = {
            "legendary_count": 0,
            "epic_count": 0,
            "dedup_count": 0,
            "total_processed": 0
        }
        os.makedirs(CORPUS_DIR, exist_ok=True)
        os.makedirs("bin", exist_ok=True)
        self.load_local_dedup_cache()
        
    def load_local_dedup_cache(self):
        """Loads existing hashes from corpus folder to prevent double-ingestion."""
        if os.path.exists(TRANSACTION_LOG):
            try:
                with open(TRANSACTION_LOG, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.known_hashes = set(data.get("hashes", []))
                    self.stats.update(data.get("stats", {}))
            except Exception:
                pass
                
        # Scan folder for newly added files if cache was empty
        if not self.known_hashes and os.path.exists(CORPUS_DIR):
            for file in os.listdir(CORPUS_DIR):
                if file.endswith(".ir"):
                    # Extract hash from format: Name_Class_Hash.ir
                    parts = file.split("_")
                    if len(parts) >= 3:
                        h = parts[-1].replace(".ir", "")
                        self.known_hashes.add(h)
                        
    def save_local_dedup_cache(self):
        """Saves current state and transaction logs to the disk."""
        with open(TRANSACTION_LOG, "w", encoding="utf-8") as f:
            json.dump({
                "hashes": list(self.known_hashes),
                "stats": self.stats
            }, f, indent=4)
            
    def process_and_commit_batch(self, results: list, batch_id: int) -> bool:
        """
        Commits a processed batch of evaluated IR functions.
        Returns: True if new samples were successfully written, False otherwise.
        """
        batch_new_written = 0
        
        # Keep transaction rollback record in case of network/compilation failure
        transaction_rollback = []
        
        for item in results:
            self.stats["total_processed"] += 1
            h = item["hash"]
            
            # Deduplication Check
            if h in self.known_hashes:
                self.stats["dedup_count"] += 1
                continue
                
            classification = item["classification"]
            if not classification:
                continue
                
            # Write to disk corpus
            name = item["name"]
            body = item["body"]
            score = item["score"]
            
            filename = f"{CORPUS_DIR}/{name}_{classification}_{h}.ir"
            metadata = (
                f"; 🔱 ZKAEDI VMAX: HARVESTED TRAINING ENTRY\n"
                f"; Source Function: {name}\n"
                f"; Score: {score} ({classification})\n"
                f"; Hash: {h}\n"
                f"; =========================================================================\n"
            )
            
            try:
                with open(filename, "w", encoding="utf-8") as f:
                    f.write(metadata + body)
                
                # Register for deduplication and transaction history
                self.known_hashes.add(h)
                transaction_rollback.append(filename)
                
                if classification == "LEGENDARY":
                    self.stats["legendary_count"] += 1
                elif classification == "EPIC":
                    self.stats["epic_count"] += 1
                    
                batch_new_written += 1
                
            except Exception as e:
                print(f"🔴 [ERROR] Failed to write telemetry file: {e}")
                # Rollback current batch files to keep corpus pristine
                for rollback_file in transaction_rollback:
                    try:
                        os.remove(rollback_file)
                    except OSError:
                        pass
                return False
                
        self.save_local_dedup_cache()
        
        if batch_new_written > 0:
            print(f"   ✓ [BATCH {batch_id}] Shipped {batch_new_written} new distinct functions to local corpus storage.")
            return True
        return False
        
    def push_to_huggingface(self) -> bool:
        """Pushes current local corpus folder to HuggingFace dataset hub in a single transaction."""
        if not self.api:
            print("⚠️ [WARNING] HuggingFace API client not initialized. Set HF_TOKEN and install huggingface_hub.")
            return False
            
        print(f"[*] Syncing corpus folder with HuggingFace Hub: {HF_DATASET_ID}")
        start_time = time.perf_counter()
        
        try:
            self.api.upload_folder(
                folder_path=CORPUS_DIR,
                path_in_repo="corpus_feed",
                repo_id=HF_DATASET_ID,
                repo_type="dataset",
                commit_message=f"🔱 VMAX Pipeline Harvest: {self.stats['legendary_count']} LEGENDARY | {self.stats['epic_count']} EPIC"
            )
            elapsed = time.perf_counter() - start_time
            print(f"✓ [SYNC SUCCESS] Upload completed in {elapsed:.2f}s!")
            return True
        except Exception as e:
            print(f"🔴 [SYNC FAILURE] HuggingFace upload failed: {e}")
            return False

def main():
    parser = argparse.ArgumentParser(description="🔱 ZKAEDI VMAX Corpus Manager")
    parser.add_argument("--push", action="store_true", help="Force direct sync to HuggingFace dataset")
    args = parser.parse_args()
    
    print("=========================================================================")
    print("          🔱 ZKAEDI VMAX: STREAMING CORPUS MANAGER")
    print("=========================================================================")
    
    manager = CorpusManager()
    print(f"[*] HF Client API Available: {'YES' if manager.api else 'NO'}")
    print(f"[*] Local Deduplication Cache: {len(manager.known_hashes)} distinct signatures loaded.")
    print(f"[*] Current running stats:")
    print(f"    - LEGENDARY : {manager.stats['legendary_count']}")
    print(f"    - EPIC      : {manager.stats['epic_count']}")
    print(f"    - Dedups    : {manager.stats['dedup_count']}")
    
    if args.push:
        manager.push_to_huggingface()
    print("=========================================================================")

if __name__ == "__main__":
    main()
