import numpy as np
from enum import Enum
from dataclasses import dataclass
from typing import Dict

class SafetyState(Enum):
    NOMINAL = "nominal"
    ANOMALY = "anomaly"
    CRITICAL = "critical"

@dataclass
class SensorReceipt:
    turbine_id: str
    vibration: float
    temperature: float
    predicted_ttf: float
    safety_state: SafetyState
    action_allowed: bool

class IndustrialGuard:
    def __init__(self):
        self.nominal_vib = (0.1, 0.3)
        self.nominal_temp = (80, 120)

    def assess_safety(self, sensors: Dict) -> SensorReceipt:
        vib, temp = sensors["vibration"], sensors["temperature"]
        vib_z = (vib - self.nominal_vib[0]) / (self.nominal_vib[1] - self.nominal_vib[0])
        temp_z = (temp - self.nominal_temp[0]) / (self.nominal_temp[1] - self.nominal_temp[0])
        anomaly_score = max(vib_z, temp_z)
        ttf = max(0.0, 48.0 - anomaly_score * 12.0)
        state = SafetyState.NOMINAL if ttf > 24 else SafetyState.CRITICAL
        action_allowed = ttf > 8
        return SensorReceipt(
            turbine_id=sensors["turbine_id"],
            vibration=float(vib),
            temperature=float(temp),
            predicted_ttf=float(ttf),
            safety_state=state,
            action_allowed=bool(action_allowed)
        )
