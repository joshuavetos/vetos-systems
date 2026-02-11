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
            tool = action["tool"]
            spec = PolicyLayer.ALLOWED_ACTIONS.get(tool, {"deny": True})
            if spec.get("deny"):
                return "DENIED: forbidden tool"
            if tool == "read_file":
                if not re.match(spec["pattern"], action["target"]):
                    return "DENIED: target violation"
            return "PASS"
    
    class BoundedAgent:
        def __init__(self):
            self.tools = {
                "read_file": self._mock_read,
                "query_db": self._mock_query,
                "run_test": self._mock_test
            }
        def _mock_read(self, target): return "data..."
        def _mock_query(self, target): return "rows..."
        def _mock_test(self, target): return "pass"
    
        def simulate_action(self, action: Dict) -> Dict:
            policy_result = PolicyLayer.check(action)
            if policy_result != "PASS":
                return {"status": "policy_violation", "detail": policy_result}
            tool = self.tools[action["tool"]]
            result = tool(action["target"])
            return {"status": "success", "preview": result[:100]}
    
        def execute_action(self, action: Dict, approval: bool = False) -> ActionReceipt:
            simulation = self.simulate_action(action)
            receipt = ActionReceipt(
                action_id=hashlib.sha256(json.dumps(action, sort_keys=True).encode()).hexdigest(),
                tool=action["tool"],
                target=str(action["target"]),
                simulation_result=simulation,
                policy_check=PolicyLayer.check(action),
                approved=bool(approval and simulation["status"] == "success")
            )
            return receipt
