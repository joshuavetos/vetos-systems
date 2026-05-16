import hashlib
import json
from collections.abc import Iterable, Mapping
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Literal, cast

from pydantic import BaseModel, ConfigDict, ValidationError

DATA_ROOT = Path("data").resolve()
MAX_INPUT_ROWS = 5000
MAX_QUERY_LIMIT = 1000
MAX_PAYLOAD_BYTES = 1_000_000
MAX_NESTING_DEPTH = 10


class PolicyViolationError(Exception):
    """Raised when a request violates an explicit policy rule."""


class PayloadLimitError(Exception):
    """Raised when a request exceeds deterministic payload limits."""


class ToolExecutionError(Exception):
    """Raised when a governed tool cannot be executed safely."""


class SchemaValidationError(Exception):
    """Raised when a request fails schema validation."""


class PolicyResult(str, Enum):
    PASS = "PASS"
    FORBIDDEN_TOOL = "DENIED_FORBIDDEN_TOOL"
    SCHEMA_INVALID = "DENIED_SCHEMA_INVALID"
    TARGET_VIOLATION = "DENIED_TARGET_VIOLATION"
    ROWS_NOT_LIST = "DENIED_ROWS_NOT_LIST"
    ROW_LIMIT_EXCEEDED = "DENIED_ROW_LIMIT_EXCEEDED"
    PAYLOAD_TOO_LARGE = "DENIED_PAYLOAD_TOO_LARGE"
    NESTING_TOO_DEEP = "DENIED_NESTING_TOO_DEEP"
    TEST_SUITE_VIOLATION = "DENIED_TEST_SUITE_VIOLATION"


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: str
    target: Any


class QueryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rows: list[dict[str, Any]]
    limit: int


class ReadFileTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str


class RunTestTarget(BaseModel):
    model_config = ConfigDict(extra="forbid")

    suite: Literal["unit", "integration"]


class ActionReceipt(BaseModel):
    action_id: str
    tool: str
    target: str
    simulation_result: dict[str, Any]
    policy_check: PolicyResult
    approved: bool


def _is_allowed_csv(target: str) -> bool:
    try:
        path = Path(target).resolve()
    except Exception:
        return False
    return path.suffix == ".csv" and DATA_ROOT in path.parents


def _max_depth(value: Any, depth: int = 0, seen: set[int] | None = None) -> int:
    if seen is None:
        seen = set()
    if depth > MAX_NESTING_DEPTH:
        return depth
    if isinstance(value, Mapping):
        mapping_value = cast(Mapping[Any, Any], value)
        object_id = id(mapping_value)
        if object_id in seen:
            return MAX_NESTING_DEPTH + 1
        seen.add(object_id)
        dict_children = cast(Iterable[Any], mapping_value.values())
        child_depths = [_max_depth(child, depth + 1, seen) for child in dict_children]
        seen.remove(object_id)
        return max(child_depths, default=depth)
    if isinstance(value, (list, tuple, set)):
        sequence_value = cast(Iterable[Any], value)
        object_id = id(sequence_value)
        if object_id in seen:
            return MAX_NESTING_DEPTH + 1
        seen.add(object_id)
        sequence_children = sequence_value
        child_depths = [_max_depth(child, depth + 1, seen) for child in sequence_children]
        seen.remove(object_id)
        return max(child_depths, default=depth)
    return depth


def _payload_size_bytes(value: Any) -> int:
    serialized = json.dumps(value, sort_keys=True, allow_nan=False, separators=(",", ":"))
    return len(serialized.encode("utf-8"))


def _validate_payload_limits(action: dict[str, Any]) -> PolicyResult:
    try:
        payload_size = _payload_size_bytes(action)
    except (TypeError, ValueError, RecursionError):
        return PolicyResult.PAYLOAD_TOO_LARGE
    if payload_size > MAX_PAYLOAD_BYTES:
        return PolicyResult.PAYLOAD_TOO_LARGE
    if _max_depth(action) > MAX_NESTING_DEPTH:
        return PolicyResult.NESTING_TOO_DEEP
    target = action.get("target")
    if isinstance(target, Mapping):
        target_mapping = cast(Mapping[str, Any], target)
        rows = target_mapping.get("rows")
        if isinstance(rows, list):
            row_values = cast(list[Any], rows)
            if len(row_values) > MAX_INPUT_ROWS:
                return PolicyResult.ROW_LIMIT_EXCEEDED
    return PolicyResult.PASS


