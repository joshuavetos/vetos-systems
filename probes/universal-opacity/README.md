![E97BC40C-8858-486E-BCBA-7F11A0553B65](https://github.com/user-attachments/assets/7da17fdf-b44c-4fca-9d95-f482642e405b)


# Universal Opacity Probe

This probe tests whether large public-interest systems destroy decision-relevant signal
between published claims (“nameplate”) and real-world outcomes (“accredited”).

The probe does not assume fraud.
It tests whether opacity is structural, contractual, or irreducible.

---

## Core Question

Can an independent observer reconstruct planning-relevant truth
using only public data and published methodology?

If not, the system is classified.

---

## Domains Swept

- Electric grid reliability (ELCC / LOLE)
- ESG ratings
- Credit ratings
- University rankings
- Insurance risk models
- Clinical trial disclosures
- SEC risk disclosures

---

## Method (Domain-Agnostic)

For each domain:

1. Identify a **nameplate claim**
2. Identify an **accredited outcome**
3. Measure the **gap**
4. Stress-test public sensitivity parameters
5. Test whether the gap can be closed within disclosed bounds

---

## Classifications

- **IRREDUCIBLE_PROXY_SYSTEM**
  Public outputs are mathematically reproducible but non-invertible.
  Signal is destroyed by design.

- **PROXY_SIGNAL_DESTRUCTION**
  Published proxies fail to predict real outcomes.

- **CONTRACT/ACCESS**
  Required inputs or models are gated behind credentials or NDAs.

- **INDETERMINATE**
  Public structure exists but is insufficient for classification.

- **CONTRACT_OK**
  System is transparent and independently reconstructable.

---

## What This Probe Found

Most systems tested do not fail due to error or fraud.
They fail because they compress reality through opaque proxies
that cannot be independently reconstructed.

Opacity is the norm.
Transparency is the exception.

---

## Files

- REPORT.json — machine-readable classifications
- SAVE_PACK.txt — verbatim forensic artifacts
- ESG_DEEP_RANKED.csv — ranked ESG decoupling evidence
- api_contract_behavior.py — executable probe logic
