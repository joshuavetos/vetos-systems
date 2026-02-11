import pandas as pd
    from typing import Dict
    import hashlib
    import numpy as np
    from datetime import datetime, UTC
    import sqlite3
    
    class TransformationReceipt:
        def __init__(self, input_hash: str, output_hash: str, op: str, params: Dict):
            self.input_hash = input_hash
            self.output_hash = output_hash
            self.op = op
            self.params = params
            self.timestamp = datetime.now(UTC).isoformat()
    
    class DataPipeline:
        def __init__(self, db_path: str = ":memory:"):
            self.conn = sqlite3.connect(db_path)
            self.conn.execute("CREATE TABLE IF NOT EXISTS receipts (input_h TEXT, output_h TEXT, op TEXT, ts TEXT)")
            self.receipts = []
    
        def hash_df(self, df: pd.DataFrame) -> str:
            return hashlib.sha256(df.to_json().encode()).hexdigest()
    
        def validate_schema(self, df: pd.DataFrame, schema: Dict) -> bool:
            required_cols = schema["required"]
            for col in required_cols:
                if col not in df.columns:
                    return False
            return True
    
        def run(self, df: pd.DataFrame, schema: Dict) -> pd.DataFrame:
            input_hash = self.hash_df(df)
            if not self.validate_schema(df, schema):
                raise ValueError("Schema validation failed")
            
            df_clean = df.dropna()
            df_clean = df_clean[df_clean["amount"] > 0].copy()
            df_clean["date"] = pd.to_datetime(df_clean["date"])
            df_clean["amount_log"] = np.log1p(df_clean["amount"])
            
            output_hash = self.hash_df(df_clean)
            receipt = TransformationReceipt(input_hash, output_hash, "clean+feature", {
                "rows_in": len(df), "rows_out": len(df_clean),
                "features_added": ["amount_log"]
            })
            self.receipts.append(receipt)
            self.conn.execute("INSERT INTO receipts VALUES (?,?,?,?)",
                              (receipt.input_hash, receipt.output_hash, receipt.op, receipt.timestamp))
            self.conn.commit()
            return df_clean
