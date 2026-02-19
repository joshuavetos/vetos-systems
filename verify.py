#!/usr/bin/env python3
"""One-click deterministic verification entry point."""

from __future__ import annotations

import difflib
import importlib.util
import io
import json
import os
import contextlib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent


def load_module(module_name: str, relative_path: str):
    module_path = REPO_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"unable to load module at {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def render_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True)


def unified_diff(expected: object, actual: object) -> str:
    expected_text = render_json(expected).splitlines()
    actual_text = render_json(actual).splitlines()
    return "\n".join(
        difflib.unified_diff(
            expected_text,
            actual_text,
            fromfile="expected",
            tofile="actual",
            lineterm="",
        )
    )


def run_unit_tests() -> tuple[bool, str]:
    captured = io.StringIO()
    with contextlib.redirect_stdout(captured), contextlib.redirect_stderr(captured):
        exit_code = pytest.main(["-q"])
    if exit_code == 0:
        return True, ""
    output = captured.getvalue().strip()
    detail = f"pytest exited with code {exit_code}"
    if output:
        detail += "\n" + output
    return False, detail


def run_funding_audit() -> tuple[bool, str]:
    module = load_module("funding_audit", "tools/funding-analysis/audit_pipeline.py")
    sample_path = REPO_ROOT / "samples" / "sample_funding_payload.json"
    payload = json.loads(sample_path.read_text(encoding="utf-8"))
    actual = module.run_financial_audit(payload)
    expected = {
        "status": "COMPLETE",
        "records_validated": 5,
        "records_rejected": 0,
        "risk_exposure": 0.0,
        "outlier_count": 0,
    }
    if actual == expected:
        return True, ""
    diff = unified_diff(expected, actual)
    return False, "Funding audit output mismatch:\n" + diff


def run_semantic_audit() -> tuple[bool, str]:
    module = load_module("semantic_auditor", "artifacts/epistemic-instruments/semantic_auditor_v3_3.py")
    csv_path = REPO_ROOT / "samples" / "sample_support_tickets.csv"
    df = module.load_input(str(csv_path), "text")
    actual = module.run_audit(df)
    expected = {
        "rows": 6,
        "clusters": {"access": 1, "billing": 2, "general": 1, "incident": 2},
        "noise_ratio": 0.1667,
        "decision": "REVIEWABLE",
    }
    if actual == expected:
        return True, ""
    diff = unified_diff(expected, actual)
    return False, "Semantic audit output mismatch:\n" + diff


def run_failure_oracle() -> tuple[bool, str]:
    module = load_module("failure_oracle", "work-samples/failure_oracle.py")
    expected_path = REPO_ROOT / "samples" / "sample_failure_oracle_output.json"

    expected = json.loads(expected_path.read_text(encoding="utf-8"))
    actual = module.run_oracle("work-samples/failure_oracle.c", seed=2026, skip_docker=True)

    if actual == expected:
        return True, ""
    diff = unified_diff(expected, actual)
    return False, "Failure Oracle output mismatch:\n" + diff


def main() -> int:
    os.environ["FAILURE_ORACLE_SEED"] = "2026"
    os.environ["FAILURE_ORACLE_SKIP_DOCKER"] = "1"

    print("VETOS SYSTEMS VERIFICATION REPORT")
    print("----------------------------------")

    checks = [
        ("Unit tests", run_unit_tests),
        ("Funding audit deterministic", run_funding_audit),
        ("Semantic audit deterministic", run_semantic_audit),
        ("Failure Oracle deterministic", run_failure_oracle),
    ]

    all_passed = True
    for label, check_fn in checks:
        try:
            passed, detail = check_fn()
        except Exception as exc:
            passed, detail = False, f"{type(exc).__name__}: {exc}"

        if passed:
            print(f"[PASS] {label}")
            continue

        all_passed = False
        print(f"[FAIL] {label}")
        if detail:
            print(detail)
        break

    status_text = "VERIFIED" if all_passed else "FAILED"
    print(f"\nRepository Status: {status_text}")
    return 0 if all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
