import numpy as np
from dataclasses import dataclass
from typing import Dict
import hashlib

@dataclass
class RAPReceipt:
    action_id: str
    leverage_raw: float
    leverage_percentile: float
    class_a: bool
    p_req: float
    bond_usd: float
    registry_hash: str

class RAPKernel:
    def __init__(self, registry: Dict):
        self.registry = registry

    def score_leverage(self, reach: float, impact: float, irrev: float, centrality: float) -> Dict:
        interaction = max(reach * impact, irrev * centrality)
        leverage_raw = 0.25 * (reach + impact + irrev + centrality) + interaction
        return {"raw": leverage_raw, "percentile": 0.99}

    def compute_p_adv(self, action_class: int) -> float:
        cp = 0.06
        evt = min(1.0, cp * 1.4)
        bayes = min(1.0, 0.5 * cp + 0.02)
        return float(np.percentile([cp, evt, bayes], 75))

    def emit_receipt(self, action: Dict) -> RAPReceipt:
        lev = self.score_leverage(**action["leverage_components"])
        class_a = (lev["percentile"] >= 0.99) or (lev["raw"] >= self.registry["L_abs"])
        p_adv = self.compute_p_adv(action["class_id"])
        p_req = max(action["p_actor"], p_adv)
        bond = self.registry["L_abs"] * p_req * self.registry["H_ceiling"]
        return RAPReceipt(
            action_id=hashlib.sha256(str(action).encode()).hexdigest(),
            leverage_raw=float(lev["raw"]),
            leverage_percentile=float(lev["percentile"]),
            class_a=bool(class_a),
            p_req=float(p_req),
            bond_usd=float(bond),
            registry_hash=str(self.registry["hash"])
        )
