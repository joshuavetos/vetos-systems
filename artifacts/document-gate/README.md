# Document Gate 

## What This Is

A deterministic, fail-closed ingestion gate.

It answers exactly one question:

    “Is this document structurally fit for downstream analysis?”

It does not:
- summarize
- interpret
- infer intent
- guess missing information

Refusal is a successful outcome.

----------------------------------------------------------------

## Terminal States

PASS:sufficient_anchors
    Document contains sufficient, unambiguous temporal and fiscal anchors.

ABSTAIN:<reason_code>
    Document is readable but insufficiently anchored.

FAIL:<reason_code>
    Document or execution environment is invalid.

----------------------------------------------------------------

## Anchors (Strict Definitions)

Temporal anchors:
- Years are counted ONLY when contextually bound
  (e.g. “FY 2026”, “fiscal year 2025”, “in 2030”)
- Unit poisoning is explicitly blocked
  (e.g. “in 2026 units” does NOT count)

Fiscal anchors:
- Explicit currency values only
  ($500, $1,234, $5.00, $1,234.56)
- Unicode currency normalized before matching (OCR-safe)
- Shorthand ($5m, $2B) intentionally rejected
- Repeated values do NOT launder legitimacy
- Anchors must appear on multiple distinct lines

----------------------------------------------------------------

## Deterministic Constraints (Defaults)

- Minimum temporal anchors: 2
- Minimum unique fiscal anchors: 3
- Minimum fiscal anchor lines: 2
- Valid year range: year_floor → (current_year + horizon)
- Empty input: FAIL (not ABSTAIN)

All thresholds are configurable via CLI.
Invalid configurations are rejected.

----------------------------------------------------------------

## Telemetry (First-Class Output)

Every execution emits telemetry containing:
- schema_version
- tool_version
- timestamp (UTC)
- resolved configuration
- anchors found (years + fiscal)
- anchor context (bounded)
- terminal decision + reason_code
- execution errors (if any)

If output writing fails, telemetry is emitted to stdout.
The program never fails silently.

----------------------------------------------------------------

## Runtime Guarantees

- Standard library only (no external dependencies)
- Fail-closed on:
  - bad input
  - bad config
  - bad encoding
  - filesystem errors
  - unexpected exceptions
- Deterministic exit codes
- No hidden defaults
- No environment inference

----------------------------------------------------------------

## Usage

    python gate.py your_document.txt

Optional flags:
    --min-year-anchors N
    --min-fiscal-unique N
    --min-fiscal-lines N
    --currency-symbols "$,€,£"
    --no-context
    --dry-run

----------------------------------------------------------------

## Why This Exists In This Repo

This artifact demonstrates:
- production-grade failure handling
- environment hostility awareness
- refusal discipline
- finished, verifiable engineering

It is intentionally boring.
Interest is a failure mode.
