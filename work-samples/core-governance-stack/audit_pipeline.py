import importlib.util
import json
import hashlib
from datetime import datetime
from pathlib import Path


def _load_controller_class():
    engine_path = (
        Path(__file__).resolve().parents[2]
        / "tools"
        / "structural-integrity-audit"
        / "macro_engine_v2.1.py"
    )
    spec = importlib.util.spec_from_file_location("macro_engine_v2_1", engine_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Unable to load macro engine module from {engine_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.VetosProportionalController


VetosProportionalController = _load_controller_class()

class AuditLedger:
    """
    Minimalist Append-Only Ledger for Risk Decisions.
    Simulates a Merkle-Log for the purpose of this work sample.
    """
    def __init__(self, ledger_file="risk_ledger.jsonl"):
        self.ledger_file = ledger_file

    def commit(self, entry: dict):
        # 1. Cryptographic Seal
        entry_str = json.dumps(entry, sort_keys=True)
        entry['hash'] = hashlib.sha256(entry_str.encode()).hexdigest()
        
        # 2. Append to Immutable Log
        with open(self.ledger_file, 'a') as f:
            f.write(json.dumps(entry) + "\n")
        
        print(f"[LEDGER] Block Committed: {entry['hash'][:12]}... | Regime: {entry['regime_status']}")

def run_audit_cycle():
    print("Initializing VETOS Governance Stack...")
    
    # 1. Initialize Infrastructure
    try:
        controller = VetosProportionalController()
        ledger = AuditLedger()
    except Exception as e:
        print(f"[FATAL] Infrastructure Init Failed: {e}")
        return

    # 2. Execute Macro Engine (Lookback Window)
    # We run a standard lookback to assess current state
    print("Executing Structural Integrity Scan...")
    try:
        engine_output = controller.run_engine(start_date="2020-01-01", end_date=datetime.today().strftime('%Y-%m-%d'))
        latest_record = engine_output.iloc[-1]
    except Exception as e:
        print(f"[FATAL] Engine Execution Failed: {e}")
        return

    # 3. Construct Audit Entry (Verbatim Telemetry)
    # This is the "Proof of Work" for the forensic audit
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "final_weight": float(latest_record['final_weight']),
        "volatility_state": {
            "current": float(latest_record['current_vol']),
            "target": float(latest_record['target_vol']),
            "entropy_ratio": float(latest_record['entropy_ratio']) # The Deception Metric
        },
        "security_gates": {
            "bond_trap_active": bool(latest_record['regime_status'] == 'EXPLOSIVE'),
            "entropy_veto_active": bool(latest_record['entropy_ratio'] < 0.40) # The "Artificial Calm" Check
        },
        "regime_status": str(latest_record['regime_status'])
    }

    # 4. Commit to Ledger
    ledger.commit(audit_entry)

if __name__ == "__main__":
    run_audit_cycle()
