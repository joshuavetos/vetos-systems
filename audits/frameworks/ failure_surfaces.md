# Failure Surfaces in Human–AI and Software Systems

**Status:** Approved for repository inclusion  
**Scope:** A complete map of structural failure surfaces where system assumptions collide with real-world inputs.

This document does not catalog bugs.  
It catalogs assumptions that guarantee failure when reality disagrees.

---

## 1. Input & Data Reality

Systems assume inputs are present, intentional, and correctly typed.

In practice, missing fields propagate silently, crashing late or defaulting to zero / null in ways that change outcomes without detection. Garbage values are frequently coerced into “valid” representations—strings become numbers, malformed dates collapse to epoch defaults, and truthy tokens masquerade as booleans. Validation is often skipped at ingestion because it is expensive; once bad data enters, it permeates downstream layers as legitimate signal.

---

## 2. Transformation & Processing

Systems assume stable distributions and bounded error.

Normalization routines flatten edge cases into incorrect standard values. Aggregation hides outliers in the name of performance, only for those outliers to reappear later as catastrophic failures. Untyped data is aggressively forced into rigid schemas; once structured, it is treated as trustworthy, even when the structure itself was built on coercion. After transformation, re-verification is usually impossible—correctness is assumed by inertia alone.

---

## 3. Control Flow & Decision Logic

Systems assume decision branches correspond to real states.

Complex risk is compressed into binary outcomes that reflect code paths, not actual conditions. Retry mechanisms assume failures are transient; when they are structural, retries amplify load and accelerate collapse. Workflow logic presumes a canonical user path; deviations create unreachable or untestable states that only surface in production. Determinism exists in code, not in environments.

---

## 4. Error Handling & Propagation

Systems assume failures are rare, local, and observable.

Most degradation is silent. Statistical failures are normalized and never logged. Exceptions are caught, sanitized, and re-thrown as generic errors, stripping away causal context. Alerts trigger too late, when latency thresholds are already breached and recovery paths are gone. Users respond by creating shadow workflows—manual replays and workarounds that convert outages into undocumented operating procedures.

---

## 5. Temporal Effects & Drift

Systems assume time is stable.

Data formats change slowly until they don’t. Deprecated fields linger indefinitely. Behavioral decisions harden into tribal knowledge that cannot be safely removed. Models trained on yesterday’s population ingest today’s anomalies as routine inputs, biasing outputs while appearing statistically healthy. Time erodes correctness invisibly.

---

## 6. Interfaces & Contracts

Systems assume contracts are explicit and honored.

In reality, contracts are defined by implementation. One side extends a schema; the other ignores it until a collision occurs. Intermediate layers coerce types without tracking, leaving no audit trail. Versioning follows deployment convenience rather than semantic change, allowing breaking changes to ship as patches. Compatibility is assumed, not proven.

---

## 7. Measurement & Observability

Systems assume dashboards represent reality.

Metrics outlive their definitions and owners. Logs optimize for search, not causality, obscuring event relationships. Slow-but-successful operations are ignored until they change user behavior. Anomaly detectors train on degraded states, reclassifying failure as normal. Visibility lags reality.

---

## 8. Human Interaction & Oversight

Systems assume humans act as rational supervisors.

Automation bias replaces verification with plausibility. Temporary overrides accumulate into permanent state. Ranking, filtering, and ordering failures remain invisible to users while systematically distorting decisions at scale. Human trust becomes a failure vector.

---

## 9. Incentives & Governance

Systems assume incentives align with reliability.

Speed outcompetes rigor. Cost outcompetes resilience. Teams optimize for metrics tied to compensation, not system stability. Governance cycles lag code velocity, turning compliance into theater rather than enforcement. Risk is externalized toward failures that are cheap to create and expensive to trace. Failure is economically rational.

---

## 10. AI Amplification

AI systems inherit every prior failure surface.

Garbage inputs, coercion, drift, and silent degradation are absorbed as training truth. Structural data flaws are reframed as probabilistic uncertainty. Manual overrides and ad-hoc fixes never enter training sets, widening the gap between operational reality and model behavior over time. AI does not introduce new failure modes—it multiplies existing ones.

---

## Summary

The surface is closed.

Every failure observed in production traces back to one or more of these categories.  
There is no additional place for failure to hide—only places it has not yet been measured.

---

## Examples

Each failure surface is demonstrated in working code under `/examples`:
- **Input & Data Reality**: CSV loader with schema validation
- **Control Flow & Decision Logic**: Retry mechanism with exponential backoff
- **Error Handling & Propagation**: API client with classified exceptions
- (etc.)
