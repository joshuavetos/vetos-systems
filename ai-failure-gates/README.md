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

## Status

This artifact is operational.
It has a single purpose: **decide whether language is allowed to exist**.

If the answer cannot be defended, it does not ship.
