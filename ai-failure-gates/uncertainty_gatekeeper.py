import hashlib
import re
from typing import Any, Dict
from pydantic import BaseModel, Field

# FAIL-CLOSED: Pydantic v2 is the ONLY supported version for deterministic serialization
from pydantic import model_validator as validator_v2

class LLMResponse(BaseModel):
    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)

    @validator_v2(mode='after')
    def enforce_threshold(self) -> 'LLMResponse':
        if self.confidence < 0.9:
            raise ValueError("Insufficient grounding")
        return self

class UncertaintyGatekeeper:
    def __init__(self, llm_client: Any):
        self.llm_client = llm_client
        self._cache: Dict[str, str] = {}

    def _density_gate(self, prompt: str):
        """
        Replaces heuristic regex with deterministic density validation.
        Enforces a minimum of 10 tokens and 50 characters.
        """
        tokens = prompt.strip().split()
        if len(tokens) < 10 or len(prompt) < 50:
            raise ValueError("Rejection: Input density insufficient for audit.")

    def execute(self, prompt: str) -> str:
        """Deterministic execution with SHA-256 caching."""
        self._density_gate(prompt)
        
        cache_key = hashlib.sha256(prompt.encode()).hexdigest()
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Call client and enforce schema
        raw = self.llm_client(prompt)
        res = LLMResponse(**raw)
        
        # Uncertainty terminates execution
        if re.search(r"\b(maybe|perhaps|probably|i think)\b", res.text, re.I):
            return "REFUSED: Probabilistic language detected"

        self._cache[cache_key] = res.text
        return res.text

# --------------------------------------------------
# Operational Rule: Refusal is success.
# --------------------------------------------------
