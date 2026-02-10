#!/usr/bin/env python3
"""
VETOS-PROOF-002
Model Integrity + Conformity Violation

Demonstrates:
- Q3 Integrity: forbidden fallback path executed
- Q4 Conformity: distribution drift beyond bound
"""

import sys
import json
import hashlib
import time
import random

RECEIPT = "receipt.qual.json"
SCHEMA = "exq://spec/v1"
DRIFT_THRESHOLD = 0.05


def now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def sha(data):
    return hashlib.sha256(json.dumps(data).encode()).hexdigest()


def run_model():
    # Claims success
    print("[MODEL] Inference service running")
    print("[MODEL] Accuracy reported: 95% ✅")

    # Reality: drift + forbidden fallback
    baseline = 0.50
    observed = sum(random.random() for _ in range(1000)) / 1000
    drift = abs(observed - baseline)

    fallback_used = True  # forbidden path

    return drift, fallback_used


def qualify():
    drift, fallback_used = run_model()

    violations = []

    if fallback_used:
        violations.append({
            "id": "Q3_Integrity",
            "evidence": "forbidden fallback path executed"
        })

    if drift > DRIFT_THRESHOLD:
        violations.append({
            "id": "Q4_Conformity",
            "evidence": {
                "baseline": 0.50,
                "observed": drift,
                "threshold": DRIFT_THRESHOLD
            }
        })

    if violations:
        receipt = {
            "schema": SCHEMA,
            "timestamp": now(),
            "status": "FAILED",
            "violations": [v["id"] for v in violations],
            "evidence": [{
                **v,
                "hash": sha(v)
            } for v in violations]
        }

        with open(RECEIPT, "w") as f:
            json.dump(receipt, f, indent=2)

        print("\n[VETOS] ❌ QUALIFICATION FAILED")
        for v in violations:
            print(f"  Violated Law: {v['id']}")
        print(f"  Receipt written → {RECEIPT}")
        sys.exit(1)

    print("[VETOS] ✅ QUALIFIED")
    sys.exit(0)


if __name__ == "__main__":
    qualify()
