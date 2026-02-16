# ================================
# FULL RAP KERNEL STRESS HARNESS
# ================================
import numpy as np
from scipy import stats

np.random.seed(42)

# -------------------------------
# CONFIG
# -------------------------------
N_ACTIONS = 500
N_CYCLES = 20
H_CEILING = 1e9
BASE_REGISTRY_BOND = 100_000_000
MIN_REGISTRY_BOND = 10_000_000

# -------------------------------
# REGISTRIES
# -------------------------------
registries = {
    "conservative": {
        "bias": 1.2,  # overestimates risk
        "L_abs": 0.6,
        "bond": BASE_REGISTRY_BOND,
        "fitness": 1.0
    },
    "permissive": {
        "bias": 0.7,  # underestimates risk
        "L_abs": 0.6,
        "bond": BASE_REGISTRY_BOND,
        "fitness": 1.0
    }
}

# -------------------------------
# UTILS
# -------------------------------
def leverage_score(reach, impact, irrev, centrality):
    interaction = np.maximum(reach * impact, irrev * centrality)
    return 0.25 * (reach + impact + irrev + centrality) + interaction

def ensemble_p_adv(p_base):
    cp = p_base
    evt = np.minimum(1.0, cp * 1.4)
    bayes = np.minimum(1.0, 0.5 * cp + 0.02)
    return np.percentile([cp, evt, bayes], 75)

def compute_class_a(leverage_raw, L_abs):
    percentile = stats.rankdata(leverage_raw) / len(leverage_raw)
    return (percentile >= 0.99) | (leverage_raw >= L_abs), percentile

def brier_score(p, o):
    return np.mean((p - o) ** 2)

# -------------------------------
# SIMULATION LOOP
# -------------------------------
for cycle in range(N_CYCLES):
    # Simulate drift in leverage distribution
    reach = np.clip(np.random.beta(2, 5, N_ACTIONS) + 0.02 * cycle, 0, 1)
    impact = np.random.beta(2, 2, N_ACTIONS)
    irrev = np.random.beta(2, 2, N_ACTIONS)
    centrality = np.random.beta(2, 2, N_ACTIONS)

    lev_raw = leverage_score(reach, impact, irrev, centrality)

    # Actor declared probabilities
    P_actor = np.random.uniform(0.01, 0.1, N_ACTIONS)

    # Registry competition
    registry_results = {}
    for name, reg in registries.items():
        # True underlying probability (independent from registry model)
        P_true = np.clip(P_actor * np.random.uniform(0.8, 1.2, N_ACTIONS), 0, 1)

        # Registry-estimated adversarial probability
        P_adv = ensemble_p_adv(P_actor) * reg["bias"]
        P_req = np.maximum(P_actor, P_adv)

        # Class A detection
        class_a, percentile = compute_class_a(lev_raw, reg["L_abs"])

        # Bond calculation
        bonds = reg["L_abs"] * P_req * H_CEILING
        bonds[class_a == False] = 0

        # Realized outcomes
        realized = np.random.binomial(1, P_true)
        DCG_expected = np.mean(P_req * H_CEILING)
        DCG_realized = np.mean(realized * H_CEILING)

        divergence = abs(DCG_realized - DCG_expected) / H_CEILING

        # Registry fitness update
        fitness = 1 - divergence
        slash_rate = max(0, 0.15 * divergence)
        slash_amount = slash_rate * reg["bond"]

        reg["bond"] = max(MIN_REGISTRY_BOND, reg["bond"] - slash_amount)
        reg["fitness"] = fitness

        # Calibration (Brier)
        bs = brier_score(P_req, realized)

        registry_results[name] = {
            "class_a_count": np.sum(class_a),
            "mean_bond": np.mean(bonds),
            "DCG_expected": DCG_expected,
            "DCG_realized": DCG_realized,
            "divergence": divergence,
            "fitness": fitness,
            "registry_bond": reg["bond"],
            "brier": bs
        }

    # Capital flight: actors shift toward higher fitness registry
    if registries["permissive"]["fitness"] < registries["conservative"]["fitness"]:
        registries["permissive"]["bond"] *= 0.98
        registries["conservative"]["bond"] *= 1.01
    else:
        registries["conservative"]["bond"] *= 0.98
        registries["permissive"]["bond"] *= 1.01

    # Print cycle summary
    print(f"\n=== CYCLE {cycle+1} ===")
    for name, res in registry_results.items():
        print(f"\nRegistry: {name}")
        print(f"  Class A count: {res['class_a_count']}")
        print(f"  Mean bond: {res['mean_bond']:.2f}")
        print(f"  Divergence: {res['divergence']:.4f}")
        print(f"  Fitness: {res['fitness']:.4f}")
        print(f"  Registry Bond: {res['registry_bond']:.2f}")
        print(f"  Brier Score: {res['brier']:.4f}")

print("\n=== FINAL REGISTRY STATES ===")
for name, reg in registries.items():
    print(f"{name}: bond={reg['bond']:.2f}, fitness={reg['fitness']:.4f}")