class PolicyLayer:
    ALLOWED_ACTIONS = {"read_file", "query_db", "run_test"}

    @staticmethod
    def parse_action(action: dict[str, Any]) -> tuple[ActionRequest | None, PolicyResult]:
        limit_result = _validate_payload_limits(action)
        if limit_result is not PolicyResult.PASS:
            return None, limit_result
        try:
            request = ActionRequest.model_validate(action)
        except ValidationError:
            return None, PolicyResult.SCHEMA_INVALID
        if request.tool not in PolicyLayer.ALLOWED_ACTIONS:
            return request, PolicyResult.FORBIDDEN_TOOL
        return request, PolicyResult.PASS

    @staticmethod
    def check(action: dict[str, Any]) -> PolicyResult:
        request, result = PolicyLayer.parse_action(action)
        if result is not PolicyResult.PASS or request is None:
            return result

        if request.tool == "read_file":
            try:
                file_target = ReadFileTarget.model_validate({"path": request.target})
            except ValidationError:
                return PolicyResult.TARGET_VIOLATION
            if not _is_allowed_csv(file_target.path):
                return PolicyResult.TARGET_VIOLATION

        if request.tool == "query_db":
            try:
                query_target = QueryTarget.model_validate(request.target)
            except ValidationError:
                return PolicyResult.SCHEMA_INVALID
            if len(query_target.rows) > MAX_INPUT_ROWS or query_target.limit > MAX_QUERY_LIMIT:
                return PolicyResult.ROW_LIMIT_EXCEEDED
            if query_target.limit < 0:
                return PolicyResult.SCHEMA_INVALID

        if request.tool == "run_test":
            try:
                RunTestTarget.model_validate({"suite": request.target})
            except ValidationError:
                return PolicyResult.TEST_SUITE_VIOLATION

        return PolicyResult.PASS


class BoundedAgent:
    def __init__(self) -> None:
        self.tools: dict[str, Callable[[Any], dict[str, Any]]] = {
            "read_file": self._read_csv_preview,
            "query_db": self._query_rows,
            "run_test": self._run_registered_test,
        }

    def _read_csv_preview(self, target: str) -> dict[str, Any]:
        path = Path(target).resolve()
        if not _is_allowed_csv(str(path)):
            raise PolicyViolationError("target violation")
        if not path.is_file():
            return {"status": "missing", "path": str(path), "rows_previewed": 0}

        lines = path.read_text(encoding="utf-8").splitlines()
        return {
            "status": "read",
            "path": str(path),
            "rows_previewed": min(len(lines), 5),
            "preview": lines[:5],
        }

    def _query_rows(self, target: dict[str, Any]) -> dict[str, Any]:
        query = QueryTarget.model_validate(target)
        selected_rows = query.rows[: query.limit]
        return {
            "status": "queried",
            "rows_returned": len(selected_rows),
            "rows": selected_rows,
        }

    def _run_registered_test(self, target: str) -> dict[str, Any]:
        suite = RunTestTarget.model_validate({"suite": target}).suite
        return {"status": "registered", "suite": suite, "executable": True}

    def simulate_action(self, action: dict[str, Any]) -> dict[str, Any]:
        policy_result = PolicyLayer.check(action)
        if policy_result is not PolicyResult.PASS:
            return {"status": "policy_violation", "detail": policy_result.value}

        request, parse_result = PolicyLayer.parse_action(action)
        if parse_result is not PolicyResult.PASS or request is None:
            return {"status": "policy_violation", "detail": parse_result.value}

        tool = self.tools.get(request.tool)
        if tool is None:
            return {"status": "policy_violation", "detail": PolicyResult.FORBIDDEN_TOOL.value}

        try:
            result = tool(request.target)
        except Exception as exc:
            return {"status": "tool_error", "detail": str(exc)}

        if result.get("status") == "missing":
            return {
                "status": "tool_error",
                "detail": "file not found",
                "preview": result,
            }
        return {"status": "success", "preview": result}

    def execute_action(self, action: dict[str, Any], approval: bool = False) -> ActionReceipt:
        request, parse_result = PolicyLayer.parse_action(action)
        tool_name = request.tool if request is not None else "invalid"
        target = request.target if request is not None else action.get("target", "")
        simulation = self.simulate_action(action)
        policy_check = (
            PolicyLayer.check(action) if parse_result is PolicyResult.PASS else parse_result
        )
        try:
            action_id = hashlib.sha256(
                json.dumps(action, sort_keys=True, allow_nan=False, default=str).encode()
            ).hexdigest()
        except (TypeError, ValueError, RecursionError):
            action_id = hashlib.sha256(b"invalid-action").hexdigest()
        return ActionReceipt(
            action_id=action_id,
            tool=tool_name,
            target=str(target),
            simulation_result=simulation,
            policy_check=policy_check,
            approved=bool(approval and simulation.get("status") == "success"),
        )
