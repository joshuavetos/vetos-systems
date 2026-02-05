<img width="1024" height="559" alt="9CEF9870-E9A2-41A2-9A68-665DAA1AF18B" src="https://github.com/user-attachments/assets/4a3cc5ab-c56e-4074-acbb-5b17c9a89775" />

# Document Gate

## Overview

Document Gate is a deterministic, fail-closed ingestion gate for raw text documents.

It answers exactly one question:

    Is this document structurally fit for downstream analysis?

It does not summarize, interpret, infer intent, or guess missing information.
Refusal is a valid and successful outcome.

This tool exists to prevent unanchored, malformed, or misleading documents from entering analysis pipelines.

---

## Terminal States

The gate always terminates in exactly one of the following states:

- PASS:sufficient_anchors  
  The document contains sufficient, unambiguous temporal and fiscal anchors.

- ABSTAIN:<reason_code>  
  The document is readable, but insufficiently anchored for safe analysis.

- FAIL:<reason_code>  
  The document or execution environment is invalid.

All terminal states are explicit. The program never fails silently.

---

## Anchor Definitions (Strict)

### Temporal Anchors

A year is counted as a temporal anchor only when it is contextually bound.

Accepted examples include:
- “FY 2026”
- “fiscal year 2025”
- “in 2030”

Explicitly rejected:
- unit poisoning (e.g. “in 2026 units”)
- quantities, percentages, or measurements adjacent to years
- free-floating numeric years without contextual binding

### Fiscal Anchors

Fiscal anchors must be explicit currency values.

Accepted formats:
- $500
- $1,234
- $5.00
- $1,234.56

Enforcement rules:
- Unicode currency is normalized before matching (OCR-safe)
- Shorthand notation ($5m, $2B) is intentionally rejected
- Repeated values do not launder legitimacy
- Anchors must appear on multiple distinct lines

---

## Deterministic Constraints (Defaults)

The following constraints are enforced by default:

- Minimum temporal anchors: 2
- Minimum unique fiscal anchors: 3
- Minimum fiscal anchor lines: 2
- Valid year range: year_floor → (current_year + horizon)
- Empty input: FAIL (not ABSTAIN)

All thresholds are configurable via CLI.
Invalid or self-defeating configurations are rejected.

---

## Telemetry (First-Class Output)

Every execution emits structured telemetry containing:

- schema_version
- tool_version
- timestamp (UTC)
- resolved configuration
- anchors detected (temporal and fiscal)
- bounded anchor context
- terminal decision and reason_code
- execution errors (if any)

If output file writing fails, telemetry is emitted to stdout.
The program never exits without emitting a decision record.

---

## Runtime Guarantees

Document Gate guarantees:

- Standard library only (no external dependencies)
- Deterministic behavior across runs
- Fail-closed handling for:
  - invalid input
  - invalid configuration
  - encoding errors
  - filesystem failures
  - unexpected exceptions
- Explicit exit codes
- No hidden defaults
- No environment inference

---

## Usage

    python gate.py your_document.txt

Optional flags:

    --min-year-anchors N
    --min-fiscal-unique N
    --min-fiscal-lines N
    --currency-symbols "$,€,£"
    --no-context
    --dry-run

---

## Why This Exists

This artifact demonstrates:

- production-grade failure handling
- deterministic validation boundaries
- environment hostility awareness
- refusal discipline
- finished, verifiable engineering

It is intentionally boring.
Interest is a failure mode.
