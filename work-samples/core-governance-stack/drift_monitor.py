import numpy as np
from scipy import stats
from typing import Dict

class DriftMonitor:
    def __init__(self):
        self.baseline_dist = np.random.normal(0, 1, 10000)

    def ks_test(self, new_data: np.ndarray) -> float:
        return float(stats.ks_2samp(self.baseline_dist, new_data).pvalue)

    def brier_score(self, probs: np.ndarray, outcomes: np.ndarray) -> float:
        return float(np.mean((probs - outcomes) ** 2))

    def health_status(self, new_data: np.ndarray, probs: np.ndarray, outcomes: np.ndarray) -> Dict:
        ks_p = self.ks_test(new_data)
        brier = self.brier_score(probs, outcomes)
        status = "HEALTHY" if ks_p > 0.01 and brier < 0.1 else "QUARANTINE"
        return {
            "ks_pvalue": ks_p,
            "brier_score": brier,
            "status": status,
            "action": "HALT" if status == "QUARANTINE" else "CONTINUE"
        }
