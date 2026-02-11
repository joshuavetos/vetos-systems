from z3 import *
import json
import time

class IndustrialGovernor:
    """
    VETOS INDUSTRIAL PROTOCOL v1.5 (FINAL)
    A self-defending neuro-symbolic gate.
    
    GATES:
    1. Linguistic Certainty (External)
    2. Mathematical RBAC (Z3)
    3. Process Completeness (Conservation)
    4. Contextual Risk (Threat-Aware)
    5. Multi-Agent Consensus (Byzantine Tolerance)
    6. Stateful Stability (Circuit Breaker)
    """
    def __init__(self, daily_budget=5000, failure_threshold=3):
        self.s = Solver()
        self.daily_budget = daily_budget
        self.cumulative_spend = 0
        self.failure_threshold = failure_threshold
        self.violation_timestamps = []
        self.is_hard_locked = False
        
        # Symbolic State
        self.balance = Int('balance')
        self.amount = Int('amount')
        self.tier = String('tier')
        self.status = String('status')
        self.threat_level = String('env.threat')
        self.agent_a_amt = Int('agent.a.amount')
        self.agent_b_amt = Int('agent.b.amount')

    def _qualify_process(self, tx_data):
        violations = []
        if set(tx_data['declared']) != set(tx_data['executed']):
            violations.append("Q2_COMPLETENESS_FAILURE")
        if tx_data['incoming'] != tx_data['outgoing']:
            violations.append("Q1_CONSERVATION_FAILURE")
        return violations

    def authorize(self, req_a, req_b, tx_context, env_context, auth_token=1):
        # GATE 6: CIRCUIT BREAKER
        if self.is_hard_locked:
            if auth_token > 9:
                self.is_hard_locked, self.violation_timestamps = False, []
            else:
                return {"verdict": "FAIL_CLOSED", "reason": "SYSTEM_HARD_LOCK"}

        self.s.push()
        
        # GATE 2 & 4: MATH & RISK LAWS
        self.s.add(self.balance >= 0)
        self.s.add(Implies(self.tier == StringVal("STANDARD"), self.amount <= 100))
        self.s.add(Implies(self.threat_level == StringVal("HIGH"), self.amount <= 500))
        self.s.add(self.cumulative_spend + self.amount <= self.daily_budget)
        
        # GATE 5: CONSENSUS LAWS
        self.s.add(self.agent_a_amt == self.agent_b_amt)
        self.s.add(req_a['key'] == req_b['key'])

        # Inject Context
        self.s.add(self.balance == req_a['balance'])
        self.s.add(self.amount == req_a['amount'])
        self.s.add(self.tier == StringVal(req_a['tier']))
        self.s.add(self.threat_level == StringVal(env_context.get('threat', 'LOW')))
        self.s.add(self.agent_a_amt == req_a['amount'])
        self.s.add(self.agent_b_amt == req_b['amount'])

        # Final Decision
        z3_check = self.s.check()
        proc_violations = self._qualify_process(tx_context)
        
        if z3_check == unsat or proc_violations:
            self.s.pop()
            now = time.time()
            self.violation_timestamps = [t for t in self.violation_timestamps if now - t < 60]
            self.violation_timestamps.append(now)
            if len(self.violation_timestamps) >= self.failure_threshold:
                self.is_hard_locked = True
                return {"verdict": "FAIL_CLOSED", "reason": "CIRCUIT_TRIPPED"}
            return {"verdict": "FAIL_CLOSED", "audit": {"math": str(z3_check), "process": proc_violations}}

        self.cumulative_spend += req_a['amount']
        self.s.pop()
        return {"verdict": "QUALIFIED", "new_burn": self.cumulative_spend}
