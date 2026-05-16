"""
Fail-Closed Decision Gate
Deterministic, portable, zero-LLM.

Decisions:
- BLOCK     : no evidence OR zero supported claims
- ESCALATE  : supported claims exist but support < MIN_SUPPORT
- ALLOW     : supported claims >= MIN_SUPPORT
"""

from enum import Enum
from typing import List, Dict, Any
from dataclasses import dataclass
from pathlib import Path
import json
import uuid


class Decision(Enum):
    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


@dataclass
class GateResult:
    decision: Decision
    reasons: List[str]
    meta: Dict[str, Any]
    trace_id: str


class VerificationGate:
    def __init__(self, min_support: int = 2):
        self.min_support = min_support
        self.trace_id = uuid.uuid4().hex[:8]
        self.traces_dir = Path("traces")
        self.traces_dir.mkdir(exist_ok=True)


    def verify(self, output: str, evidence: List[Dict[str, Any]]) -> GateResult:
        trace_file = self.traces_dir / f"{self.trace_id}.jsonl"

        # Invariant 1: no evidence
        if not evidence or not all(e.get("content", "").strip() for e in evidence):
            result = GateResult(
                Decision.BLOCK,
                ["No valid evidence"],
                {},
                self.trace_id
            )
            self._log(trace_file, "evidence_check", result)
            return result

        claims = self._extract_claims(output)
        support = self._support_counts(claims, evidence)

        supported = {c: n for c, n in support.items() if n > 0}

        # Invariant 2: zero supported claims
        if not supported:
            result = GateResult(
                Decision.BLOCK,
                ["No claims supported by evidence"],
                {"supports": support},
                self.trace_id
            )
            self._log(trace_file, "alignment_fail", result)
            return result

        min_support = min(supported.values())

        # Invariant 3: weak support
        if min_support < self.min_support:
            result = GateResult(
                Decision.ESCALATE,
                [f"Insufficient support ({min_support}/{self.min_support})"],
                {"supports": support},
                self.trace_id
            )
            self._log(trace_file, "threshold_check", result)
            return result

        result = GateResult(
            Decision.ALLOW,
            ["All checks passed"],
            {"supports": support},
            self.trace_id
        )
        self._log(trace_file, "final", result)
        return result


    def _extract_claims(self, text: str) -> List[str]:
        sentences = [s.strip() for s in text.split(".") if len(s.strip()) > 5]
        verbs = {"is", "are", "was", "were", "has", "have", "shows", "indicates"}
        return [
            s for s in sentences
            if any(v in s.lower().split() for v in verbs)
        ]


    def _support_counts(
        self,
        claims: List[str],
        evidence: List[Dict[str, Any]]
    ) -> Dict[str, int]:
        counts = {}
        for claim in claims:
            counts[claim] = sum(
                claim.lower() in e["content"].lower()
                for e in evidence
            )
        return counts


    def _log(self, path: Path, step: str, result: GateResult) -> None:
        record = {
            "trace_id": result.trace_id,
            "step": step,
            "decision": result.decision.value,
            "reasons": result.reasons,
            "meta": result.meta,
        }
        with open(path, "a") as f:
            f.write(json.dumps(record) + "\n")
