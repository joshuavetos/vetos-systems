import importlib.util
import json
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "funding-analysis" / "audit_pipeline.py"
spec = importlib.util.spec_from_file_location("funding_audit", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_run_financial_audit_rejects_invalid_record():
    payload = [
        {"project_name": "A", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2026},
        {"project_name": "B", "budget_allocation": -10.0, "fiscal_start": 2025, "fiscal_end": 2026},
        {"project_name": "C", "budget_allocation": 1002.0, "fiscal_start": 2025, "fiscal_end": 2027},
        {"project_name": "D", "budget_allocation": 1003.0, "fiscal_start": 2025, "fiscal_end": 2027},
        {"project_name": "E", "budget_allocation": 1004.0, "fiscal_start": 2025, "fiscal_end": 2027},
    ]

    with pytest.raises(ValueError):
        module.run_financial_audit(payload)


def test_run_financial_audit_entropy_veto_raises():
    payload = [
        {"project_name": "A", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2026},
        {"project_name": "B", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2026},
        {"project_name": "C", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2027},
        {"project_name": "D", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2027},
        {"project_name": "E", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2027},
    ]

    with pytest.raises(RuntimeError):
        module.run_financial_audit(payload)


def test_integration_sample_payload_is_auditable():
    sample_payload = json.loads((REPO_ROOT / "samples" / "sample_funding_payload.json").read_text(encoding="utf-8"))
    result = module.run_financial_audit(sample_payload)

    assert result["status"] == "COMPLETE"
    assert result["records_validated"] == 5
    assert result["records_rejected"] == 0
