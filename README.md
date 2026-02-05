# Engineering Log & Technical Artifacts

This repository is a record of my approach to system design, problem-solving, and the integration of probabilistic tools into deterministic workflows.

### Operational Posture
I focus on **AI/ML System Design** with an emphasis on **Epistemic Integrity**. My workflow utilizes Large Language Models (LLMs) as high-bandwidth collaborators for stress-testing and rapid prototyping, while maintaining a strict boundary between generated hypotheses and validated code.

* **Fail-Closed Design:** Systems are architected to refuse output by default if grounding or confidence thresholds are not met.
* **Radical Simplicity:** I prioritize solutions where the technical overhead is lower than the problem’s complexity. 
* **Adversarial Validation:** Every AI-assisted solution is treated as a hostile input until it passes deterministic validation layers.

### Evaluation Criteria
For those auditing this repository for professional collaboration, these projects demonstrate:
1. **Problem Framing:** Stripping complex requirements to a testable core.
2. **Tool Skepticism:** Identifying exactly where probabilistic tools fail and building the guardrails to contain them.
3. **Architectural Discipline:** The willingness to discard over-engineered or fragile solutions in favor of stability.

---

### Technical Artifacts
* **[Municipal Budget Audit Pipeline](./tools/funding-analysis):** A financial auditor using Modified Z-Score (MAD) statistics and Pydantic schema enforcement to identify capital risk.
* **[AI Failure Gates](./ai-failure-gates):** Behavioral rules and deterministic wrappers for preventing hallucination leakage in LLM outputs.
