# text_scalpel/vetos_gate.py

import ast
import json
import hashlib
import time

def now_utc():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256(s: str) -> str:
    return hashlib.sha256(s.encode()).hexdigest()

def vetos_qualify(original: str, modified: str, payload: str):
    evidence = []

    # -------------------------
    # Q1 — Conservation
    # -------------------------
    in_lines = len(original.splitlines())
    out_lines = len(modified.splitlines())
    inserted = len(payload.splitlines())

    q1_ok = (out_lines == in_lines + inserted)
    q1_ev = {
        "law": "Q1_Conservation",
        "input_lines": in_lines,
        "output_lines": out_lines,
        "inserted_lines": inserted,
        "delta": out_lines - (in_lines + inserted),
    }
    evidence.append(q1_ev)

    # -------------------------
    # Q3 — Integrity (syntax)
    # -------------------------
    try:
        ast.parse(modified)
        q3_ok = True
        q3_ev = {"law": "Q3_Integrity", "syntax": "valid"}
    except SyntaxError as e:
        q3_ok = False
        q3_ev = {"law": "Q3_Integrity", "error": str(e)}

    evidence.append(q3_ev)

    qualified = q1_ok and q3_ok

    receipt = {
        "schema": "exq://spec/v1",
        "timestamp": now_utc(),
        "status": "QUALIFIED" if qualified else "FAILED",
        "violations": [
            ev["law"] for ev, ok in zip(evidence, [q1_ok, q3_ok]) if not ok
        ],
        "evidence": [
            {**ev, "hash": sha256(json.dumps(ev, sort_keys=True))}
            for ev in evidence
        ],
    }

    with open("receipt.qual.json", "w") as f:
        json.dump(receipt, f, indent=2)

    return qualified
