<img width="1024" height="559" alt="7E08A0F4-5278-41CB-B0A3-3F9BDAB72693" src="https://github.com/user-attachments/assets/5b4b61bf-4f51-4d95-9921-4bf44ceac925" />

# Epistemic Instruments

This directory contains executable decision instruments.

These tools do not optimize, recommend, or automate action.
They determine whether conditions are sufficient to justify human review.

Refusal is a valid and expected outcome.

---

## Semantic Auditor (v3.3)

File: semantic_auditor_v3_3.py

Purpose:
Determines whether semantic clusters in support-ticket text are stable enough
to justify human inspection.

What it does:
- Validates input data and rejects missing/empty sources
- Tests embedding consistency
- Performs unsupervised clustering
- Stress-tests cluster stability (noise, parameters, order)
- Produces a statistical summary only if stability thresholds are met

What it explicitly does NOT do:
- Does not explain clusters
- Does not label intent
- Does not recommend fixes
- Does not generate actions
- Does not fabricate data

If stability conditions are not met, the tool abstains.

Usage:
```bash
python artifacts/epistemic-instruments/semantic_auditor_v3_3.py --input-csv /path/to/real_tickets.csv --text-column text
```

The auditor refuses to run without an explicit CSV source and does not generate fallback ticket data.


---

## Design Principles

- Fail-closed by default
- Stability before interpretation
- Statistics over narrative
- Human judgment remains sovereign

---

## Expected Outcomes

- PRODUCTION READY — clusters are stable enough for review
- HIGH NOISE — data cannot be reliably segmented
- UNSTABLE — clusters are too fragile to trust

All outcomes are correct outcomes.

---

## Usage Contract

This instrument is intentionally conservative.

If it feels boring, that is by design.
If it refuses to run, that is success.
