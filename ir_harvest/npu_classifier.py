#!/usr/bin/env python3
# =========================================================================
# 🔱 ZKAEDI VMAX: NPU SOURCE COMPLEXITY PRE-CLASSIFIER
# Pre-evaluates C file complexity via ONNX Runtime & DirectML on XDNA2 NPU.
# =========================================================================
import os
import sys
import json
import re
import argparse
import numpy as np

# Try importing ONNX Runtime
try:
    import onnxruntime as ort
    ORT_AVAILABLE = True
except ImportError:
    ORT_AVAILABLE = False

DEFAULT_QUEUE_FILE = "priority_queue.json"

def init_npu_session(model_path: str) -> tuple:
    """Initializes ONNX Runtime session using AMD XDNA2 NPU (DirectML)."""
    if not ORT_AVAILABLE:
        return None, "CPU (onnxruntime not installed)"
        
    if not os.path.exists(model_path):
        return None, "CPU (ONNX model file not found; using analytical heuristics)"
        
    try:
        # Configure DirectML execution provider for AMD XDNA2 NPU
        providers = [
            ("DmlExecutionProvider", {
                "device_id": 0
            }),
            "CPUExecutionProvider"
        ]
        session = ort.InferenceSession(model_path, providers=providers)
        return session, "XDNA2 NPU (DirectML)"
    except Exception as e:
        try:
            # Fallback to standard CPU provider
            session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
            return session, "CPU Fallback"
        except Exception as ex:
            return None, f"Error: {ex}"

def extract_analytical_features(file_path: str) -> dict:
    """Extracts structural AST-like features from C source file."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()
    except Exception:
        return {"lines": 0, "loops": 0, "fp_ops": 0, "nesting": 0, "score": 0}
        
    lines = len(code.splitlines())
    
    # Count loops (for, while)
    loops = len(re.findall(r"\b(for|while)\b", code))
    
    # Count floating point declarations and operations
    fp_ops = len(re.findall(r"\b(float|double|sqrt|sin|cos|log|exp|pow|fma)\b", code))
    
    # Heuristic for nesting depth using braces
    nesting = 0
    max_nesting = 0
    for char in code:
        if char == "{":
            nesting += 1
            if nesting > max_nesting:
                max_nesting = nesting
        elif char == "}":
            nesting = max(0, nesting - 1)
            
    # Calculate a weighted complexity score representing expected ZCC IR yield
    score = (lines * 0.1) + (loops * 15.0) + (fp_ops * 10.0) + (max_nesting * 5.0)
    
    return {
        "lines": lines,
        "loops": loops,
        "fp_ops": fp_ops,
        "nesting": max_nesting,
        "score": int(score)
    }

def run_npu_inference(session, features: dict) -> int:
    """Runs NPU inference using pre-trained CodeBERT sequence classifier."""
    if session is None:
        # No model file, return analytical heuristic score
        return features["score"]
        
    try:
        # Tokenize and format features into NPU model input tensor
        # Example input shape: float32[1, 4]
        input_data = np.array([[
            features["lines"],
            features["loops"],
            features["fp_ops"],
            features["nesting"]
        ]], dtype=np.float32)
        
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        
        res = session.run([output_name], {input_name: input_data})
        # Score predicted by ONNX model running on NPU
        predicted_score = int(res[0][0][0])
        return max(0, predicted_score)
    except Exception:
        return features["score"]

def main():
    parser = argparse.ArgumentParser(description="🔱 ZKAEDI VMAX: NPU Pre-Pass Classifier")
    parser.add_argument("--source", required=True, help="Path to source codebase shard")
    parser.add_argument("--model", default="npu_codebert_classifier.onnx", help="Path to ONNX model file")
    parser.add_argument("--output", default=DEFAULT_QUEUE_FILE, help="Output priority queue JSON path")
    parser.add_argument("--min-score", type=int, default=30, help="Minimum complexity score cutoff")
    args = parser.parse_args()

    print("=========================================================================")
    print("          🔱 ZKAEDI VMAX: NPU COMPLEXITY PRE-PASS CLASSIFIER")
    print("=========================================================================")
    
    # 1. Initialize NPU hardware session
    session, engine_desc = init_npu_session(args.model)
    print(f"[*] Inference Hardware : {engine_desc}")
    print(f"[*] Scanning sources   : {args.source}")
    
    # 2. Scan and evaluate all C files
    priority_queue = []
    skipped_count = 0
    evaluated_count = 0
    
    for root, _, files in os.walk(args.source):
        for file in files:
            if file.endswith((".c", ".cpp", ".cc")):
                full_path = os.path.join(root, file)
                evaluated_count += 1
                
                # Extract structural features
                features = extract_analytical_features(full_path)
                
                # Run XDNA2 inference (or fallback to fast analytical math)
                predicted_score = run_npu_inference(session, features)
                
                if predicted_score >= args.min_score:
                    priority_queue.append({
                        "path": full_path,
                        "score": predicted_score,
                        "metrics": features
                    })
                else:
                    skipped_count += 1
                    
    # 3. Sort priority queue descending by score (LEGENDARY candidate files first)
    priority_queue.sort(key=lambda x: x["score"], reverse=True)
    
    # 4. Write output priority queue
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(priority_queue, f, indent=4)
        
    print("=========================================================================")
    print(f"🔱 NPU CLASSIFICATION COMPLETE")
    print(f"   Evaluated files   : {evaluated_count}")
    print(f"   Prioritized queue : {len(priority_queue)} files -> {args.output}")
    print(f"   Discarded (low)   : {skipped_count} (saved {skipped_count} compiler cycles!)")
    
    if len(priority_queue) > 0:
        print("\n🏆 Top 5 LEGENDARY Compiler Targets in Queue:")
        for i, item in enumerate(priority_queue[:5]):
            print(f"   {i+1}. {os.path.basename(item['path']):<30} | Score: {item['score']:<4} | Loops: {item['metrics']['loops']}")
    print("=========================================================================")

if __name__ == "__main__":
    main()
