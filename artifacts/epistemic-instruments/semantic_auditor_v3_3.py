#!/usr/bin/env python3
"""Deterministic semantic auditor with explicit failure semantics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


class SemanticAuditError(RuntimeError):
    """Raised when semantic auditing cannot continue deterministically."""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic semantic stability checks.")
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--text-column", default="text")
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def load_input(path: str, text_column: str) -> pd.DataFrame:
    csv_path = Path(path)
    if not csv_path.exists():
        raise SemanticAuditError(f"input CSV does not exist: {path}")

    df = pd.read_csv(csv_path)
    if text_column not in df.columns:
        raise SemanticAuditError(f"missing required text column '{text_column}'")

    text_series = df[text_column].dropna().astype(str).str.strip()
    text_series = text_series[text_series != ""]
    if text_series.empty:
        raise SemanticAuditError("input data contains no usable text rows")

    return pd.DataFrame({"text": text_series})


def lexical_cluster(tokens: list[str]) -> str:
    token_set = set(tokens)
    if token_set & {"error", "fail", "crash", "timeout", "bug"}:
        return "incident"
    if token_set & {"refund", "invoice", "charge", "billing", "payment"}:
        return "billing"
    if token_set & {"login", "password", "access", "auth", "signin"}:
        return "access"
    return "general"


def run_audit(df: pd.DataFrame) -> dict:
    labels: list[str] = []
    for text in df["text"]:
        normalized = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
        tokens = [tok for tok in normalized.split() if tok]
        labels.append(lexical_cluster(tokens))

    out = df.copy()
    out["cluster"] = labels
    counts = out.groupby("cluster").size().sort_values(ascending=False)
    noise_ratio = float((counts.get("general", 0) / len(out)))
    decision = "REVIEWABLE" if noise_ratio < 0.6 else "UNSTABLE_HIGH_NOISE"

    return {
        "rows": int(len(out)),
        "clusters": {name: int(value) for name, value in counts.items()},
        "noise_ratio": round(noise_ratio, 4),
        "decision": decision,
    }


def main() -> None:
    args = parse_args()
    df = load_input(args.input_csv, args.text_column)
    result = run_audit(df)
    rendered = json.dumps(result, indent=2, sort_keys=True)

    if args.output_json:
        Path(args.output_json).write_text(rendered + "\n", encoding="utf-8")

    print(rendered)


if __name__ == "__main__":
    main()
