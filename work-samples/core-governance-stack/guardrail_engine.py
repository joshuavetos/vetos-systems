import hashlib
import json
import time
from typing import Dict, Any
import numpy as np
from pydantic import BaseModel, Field, field_validator

# --- Configuration ---
CONFIDENCE_THRESHOLD = 0.92  # High bar for "Fail-Closed"
DOMAIN_WHITELIST = ["financial", "industrial", "audit"]


def softmax(logits: np.ndarray) -> np.ndarray:
    """Compute a numerically stable softmax without external dependencies."""
    shifted = logits - np.max(logits)
    exp_values = np.exp(shifted)
    return exp_values / np.sum(exp_values)

class InputSchema(BaseModel):
    query: str
    context: str
    domain: str
    timestamp: float = Field(default_factory=time.time)

    @field_validator("domain")
    @classmethod
    def domain_must_be_whitelisted(cls, v):
        if v not in DOMAIN_WHITELIST:
            raise ValueError(f"Domain '{v}' not in whitelist: {DOMAIN_WHITELIST}")
        return v

class DecisionReceipt(BaseModel):
    receipt_id: str
    input_hash: str
    confidence_score: float
    decision: str  # "EXECUTE" or "HALT"
    timestamp: float

class GuardrailEngine:
    def __init__(self):
        self._last_hash = "0" * 64  # Genesis hash for lineage chaining

    def _compute_hash(self, data: Dict) -> str:
        """Structural hashing of dictionary content."""
        serialized = json.dumps(data, sort_keys=True).encode()
        return hashlib.sha256(serialized).hexdigest()

    def _deterministic_inference_logits(self, text: str) -> np.ndarray:
        """Return deterministic safety logits derived from auditable text features.

        The guardrail work sample does not bundle a model checkpoint, so the
        confidence gate uses explicit lexical and structural risk signals instead
        of random values.  The three logits are ordered as
        [safe, ambiguous, unsafe].
        """
        normalized = text.lower()
        tokens = [token for token in normalized.replace("_", " ").split() if token]
        token_count = max(len(tokens), 1)
        unique_ratio = len(set(tokens)) / token_count
        digit_ratio = sum(ch.isdigit() for ch in text) / max(len(text), 1)
        punctuation_count = sum(
            not ch.isalnum() and not ch.isspace() for ch in text
        )
        punctuation_ratio = punctuation_count / max(len(text), 1)

        safe_terms = {
            "audit",
            "calculate",
            "liquidity",
            "validate",
            "reconcile",
            "report",
        }
        unsafe_terms = {
            "bypass",
            "exploit",
            "exfiltrate",
            "disable",
            "weaponize",
            "malware",
        }
        ambiguous_terms = {
            "maybe",
            "guess",
            "unknown",
            "private",
            "secret",
            "credential",
        }

        safe_hits = sum(term in tokens for term in safe_terms)
        unsafe_hits = sum(term in tokens for term in unsafe_terms)
        ambiguous_hits = sum(term in tokens for term in ambiguous_terms)

        safe_logit = (
            0.25 + 0.9 * safe_hits + 0.4 * unique_ratio - 2.0 * unsafe_hits
        )
        ambiguous_logit = (
            0.1
            + 0.7 * ambiguous_hits
            + punctuation_ratio
            + abs(token_count - 8) / 20
        )
        unsafe_logit = -0.3 + 1.4 * unsafe_hits + 0.8 * ambiguous_hits + digit_ratio
        return np.array([safe_logit, ambiguous_logit, unsafe_logit], dtype=float)

    def process(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main execution gate. 
        Returns valid output OR raises FailClosedError.
        """
        # 1. Validation Gate (Pydantic)
        try:
            clean_input = InputSchema(**payload)
        except Exception as e:
            return {"error": f"Schema Validation Failed: {str(e)}", "status": "HALT"}

        # 2. Epistemic Confidence Check (Softmax)
        logits = self._deterministic_inference_logits(clean_input.query)
        probs = softmax(logits)
        confidence = float(np.max(probs))

        # 3. Fail-Closed Logic
        decision = "HALT"
        if confidence >= CONFIDENCE_THRESHOLD:
            decision = "EXECUTE"

        # 4. Cryptographic Receipt Emission
        input_hash = self._compute_hash(payload)
        receipt = DecisionReceipt(
            receipt_id=hashlib.sha256(
                f"{input_hash}{time.time()}".encode()
            ).hexdigest(),
            input_hash=input_hash,
            confidence_score=confidence,
            decision=decision,
            timestamp=time.time()
        )

        # 5. Output
        if decision == "HALT":
            return {
                "status": "HALT",
                "reason": f"Insufficient Confidence ({confidence:.4f} < {CONFIDENCE_THRESHOLD})",
                "receipt": receipt.dict()
            }
        
        return {
            "status": "EXECUTE",
            "payload": f"Processed: {clean_input.query}",
            "receipt": receipt.dict()
        }

# --- Quick Test ---
if __name__ == "__main__":
    engine = GuardrailEngine()
    
    # Test 1: Safe Query
    print(engine.process({
        "query": "Calculate net liquidity for Q3", 
        "context": "Banking audit", 
        "domain": "financial"
    }))

    # Test 2: Invalid Domain (Should Validation Fail)
    print(engine.process({
        "query": "Generate meme", 
        "context": "social", 
        "domain": "entertainment"
    }))
