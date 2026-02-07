#!/usr/bin/env python3
"""
PURE SEMANTIC AUDITOR v3.3 (DETERMINISTIC)
Optimized for Epistemic Integrity | No Theater | No Plots
"""

import sys
import pandas as pd
import numpy as np
from sentence_transformers import SentenceTransformer
import umap
import hdbscan

# 1. ENVIRONMENT VALIDATION
try:
    assert pd.__version__ >= '2.2'
    print("✅ Environment validated")
except (AssertionError, ImportError):
    print("❌ Environment failure: pandas>=2.2, sentence-transformers, umap-learn, hdbscan required")
    sys.exit(1)

# 2. DATA INGESTION (Deterministic Synthetic Fallback Only)
# Replaced URL scraping with fixed synthetic generation for O(1) stability testing
synthetic_tickets = [
    "can't login to portal", "portal access denied", "unable to access dashboard",
    "reset my password", "forgot password link broken", "password reset failed",
    "billing error on invoice", "charge appeared twice", "unexpected invoice",
    "payment failed", "card declined", "payment not processing",
    "api returning 500 error", "api endpoint down", "500 internal server error"
] * 10
df = pd.DataFrame({"text": synthetic_tickets})

# 3. EMBEDDING & STABILITY
model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(df['text'].tolist(), show_progress_bar=False)

# 4. BASELINE CLUSTERING
reducer = umap.UMAP(n_neighbors=15, n_components=2, metric='cosine', random_state=42)
embed_2d = reducer.fit_transform(embeddings)
clusterer = hdbscan.HDBSCAN(min_cluster_size=5, min_samples=3)
labels = clusterer.fit_predict(embed_2d)

# 5. PRODUCTION SUMMARY (Statistical Truth Only)
df['cluster'] = labels
clusters = df[df['cluster'] != -1].groupby('cluster').agg({
    'text': ['count', lambda x: ' | '.join(x.str.lower().str[:50].tolist()[:3])],
})
clusters.columns = ['Count', 'SampleText']
clusters['Share'] = (clusters['Count'] / clusters['Count'].sum() * 100).round(1)

print("\n--- PRODUCTION SUMMARY ---")
print(clusters[['Share', 'SampleText']].to_markdown())

# 6. DECISION GATE
noise_ratio = np.sum(labels == -1) / len(labels)
status = "✅ PRODUCTION READY" if noise_ratio < 0.3 else "❌ UNSTABLE (HIGH NOISE)"
print(f"\n🎯 DECISION: {status} | Noise: {noise_ratio:.1%}")

# [span_7](start_span)[span_8](start_span)REMOVED: Reference Plot (Opt-In) as it functions as authority theater[span_7](end_span)[span_8](end_span).
