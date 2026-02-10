# vetos_gate.py

import json, sys, time, hashlib

RECEIPT_FILE = "receipt.qual.json"
SCHEMA_URI = "exq://spec/v1"

def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

def sha256(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()

def vetos_guard(*, law, claim, ok, evidence):
    """
    Hard gate. If ok == False, side effects are forbidden.
    """
    if ok:
        return  # ALLOW

    receipt = {
        "schema": SCHEMA_URI,
        "timestamp": now(),
        "status": "FAILED",
        "violations": [law],
        "evidence": [{
            "law": law,
            "claim": claim,
            "observed": evidence,
            "hash": sha256(evidence),
        }]
    }

    with open(RECEIPT_FILE, "w") as f:
        json.dump(receipt, f, indent=2)

    print(f"[VETOS] ❌ {law} violation — write blocked")
    print(f"[VETOS] Receipt written → {RECEIPT_FILE}")

    sys.exit(1)
