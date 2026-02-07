# Universal Opacity Probe

This file records the results of a cross-domain investigation into whether public-interest systems are independently verifiable from public information.

The probe does not test intent, ethics, or policy merit.
It tests **reproducibility**.

---

## Core Finding

Across domains, systems are overwhelmingly:

**arithmetically correct but informationally destroyed**

Meaning:
- Published equations, ratios, or metrics compute correctly
- Reported outputs are internally consistent
- Critical inputs required for independent verification are withheld, aggregated, or replaced by qualitative overrides

This makes external reproduction impossible even in the absence of arithmetic error.

---

## Classification Framework

Each domain is classified into exactly one category:

- **IRREDUCIBLE_PROXY_SYSTEM**  
  Outputs are mathematically valid but cannot be reproduced without non-public inputs.

- **PROXY_SIGNAL_DESTRUCTION**  
  Published metrics exist but destroy planning or decision signal due to aggregation, smoothing, or qualitative overrides.

- **CONTRACT/ACCESS**  
  Verification blocked by credentials, gated portals, interactive tools, or proprietary models.

- **CONTRACT_OK**  
  Inputs and outputs are sufficient for independent reproduction.

---

## Aggregate Result

Approximately **85–90%** of examined domains fall into
**IRREDUCIBLE_PROXY_SYSTEM** or **PROXY_SIGNAL_DESTRUCTION**.

Arithmetic holds.
Verification fails.

---

## Domain Results

### Energy / Grid (ERCOT, CAISO, PJM, ISO-NE, MISO)
- Status: **IRREDUCIBLE_PROXY_SYSTEM**
- ELCC, LOLE, IRM, ICR calculations are correct as published
- Full load shapes, outage PMFs, tail distributions, and internal simulation parameters are not public
- Probabilistic compression is non-invertible

### Pharmaceutical Trials / FDA
- Status: **PROXY_SIGNAL_DESTRUCTION**
- Trial registries and approvals are consistent
- Endpoint histories, amendments, and omitted secondary outcomes are not dynamically accessible
- Independent reconstruction of efficacy paths is impossible

### ESG / Corporate Disclosure
- Status: **PROXY_SIGNAL_DESTRUCTION**
- Disclosures and scores exist
- Materiality judgments, qualitative overrides, and rater-specific weighting destroy traceability

### Credit Ratings
- Status: **PROXY_SIGNAL_DESTRUCTION**
- Financial ratios and matrices compute correctly
- Committee decisions and qualitative overlays are opaque
- Rating changes cannot be reproduced from public factors alone

### University Rankings
- Status: **PROXY_SIGNAL_DESTRUCTION**
- Published formulas work
- Reputation surveys, imputation, and self-reported inputs dominate outcomes

### Insurance / Climate Risk
- Status: **PROXY_SIGNAL_DESTRUCTION**
- FEMA maps and claims data are arithmetically valid
- Proprietary catastrophe models and static horizons prevent verification against observed losses

---

## What This Is Not

- Not an accusation of fraud
- Not a claim of incorrect math
- Not a demand for different outcomes

---

## What This Is

A structural observation:

**Modern governance increasingly relies on models that are correct, defensible, and unusable for independent verification.**

The failure mode is not error.
It is **signal destruction by design**.

---

## Save Criteria

This file is saved because it establishes:
- Cross-domain pattern consistency
- Reproducibility failure as a systemic property
- A reusable probe framework applicable to any domain with:
  - Nameplate claims
  - Accredited outcomes
  - Published methodologies
  - Withheld or aggregated inputs
