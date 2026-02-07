![8E93F5C3-4637-4D27-AB77-6B92339CFF0F](https://github.com/user-attachments/assets/b0c3ba2b-4fc0-4f58-b57c-fbab8f50cdd7)

# Uncertainty Gatekeeper & Claim Auditor

This artifact is a deterministic boundary layer for interacting with LLMs under ambiguity.
It is designed to **refuse output by default** unless explicit confidence, structure, and grounding requirements are satisfied.

This is not a chatbot.
It is not a reasoning assistant.
It is a control surface that decides whether language is allowed to exit the system.

--------------------------------------------------

## What This Is

A fail-closed execution wrapper around an LLM client that:

- Treats refusal as a correct outcome
- Blocks low-confidence or weakly grounded responses
- Enforces an explicit audit contract before text is released
- Produces machine-readable refusal objects instead of explanations
- Records metrics about failure modes rather than hiding them

The system assumes the model will be confidently wrong unless proven otherwise.

--------------------------------------------------

## Core Components

### UncertaintyGatekeeper

The primary execution boundary.

Responsibilities:
- Pre-flight rejection of low-density or semantically weak prompts
- Confidence threshold enforcement
- Blocking probabilistic or hedging language
- Mandatory citation enforcement when required
- Idempotent execution via SHA-256 prompt caching
- Deterministic refusal with explicit failure codes

If any validation step fails, **no text is returned**.
A structured REFUSED response is emitted instead.

--------------------------------------------------

### AuditContract

An immutable rule set governing what constitutes an acceptable response.

Enforces:
- Minimum confidence threshold
- Disallowed uncertainty language patterns
- Citation requirements
- Non-negotiable validation rules

Contracts are configuration, not behavior.
Changing the contract changes what is allowed to exist.

--------------------------------------------------

### ClaimAuditor

A secondary verifier for comparing claims against reference text.

Responsibilities:
- Normalizes numeric expressions (e.g. 1,000 vs 1000)
- Rejects claims when numeric anchors do not match references
- Returns NULL rather than partial or speculative matches
- Performs strict semantic correspondence checks only

If correspondence is not exact, the claim is rejected.

--------------------------------------------------

## What This Does NOT Do

- It does not explain refusals conversationally
- It does not soften failure modes
- It does not guess, interpolate, or “help”
- It does not optimize for user satisfaction
- It does not recover from uncertainty

Uncertainty terminates execution.

--------------------------------------------------

## Design Principles

- Refusal is success
- Silence is containment
- Confidence must be explicit
- Verification beats completion
- The user is not the optimization target

This artifact exists to prevent bad language from escaping the system,
not to make interaction pleasant.

--------------------------------------------------

## Typical Use

- Wrap any LLM call that must not hallucinate
- Enforce contracts in legal, financial, or policy contexts
- Detect and block confident nonsense early
- Collect metrics on why language was refused
- Serve as a hard boundary between models and downstream systems

--------------------------------------------------

## MULTI-GATE ORCHESTRATION & ESCALATION SEMANTICS (AUTHORITATIVE)

This section defines how multiple failure gates interact.
No gate may redefine these rules locally.

---

## 1. GATE ORDERING (TOTAL, NOT PARTIAL)

Gates are executed in a fixed, total order:

G1 → G2 → G3 → … → Gn

Examples:
- G1: Structural / Schema
- G2: Budget / Quantitative
- G3: Legal / Compliance
- G4: Temporal / Feasibility

Order is immutable per artifact class.

---

## 2. REGENERATION ENTRY RULE (CRITICAL)

If an artifact fails **Gate k**:

- Regeneration re-enters at **Gate k**
- Gates **G1 … G(k−1)** are considered *conditionally passed*
- However: **they are revalidated after regeneration**

This prevents:
- Skipping earlier gates
- Assuming earlier correctness after mutation

---

## 3. PASS INVALIDATION RULE (ANTI-REGRESSION)

After regeneration for Gate k:

- Gates G1 … G(k−1) are automatically rechecked
- If any earlier gate now fails:
  - Control returns to the **earliest failed gate**
  - Retry budget is charged to that gate

This explicitly prevents:
“Fix Gate 2 → silently break Gate 1” loops

---

## 4. RETRY BUDGET SCOPE (LOCKED)

Retry budgets are:

- **Per-gate**
- **Non-transferable**
- **Non-resetting**

Rules:
- Each gate has its own retry counter (e.g. 3–5)
- Passing a gate does **not** reset its budget
- If Gate 2 exhausts retries → permanent ABSTAIN
- Passing Gate 2 does not refund Gate 1 retries

Rationale:
Retries measure instability, not effort.

---

## 5. DOWNSTREAM REFUSAL MODES

Every downstream system MUST declare one of:

### A. HARD REFUSAL
- Any `FORCE_PASS` artifact is rejected automatically
- Used for:
  - Financial execution
  - Legal submission
  - External publication

### B. SOFT REFUSAL
- Artifact is accepted
- Flag is visible and persistent
- Human must explicitly acknowledge flag

### C. CONTEXTUAL
- Policy map determines acceptance
- Example:
  - Allowed for internal review
  - Rejected for final filing

Default mode is **HARD REFUSAL** unless explicitly overridden.

---

## 6. OPERATOR OVERRIDE INTERVENTION LADDER

Override monitoring is not advisory.

Escalation ladder:

1. **Visibility**
   - Override rate
   - Time-to-override
   - ABSTAIN frequency

2. **Threshold Trigger**
   - Exceeds baseline → automatic flag

3. **Constraint**
   - Reduced override privileges
   - Mandatory second reviewer

4. **Suspension**
   - Override disabled pending review

No silent penalties.
All actions are logged.

---

## 7. COLD-START BASELINE PROTOCOL

During initial deployment:

- Overrides are **allowed but labeled**
- No penalties for first N artifacts (configurable)
- Metrics are collected but not enforced

After baseline window:
- Median ABSTAIN rate becomes reference
- Deviations are evaluated relative to baseline, not absolute counts

This prevents:
- Premature rubber-stamping
- Early-stage paralysis

---

## 8. NON-NEGOTIABLE INVARIANTS

- Passed gates are *revalidated*, never trusted
- Retry exhaustion is terminal
- Overrides increase scrutiny, never reduce it
- Silence is always an acceptable output

This section supersedes any conflicting implementation detail.

## Status

This artifact is operational.
It has a single purpose: **decide whether language is allowed to exist**.

If the answer cannot be defended, it does not ship.
## GATE CONTEXT, DEPENDENCIES, AND REVALIDATION RULES (LOCKED)

This section defines how gates interact across regeneration, time, and overrides.
No gate may weaken or reinterpret these rules.

---

## 9. BASELINE REFERENCE MODEL (AUTHORITATIVE)

ABSTAIN baselines are defined as:

- **Primary:** Per-artifact-type median ABSTAIN rate
- **Secondary (diagnostic only):**
  - Global median
  - Per-operator median

Enforcement decisions MUST reference the per-artifact-type baseline.
Global and per-operator baselines exist only to surface anomalies.

---

## 10. GATE DEPENDENCY RULE (NO STALE ASSUMPTIONS)

If Gate k consumes outputs from Gate j (j < k):

- Any regeneration affecting Gate j outputs INVALIDATES Gate k
- Gate k MUST be fully re-executed, not merely revalidated

Example:
- Budget Gate changes $5M → $3M
- Legal Gate must re-run compliance checks for $3M
- Cached approvals are forbidden

---

## 11. CONTEXT FREEZING (DETERMINISM)

Each artifact evaluation operates under a **frozen context snapshot**:

- Policy versions
- Schemas
- Reference documents
- External data sources

Rules:
- Context snapshot is captured at first gate entry
- All revalidations use the same snapshot
- Context changes require a NEW artifact evaluation

This prevents time-based nondeterminism.

---

## 12. REVALIDATION VS RETRY (CRITICAL)

Revalidation after regeneration is NOT free.

Rules:
- If revalidation fails, it consumes retry budget
- If retry budget is exhausted, failure is terminal
- There is no “automatic fail without charging”

Rationale:
Revalidation is a test of stability, not a courtesy check.

---

## 13. CIRCULAR DEPENDENCY TERMINATION

Circular regeneration loops are explicitly bounded.

Rules:
- Per-gate retry budgets apply
- Additionally, each artifact has a **global regeneration cap**
  (default: 2 × total gate count)

If the global cap is reached:
- Artifact enters permanent ABSTAIN
- No further regeneration is permitted

This guarantees termination.

---

## 14. OVERRIDE PROPAGATION SEMANTICS

Overrides are **sticky and propagating**.

Rules:
- Any FORCE_PASS at Gate k marks the artifact as FORCE_PASS
- The flag persists through all downstream gates
- Downstream gates may still fail or override independently

Final artifact status may be:
- CLEAN (no overrides)
- OVERRIDDEN (one or more gates)

No override is ever hidden or erased.

---

## 15. FINAL INVARIANTS (NON-NEGOTIABLE)

- No gate may rely on stale upstream outputs
- No gate may use live context during revalidation
- Retry exhaustion is terminal
- Overrides increase scrutiny; they never reduce it
- Termination is guaranteed

This section is authoritative and supersedes local implementations.
## 16. GLOBAL REGENERATION CAP (DEFAULT + RATIONALE)

Default global regeneration cap = 2 × gate_count.

This value is a **heuristic default**, not an empirical constant.
Rationale: it permits (a) one full forward pass plus (b) one full corrective pass across the pipeline,
while preventing “bounce loops” between coupled gates.

Requirements:
- The cap MUST be configurable per artifact type.
- The cap MUST be recorded in the artifact’s context snapshot metadata.

---

## 17. OVERRIDE SPECIFICITY (REQUIRED FOR AUDIT)

Overrides MUST be recorded with:
- gate_id
- check_id (optional if gate is single-check)
- override_reason_code
- operator_id (or system actor)
- timestamp
- justification_text (min length enforced)

Final artifact MUST expose:
- overall_status: CLEAN | OVERRIDDEN | FAILED
- override_list: [ {gate_id, check_id?, reason_code, operator_id, timestamp} ... ]

If Gate 2 is FORCE_PASS and Gate 3 fails normally:
- artifact status = FAILED
- override_list includes Gate 2 entry
- failure_list includes Gate 3 failure entry
Nothing is collapsed into a generic “OVERRIDDEN” flag.

---

## 18. GATE VERSION REVOCATION (KILL SWITCH)

Every gate execution MUST record gate_id + gate_version in the artifact.

A Gate Version Revocation List (GVRL) exists:
- Entries: {gate_id, gate_version, revoked_at, severity, reason_code}

Trust evaluation rule:
- If any artifact references a revoked {gate_id, gate_version} → artifact status becomes REVOKED_TRUST
  (distinct from FAILED; it means “was validated by a now-invalid validator”).

Optional enforcement modes:
- HARD: REVOKED_TRUST blocks all downstream use automatically
- SOFT: REVOKED_TRUST warns and requires override to proceed

Revalidation protocol:
- Revalidation is performed only by creating a NEW evaluation run under a new context snapshot.
- Prior artifacts are not mutated; they are superseded by lineage.

---

## 19. CONTEXT SNAPSHOT MANIFEST (REPRODUCIBILITY REQUIREMENT)

Each artifact MUST carry a context_manifest, hashed and committed:

context_manifest = {
  artifact_type,
  gate_order_version,
  gates: [ {gate_id, gate_version, config_hash} ... ],
  references: [ {name, version, content_hash} ... ],
  schemas: [ {name, version, content_hash} ... ],
  external_sources: [ {name, version_or_timestamp, content_hash_or_query_hash} ... ],
  global_regen_cap,
  per_gate_retry_budgets
}

context_snapshot_id = SHA256(canonical_json(context_manifest))

audit_hash preimage MUST include:
- input_fingerprint
- context_snapshot_id
- per-gate results (pass/fail/abstain)
- override_list + failure_list
- core output metrics

Without context_snapshot_id in the commitment, “same input → same hash” is not guaranteed.

---

## 20. DELIBERATE REVALIDATION AGAINST NEW RULES (LINEAGE)

Revalidating against updated rules is done by issuing a NEW artifact evaluation:
- same inputs (or a declared input_delta)
- new context_snapshot_id

Lineage fields (required):
- artifact_id
- parent_artifact_id (nullable)
- lineage_reason: POLICY_UPDATE | GATE_UPDATE | BUG_REVOCATION | OPERATOR_REQUEST
- supersedes: [artifact_id ...] (optional)

Supersession semantics:
- “superseded” does not delete or invalidate history
- it indicates “preferred current evaluation under newer context”

---

## 21. PARTIAL CONTEXT UPDATES (MODEL)

Model = component-wise versioning with an atomic manifest.

Meaning:
- individual components (policy, legal refs, schemas, data source definitions) have their own versions/hashes
- any change to any component produces a NEW context_snapshot_id
- snapshots are atomic at the manifest level

This preserves granular provenance without allowing mixed “live” context during a run.

---

## 22. GATE ORDERING CHANGES (MIGRATION PROTOCOL)

Gate order is immutable per artifact_type + gate_order_version.

Changing order requires:
- new gate_order_version
- new context_snapshot_id
- new evaluation run (lineage parent points to prior artifact)

No artifact is silently “migrated” in place.

---

## 23. OVERRIDE GRANULARITY (CHECK-LEVEL OVERRIDES)

Gates with multiple checks MUST expose stable check_id values.

Override may target:
- entire gate (gate-level override)
- specific check_id (check-level override)

The smallest override scope MUST be preferred.

Final artifact must therefore support:
override_list entries with optional check_id:
- OVERRIDDEN: Legal.StateLaw42
- without implying OVERRIDDEN: Legal (entire gate)
