#!/usr/bin/env python3
"""
PURE SEMANTIC AUDITOR v3.3 (DETERMINISTIC)
Optimized for Epistemic Integrity | No Theater | No Plots
"""

import argparse
import sys

import hdbscan
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import umap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run semantic stability checks on real support ticket text."
    )
    parser.add_argument(
        "--input-csv",
        required=True,
        help="Path to a CSV file containing real support-ticket records.",
    )
    parser.add_argument(
        "--text-column",
        default="text",
        help="Name of the CSV column containing ticket text (default: text).",
    )
    return parser.parse_args()


def validate_environment() -> None:
    try:
        assert pd.__version__ >= "2.2"
        print("✅ Environment validated")
    except (AssertionError, ImportError):
        print(
            "❌ Environment failure: pandas>=2.2, sentence-transformers, umap-learn, hdbscan required"
        )
        sys.exit(1)


def load_input(path: str, text_column: str) -> pd.DataFrame:
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        print(f"❌ Unable to read input CSV: {exc}")
        sys.exit(1)

    if text_column not in df.columns:
        print(
            f"❌ Missing required text column '{text_column}'. Available columns: {list(df.columns)}"
        )
        sys.exit(1)

    text_series = df[text_column].dropna().astype(str).str.strip()
    text_series = text_series[text_series != ""]

    if text_series.empty:
        print("❌ Input data contains no usable text rows")
        sys.exit(1)

    print(f"✅ Loaded {len(text_series)} records from {path}")
    return pd.DataFrame({"text": text_series})


def main() -> None:
    args = parse_args()
    validate_environment()
    df = load_input(args.input_csv, args.text_column)

    model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(df["text"].tolist(), show_progress_bar=False)

    reducer = umap.UMAP(n_neighbors=15, n_components=2, metric="cosine", random_state=42)
    embed_2d = reducer.fit_transform(embeddings)
    clusterer = hdbscan.HDBSCAN(min_cluster_size=5, min_samples=3)
    labels = clusterer.fit_predict(embed_2d)

    df["cluster"] = labels
    clusters = df[df["cluster"] != -1].groupby("cluster").agg(
        {
            "text": ["count", lambda x: " | ".join(x.str.lower().str[:50].tolist()[:3])],
        }
    )
    clusters.columns = ["Count", "SampleText"]
    clusters["Share"] = (clusters["Count"] / clusters["Count"].sum() * 100).round(1)

    print("\n--- PRODUCTION SUMMARY ---")
    if clusters.empty:
        print("No non-noise clusters found.")
    else:
        print(clusters[["Share", "SampleText"]].to_markdown())

    noise_ratio = np.sum(labels == -1) / len(labels)
    status = "✅ PRODUCTION READY" if noise_ratio < 0.3 else "❌ UNSTABLE (HIGH NOISE)"
    print(f"\n🎯 DECISION: {status} | Noise: {noise_ratio:.1%}")


if __name__ == "__main__":
    main()
