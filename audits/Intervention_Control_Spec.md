<img width="1024" height="559" alt="CCEB8AE0-749C-4DD8-A59E-0907B1558C6C" src="https://github.com/user-attachments/assets/6f18be9f-428a-4ea0-87ff-a9d67901478f" />

# Intervention Control Spec v1.0

Common Schema Across Domains  
All interventions follow this fixed control loop. Variables are per-cohort (N=10k claims/approvals) over 30-day windows. Computable from standard logs: approvals/denials, appeals_filed, overturns, budget_delta, downstream_reversals.

VARIABLES (per cohort-month):
cost_FN = (denials * avg_user_delay_cost) + eligible_nonparticipants * unit_cost
cost_FP = (approvals_reversed * avg_inst_recover_cost) + fraud_delta
Δbudget = (new_approvals * unit_payout) - clawbacks
FP_rate = reversals / approvals
headroom = (budget_quarterly / 4) - current_burn

Core Adjustment Rules
IF FN_proxy > 1.2 * baseline AND FP_rate < 0.12 AND Δbudget < 0.15*headroom
  → relax δ by 0.1 (threshold down / appeal preload +10%)
ELSE IF FP_rate > 0.15 OR Δbudget > 0.20*headroom
  → ROLLBACK δ to baseline (auto-revert in 7 days)
ELSE IF appeals_filed / denials > 0.4
  → pivot to Proxy Augmentation (no threshold change)

Kill-Switches (Immediate Revert)
1. FP_rate > 0.20
2. Δbudget > 0.25*headroom
3. appeals_backlog > 60 days
4. downstream_harm_proxy > 1.5*baseline (domain-specific: defaults/mortality/churn)

Domain-Specific Caps Table

| Domain | Baseline Denial % | Max δ Relax | FN Cost Unit | FP Cost Unit | Headroom Cap | Rollback Trigger |
|--------|-------------------|-------------|--------------|--------------|--------------|------------------|
| SSDI | 65% | +8% approvals | $2k/month income | $5k overpayment | 10% quarterly | ALJ overturn >55% (verify via GAO / SSA) |
| NHS Referral | 75% specialist block | +12% referrals | 6% survival drop | £200/visit | 8% budget | wait_time >18 weeks |
| Mortgage | 15% | +4% approvals | $50k opportunity | 2% default loss | 5% capital | default_rate >3% (verify via HMDA/FFIEC) |
| College Admissions | 90% | +5% admits | $200k lifetime | $40k dropout cost | 7% endowment | yield <65% (verify via IPEDS/NCES) |
| UI Claims | 40% | +10% payments | $1.5k/week gap | $2k fraud | 12% fund | improper_payment >9% (verify via DOL UI Integrity) |

Control Loop (Weekly Execution)

INPUTS  ← {approvals, denials, appeals_filed, overturns, reversals, budget_burn}
COMPUTE ← {FN_proxy = (overturns/denials) + nonparticipants_est; FP_proxy = reversals/approvals}
CHECK   ← kill-switches ? ROLLBACK : adjustment_rules ? Δδ : HOLD
LOG     ← {timestamp, cohort_N, pre/post metrics, action_taken}

Operational Notes
- Strong Evidence: Caps derived from gov audit baselines (SSDI/UI) and systematic reviews (NHS).
- Speculative: Exact nonparticipants_est requires sampling; yield/harm proxies observational.
- Falsifiable: All vars extractable from HMDA/IPEDS/DOL/GAO public datasets.
- No Blowup: Denial floor = baseline - max_δ preserves ≥85% scarcity.

Sources
[1] Gatekeeping or Provider Choice for Sustainable Health Systems? A ... https://pmc.ncbi.nlm.nih.gov/articles/PMC11677736/
