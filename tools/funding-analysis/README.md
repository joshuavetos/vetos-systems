# Funding / Allocation Analysis Tool

This folder contains a deterministic tool for extracting, validating, and auditing
financial allocations across time from planning, regulatory, or disclosure documents.

The goal is not to summarize documents, but to detect where funding exists,
where it does not, and where claims fail basic validation.

## What This Does

- Extracts year references and monetary amounts from documents
- Normalizes values (e.g. millions vs billions, signed values)
- Applies hard sanity bounds to reject implausible data
- Logs every rejection with evidence instead of hiding failures
- Computes coverage across a target year horizon
- Identifies years with no associated funding ("gaps")

## What This Does NOT Do

- It does not infer intent
- It does not assume missing data is zero
- It does not fill gaps
- It does not summarize or narrate findings
- It does not claim correctness when inputs are incomplete

## How It Works (High Level)

1. Parse candidate year and currency tokens from text
2. Normalize units and signs
3. Apply explicit validation bounds
4. Reject and log invalid or ambiguous values
5. Build a coverage vector across the target horizon
6. Report funded vs unfunded years and data quality metrics

Rejection is treated as a first-class outcome.

## How To Use

- Provide document text as input
- Run the extraction and validation logic
- Review:
  - accepted allocations
  - rejected values and reasons
  - coverage across the year range

If rejection rates exceed thresholds, the document should be flagged
for manual review rather than trusted.

## Design Principle

This tool prefers observable absence and explicit refusal
over speculative completeness.
