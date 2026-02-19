import importlib.util
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = REPO_ROOT / "artifacts" / "epistemic-instruments" / "semantic_auditor_v3_3.py"
spec = importlib.util.spec_from_file_location("semantic_auditor", MODULE_PATH)
module = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(module)


def test_semantic_auditor_sample_csv():
    df = module.load_input(str(REPO_ROOT / "samples" / "sample_support_tickets.csv"), "text")
    result = module.run_audit(df)
    assert result["rows"] == 6
    assert result["decision"] in {"REVIEWABLE", "UNSTABLE_HIGH_NOISE"}
    assert sum(result["clusters"].values()) == 6
