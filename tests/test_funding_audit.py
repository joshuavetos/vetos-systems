import importlib.util
import json
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "tools" / "funding-analysis" / "audit_pipeline.py"
spec = importlib.util.spec_from_file_location("funding_audit", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
assert spec.loader is not None
spec.loader.exec_module(module)

EXTRACTION_MODULE_PATH = REPO_ROOT / "tools" / "funding-analysis" / "allocation_extraction.py"
extraction_spec = importlib.util.spec_from_file_location("allocation_extraction", EXTRACTION_MODULE_PATH)
extraction_module = importlib.util.module_from_spec(extraction_spec)
sys.modules[extraction_spec.name] = extraction_module
assert extraction_spec.loader is not None
extraction_spec.loader.exec_module(extraction_module)


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


def test_filing_auditor_accepts_iso_date_string():
    auditor = extraction_module.FilingAuditor(target_years=[2024])
    filing = extraction_module.Filing(
        identifier="f-1",
        filing_type="10-K",
        accepted_date="2024-01-15",
        processed_text="For fiscal year 2024 revenue was $100.",
    )

    auditor.audit_filing(filing)

    assert auditor.coverage[2024] == 1


def test_filing_auditor_rejects_outlier_not_in_first_five_mentions():
    auditor = extraction_module.FilingAuditor(target_years=[2024])
    filing = extraction_module.Filing(
        identifier="f-2",
        filing_type="10-K",
        accepted_date="2024-01-15",
        processed_text="\n".join(
            [
                "$100",
                "$101",
                "$102",
                "$103",
                "$104",
                "$1,000,000",
            ]
        ),
    )

    auditor.audit_filing(filing)

    assert any(
        rejection["context"] == "financial_outlier" and rejection["value"] == 1000000.0
        for rejection in auditor.telemetry.rejections
    )


def test_run_financial_audit_prioritizes_schema_validation_before_entropy_gate():
    payload = [
        {"project_name": "A", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2026},
        {"project_name": "B", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2026},
        {"project_name": "C", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2027},
        {"project_name": "D", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2027},
        {"project_name": "", "budget_allocation": 1000.0, "fiscal_start": 2025, "fiscal_end": 2027},
    ]

    with pytest.raises(ValueError, match="record at index 4 failed validation"):
        module.run_financial_audit(payload)


def test_filing_auditor_extracts_unformatted_and_shorthand_currency():
    auditor = extraction_module.FilingAuditor(target_years=[2024])
    filing = extraction_module.Filing(
        identifier="f-3",
        filing_type="10-Q",
        accepted_date="2024-05-01",
        processed_text="Budget for year 2024 includes $1000 and reserve of $2m.",
    )

    auditor.audit_filing(filing)

    outlier_values = {rejection["value"] for rejection in auditor.telemetry.rejections if rejection["context"] == "financial_outlier"}
    assert 1000.0 not in outlier_values
    assert 2000000.0 not in outlier_values
