from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel, validator
    import hashlib
    import time
    from typing import Dict, Any
    import numpy as np
    from scipy.special import softmax
    from dataclasses import dataclass
    
    @dataclass
    class DecisionReceipt:
        action_hash: str
        confidence: float
        threshold: float
        decision: str
        lineage: Dict[str, Any]
        timestamp: float
    
    class InputSchema(BaseModel):
        query: str
        context: str
        domain: str
    
        @validator("query")
        def validate_query(cls, v):
            if len(v) > 500:
                raise ValueError("Query too long")
            return v
    
    app = FastAPI(title="Fail-Closed Guardrail Engine")
    
    DOMAIN_THRESHOLDS = {
        "financial": 0.95,
        "medical": 0.98,
        "legal": 0.97,
        "general": 0.90
    }
    
    @app.post("/query")
    async def guarded_query(input: InputSchema) -> Dict[str, Any]:
        threshold = DOMAIN_THRESHOLDS.get(input.domain, 0.90)
        mock_logits = np.random.logistic(0, 0.1, 100)
        confidence = float(np.max(softmax(mock_logits)))
        
        lineage = {
            "query_hash": hashlib.sha256(input.query.encode()).hexdigest()[:16],
            "context_tokens": len(input.context.split()),
            "ood_score": float(np.random.uniform(0, 0.1))
        }
        
        action_hash = hashlib.sha256(f"{input.query}{confidence}".encode()).hexdigest()
        
        if confidence < threshold:
            raise HTTPException(
                status_code=403,
                detail={"decision": "REFUSED", "reason": f"confidence {confidence:.3f} < threshold {threshold}"}
            )
        return {
            "response": f"Processed: {input.query}",
            "confidence": confidence,
            "receipt": {
                "action_hash": action_hash,
                "decision": "APPROVED",
                "threshold": threshold
            }
        }
