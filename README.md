# Human–AI Leverage: Failure-First Portfolio

This repository is **not a demo reel**.  
It is a **laboratory notebook** proving operational competence in human–AI leverage.

Real competence is demonstrated only when systems:
- fail visibly,
- log those failures,
- repair them using AI tools,
- and quantify improvement with calibrated metrics.

Any artifact that does not expose baselines, breakdowns, and verification is considered **incomplete by design**.

---

## What This Repo Proves (and What It Does Not)

**This repo proves:**
- Mastery of AI-augmented cognition (LLMs, search, code execution, multimodality)
- Systematic handling of ambiguity, uncertainty, and failure
- Tool orchestration across multiple steps and models
- Verification, calibration, and adversarial self-critique

**This repo does NOT attempt to prove:**
- Custom model training
- Benchmark leaderboard performance
- Production deployment resilience (only simulated proxies)

Static repositories cannot prove runtime emergence; this repo uses falsifiable proxies where necessary.

---

## Evaluation Standard (Non-Negotiable)

All domains follow the same epistemic sequence:

**Baseline Failure → Tool Augmentation → Adversarial Critique → Repair → Calibration**

Any artifact skipping a stage is invalid.

---

## Competency Domains

| Domain | Real Competence | Fake / Shallow | Minimum Required Artifacts | Static Repo Viable |
|------|---------------|----------------|----------------------------|-------------------|
| Rapid Knowledge Synthesis | Resolve contradictions across 50+ sources with gaps flagged | Unverified summaries | Query logs, source diffs, resolution tables, uncertainty scores | Yes |
| Multi-Step Tool Orchestration | ≥80% success on 20 seeded tasks chaining ≥5 tools | One-off screenshots | Runnable scripts, JSON traces, task suites | Yes |
| Adversarial Querying | <10% attack success after mitigation on 100+ prompts | Happy-path safety demos | Red-team YAML, ASR tables, mitigation diffs | Yes |
| Mechanistic Reasoning | ≥90% fidelity causal edits (open models) | Chain-of-thought only | Edit scripts, pre/post tests, circuit proxies | Partial |
| Temporal / Multiscale Reasoning | ≥20% improvement over baseline under drift | Static reasoning | Drift simulations, trajectory logs | Yes |
| Multimodal Synthesis | ≥95% inconsistency detection across modalities | Isolated captions | Fusion pipelines, failure galleries | Yes |
| Code Generation & Debugging | ≥90% test pass on ≥1k LOC | Toy scripts | Git-annotated diffs, pytest suites | Yes |
| Epistemic Auditing | Brier score <0.15 on held-out queries | Unqualified answers | Calibration plots, plated outputs | Yes |

If any domain lacks its minimum artifacts, **competence is not demonstrated**.

---

## Canonical Failure-First Artifact

All work in this repo must reduce to the following pattern.

Reference notebook:  
`/reference/failure_first_template.ipynb`

### Example Task
> Quantify 2025 AI hiring shifts, predict 2026 trends, and flag risks using public data.

```python
# Step 1 — Naive Attempt (Expected Failure)
output = llm("Summarize 2025 AI hiring trends.")
log = {"failure": "unsourced claims", "confidence": 1.0}
baseline_accuracy = 0.2

# Step 2 — Failure Analysis
issues = ["no verification", "recency bias", "no quantification"]

# Step 3 — Tool Chain
data = search(...) + code_exec(...)
output2 = llm.synthesis(data)
log = {"failure": "outlier sensitivity"}

# Step 4 — Adversarial Critique
critic = llm("Attack this analysis.")
mitigations = ["drift tests", "cross-model check"]

# Step 5 — Repair via Orchestration
agent = ToolChain([...], retries=3)
final = agent.run(task)

# Step 6 — Calibration
brier = compute_brier(final.confidence, ground_truth)
---

## Closing Note

This repository documents ways of thinking with AI, not finished answers.

Artifacts may be rough, incomplete, or exploratory by design. The focus is on testing ideas, exposing failure, and revising assumptions when reality disagrees.

Structure varies because problems vary. Rigor, curiosity, and verification are the through-line.

This is not a catalog of conclusions, but a record of how understanding was pursued.
