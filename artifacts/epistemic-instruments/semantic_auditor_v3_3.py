#!/usr/bin/env python3
"""Semantic auditor with explicit failure semantics."""

import argparse

import hdbscan
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
import umap


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run semantic stability checks on real support ticket text."
    )
    parser.add_argument("--input-csv", required=True)
    parser.add_argument("--text-column", default="text")
    return parser.parse_args()


def validate_environment() -> None:
    if pd.__version__ < "2.2":
        raise RuntimeError("pandas>=2.2 required")


def load_input(path: str, text_column: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    if text_column not in df.columns:
        raise ValueError(f"missing required text column '{text_column}'")

    text_series = df[text_column].dropna().astype(str).str.strip()
    text_series = text_series[text_series != ""]
    if text_series.empty:
        raise ValueError("input data contains no usable text rows")

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
        {"text": ["count", lambda x: " | ".join(x.str.lower().str[:50].tolist()[:3])]}
    )
    clusters.columns = ["Count", "SampleText"]
    clusters["Share"] = (clusters["Count"] / clusters["Count"].sum() * 100).round(1)

    if clusters.empty:
        print("DECISION: INSUFFICIENT_STRUCTURE")
    else:
        print(clusters[["Share", "SampleText"]].to_markdown())

    noise_ratio = np.sum(labels == -1) / len(labels)
    decision = "REVIEWABLE" if noise_ratio < 0.3 else "UNSTABLE_HIGH_NOISE"
    print(f"DECISION: {decision} | noise_ratio={noise_ratio:.1%}")


if __name__ == "__main__":
    main()
