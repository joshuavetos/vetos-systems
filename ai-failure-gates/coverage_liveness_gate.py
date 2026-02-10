#!/usr/bin/env python3
"""
Coverage Liveness Gate v1.0

STATUS: FROZEN
ROLE: SECURITY LIVENESS GATE

MODIFICATION RULE:
- This file MUST NOT be edited in place.
- Any change requires a new file, new gate name, and explicit version.
- This gate defines a binding security invariant.

INVARIANT:
A system is only ALIVE if it is capable of making evidence-backed decisions.
Loss of decision coverage is a system failure, not a performance issue.
"""

import hashlib
import time
from collections import defaultdict
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Dict, Any


# =========================
# Receipt
# =========================

@dataclass
class CoverageReceipt:
    receipt_type: str
    timestamp: str
    system_id: str
    status: str

    coverage_global_ready: float
    worst_segment_ready: float

    ready_ingested_total: int
    ready_scored_total: int

    total_ingested_all: int
    total_scored_all: int

    failed_ready_segments: Dict[str, float]
    quarantined_segments: Dict[str, Any]
    probation_segments: Dict[str, Any]

    reasons: list

    proof_hash: str
    receipt_id: str

    @staticmethod
    def generate(system_id: str, payload: Dict[str, Any]) -> "CoverageReceipt":
        ts = datetime.now(timezone.utc).isoformat()
        proof_src = f"{system_id}:{ts}:{payload['status']}:{payload['coverage_global_ready']:.6f}"
        proof_hash = hashlib.sha256(proof_src.encode()).hexdigest()
        receipt_id = hashlib.sha256(f"{proof_hash}:{ts}".encode()).hexdigest()[:16]

        return CoverageReceipt(
            receipt_type="DEGRADED",
            timestamp=ts,
            system_id=system_id,
            status=payload["status"],

            coverage_global_ready=payload["coverage_global_ready"],
            worst_segment_ready=payload["worst_segment_ready"],

            ready_ingested_total=payload["ready_ingested_total"],
            ready_scored_total=payload["ready_scored_total"],

            total_ingested_all=payload["total_ingested_all"],
            total_scored_all=payload["total_scored_all"],

            failed_ready_segments=payload["failed_ready_segments"],
            quarantined_segments=payload["quarantined_segments"],
            probation_segments=payload["probation_segments"],

            reasons=payload["reasons"],

            proof_hash=proof_hash,
            receipt_id=receipt_id,
        )


# =========================
# Gate
# =========================

class CoverageLivenessGate:
    def __init__(
        self,
        system_id: str,
        min_global_ready: float = 0.95,
        min_segment_ready: float = 0.90,
        min_segment_samples: int = 50,
        probation_samples: int = 150,
    ):
        self.system_id = system_id
        self.min_global_ready = min_global_ready
        self.min_segment_ready = min_segment_ready
        self.min_segment_samples = min_segment_samples
        self.probation_samples = probation_samples

        self.ingested = defaultdict(int)
        self.scored = defaultdict(int)

        self.quarantined = set()
        self.probation = defaultdict(lambda: {"ingested": 0, "scored": 0})

    # -------------------------

    def _segment_key(self, event: Dict[str, Any]) -> str:
        return f"{event.get('bin','unk')}/{event.get('geo','unk')}/{event.get('device','unk')}"

    # -------------------------

    def record_event(self, event: Dict[str, Any], scored: bool):
        seg = self._segment_key(event)

        self.ingested[seg] += 1
        if scored:
            self.scored[seg] += 1

        if seg in self.quarantined:
            self.probation[seg]["ingested"] += 1
            if scored:
                self.probation[seg]["scored"] += 1

            if self.probation[seg]["ingested"] >= self.probation_samples:
                ratio = self.probation[seg]["scored"] / self.probation[seg]["ingested"]
                if ratio >= self.min_segment_ready:
                    self.quarantined.remove(seg)
                    del self.probation[seg]

    # -------------------------

    def evaluate(self) -> Dict[str, Any]:
        total_ingested = sum(self.ingested.values())
        total_scored = sum(self.scored.values())

        ready_ingested = 0
        ready_scored = 0

        failed_ready = {}
        reasons = []

        for seg, count in self.ingested.items():
            scored = self.scored[seg]
            ratio = scored / count if count else 1.0

            if seg not in self.quarantined:
                ready_ingested += count
                ready_scored += scored

                if count >= self.min_segment_samples and ratio < self.min_segment_ready:
                    failed_ready[seg] = round(ratio, 6)

        coverage_ready = ready_scored / ready_ingested if ready_ingested else 1.0
        worst_ready = min(failed_ready.values()) if failed_ready else 1.0

        status = "ALIVE"

        if coverage_ready < self.min_global_ready:
            status = "DEGRADED"
            reasons.append(
                f"global_ready_coverage {coverage_ready:.4f} < {self.min_global_ready:.4f}"
            )

        if failed_ready:
            status = "DEGRADED"
            reasons.append(
                f"{len(failed_ready)} ready segments < {self.min_segment_ready:.2f} (pre-quarantine)"
            )

        if status == "DEGRADED":
            for seg in failed_ready:
                if seg not in self.quarantined:
                    self.quarantined.add(seg)

        payload = {
            "status": status,
            "coverage_global_ready": coverage_ready,
            "worst_segment_ready": worst_ready,
            "ready_ingested_total": ready_ingested,
            "ready_scored_total": ready_scored,
            "total_ingested_all": total_ingested,
            "total_scored_all": total_scored,
            "failed_ready_segments": failed_ready,
            "quarantined_segments": {s: True for s in self.quarantined},
            "probation_segments": {
                s: {
                    "prob_ingested": v["ingested"],
                    "prob_scored": v["scored"],
                    "prob_needed": self.probation_samples,
                }
                for s, v in self.probation.items()
            },
            "reasons": reasons,
        }

        if status == "DEGRADED":
            receipt = CoverageReceipt.generate(self.system_id, payload)
            return {"status": "DEGRADED", "receipt": asdict(receipt)}

        return {
            "status": "ALIVE",
            "coverage_global_ready": coverage_ready,
            "worst_segment_ready": worst_ready,
            "quarantined": len(self.quarantined),
        }
