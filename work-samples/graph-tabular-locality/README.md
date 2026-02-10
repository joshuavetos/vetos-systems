<img width="1024" height="572" alt="E147904F-A30A-4D60-8928-1E417E3978CF" src="https://github.com/user-attachments/assets/f2ac8897-fe43-4ecc-aa1e-642be63bbe74" />

# Adaptive Locality in Graph-Based Tabular Regression

## Problem

Graph-based message passing is increasingly applied to tabular regression problems.
Empirically, these methods sometimes improve performance and sometimes degrade it,
especially on heavy-tailed targets.

A hidden assumption in most applications is that a fixed neighborhood size (k)
is sufficient across the entire feature space.

This repository demonstrates that assumption is false.

---

## Observation

Through controlled experiments, we observe a consistent, non-monotonic relationship
between neighborhood size and predictive performance:

- Small neighborhoods (k ≈ 3) are necessary to resolve high-variance tail cases.
- Larger neighborhoods (k ≈ 10) improve global stability but over-smooth tail signal.
- Fixed-k graph message passing can actively harm predictions in locally complex regions.

These effects are stable across random seeds and reproducible across domains.

---

## Method

We construct a k-NN graph over samples in feature space and learn a relational
representation using a Graph Neural Network (GCN).

Key components:

- Nodes: samples
- Edges: k-nearest neighbors in feature space
- Encoder: shallow GCN for message passing
- Downstream model: XGBoost regressor

We then replace fixed-k graph construction with an **adaptive locality rule**:

- Use small k in sparse, high-variance, or high-gradient regions
- Use larger k in dense, stable regions

This explicitly controls information flow and prevents over-smoothing.

---

## Evidence

The method was pressure-tested using:

- Seed stability analysis (multiple random seeds)
- k-sweep experiments (k ∈ {3, 5, 10})
- Tail-specific error attribution
- Neighborhood variance diagnostics
- Domain transfer validation

Results were consistent across:
- A synthetic consumer LTV dataset
- The California Housing regression dataset

Adaptive locality improves tail robustness while preserving global stability.

---

## Conclusion

Neighborhood size is not a tuning knob.
It is a control parameter that governs whether relational learning helps or harms.

For heavy-tailed tabular regression:
- Fixed-k graph message passing is unreliable.
- Adaptive locality restores predictable improvements by aligning message passing
  with local feature-space geometry.

This repository encodes that rule as a minimal, reproducible artifact.
