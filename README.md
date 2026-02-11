<img width="1536" height="1024" alt="80B1F0DD-9449-40A3-9FA6-F348CB351E3E" src="https://github.com/user-attachments/assets/3205e20d-28a9-4c93-9b32-e56715847778" />

# Vetos Systems: The Fail-Closed Governance Stack

**A repository documenting how complex AI and industrial systems are audited, constrained, and deliberately halted when certainty is insufficient.**

---

## 🛠 Philosophy: Reliability Over Appearance

In high-consequence environments—banking, energy, and defense—failure is not just a bug; it is a structural risk. This repository is built on three non-negotiable invariants:

1. **Fail-Closed by Design:** Systems must move to a safe state (Halt) rather than degrading silently or hallucinating.
2. **Auditable Lineage:** Every actuation must emit a cryptographically verifiable receipt.
3. **Epistemic Modesty:** If a system cannot prove its input is valid or its confidence is sufficient, it is forbidden from acting.

---

## 🏗 Core Governance & Reliability Stack

The following artifacts, located in `work-samples/core-governance-stack/`, demonstrate specific solutions to critical failure modes:

| Component | Failure Mode Solution | Mechanism |
| :--- | :--- | :--- |
| **`guardrail_engine.py`** | Probabilistic Refusal | Uses Softmax confidence thresholds to block low-certainty AI inference. |
| **`audit_pipeline.py`** | Immutable Data Lineage | A SQLite-backed ledger that generates cryptographic receipts for ETL steps. |
| **`bounded_agent.py`** | Policy-Enforced Actuation | A policy layer that intercepts and validates tool-calls before execution. |
| **`rap_kernel.py`** | Systemic Risk Bonding | Implements Action-Scoped Bonding to internalize the cost of failure. |
| **`concur_guard.py`** | Deterministic Financial Gating | A hash-chained ledger to block duplicate or unauthorized financial actions. |
| **`drift_monitor.py`** | Statistical Health Validation | Uses Kolmogorov-Smirnov tests to quarantine models exhibiting drift. |
| **`industrial_guard.py`** | OT / Automation Safety | A deterministic state machine for predictive maintenance in industrial OT. |
| **`stress_cycle_v3.py`** | Mechanism Design Testing | Full-cycle stress testing of risk allocation kernels using ensemble models. |

---

## 📈 Specialized Tooling: Institutional Macro Engine

Located in `tools/macro_engine_v2.py`, this engine is an institutional-grade risk monitor designed to bridge macroeconomic data with portfolio safety.

- **GARCH(1,1) Volatility Surface:** Identifies clustering of variance to distinguish noise from structural shifts.
- **High-Frequency Net Liquidity:** Monitors the "Systemic Oxygen" (Fed Assets - TGA - RRP) to identify lead-time drawdowns.
- **The Quarantine Gate:** A hard-coded "Veto" logic that halts rebalancing if liquidity drains or volatility surface spikes.

---

## 🚫 What This Repository Is Not

This is **not** a showcase of "AI magic," prompt engineering, or leaderboard-chasing benchmarks. This is a working record of **Constraint Enforcement**. It documents the defensive architecture required to make autonomous systems safe for real-world deployment.

---
**Maintained by Joshua Scott Vetos | 2026**
