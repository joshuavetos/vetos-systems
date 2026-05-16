from pathlib import Path
from typing import Dict
from pydantic import BaseModel
import hashlib
import json
import re


class ActionReceipt(BaseModel):
    action_id: str
    tool: str
    target: str
    simulation_result: Dict
    policy_check: str
    approved: bool


class PolicyLayer:
    ALLOWED_ACTIONS = {
        "read_file": {"pattern": r"^data/.*\.csv$"},
        "query_db": {"max_rows": 1000},
        "run_test": {"allowed_suites": ["unit", "integration"]}
    }

    @staticmethod
    def check(action: Dict) -> str:
        tool = action.get("tool")
        spec = PolicyLayer.ALLOWED_ACTIONS.get(tool, {"deny": True})
        if spec.get("deny"):
            return "DENIED: forbidden tool"

        target = action.get("target")
        if tool == "read_file":
            if not isinstance(target, str) or not re.match(spec["pattern"], target):
                return "DENIED: target violation"

        if tool == "query_db":
            if not isinstance(target, dict):
                return "DENIED: query target must be an object"
            rows = target.get("rows", [])
            if not isinstance(rows, list):
                return "DENIED: rows must be a list"
            limit = target.get("limit", len(rows))
            if not isinstance(limit, int) or limit < 0:
                return "DENIED: limit must be a non-negative integer"
            if limit > spec["max_rows"]:
                return "DENIED: row limit exceeds policy"

        if tool == "run_test":
            if target not in spec["allowed_suites"]:
                return "DENIED: test suite violation"

        return "PASS"


class BoundedAgent:
    def __init__(self):
        self.tools = {
            "read_file": self._read_csv_preview,
            "query_db": self._query_rows,
            "run_test": self._run_registered_test
        }

    def _read_csv_preview(self, target):
        path = Path(target)
        if not path.is_file():
            return {"status": "missing", "path": str(path), "rows_previewed": 0}

        lines = path.read_text(encoding="utf-8").splitlines()
        return {
            "status": "read",
            "path": str(path),
            "rows_previewed": min(len(lines), 5),
            "preview": lines[:5],
        }

    def _query_rows(self, target):
        rows = target["rows"]
        limit = target.get("limit", len(rows))
        selected_rows = rows[:limit]
        return {
            "status": "queried",
            "rows_returned": len(selected_rows),
            "rows": selected_rows,
        }

    def _run_registered_test(self, target):
        return {"status": "registered", "suite": target, "executable": True}

    def simulate_action(self, action: Dict) -> Dict:
        policy_result = PolicyLayer.check(action)
        if policy_result != "PASS":
            return {"status": "policy_violation", "detail": policy_result}
        tool = self.tools[action["tool"]]
        result = tool(action["target"])
        if isinstance(result, dict) and result.get("status") == "missing":
            return {
                "status": "tool_error",
                "detail": "file not found",
                "preview": result,
            }
        return {"status": "success", "preview": result}

    def execute_action(self, action: Dict, approval: bool = False) -> ActionReceipt:
        simulation = self.simulate_action(action)
        receipt = ActionReceipt(
            action_id=hashlib.sha256(
                json.dumps(action, sort_keys=True).encode()
            ).hexdigest(),
            tool=action["tool"],
            target=str(action["target"]),
            simulation_result=simulation,
            policy_check=PolicyLayer.check(action),
            approved=bool(approval and simulation["status"] == "success")
        )
        return receipt
