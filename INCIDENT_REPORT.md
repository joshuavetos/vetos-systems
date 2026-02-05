# Incident Report: Statistical Failure in Mean-Based Auditing

## Objective
To analyze the "normalization of deviance" in standard Z-score models when applied to power-law municipal budgets.

## The Mechanism of Failure
Standard Z-scores use the **Arithmetic Mean**, which is non-robust. In municipal data, a single megaproject (e.g., a $100M facility) drifts the mean significantly, causing:
1. **False Negatives:** High-risk megaprojects appear "normal" (Z < 2.0).
2. **False Positives:** Typical small-scale repairs ($50k) appear as outliers.

## The Robust Alternative
This pipeline utilizes the **Modified Z-Score (MAD)**. By anchoring to the **Median**, the statistical center remains stable regardless of megaproject concentration.

| Metric | Mean-Based Z-Score | Median-Based MAD |
| :--- | :--- | :--- |
| **Stability** | Fragile | Robust |
| **Center** | Skewed by Outliers | Anchored to Typicality |
| **Risk Detection** | Obscures Capital Concentration | Exposes Capital Concentration |
