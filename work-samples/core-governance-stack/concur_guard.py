import json
import hashlib
import os
from datetime import datetime, timezone

LEDGER_FILE = "receipt_ledger.json"
EXPECTED_ACCOUNTS = {"123456"}
ZERO_HASH = "0" * 64
CI_MODE = False  # Set True if using in real CI

def sha(data: str) -> str:
    return hashlib.sha256(data.encode()).hexdigest()

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def load_ledger():
    if not os.path.exists(LEDGER_FILE):
        return []
    with open(LEDGER_FILE) as f:
        data = json.load(f)
    return data.get("receipts", [])

def save_ledger(receipts):
    verdict = derive_verdict(receipts)
    with open(LEDGER_FILE, "w") as f:
        json.dump({"receipts": receipts, "verdict": verdict}, f, indent=2)
    return verdict

def derive_verdict(receipts):
    for r in receipts:
        if r["decision"] == "BLOCK":
            return "MERGE_BLOCKED"
    return "MERGE_ALLOWED"

def replay_verify(receipts):
    parent = ZERO_HASH
    for r in receipts:
        payload = json.dumps(
            {
                "kind": r["kind"],
                "constraint": r["constraint"],
                "context": r["context"],
                "result": r["result"],
                "decision": r["decision"],
                "parent_hash": parent,
            },
            sort_keys=True,
        )
        expected_hash = sha(payload)
        if r["hash"] != expected_hash:
            raise RuntimeError("Ledger hash mismatch — tampering detected")
        if r["parent_hash"] != parent:
            raise RuntimeError("Parent hash mismatch — chain broken")
        parent = r["hash"]
    return True

def emit_receipt(receipts, kind, constraint, context, result, decision):
    parent_hash = receipts[-1]["hash"] if receipts else ZERO_HASH
    payload = json.dumps(
        {
            "kind": kind,
            "constraint": constraint,
            "context": context,
            "result": result,
            "decision": decision,
            "parent_hash": parent_hash,
        },
        sort_keys=True,
    )
    h = sha(payload)
    receipt = {
        "timestamp": utc_now(),
        "kind": kind,
        "constraint": constraint,
        "context": context,
        "result": result,
        "decision": decision,
        "hash": h,
        "parent_hash": parent_hash,
    }
    receipts.append(receipt)
    print(f"{kind}: {constraint} -> {decision}")
    return receipt

def submit_expense(receipts, context):
    if context["account_id"] not in EXPECTED_ACCOUNTS:
        return emit_receipt(
            receipts, "VIOLATION", "Account.status == 'ACTIVE'",
            context, "FORBIDDEN", "BLOCK",
        )
    seen = {r["context"]["receipt_id"] for r in receipts}
    if context["receipt_id"] in seen:
        return emit_receipt(
            receipts, "VIOLATION", "duplicate_receipt",
            context, "INSUFFICIENT_FUNDS", "BLOCK",
        )
    return emit_receipt(
        receipts, "QUALIFIED", "ALL",
        context, "OK", "ALLOW",
    )

def run_demo():
    receipts = load_ledger()
    if receipts:
        replay_verify(receipts)
        print("Ledger verified.")

    scenarios = [
        {"portal_url": "https://www.concur.com/expense/submit", "account_id": "789012", "visible_name": "Jane Roe (ID:789012)", "receipt_id": "EXP-2026-001", "amount": 0},
        {"portal_url": "https://www.concur.com/expense/submit", "account_id": "123456", "visible_name": "John Doe (ID:123456)", "receipt_id": "EXP-2026-002", "amount": 1},
        {"portal_url": "https://www.concur.com/expense/submit", "account_id": "123456", "visible_name": "John Doe (ID:123456)", "receipt_id": "EXP-2026-002", "amount": 1},
    ]
    for s in scenarios:
        submit_expense(receipts, s)

    verdict = save_ledger(receipts)
    print(f"\nFinal Verdict: {verdict}")
    if verdict == "MERGE_BLOCKED":
        if CI_MODE: raise SystemExit(1)
        else: print("Fail-closed triggered (CI disabled in Colab).")

if __name__ == "__main__":
    run_demo()
