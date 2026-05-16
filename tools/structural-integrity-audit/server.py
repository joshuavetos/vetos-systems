import json
import os
import uuid
from pathlib import Path

import gradio as gr
import numpy as np
import pandas as pd
import torch
from fpdf import FPDF
from PIL import Image
from scipy import stats

EVIDENCE_ROOT = Path("evidence").resolve()
EVIDENCE_ROOT.mkdir(exist_ok=True)
MAX_REPORT_JSON_BYTES = 1_000_000
MAX_PDF_BYTES = 2_000_000
MAX_TENSOR_COUNT = 10_000
MAX_TENSOR_ELEMENTS = 50_000_000
MAX_CHECKPOINT_BYTES = 500_000_000
ALLOWED_TENSOR_DTYPES = {
    torch.float16,
    torch.float32,
    torch.float64,
    torch.bfloat16,
    torch.int8,
    torch.int16,
    torch.int32,
    torch.int64,
    torch.uint8,
    torch.bool,
}


class AuditCertificate(FPDF):
    def header(self):
        self.set_font("Arial", "B", 16)
        self.cell(0, 10, "STRUCTURAL INTEGRITY AUDIT: CERTIFICATE", 0, 1, "C")
        self.ln(10)


def _validate_report_payload(report):
    payload = json.dumps(report, indent=2, sort_keys=True, allow_nan=False)
    if len(payload.encode("utf-8")) > MAX_REPORT_JSON_BYTES:
        raise ValueError("report payload exceeds maximum JSON size")
    return payload


def _certificate_path():
    path = (EVIDENCE_ROOT / f"cert_{uuid.uuid4().hex}.pdf").resolve()
    if EVIDENCE_ROOT not in path.parents:
        raise ValueError("certificate path escapes evidence root")
    return path


def generate_pdf(report, filename):
    try:
        payload = _validate_report_payload(report)
        pdf = AuditCertificate()
        pdf.add_page()
        pdf.set_font("Courier", size=10)
        pdf.multi_cell(0, 5, payload)
        path = _certificate_path()
        pdf.output(str(path))
        if path.stat().st_size > MAX_PDF_BYTES:
            path.unlink(missing_ok=True)
            raise ValueError("generated PDF exceeds maximum size")
        return str(path)
    except Exception as exc:
        raise RuntimeError(f"PDF generation failed: {exc}") from exc


def _iter_tensors(state):
    if isinstance(state, torch.Tensor):
        yield "tensor", state
    elif isinstance(state, dict):
        for key, value in state.items():
            if isinstance(value, torch.Tensor):
                yield str(key), value
            elif isinstance(value, dict):
                for nested_key, tensor in _iter_tensors(value):
                    yield f"{key}.{nested_key}", tensor


def _load_torch_state(path):
    if Path(path).stat().st_size > MAX_CHECKPOINT_BYTES:
        raise ValueError("checkpoint exceeds maximum allowed size")
    state = torch.load(path, map_location="cpu", weights_only=True)
    if hasattr(state, "state_dict"):
        state = state.state_dict()
    tensors = list(_iter_tensors(state))
    if not tensors:
        raise ValueError("checkpoint contains no tensors")
    if len(tensors) > MAX_TENSOR_COUNT:
        raise ValueError("checkpoint contains too many tensors")
    total_elements = 0
    for name, tensor in tensors:
        if tensor.dtype not in ALLOWED_TENSOR_DTYPES:
            raise ValueError(f"tensor {name} has disallowed dtype {tensor.dtype}")
        total_elements += tensor.numel()
        if total_elements > MAX_TENSOR_ELEMENTS:
            raise ValueError("checkpoint exceeds tensor element ceiling")
    return state, tensors


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
            if name.endswith(".csv"):
                df = pd.read_csv(path)
                numeric_cols = df.select_dtypes(include=[np.number])
                outliers = (
                    int((np.abs(stats.zscore(numeric_cols.fillna(0))) > 3).sum().sum())
                    if not numeric_cols.empty
                    else 0
                )
                report["checks"].append(
                    {
                        "nulls": int(df.isnull().sum().sum()),
                        "outliers_detected": outliers,
                        "rows": len(df),
                    }
                )
                report["verdict"] = "HOLDS" if outliers < (len(df) * 0.05) else "FAILS (HIGH DRIFT)"
            elif name.endswith((".pt", ".pth")):
                _state, tensors = _load_torch_state(path)
                nan_layers = [
                    key
                    for key, tensor in tensors
                    if torch.is_floating_point(tensor) and torch.isnan(tensor).any()
                ]
                total_elements = sum(tensor.numel() for _key, tensor in tensors)
                report["checks"].append(
                    {
                        "nan_layers_detected": len(nan_layers),
                        "total_keys": len(tensors),
                        "total_elements": total_elements,
                    }
                )
                report["verdict"] = "HOLDS" if not nan_layers else "FAILS (CORRUPT WEIGHTS)"
            elif name.endswith((".png", ".jpg", ".jpeg")):
                img = Image.open(path)
                img.verify()
                report["checks"].append({"format": img.format, "res": f"{img.width}x{img.height}"})
                report["verdict"] = "HOLDS"
            else:
                report["verdict"] = "CRITICAL_FAILURE: unsupported file type"
        except Exception as e:
            report["verdict"] = f"CRITICAL_FAILURE: {str(e)}"
        batch_results.append(report)
        try:
            cert_paths.append(generate_pdf(report, os.path.basename(path)))
        except Exception as exc:
            report["checks"].append({"pdf_error": str(exc)})
    return json.dumps(batch_results, indent=2, sort_keys=True, allow_nan=False), cert_paths


interface = gr.Interface(
    fn=run_audit,
    inputs=gr.File(label="Upload Assets (Select multiple for Batch Mode)", file_count="multiple"),
    outputs=[
        gr.Code(label="Batch Audit Trail (JSON)"),
        gr.File(label="Download Audit Certificates (PDFs)"),
    ],
    title="Tessrax Hardened Audit Pipeline",
    description="Secure, headless-ready validation for Tabular, Tensor, and Vision assets.",
)

if __name__ == "__main__":
    interface.launch(share=True)
    print("Audit engine launched.")
