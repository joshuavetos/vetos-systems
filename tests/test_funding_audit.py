import importlib.util
from pathlib import Path

import pytest


MODULE_PATH = Path(__file__).resolve().parents[1] / "tools" / "funding-analysis" / "audit_pipeline.py"
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
