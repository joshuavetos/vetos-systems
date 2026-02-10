import os
import shutil
import uvicorn
import pandas as pd
import numpy as np
import torch
import json
import chardet
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import FileResponse
from PIL import Image
from fpdf import FPDF

# --- Configuration ---
app = FastAPI(title="Structural Integrity Audit API")
os.makedirs("evidence", exist_ok=True)
report_registry = {}

# --- PDF Generator ---
class PDFReportGenerator(FPDF):
    def header(self):
        self.set_font("Arial", "B", 14)
        self.cell(0, 10, "Structural Integrity Audit Certificate", 0, 1, "C")
        self.ln(6)

    def generate(self, report, output_path):
        self.add_page()
        self.set_font("Arial", "", 11)

        self.cell(0, 8, f"Type: {report.get('type')}", 0, 1)
        self.set_font("Arial", "B", 12)
        self.cell(0, 8, f"Verdict: {report.get('verdict')}", 0, 1)
        self.set_font("Arial", "", 11)
        self.ln(4)

        self.cell(80, 8, "Check", 1)
        self.cell(100, 8, "Result", 1)
        self.ln()

        for check in report.get("checks", []):
            for k, v in check.items():
                self.cell(80, 8, str(k), 1)
                self.cell(100, 8, str(v), 1)
                self.ln()

        self.output(output_path)

# --- Core Audit Logic ---
def analyze_input(text, file):
    report = {
        "type": None,
        "checks": [],
        "verdict": "UNKNOWN",
        "evidence_files": []
    }

    def extract_tensors(obj):
        if isinstance(obj, torch.Tensor):
            return [obj]
        if isinstance(obj, dict):
            return sum((extract_tensors(v) for v in obj.values()), [])
        if isinstance(obj, (list, tuple)):
            return sum((extract_tensors(v) for v in obj), [])
        return []

    try:
        path = file.name
        name = path.lower()

        # --- CSV ---
        if name.endswith(".csv"):
            report["type"] = "tabular"
            with open(path, "rb") as f:
                encoding = chardet.detect(f.read(10000))["encoding"]

            df = pd.read_csv(path, encoding=encoding)
            null_rows = df[df.isnull().any(axis=1)]
            dup_rows = df[df.duplicated()]

            report["checks"].append({"encoding": encoding})
            report["checks"].append({"null_rows": int(len(null_rows))})
            report["checks"].append({"duplicate_rows": int(len(dup_rows))})

            if len(null_rows) or len(dup_rows):
                ev = f"evidence/sample_{os.path.basename(path)}"
                pd.concat([null_rows.head(), dup_rows.head()]).to_csv(ev)
                report["evidence_files"].append(ev)
                report["verdict"] = "FAILS"
            else:
                report["verdict"] = "HOLDS"

        # --- IMAGE ---
        elif name.endswith((".png", ".jpg", ".jpeg", ".gif", ".tif", ".tiff")):
            report["type"] = "image"
            img = Image.open(path)
            frames = getattr(img, "n_frames", 1)
            report["checks"].append({
                "dimensions": f"{img.width}x{img.height}",
                "mode": img.mode,
                "frames": frames
            })
            report["verdict"] = "HOLDS"

        # --- TORCH MODEL ---
        elif name.endswith((".pt", ".pth")):
            report["type"] = "model"
            state = torch.load(path, map_location="cpu", weights_only=True)
            tensors = extract_tensors(state)

            nan_layers = []
            for k, v in state.items():
                if isinstance(v, torch.Tensor) and torch.isnan(v).any():
                    nan_layers.append(k)

            report["checks"].append({"tensor_count": len(tensors)})
            report["checks"].append({"nan_layers": nan_layers})

            if nan_layers:
                ev = f"evidence/nans_{os.path.basename(path)}.log"
                with open(ev, "w") as f:
                    f.write("\n".join(nan_layers))
                report["evidence_files"].append(ev)
                report["verdict"] = "FAILS"
            else:
                report["verdict"] = "HOLDS"

        # --- TEXT ---
        elif text.strip():
            report["type"] = "text"
            report["checks"].append({"length": len(text)})
            report["verdict"] = "ACKNOWLEDGED"

        else:
            report["verdict"] = "FAILS"

    except Exception as e:
        report["verdict"] = "FAILS"
        report["checks"].append({"error": str(e)})

    return report

# --- API ---
@app.post("/audit")
async def audit(file: UploadFile = File(...)):
    tmp = f"_tmp_{file.filename}"
    with open(tmp, "wb") as f:
        shutil.copyfileobj(file.file, f)

    class F:
        def __init__(self, name): self.name = name

    report = analyze_input("", F(tmp))
    report_registry[file.filename] = report
    os.remove(tmp)
    return report

@app.post("/batch-audit")
async def batch(directory_path: str = Form(...)):
    results = {}
    for fn in os.listdir(directory_path):
        p = os.path.join(directory_path, fn)
        if os.path.isfile(p):
            class F:
                def __init__(self, name): self.name = name
            results[fn] = analyze_input("", F(p))
    return results

@app.post("/certificate")
async def certificate(report_id: str):
    pdf_path = f"evidence/certificate_{report_id}.pdf"
    pdf = PDFReportGenerator()
    pdf.generate(report_registry[report_id], pdf_path)
    return FileResponse(pdf_path, filename=os.path.basename(pdf_path))

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
