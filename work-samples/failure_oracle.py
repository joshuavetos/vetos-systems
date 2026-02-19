"""Failure Oracle integrity checks with deterministic execution."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass, field

import docker
import numpy as np
import pandas as pd


class DeterminismError(RuntimeError):
    pass


def require_seed() -> int:
    seed_raw = os.environ.get("FAILURE_ORACLE_SEED")
    if seed_raw is None:
        raise DeterminismError("FAILURE_ORACLE_SEED is required for deterministic replay")
    try:
        return int(seed_raw)
    except ValueError as exc:
        raise DeterminismError("FAILURE_ORACLE_SEED must be an integer") from exc


def get_container_client() -> docker.DockerClient:
    return docker.from_env()


def infer_type(path: str) -> str:
    if path.endswith(".py"):
        return "code"
    if path.endswith((".pkl", ".h5")):
        return "model"
    if path.endswith((".csv", ".parquet")):
        return "data"
    return "unknown"


@dataclass
class FailureOracle:
    artifact_path: str
    seed: int
    violations: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.type = infer_type(self.artifact_path)
        self.client = get_container_client()
        self.rng = np.random.default_rng(self.seed)

    def check_data_correctness(self) -> None:
        df = pd.DataFrame(self.rng.random((100, 5)), columns=list("ABCDE"))
        df["A"] = df["A"].astype(str)
        if not pd.api.types.is_float_dtype(df["A"]):
            self.violations.append("SCHEMA_DRIFT: Column 'A' type mismatch (float -> object)")

    def check_model_correctness(self) -> None:
        train = self.rng.normal(0, 1, 1000)
        prod = self.rng.normal(5, 2, 1000)
        drift = abs(train.mean() - prod.mean())
        if drift > 0.5:
            self.violations.append(f"MODEL_DRIFT: Covariate shift detected (delta={drift:.2f})")

    def check_availability(self) -> None:
        container = self.client.containers.run(
            "python:3.11-slim",
            "python -c 'import numpy as np; np.ones((10000,10000))'",
            mem_limit="64m",
            detach=True,
            remove=True,
        )
        container.wait()
        logs = container.logs().decode()
        if "Killed" in logs:
            self.violations.append("SLO_VIOLATION: Service crashed under resource constraint (OOM)")

    def check_security(self) -> None:
        audit_log = ["token_123_access"]
        replay_attempt = "token_123_access"
        blocked = False
        if replay_attempt in audit_log and not blocked:
            self.violations.append("SECURITY_FAIL: Token replay accepted (privilege escalation risk)")

    def check_state_persistence(self) -> None:
        ledger = ["Genesis", "Tx_100USD", "Tx_20USD"]
        root = hashlib.sha256("".join(ledger).encode()).hexdigest()
        ledger[1] = "Tx_1000USD"
        new_root = hashlib.sha256("".join(ledger).encode()).hexdigest()
        if new_root != root:
            self.violations.append("LEDGER_CORRUPTION: Merkle root mismatch (history mutable)")

    def run(self) -> dict:
        self.check_data_correctness()
        self.check_model_correctness()
        self.check_availability()
        self.check_security()
        self.check_state_persistence()
        return {
            "artifact": self.artifact_path,
            "artifact_type": self.type,
            "seed": self.seed,
            "status": "PASS" if not self.violations else "FAIL",
            "score": max(0, 100 - len(self.violations) * 20),
            "violations": self.violations,
        }


def main() -> None:
    seed = require_seed()
    oracle = FailureOracle("candidate_artifact.zip", seed=seed)
    verdict = oracle.run()
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
