# vetos-systems

Deterministic execution audit tooling with fail-closed behavior and explicit refusal under ambiguity.

## Flagship capability

**Deterministic execution receipts for auditable decisions.**

Given a fixed input, the tools in this repository produce:
- fixed validation outcomes,
- fixed refusal behavior (`HALT`, `SKIP`, `UNKNOWN`-style explicit non-success states), and
- reproducible machine-checkable receipts.

This makes failures testable and replayable instead of silently corrected.

## Problem this solves

Operational pipelines often fail in ways that are hard to verify later:
- validation happens inconsistently,
- retries or inferred fixes hide the original failure,
- run outputs vary because behavior depends on ambient state.

This repository narrows scope to deterministic, fail-closed checks where ambiguity is preserved as refusal, not guessed away.

## Why common systems fail here

Typical analysis pipelines optimize for completion, not falsifiability. They may:
- auto-correct malformed inputs,
- hide retries,
- blend deterministic and nondeterministic decision paths.

This codebase intentionally does not do that.

## Core invariant

> For equivalent input and configuration, the system must return reproducible validation/refusal results and reproducible receipts.

## Repository audit

### CORE (keep)
- `tools/funding-analysis/audit_pipeline.py`: deterministic schema validation + entropy veto + outlier reporting.
- `tools/funding-analysis/allocation_extraction.py`: deterministic extraction and explicit rejection telemetry.
- `work-samples/failure_oracle.py`: deterministic artifact hashing and environment-gated availability checks.
- `tests/`: replay checks for deterministic and fail-closed behavior.
- `samples/`: fixed fixtures used in tests.

### NON-CORE (retain only as examples)
- `work-samples/text-scalpel/*`
- `tools/geospatial-discovery-engine/*`
- `tools/structural-integrity-audit/*`

These are useful experiments but are not required for the flagship deterministic receipt workflow.

### REMOVE (for production hardening path)
- Governance/philosophy-heavy narrative content and naming.
- Experimental modules not tied to a production invariant.
- Any component that expands toward generalized orchestration or policy platform behavior.

## Refactor plan

1. **Stabilize the deterministic core**
   - Keep only funding audit + failure oracle + tests in critical path.
2. **Collapse naming to operational terms**
   - Replace conceptual labels with verifier/validator/receipt language.
3. **Fence non-core modules**
   - Mark as experimental and remove from default execution and CI.
4. **Enforce hard fail-closed boundaries**
   - No hidden retries, no automatic reconciliation.
5. **Tighten reproducibility checks**
   - Require receipt replay tests in CI gates.

### Dependency graph (minimal)
- `samples/*` -> `tools/funding-analysis/audit_pipeline.py` -> `tests/test_funding_audit.py`
- `work-samples/failure_oracle.py` -> `samples/sample_failure_oracle_output.json` -> `tests/test_failure_oracle.py`

### Migration risk
- **Low**: documentation and naming cleanup.
- **Medium**: removing old modules may break imports in ad-hoc scripts.
- **High**: changing receipt schema without fixture/test migration.

## Renaming table (planned)

| Old name | New name |
|---|---|
| `failure_oracle` | `artifact_verifier` |
| `semantic_auditor_v3_3` | `ticket_validator` |
| `core-governance-stack` | `deterministic-guards` |
| `guardrail_engine` | `refusal_gate` |
| `audit_pipeline` | `deterministic_audit_runner` |

## Minimal MVP definition

Smallest production-credible version:
1. Deterministic JSON input validation.
2. Fail-closed entropy veto for low-information inputs.
3. Deterministic outlier detection.
4. Append-only execution receipt output.
5. Replay tests asserting identical outcomes from fixed fixtures.

## Technical debt table

| Issue | Severity | Exploitability | Recommended fix |
|---|---|---|---|
| Mixed prototype and production intent in root structure | Medium | Medium | Move non-core modules to `experimental/` and exclude from CI critical path |
| Legacy conceptual naming in paths and docs | Medium | Low | Rename to operational names; keep compatibility aliases briefly |
| Receipt schema spread across modules | Medium | Medium | Standardize one receipt schema and version it |
| Optional environment checks (`docker`) may be interpreted as runtime dependency | Low | Low | Keep explicit SKIP semantics and document non-requirement |

## Stop condition (what must NOT be added)

Do **not** add:
- generalized orchestration runtime,
- policy/governance framework layers,
- adaptive/AI decision logic,
- hidden retry/reconciliation systems,
- non-deterministic scoring paths without explicit refusal semantics.

If a feature does not enforce a concrete invariant in deterministic execution or receipt verification, it should not be added.

## What is implemented now

- Deterministic funding audit with schema validation and entropy veto.
- Deterministic artifact verification with explicit availability checks.
- Deterministic/refusal behavior tested with fixed fixtures.

## What is intentionally not implemented

- No generalized workflow engine.
- No identity or tenancy platform.
- No adaptive remediation.
- No speculative “governance stack” runtime.

## Run

Install dependencies:

```bash
python -m pip install -r requirements.txt -r requirements-dev.txt
```

Run tests:

```bash
pytest -q
```

Run deterministic funding audit:

```bash
python tools/funding-analysis/audit_pipeline.py \
  --input-json samples/sample_funding_payload.json
```

Run deterministic artifact verification:

```bash
FAILURE_ORACLE_SEED=2026 FAILURE_ORACLE_SKIP_DOCKER=1 \
python work-samples/failure_oracle.py \
  --artifact-path work-samples/failure_oracle.py
```

## Verify

Verification is successful when:
- tests pass,
- fixture-based outputs are stable,
- failure paths are explicit (exception, `HALT`, or `SKIP`) rather than silently corrected.

## Known limits

- Some repository directories remain experimental and use legacy naming.
- The current test matrix is Python-focused and does not include multi-runtime conformance.
- Receipt schema standardization is partial and should be unified for stricter long-term compatibility.
