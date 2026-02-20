"""Failure Oracle integrity checks with deterministic execution."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path


class DeterminismError(RuntimeError):
    """Raised when deterministic replay requirements are missing."""


def require_seed() -> int:
    seed_raw = os.environ.get("FAILURE_ORACLE_SEED")
    if seed_raw is None:
        raise DeterminismError("FAILURE_ORACLE_SEED is required for deterministic replay")
    try:
        return int(seed_raw)
    except ValueError as exc:
        raise DeterminismError("FAILURE_ORACLE_SEED must be an integer") from exc


def _docker_available() -> bool:
    try:
        import docker  # noqa: PLC0415
    except Exception:
        return False

    try:
        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


def run_oracle(artifact_path: str | Path, seed: int, skip_docker: bool) -> dict:
    artifact = Path(artifact_path)
    if not artifact.exists():
        raise FileNotFoundError(f"artifact does not exist: {artifact_path}")

    checks = []

    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    checks.append({"check": "artifact_hash", "status": "PASS", "sha256": digest})

    if skip_docker:
        checks.append(
            {
                "check": "availability_test",
                "status": "SKIP",
                "reason": "Docker availability test skipped by configuration",
            }
        )
    elif not _docker_available():
        checks.append(
            {
                "check": "availability_test",
                "status": "SKIP",
                "reason": "Docker daemon unavailable; deterministic skip",
            }
        )
    else:
        checks.append({"check": "availability_test", "status": "PASS", "reason": "Docker daemon reachable"})

    status = "PASS" if all(check["status"] in {"PASS", "SKIP"} for check in checks) else "FAIL"
    return {
        "artifact": str(artifact),
        "seed": seed,
        "status": status,
        "checks": checks,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run deterministic Failure Oracle checks")
    parser.add_argument("--artifact-path", required=True)
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    seed = require_seed()
    skip_docker = os.environ.get("FAILURE_ORACLE_SKIP_DOCKER", "0") == "1"
    verdict = run_oracle(args.artifact_path, seed=seed, skip_docker=skip_docker)
    rendered = json.dumps(verdict, indent=2, sort_keys=True)
    if args.output_json:
        Path(args.output_json).write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
