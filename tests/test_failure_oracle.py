import importlib.util
import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "work-samples" / "failure_oracle.py"
spec = importlib.util.spec_from_file_location("failure_oracle", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_failure_oracle_matches_committed_output():
    expected = json.loads((REPO_ROOT / "samples" / "sample_failure_oracle_output.json").read_text(encoding="utf-8"))
    actual = module.run_oracle("work-samples/failure_oracle.c", seed=2026, skip_docker=True)
    assert actual == expected
