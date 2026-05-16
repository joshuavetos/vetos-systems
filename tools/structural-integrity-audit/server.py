import os
import pandas as pd
import numpy as np
import torch
import json
from PIL import Image
from scipy import stats
from fpdf import FPDF
import gradio as gr

# Create evidence directory
os.makedirs('evidence', exist_ok=True)

# --- 1. Forensic PDF Logic ---
class AuditCertificate(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'STRUCTURAL INTEGRITY AUDIT: CERTIFICATE', 0, 1, 'C')
        self.ln(10)

def generate_pdf(report, filename):
    pdf = AuditCertificate()
    pdf.add_page()
    pdf.set_font("Courier", size=10)
    pdf.multi_cell(0, 5, json.dumps(report, indent=2))
    safe_name = "".join([c for c in filename if c.isalnum() or c in (' ', '.', '_')]).rstrip()
    path = f"evidence/cert_{safe_name}.pdf"
    pdf.output(path)
    return path

# --- 2. Hardened Audit Core ---
def run_audit(files):
    if not isinstance(files, list):
        files = [files]
    batch_results = []
    cert_paths = []
    for file in files:
        report = {"file": os.path.basename(file.name), "verdict": "UNKNOWN", "checks": []}
        path = file.name
        name = path.lower()
        try:
            if name.endswith('.csv'):
                df = pd.read_csv(path)
                numeric_cols = df.select_dtypes(include=[np.number])
                outliers = int(np.abs(stats.zscore(numeric_cols.fillna(0))) > 3).sum().sum() if not numeric_cols.empty else 0
                report["checks"].append({"nulls": int(df.isnull().sum().sum()), "outliers_detected": outliers, "rows": len(df)})
                report["verdict"] = "HOLDS" if outliers < (len(df) * 0.05) else "FAILS (HIGH DRIFT)"
            elif name.endswith(('.pt', '.pth')):
                state = torch.load(path, map_location="cpu", weights_only=True)
                if hasattr(state, 'state_dict'):
                    state = state.state_dict()
                nan_layers = [k for k, v in state.items() if isinstance(v, torch.Tensor) and torch.isnan(v).any()]
                report["checks"].append({"nan_layers_detected": len(nan_layers), "total_keys": len(state)})
                report["verdict"] = "HOLDS" if not nan_layers else "FAILS (CORRUPT WEIGHTS)"
            elif name.endswith(('.png', '.jpg', '.jpeg')):
                img = Image.open(path)
                img.verify()
                report["checks"].append({"format": img.format, "res": f"{img.width}x{img.height}"})
                report["verdict"] = "HOLDS"
        except Exception as e:
            report["verdict"] = f"CRITICAL_FAILURE: {str(e)}"
        batch_results.append(report)
        cert_paths.append(generate_pdf(report, os.path.basename(path)))
    return json.dumps(batch_results, indent=2), cert_paths

# --- 3. Gradio Interface ---
interface = gr.Interface(
    fn=run_audit,
    inputs=gr.File(label="Upload Assets (Select multiple for Batch Mode)", file_count="multiple"),
    outputs=[
        gr.Code(label="Batch Audit Trail (JSON)"),
        gr.File(label="Download Audit Certificates (PDFs)")
    ],
    title="Tessrax Hardened Audit Pipeline",
    description="Secure, headless-ready validation for Tabular, Tensor, and Vision assets."
)

interface.launch(share=True)
print('Audit engine launched.')
