import importlib.util
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BOUNDED_AGENT_PATH = (
    REPO_ROOT / "work-samples" / "core-governance-stack" / "bounded_agent.py"
)
GUARDRAIL_PATH = (
    REPO_ROOT / "work-samples" / "core-governance-stack" / "guardrail_engine.py"
)
GEO_PATH = REPO_ROOT / "tools" / "geospatial-discovery-engine" / "discovery_engine.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_bounded_agent_enforces_query_row_limit():
    module = load_module("bounded_agent", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()

    receipt = agent.execute_action(
        {"tool": "query_db", "target": {"rows": [{"id": 1}], "limit": 1001}},
        approval=True,
    )

    assert receipt.policy_check == "DENIED: row limit exceeds policy"
    assert receipt.approved is False
    assert receipt.simulation_result["status"] == "policy_violation"


def test_bounded_agent_does_not_approve_missing_allowed_file():
    module = load_module("bounded_agent_missing_file", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()

    receipt = agent.execute_action(
        {"tool": "read_file", "target": "data/missing.csv"}, approval=True
    )

    assert receipt.policy_check == "PASS"
    assert receipt.approved is False
    assert receipt.simulation_result["status"] == "tool_error"


def test_bounded_agent_queries_supplied_rows_without_external_state():
    module = load_module("bounded_agent_success", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()

    receipt = agent.execute_action(
        {"tool": "query_db", "target": {"rows": [{"id": 1}, {"id": 2}], "limit": 1}},
        approval=True,
    )

    assert receipt.approved is True
    assert receipt.simulation_result["status"] == "success"
    preview = receipt.simulation_result["preview"]
    assert preview["rows_returned"] == 1
    assert preview["rows"] == [{"id": 1}]


def test_guardrail_logits_are_deterministic():
    module = load_module("guardrail_engine", GUARDRAIL_PATH)
    engine = module.GuardrailEngine()

    first = engine._deterministic_inference_logits("Calculate liquidity audit report")
    second = engine._deterministic_inference_logits("Calculate liquidity audit report")

    assert first.tolist() == second.tolist()
    assert first.shape == (3,)


def test_validate_mean_coherence_rejects_non_finite_values():
    module = load_module("discovery_engine", GEO_PATH)

    assert module.validate_mean_coherence(float("nan")) is False
    assert module.validate_mean_coherence(float("inf")) is False
    assert module.validate_mean_coherence(0.39) is False
    assert module.validate_mean_coherence(0.4) is True
