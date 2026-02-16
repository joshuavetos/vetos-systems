import numpy as np
import scipy.stats as stats

np.random.seed(42)

# =========================================
# REGISTRY CONFIG (Domain Adapter Mock)
# =========================================
registry = {
    "domain": "ai_frontier",
    "H_ceiling": 1e12,
    "L_abs": 0.5,
    "min_bond_floor": 10e6,
    "registry_bond": 200e6,
    "bias_factor": 0.7  # <1 = permissive registry underestimates risk
}

# =========================================
# SYNTHETIC DOMAIN SETUP
# =========================================
N = 5000
n_classes = 20
action_class = np.random.randint(0, n_classes, N)
P_true_class = np.random.uniform(0.01, 0.1, n_classes)
P_registry_class = P_true_class * registry["bias_factor"]

# =========================================
# LEVERAGE (Additive + Interaction + Percentile OR Absolute)
# =========================================
reach = np.random.rand(N)
impact = np.random.rand(N)
irrev = np.random.rand(N)
centrality = np.random.rand(N)

interaction_bonus = np.maximum(reach * impact, irrev * centrality)
leverage_raw = 0.25 * (reach + impact + irrev + centrality) + interaction_bonus

leverage_percentile = stats.rankdata(leverage_raw) / N
class_a = (leverage_percentile >= 0.99) | (leverage_raw >= registry["L_abs"])

# =========================================
# CLASS-LEVEL HISTORICAL ANALOGS
# =========================================
hist_k = np.random.binomial(50, P_registry_class)
hist_n = np.full(n_classes, 50)

def clopper_pearson(k, n, alpha=0.05):
    return stats.beta.ppf(1 - alpha, k + 1, n - k)

P_adv_class = np.array([
    np.percentile([
        clopper_pearson(hist_k[c], hist_n[c]),
        min(1.0, hist_k[c]/hist_n[c] * 1.4), 
        min(1.0, 0.5 * (hist_k[c]/hist_n[c]) + 0.02)
    ], 75) for c in range(n_classes)
])

P_actor = np.random.uniform(0.01, 0.1, N)
P_req = np.maximum(P_actor, P_adv_class[action_class])

# =========================================
# BOND CALCULATION
# =========================================
m = 1.0
bond = registry["L_abs"] * P_req * registry["H_ceiling"] * m
bond = np.maximum(bond, registry["min_bond_floor"])
bond_required = np.where(class_a, bond, 0)

# =========================================
# OUTCOME SIMULATION (True vs Registry)
# =========================================
P_true = P_true_class[action_class]
realized_events = np.random.binomial(1, P_true)

realized_DCG = np.mean(realized_events) * registry["H_ceiling"]
expected_DCG = np.mean(P_req) * registry["H_ceiling"]

delta_DCG = abs(realized_DCG - expected_DCG)
fitness = 1 - delta_DCG / registry["H_ceiling"]

slash_rate = max(0, 0.1 * delta_DCG / registry["H_ceiling"])
registry_slash = slash_rate * registry["registry_bond"]

# =========================================
# OUTPUT
# =========================================
if __name__ == "__main__":
    print("---- Governance Stress Cycle ----")
    print(f"Total Actions: {N}")
    print(f"Class A Actions: {np.sum(class_a)}")
    print(f"Average Bond (Class A): ${np.mean(bond_required[class_a]):,.0f}")
    print(f"Expected DCG (Registry Model): ${expected_DCG:,.0f}")
    print(f"Realized DCG (True Model): ${realized_DCG:,.0f}")
    print(f"DCG Divergence: ${delta_DCG:,.0f}")
    print(f"Registry Fitness: {fitness:.3f}")
    print(f"Registry Slash: ${registry_slash:,.0f}")

