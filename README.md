## Reproducibility

This repository has been validated from clean-room Linux environments.

Execution receipts from fresh runs are included under artifacts/execution-proofs/.

See REPRODUCIBILITY.md for environment details and reproduction steps.

## Verification Status

- Clean-room tested on WSL Ubuntu
- Modern Python packaging (PEP 668 compliant)
- Deterministic pytest execution
- Raw execution receipts included

---
# Vetos Systems — Deterministic Governance Prototypes

## What This Repository Demonstrates
- Fail-closed execution
- Deterministic replay
- Schema-enforced validation
- Entropy-based veto
- Explicit failure semantics

## Reproducibility

```bash
python verify.py
```

Secondary option:

```bash
make verify
```

## Failure Surfaces Covered
- Missing deterministic seed (`FAILURE_ORACLE_SEED`) raises a hard failure.
- Invalid funding schema records fail validation with index-specific errors.
- Entropy collapse in budget allocations triggers a veto.
- Missing semantic text columns fail before analysis.
- Empty semantic ticket rows fail as unusable input.
- Docker daemon absence produces deterministic availability skip messaging.
- Failure Oracle artifact path mismatch fails with explicit file-not-found.
- Failure Oracle output drift is detected by exact JSON equality check.

## Design Constraints
- No fallback data sources.
- No implicit interpretation of malformed payloads.
- No recommendations or auto-remediation output.
- No hidden infrastructure requirements.
- No Docker daemon requirement for verification.
- No synthetic data generation in verification flow.
