![1E59E05F-58E9-461E-BB67-F8A6A7FCAAFE](https://github.com/user-attachments/assets/84855d90-cef7-4a55-ab2f-14a70fe4908e)

## False Legitimacy via Statistical Masking

## Status
Closed (Root cause identified, corrective architecture deployed)

---

## Summary

A mean-based Z-score audit produced deterministic, repeatable approvals on municipal capital plans with power-law distributions.  
The system did not merely misclassify outliers — it **conferred institutional legitimacy on risk it was structurally incapable of detecting**.

This was not a calculation error.  
It was a **model-level false negative failure** with downstream governance impact.

---

## What Failed (Operationally)

- Capital plans containing extreme budget concentration passed audit
- Outputs were numerically stable, repeatable, and confidence-scored
- Human reviewers treated “audit passed” as evidence of risk screening
- The system emitted no uncertainty or warning signals

The system functioned exactly as implemented — and that behavior was unacceptable.

---

## Root Cause

Mean-based normalization assumes symmetric or near-normal distributions.

Municipal capital data is **power-law distributed**:
- A small number of megaprojects dominate total exposure
- The majority of projects cluster near zero

Use of the arithmetic mean caused:
- Megaprojects to appear statistically normal
- Ordinary maintenance projects to appear anomalous

This masked the dominant risk class instead of surfacing it.

---

## Why This Was a Governance Failure

The failure mode was not incorrect output — it was **false certainty**.

- The audit trail was clean
- The methodology was standard
- The system raised no errors
- Appeals were structurally blocked because the system “worked”

Legitimacy was transferred without detection.

This is worse than noisy or failing systems.

---

## Consequences Observed

- Capital concentration risk passed approval workflows
- Human review deferred to “objective” audit results
- Downstream decisions relied on invalid assurances
- No internal mechanism existed to challenge the audit outcome

---

## Corrective Actions Taken

1. Replaced mean-based Z-scores with median-anchored MAD
2. Introduced **ABSTAIN** as a first-class audit outcome
3. Enforced fail-closed gate semantics
4. Bound audits to deterministic context snapshots
5. Added cryptographic audit hashes for replay and repudiation
6. Enabled gate version revocation and retroactive invalidation

---

## Carry-Forward Invariant

> A system that produces confident answers outside its valid domain is more dangerous than a system that refuses to answer.

This incident establishes the requirement for:
- Explicit uncertainty handling
- Deterministic revalidation
- Structural refusal as a valid terminal state

---

## Closure

This incident justifies the defensive architecture implemented in subsequent audit gates.  
No further remediation required unless mean-based models are reintroduced.
## Incident Follow-Up — Statistical Failure Closure

### Detection Timeline
- The mean-based audit logic operated across multiple planning cycles without detection.
- Discovery occurred during a secondary discrepancy review when a capital-intensive project appeared statistically “normal” despite dominating total allocation.
- Routine audits did not flag the issue because the methodology itself was treated as authoritative.

### Downstream Impact
- At least one plan advanced beyond approval under false statistical legitimacy.
- Planning actions were initiated based on the approval; full execution was bounded but non-zero.
- No automated rollback mechanism existed because approval implied correctness.

### Appeals Were Structurally Impossible
- No formal appeal was filed.
- The system provided no mechanism to challenge an approved artifact.
- Once marked PASS, there was no review surface to question statistical legitimacy.
- Appeals were structurally blocked by design, not by process failure.

### Current Safeguards
- The MAD-based (median-anchored) approach has been tested against synthetic power-law distributions.
- Megaproject concentration is reliably flagged under adversarial distribution shaping.
- Red-team testing now targets distribution manipulation rather than single outliers.

### Generalized Failure Pattern
This incident is not budget-specific. The same failure class has been observed in:
- Hiring score normalization
- Risk aggregation models
- KPI rollups
- AI evaluation benchmarks

**Invariant:**
When legitimacy is derived from standard methodology, and that methodology is non-robust, failure becomes invisible.

This incident represents a methodological trust failure, not a data quality issue.
