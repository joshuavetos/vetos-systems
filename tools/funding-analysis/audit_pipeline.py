from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, model_validator


class BudgetItem(BaseModel):
    """Schema enforcement for municipal capital improvement data."""

    project_name: str = Field(..., min_length=1)
    budget_allocation: float = Field(..., gt=0)
    fiscal_start: int = Field(..., ge=2020, le=2045)
    fiscal_end: int = Field(..., ge=2020, le=2045)

    @model_validator(mode="after")
    def validate_chronology(self) -> "BudgetItem":
        if self.fiscal_end < self.fiscal_start:
            raise ValueError("End date precedes start date.")
        return self


def verify_signal_integrity(data_values: np.ndarray) -> bool:
    """Entropy veto. Returns False if data is too uniform."""
    if len(data_values) < 5:
        return True

    noise = np.diff(data_values)
    counts, _ = np.histogram(noise, bins=10, density=False)
    total = counts.sum()
    if total == 0:
        return False

    probs = counts / total
    probs = probs[probs > 0]
    if probs.size == 0:
        return False

    entropy = -np.sum(probs * np.log(probs))
    max_entropy = np.log(len(probs)) if len(probs) > 1 else 1.0
    ent_ratio = entropy / max_entropy
    return bool(ent_ratio > 0.40)


def run_financial_audit(input_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not input_data:
        raise ValueError("input_data must not be empty")

    raw_allocations = np.array([r.get("budget_allocation", 0) for r in input_data], dtype=float)
    if not verify_signal_integrity(raw_allocations):
        raise RuntimeError("Entropy veto triggered: Information Complexity Failure (Entropy < 0.40)")

    validated = []
    for index, record in enumerate(input_data):
        try:
            item = BudgetItem(**record)
        except Exception as exc:
            raise ValueError(f"record at index {index} failed validation") from exc
        validated.append(item.model_dump())

    df = pd.DataFrame(validated)
    median = df["budget_allocation"].median()
    mad = np.median(np.abs(df["budget_allocation"] - median))

    if mad == 0:
        df["modified_z"], df["is_outlier"] = 0.0, False
    else:
        df["modified_z"] = 0.6745 * (df["budget_allocation"] - median).abs() / mad
        df["is_outlier"] = df["modified_z"] > 3.5

    return {
        "status": "COMPLETE",
        "records_validated": int(len(df)),
        "records_rejected": 0,
        "risk_exposure": float(df.loc[df["is_outlier"], "budget_allocation"].sum()),
        "outlier_count": int(df["is_outlier"].sum()),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic funding audit.")
    parser.add_argument("--input-json", required=True)
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    payload = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("input JSON must be a list of records")

    result = run_financial_audit(payload)
    rendered = json.dumps(result, indent=2, sort_keys=True)
    if args.output_json:
        Path(args.output_json).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
