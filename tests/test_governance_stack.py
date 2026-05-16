import copy
import importlib.util
import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
BOUNDED_AGENT_PATH = REPO_ROOT / "work-samples" / "core-governance-stack" / "bounded_agent.py"
GUARDRAIL_PATH = REPO_ROOT / "work-samples" / "core-governance-stack" / "guardrail_engine.py"
GEO_PATH = REPO_ROOT / "tools" / "geospatial-discovery-engine" / "discovery_engine.py"
TEXT_SCALPEL_CORE_PATH = (
    REPO_ROOT / "work-samples" / "text-scalpel" / "src" / "text_scalpel" / "core.py"
)


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

    assert receipt.policy_check == module.PolicyResult.ROW_LIMIT_EXCEEDED
    assert receipt.approved is False
    assert receipt.simulation_result["status"] == "policy_violation"


def test_bounded_agent_does_not_approve_missing_allowed_file():
    module = load_module("bounded_agent_missing_file", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()

    receipt = agent.execute_action(
        {"tool": "read_file", "target": "data/missing.csv"}, approval=True
    )

    assert receipt.policy_check == module.PolicyResult.PASS
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


def test_bounded_agent_rejects_traversal_attempt():
    module = load_module("bounded_agent_traversal", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()

    receipt = agent.execute_action(
        {"tool": "read_file", "target": "data/../../secret.csv"}, approval=True
    )

    assert receipt.policy_check == module.PolicyResult.TARGET_VIOLATION
    assert receipt.approved is False
    assert receipt.simulation_result["status"] == "policy_violation"


@pytest.mark.parametrize(
    "action, expected",
    [
        (
            {"tool": "query_db", "target": {"rows": [{"x": float("nan")}], "limit": 1}},
            "policy_violation",
        ),
        (
            {"tool": "query_db", "target": {"rows": [{"x": float("inf")}], "limit": 1}},
            "policy_violation",
        ),
        ({"tool": "", "target": ""}, "policy_violation"),
        ({"tool": "delete_file", "target": "data/a.csv"}, "policy_violation"),
        ({"tool": "query_db", "target": "{rows: malformed}"}, "policy_violation"),
    ],
)
def test_bounded_agent_adversarial_inputs_fail_closed(action, expected):
    module = load_module(f"bounded_agent_adv_{abs(hash(str(action)))}", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()

    receipt = agent.execute_action(action, approval=True)

    assert receipt.approved is False
    assert receipt.simulation_result["status"] == expected


def test_bounded_agent_rejects_deep_and_oversized_payloads():
    module = load_module("bounded_agent_limits", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()
    nested = {}
    cursor = nested
    for index in range(module.MAX_NESTING_DEPTH + 1):
        cursor["x"] = {"index": index}
        cursor = cursor["x"]

    deep_receipt = agent.execute_action({"tool": "query_db", "target": nested}, approval=True)
    row_receipt = agent.execute_action(
        {"tool": "query_db", "target": {"rows": [{}] * (module.MAX_INPUT_ROWS + 1), "limit": 1}},
        approval=True,
    )

    assert deep_receipt.policy_check == module.PolicyResult.NESTING_TOO_DEEP
    assert row_receipt.policy_check == module.PolicyResult.ROW_LIMIT_EXCEEDED


def test_bounded_agent_does_not_mutate_caller_payload():
    module = load_module("bounded_agent_no_mutation", BOUNDED_AGENT_PATH)
    agent = module.BoundedAgent()
    action = {"tool": "query_db", "target": {"rows": [{"id": 1}], "limit": 1}}
    original = copy.deepcopy(action)

    agent.execute_action(action, approval=True)

    assert action == original


def test_guardrail_logits_are_deterministic():
    module = load_module("guardrail_engine", GUARDRAIL_PATH)
    engine = module.GuardrailEngine()

    first = engine._deterministic_inference_logits("Calculate liquidity audit report")
    second = engine._deterministic_inference_logits("Calculate liquidity audit report")

    assert first.tolist() == second.tolist()
    assert first.shape == (3,)


def test_guardrail_confidence_calibration_and_unsafe_dominance():
    module = load_module("guardrail_engine_calibration", GUARDRAIL_PATH)

    safe = module.GuardrailEngine().process(
        {
            "query": "Calculate liquidity audit report validate reconcile",
            "context": "audit",
            "domain": "audit",
            "timestamp": 1.0,
        }
    )
    malicious = module.GuardrailEngine().process(
        {
            "query": "exploit malware exfiltrate credentials",
            "context": "audit",
            "domain": "audit",
            "timestamp": 1.0,
        }
    )
    ambiguous = module.GuardrailEngine().process(
        {
            "query": "credential maybe private",
            "context": "audit",
            "domain": "audit",
            "timestamp": 1.0,
        }
    )
    punctuation = module.GuardrailEngine().process(
        {"query": "!!!!! ????? !!!!!", "context": "audit", "domain": "audit", "timestamp": 1.0}
    )
    digits = module.GuardrailEngine().process(
        {"query": "1234567890 9999999999", "context": "audit", "domain": "audit", "timestamp": 1.0}
    )
    mixed = module.GuardrailEngine().process(
        {
            "query": "Calculate liquidity audit report exploit exfiltrate",
            "context": "audit",
            "domain": "audit",
            "timestamp": 1.0,
        }
    )

    assert safe["status"] == "EXECUTE"
    assert malicious["status"] == "HALT"
    assert ambiguous["status"] == "HALT"
    assert punctuation["status"] == "HALT"
    assert digits["status"] == "HALT"
    assert mixed["status"] == "HALT"
    assert malicious["receipt"]["confidence_score"] > ambiguous["receipt"]["confidence_score"]
    assert mixed["receipt"]["confidence_score"] > safe["receipt"]["confidence_score"] - 0.01


def test_guardrail_receipt_lineage_is_stable_for_identical_engine_state():
    module = load_module("guardrail_engine_lineage", GUARDRAIL_PATH)
    payload = {
        "query": "Calculate liquidity audit report validate reconcile",
        "context": "audit",
        "domain": "audit",
        "timestamp": 42.0,
    }

    first = module.GuardrailEngine().process(payload)
    second = module.GuardrailEngine().process(payload)

    assert first["receipt"]["receipt_id"] == second["receipt"]["receipt_id"]
    assert first["receipt"]["input_hash"] == second["receipt"]["input_hash"]


def test_validate_mean_coherence_rejects_non_finite_values():
    module = load_module("discovery_engine", GEO_PATH)

    assert module.validate_mean_coherence(float("nan")) is False
    assert module.validate_mean_coherence(float("inf")) is False
    assert module.validate_mean_coherence(0.39) is False
    assert module.validate_mean_coherence(0.4) is True


def test_compute_mean_coherence_returns_none_on_reduction_failure(monkeypatch):
    module = load_module("discovery_engine_failure", GEO_PATH)

    class Reducer:
        @staticmethod
        def mean():
            return object()

    class EE:
        pass

    EE.Reducer = Reducer

    class BrokenImage:
        def reduceRegion(self, **_kwargs):
            raise RuntimeError("ee failure")

    monkeypatch.setattr(module, "_require_earth_engine", lambda: EE)

    assert module.compute_mean_coherence(BrokenImage(), object()) is None


def test_text_scalpel_inserts_into_empty_source_buffer():
    module = load_module("text_scalpel_core_empty", TEXT_SCALPEL_CORE_PATH)

    result = module.ScalpelEngine.insert("", line_number=1, new_code="value = 1")

    assert result == "value = 1"


def test_text_scalpel_rejects_unknown_position():
    module = load_module("text_scalpel_core_bad_position", TEXT_SCALPEL_CORE_PATH)

    with pytest.raises(ValueError, match="position must be either"):
        module.ScalpelEngine.insert(
            "value = 1", line_number=1, new_code="next_value = 2", position="middle"
        )


def test_text_scalpel_rejects_malformed_unicode_and_binary_input():
    module = load_module("text_scalpel_core_unicode", TEXT_SCALPEL_CORE_PATH)

    with pytest.raises(ValueError, match="valid UTF-8"):
        module.ScalpelEngine.insert("value = 1", line_number=1, new_code="\ud800")
    with pytest.raises(ValueError, match="binary NUL"):
        module.ScalpelEngine.insert("value = 1\x00", line_number=1, new_code="x = 2")


def test_text_scalpel_rejects_repeated_huge_and_syntax_poison_insertions():
    module = load_module("text_scalpel_core_hardening", TEXT_SCALPEL_CORE_PATH)

    with pytest.raises(ValueError, match="duplicate insertion"):
        module.ScalpelEngine.insert("value = 1", line_number=1, new_code="value = 1")
    with pytest.raises(ValueError, match="maximum insertion size"):
        module.ScalpelEngine.insert(
            "value = 1", line_number=1, new_code="x" * (module.MAX_INSERTION_BYTES + 1)
        )
    with pytest.raises(SyntaxError, match="syntax validation"):
        module.ScalpelEngine.insert("value = 1", line_number=1, new_code="if True")


def test_guardrail_durable_ledger_replays_stably(tmp_path):
    module = load_module("guardrail_engine_replay_stable", GUARDRAIL_PATH)
    ledger = tmp_path / "receipts.jsonl"
    payload = {
        "query": "Calculate liquidity audit report validate reconcile",
        "context": "audit",
        "domain": "audit",
        "timestamp": 7.0,
    }

    first = module.GuardrailEngine(ledger_path=ledger).process(payload)
    second = module.GuardrailEngine(ledger_path=ledger).process(payload)
    replay = module.ReceiptLedger.validate(ledger)

    assert first["status"] == "EXECUTE"
    assert second["status"] == "EXECUTE"
    assert first["receipt"]["sequence"] == 0
    assert second["receipt"]["sequence"] == 1
    assert second["receipt"]["previous_hash"] == first["receipt"]["receipt_id"]
    assert replay.valid is True
    assert replay.next_sequence == 2
    assert replay.last_hash == second["receipt"]["receipt_id"]


def test_guardrail_receipt_reproduction_is_deterministic(tmp_path):
    module = load_module("guardrail_engine_reproduction", GUARDRAIL_PATH)
    first_ledger = tmp_path / "first.jsonl"
    second_ledger = tmp_path / "second.jsonl"
    payloads = [
        {
            "query": "Calculate liquidity audit report validate reconcile",
            "context": "audit",
            "domain": "audit",
            "timestamp": 1.0,
        },
        {
            "query": "exploit malware exfiltrate credentials",
            "context": "audit",
            "domain": "audit",
            "timestamp": 2.0,
        },
    ]

    first_receipts = [module.GuardrailEngine(ledger_path=first_ledger).process(payload)["receipt"] for payload in payloads]
    second_receipts = [module.GuardrailEngine(ledger_path=second_ledger).process(payload)["receipt"] for payload in payloads]

    assert first_receipts == second_receipts
    assert first_ledger.read_text(encoding="utf-8") == second_ledger.read_text(encoding="utf-8")


def test_guardrail_replay_detects_tampered_ledger_row(tmp_path):
    module = load_module("guardrail_engine_tamper", GUARDRAIL_PATH)
    ledger = tmp_path / "receipts.jsonl"
    payload = {
        "query": "Calculate liquidity audit report validate reconcile",
        "context": "audit",
        "domain": "audit",
        "timestamp": 3.0,
    }
    module.GuardrailEngine(ledger_path=ledger).process(payload)
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    row["receipt"]["decision"] = "HALT"
    ledger.write_text(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n", encoding="utf-8")

    with pytest.raises(module.SerializationError, match="ledger row hash mismatch"):
        module.ReceiptLedger.validate(ledger)


def test_guardrail_replay_detects_reordered_receipts(tmp_path):
    module = load_module("guardrail_engine_reordered", GUARDRAIL_PATH)
    ledger = tmp_path / "receipts.jsonl"
    payloads = [
        {
            "query": "Calculate liquidity audit report validate reconcile",
            "context": "audit",
            "domain": "audit",
            "timestamp": 4.0,
        },
        {
            "query": "Calculate liquidity audit report validate reconcile",
            "context": "audit",
            "domain": "audit",
            "timestamp": 5.0,
        },
    ]
    for payload in payloads:
        module.GuardrailEngine(ledger_path=ledger).process(payload)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    ledger.write_text("\n".join(reversed(lines)) + "\n", encoding="utf-8")

    with pytest.raises(module.GovernanceRuntimeError, match="receipt sequence discontinuity"):
        module.ReceiptLedger.validate(ledger)


def test_guardrail_replay_detects_duplicate_sequence_ids(tmp_path):
    module = load_module("guardrail_engine_duplicate", GUARDRAIL_PATH)
    ledger = tmp_path / "receipts.jsonl"
    payloads = [
        {
            "query": "Calculate liquidity audit report validate reconcile",
            "context": "audit",
            "domain": "audit",
            "timestamp": 6.0,
        },
        {
            "query": "Calculate liquidity audit report validate reconcile",
            "context": "audit",
            "domain": "audit",
            "timestamp": 7.0,
        },
    ]
    for payload in payloads:
        module.GuardrailEngine(ledger_path=ledger).process(payload)
    lines = ledger.read_text(encoding="utf-8").splitlines()
    first_row = json.loads(lines[0])
    second_row = json.loads(lines[1])
    second_row["receipt"]["sequence"] = 0
    second_row["receipt"]["receipt_id"] = module.ReceiptLedger.receipt_hash(
        module.DecisionReceipt.model_validate(second_row["receipt"])
    )
    second_row["row_hash"] = module.ReceiptLedger.row_hash(second_row["receipt"])
    ledger.write_text(
        json.dumps(first_row, sort_keys=True, separators=(",", ":"))
        + "\n"
        + json.dumps(second_row, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(module.GovernanceRuntimeError, match="receipt sequence discontinuity"):
        module.ReceiptLedger.validate(ledger)


def test_guardrail_replay_detects_truncated_ledger_file(tmp_path):
    module = load_module("guardrail_engine_truncated", GUARDRAIL_PATH)
    ledger = tmp_path / "receipts.jsonl"
    payload = {
        "query": "Calculate liquidity audit report validate reconcile",
        "context": "audit",
        "domain": "audit",
        "timestamp": 8.0,
    }
    module.GuardrailEngine(ledger_path=ledger).process(payload)
    ledger.write_text(ledger.read_text(encoding="utf-8").rstrip("\n"), encoding="utf-8")

    with pytest.raises(module.SerializationError, match="ledger row is truncated"):
        module.ReceiptLedger.validate(ledger)


def test_guardrail_replay_detects_malformed_canonical_serialization(tmp_path):
    module = load_module("guardrail_engine_noncanonical", GUARDRAIL_PATH)
    ledger = tmp_path / "receipts.jsonl"
    payload = {
        "query": "Calculate liquidity audit report validate reconcile",
        "context": "audit",
        "domain": "audit",
        "timestamp": 9.0,
    }
    module.GuardrailEngine(ledger_path=ledger).process(payload)
    row = json.loads(ledger.read_text(encoding="utf-8").splitlines()[0])
    ledger.write_text(json.dumps(row, sort_keys=False, indent=0) + "\n", encoding="utf-8")

    with pytest.raises(module.SerializationError):
        module.ReceiptLedger.validate(ledger)


def test_guardrail_does_not_mutate_payload_and_recursive_payload_fails_closed():
    module = load_module("guardrail_engine_immutable", GUARDRAIL_PATH)
    payload = {
        "query": "Calculate liquidity audit report validate reconcile",
        "context": "audit",
        "domain": "audit",
        "timestamp": 10.0,
    }
    original_bytes = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    result = module.GuardrailEngine().process(payload)

    assert result["status"] == "EXECUTE"
    assert json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8") == original_bytes

    recursive = {"query": "Calculate liquidity audit report", "context": "audit", "domain": "audit", "timestamp": 11.0}
    recursive["self"] = recursive
    denied = module.GuardrailEngine().process(recursive)

    assert denied["status"] == "HALT"
    assert denied["error"]["category"] in {"resource_limit", "serialization"}


def test_guardrail_audit_log_records_redacted_policy_denial(tmp_path):
    module = load_module("guardrail_engine_audit", GUARDRAIL_PATH)
    audit_log = tmp_path / "audit.jsonl"
    denied = module.GuardrailEngine(audit_log_path=audit_log).process(
        {
            "query": "exploit malware exfiltrate credentials",
            "context": "audit",
            "domain": "audit",
            "timestamp": 12.0,
        }
    )

    assert denied["status"] == "HALT"
    assert module.DeterministicAuditLog.validate(audit_log) == 1
    row = json.loads(audit_log.read_text(encoding="utf-8"))
    assert row["event_type"] == "policy_denial"
    assert row["code"] == "INSUFFICIENT_CONFIDENCE"
    assert "input_hash" in row
    assert "receipt_id" in row
    assert "query" not in row
    assert "payload" not in row
