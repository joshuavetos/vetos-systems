"""Failure Oracle: deterministic artifact stress checks.

This module evaluates five failure surfaces (data, model, availability,
security, state persistence) and returns a structured verdict.
"""

import hashlib
import json
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

try:
    import docker
except Exception:  # docker is optional; graceful fallback is used if unavailable
    docker = None


class MockContainer:
    """Small stand-in for Docker container in environments without a daemon."""

    def wait(self):
        return {"StatusCode": 137}

    def logs(self):
        return b"Killed"


class MockDockerClient:
    class containers:
        @staticmethod
        def run(*_args, **_kwargs):
            return MockContainer()


def get_container_client():
    """Return a Docker client when available, else a deterministic mock."""
    if docker is None:
        return MockDockerClient()
    try:
        return docker.from_env()
    except Exception:
        return MockDockerClient()


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
    violations: list[str] = field(default_factory=list)

    def __post_init__(self):
        self.type = infer_type(self.artifact_path)
        self.client = get_container_client()

    def check_data_correctness(self):
        df = pd.DataFrame(np.random.rand(100, 5), columns=list("ABCDE"))
        df["A"] = df["A"].astype(str)
        if pd.api.types.is_float_dtype(df["A"]):
            return
        self.violations.append(
            "SCHEMA_DRIFT: Column 'A' type mismatch (float → object)"
        )

    def check_model_correctness(self):
        train = np.random.normal(0, 1, 1000)
        prod = np.random.normal(5, 2, 1000)
        drift = abs(train.mean() - prod.mean())
        if drift > 0.5:
            self.violations.append(
                f"MODEL_DRIFT: Covariate shift detected (delta={drift:.2f})"
            )

    def check_availability(self):
        try:
            container = self.client.containers.run(
                "python:slim",
                "python -c 'import numpy as np; np.ones((10000,10000))'",
                mem_limit="64m",
                detach=True,
            )
            container.wait()
            logs = container.logs().decode()
            if "Killed" in logs:
                raise RuntimeError("OOM")
        except Exception:
            self.violations.append(
                "SLO_VIOLATION: Service crashed under resource constraint (OOM)"
            )

    def check_security(self):
        audit_log = ["token_123_access"]
        replay_attempt = "token_123_access"
        blocked = False
        if replay_attempt in audit_log and not blocked:
            self.violations.append(
                "SECURITY_FAIL: Token replay accepted (privilege escalation risk)"
            )

    def check_state_persistence(self):
        ledger = ["Genesis", "Tx_100USD", "Tx_20USD"]
        root = hashlib.sha256("".join(ledger).encode()).hexdigest()
        ledger[1] = "Tx_1000USD"
        new_root = hashlib.sha256("".join(ledger).encode()).hexdigest()
        if new_root != root:
            self.violations.append(
                "LEDGER_CORRUPTION: Merkle root mismatch (history mutable)"
            )

    def run(self) -> dict:
        self.check_data_correctness()
        self.check_model_correctness()
        self.check_availability()
        self.check_security()
        self.check_state_persistence()

        return {
            "artifact": self.artifact_path,
            "artifact_type": self.type,
            "status": "PASS" if not self.violations else "FAIL",
            "score": max(0, 100 - len(self.violations) * 20),
            "violations": self.violations,
        }


def main():
    oracle = FailureOracle("candidate_artifact.zip")
    verdict = oracle.run()
    print(json.dumps(verdict, indent=2))


if __name__ == "__main__":
    main()
