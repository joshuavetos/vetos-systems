import pandas as pd
import numpy as np
from typing import List, Dict, Any
from pydantic import BaseModel, Field, ValidationError

# Environment-agnostic Pydantic implementation (v1/v2 compatible)
try:
    from pydantic import model_validator as validator_v2
    PYDANTIC_V2, SERIALIZE = True, 'model_dump'
except ImportError:
    from pydantic import root_validator as validator_v1
    PYDANTIC_V2, SERIALIZE = False, 'dict'

class BudgetItem(BaseModel):
    """Schema enforcement for municipal capital improvement data."""
    project_name: str = Field(..., min_length=1)
    budget_allocation: float = Field(..., gt=0)
    fiscal_start: int = Field(..., ge=2020, le=2045)
    fiscal_end: int = Field(..., ge=2020, le=2045)

    if PYDANTIC_V2:
        @validator_v2(mode='after')
        def validate_chronology(self):
            if self.fiscal_end < self.fiscal_start:
                raise ValueError("End date precedes start date.")
            return self
    else:
        @validator_v1
        def validate_chronology(cls, values):
            if values.get('fiscal_end') < values.get('fiscal_start'):
                raise ValueError("End date precedes start date.")
            return values

def run_financial_audit(input_data: List[Dict]) -> Dict[str, Any]:
    """
    Deterministic audit engine.
    Implements fail-closed validation and robust outlier detection.
    """
    validated, rejected = [], []

    # Phase 1: Schema Enforcement
    for i, record in enumerate(input_data):
        try:
            item = BudgetItem(**record)
            validated.append(getattr(item, SERIALIZE)())
        except Exception as e:
            rejected.append({"index": i, "input": record, "error": str(e)})

    # Phase 2: Determination of Epistemic Integrity
    if not validated:
        return {
            "status": "ABSTAIN",
            "records_validated": 0,
            "records_rejected": len(rejected),
            "rejection_log": rejected
        }

    # Phase 3: Robust Statistical Analysis (Modified Z-Score)
    df = pd.DataFrame(validated)
    median = df['budget_allocation'].median()
    mad = np.median(np.abs(df['budget_allocation'] - median))

    # Handle zero-variance distributions
    if mad == 0:
        df['modified_z'], df['is_outlier'] = 0.0, False
    else:
        # Standard consistency constant for MAD (0.6745)
        df['modified_z'] = 0.6745 * (df['budget_allocation'] - median).abs() / mad
        df['is_outlier'] = df['modified_z'] > 3.5

    return {
        "status": "COMPLETE",
        "records_validated": len(df),
        "records_rejected": len(rejected),
        "risk_exposure": df.loc[df['is_outlier'], 'budget_allocation'].sum(),
        "analysis_frame": df,
        "rejection_log": rejected
    }
