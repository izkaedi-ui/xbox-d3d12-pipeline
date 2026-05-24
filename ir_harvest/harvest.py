#!/usr/bin/env python3
import os, sys, re, hashlib, argparse

CORPUS_DIR      = "corpus"
SCORE_EPIC      = 50
SCORE_LEGENDARY = 120

FUNC_RE = re.compile(r"^\s*;\s*func\s+(\w+)\s*->")
END_RE  = re.compile(r"^\s*;\s*end\s+(\w+)")

SCORING_RULES = [
    (r"\b(JMP|JZ|JNZ|JG|JL|JGE|JLE|CMP|LABEL)\b", 15),
    (r"\b(FADD|FSUB|FMUL|FDIV|FNEG|FMA)\b",        10),
    (r"\b(ADD|SUB|MUL|DIV|SHL|SHR|XOR|AND|OR)\b",   4),
    (r"\b(LOAD|STORE|ADDR|CONST)\b",                  3),
]

def parse_ir(ir_text):
    funcs, current, body = {}, None, []
    for line in ir_text.splitlines():
        m = FUNC_RE.match(line)
        if m:
            if current: funcs[current] = "\n".join(body)
            current, body = m.group(1), [line]
            continue
        e = END_RE.match(line)
        if e and current:
            body.append(line)
            funcs[current] = "\n".join(body)
            current, body = None, []
            continue
        if current:
            body.append(line)
    if current:
        funcs[current] = "\n".join(body)
    return funcs

def score(ir_body):
    return sum(len(re.findall(p, ir_body)) * w for p, w in SCORING_RULES)

def save(name, body, s, cls):
    os.makedirs(CORPUS_DIR, exist_ok=True)
    h = hashlib.sha256(body.encode()).hexdigest()[:12]
    path = f"{CORPUS_DIR}/{name}_{cls}_{h}.ir"
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"; ZKAEDI VMAX HARVESTED ENTRY\n; Function : {name}\n; Score    : {s} ({cls})\n; Hash     : {h}\n")
        f.write(body)
    return path

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clean", action="store_true")
    ap.add_argument("--ir", default="out.ir")
    args = ap.parse_args()

    if not os.path.exists(args.ir):
        print(f"[ERROR] IR file not found: {args.ir}")
        print("Run build.zcc.sh first.")
        sys.exit(1)

    with open(args.ir, "r", encoding="utf-8", errors="replace") as f:
        ir = f.read()

    if not FUNC_RE.findall(ir):
        print("[GATE FAIL] No '; func <name> ->' headers found.")
        print("Verify: grep -m 5 '; func' out.ir")
        sys.exit(1)

    funcs = parse_ir(ir)
    legendary, epic = 0, 0

    for name, body in funcs.items():
        s = score(body)
        cls = "LEGENDARY" if s >= SCORE_LEGENDARY else "EPIC" if s >= SCORE_EPIC else None
        if cls:
            if cls == "LEGENDARY": legendary += 1
            else: epic += 1
            out = save(name, body, s, cls)
            print(f"  {name:<40} | {s:<5} | {cls:<10} -> {os.path.basename(out)}")

    print(f"\nHARVEST COMPLETE: {legendary} LEGENDARY | {epic} EPIC | {len(funcs)} total parsed")

    if args.clean and legendary + epic > 0:
        os.remove(args.ir)

if __name__ == "__main__":
    main()
