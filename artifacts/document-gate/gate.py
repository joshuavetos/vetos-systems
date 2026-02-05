#!/usr/bin/env python3
"""
Document Gate — v1.5 (LOCKED)

Deterministic, fail-closed validation gate for document ingestion.
"""

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

TOOL_VERSION = "1.5.0"
TELEMETRY_SCHEMA_VERSION = "doc_gate_telemetry_v1"

@dataclass(frozen=True)
class GateConfig:
    min_year_anchors: int
    min_fiscal_anchors_unique: int
    min_fiscal_anchor_lines: int
    horizon_years_forward: int
    year_floor: int
    capture_context: bool
    max_context_chars: int
    currency_symbols: Tuple[str, ...]

DEFAULT_CONFIG = GateConfig(
    min_year_anchors=2,
    min_fiscal_anchors_unique=3,
    min_fiscal_anchor_lines=2,
    horizon_years_forward=30,
    year_floor=1900,
    capture_context=True,
    max_context_chars=240,
    currency_symbols=("$",),
)

def normalize_unicode_currency(text: str) -> str:
    mappings = {
        "＄": "$", "¢": "$", "₿": "$",
        "€": "€", "£": "£", "¥": "¥",
    }
    for k, v in mappings.items():
        text = text.replace(k, v)
    return text

def build_currency_pattern(currency_symbols: Tuple[str, ...]) -> Optional[re.Pattern]:
    if not currency_symbols:
        return None
    sym = "|".join(re.escape(s) for s in currency_symbols)
    pat = rf"(?<!\w)(?P<sym>{sym})\s*(?P<num>\d{{1,3}}(?:,\d{{3}})*|\d+)(?P<dec>\.\d{{2}})?(?!\w)"
    return re.compile(pat)

def build_year_pattern() -> re.Pattern:
    unit_blockers = (
        r"units?|percent|%|tons?|kg|lbs?|items?|shares?|"
        r"thousand|million|billion|trillion|"
        r"dollars?|usd|eur|yen|pounds?"
    )
    return re.compile(
        r"(?i)\b("
        r"(?:fy|fiscal(?:\s+year)?|cy|calendar(?:\s+year)?|year|period)"
        r"\s*[:\-]?\s*(19\d{2}|20\d{2})(?!\s+" + unit_blockers + r")"
        r"|"
        r"(19\d{2}|20\d{2})\s+(?:fy|fiscal(?:\s+year)?|cy|calendar(?:\s+year)?)"
        r"|"
        r"(?:in|for)\s+(19\d{2}|20\d{2})(?!\s+" + unit_blockers + r")"
        r")\b"
    )

YEAR_CTX_RE = build_year_pattern()

def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def safe_trim(s: str, max_chars: int) -> str:
    s = s.strip().replace("\t", " ").replace("\n", " ")
    return s if len(s) <= max_chars else s[:max_chars - 3] + "..."

def validate_input_path(input_path: str):
    if not input_path or not input_path.strip():
        return False, "invalid_input_path", "empty_path"
    try:
        p = os.path.abspath(input_path)
    except Exception:
        return False, "invalid_input_path", "path_resolution_failed"
    if not os.path.exists(p):
        return False, "input_not_found", p
    if not os.path.isfile(p):
        return False, "input_not_a_file", p
    return True, None, p

def ensure_dir(path: str):
    try:
        os.makedirs(path, exist_ok=True)
        return None
    except Exception as e:
        return str(e)

def write_text(path: str, content: str):
    try:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return None
    except Exception as e:
        return str(e)

def write_json(path: str, obj: dict):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
        return None
    except Exception as e:
        return str(e)

def normalize_currency(sym: str, num: str, dec: Optional[str]) -> str:
    return f"{sym}{num.replace(',', '')}{dec if dec else '.00'}"

def extract_year_anchors(text: str, year_floor: int, year_ceiling: int) -> List[int]:
    years = []
    for m in YEAR_CTX_RE.finditer(text):
        y = m.group(2) or m.group(3) or m.group(4)
        if y:
            yi = int(y)
            if year_floor <= yi <= year_ceiling:
                years.append(yi)
    return sorted(set(years))

def extract_currency_anchors(text, currency_re, capture_context, max_context_chars):
    text = normalize_unicode_currency(text)
    values, contexts, lines = [], [], set()
    if not currency_re:
        return values, contexts, 0
    for i, line in enumerate(text.splitlines()):
        matched = False
        for m in currency_re.finditer(line):
            norm = normalize_currency(m.group("sym"), m.group("num"), m.group("dec"))
            values.append(norm)
            matched = True
            if capture_context:
                contexts.append({
                    "value": norm,
                    "line_no": i + 1,
                    "context": safe_trim(line, max_context_chars),
                })
        if matched:
            lines.add(i + 1)
    return values, contexts, len(lines)

def run_gate(input_path, cfg):
    telemetry = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "timestamp": utc_now_iso(),
        "input_file": input_path,
        "config": cfg.__dict__,
        "anchors_found": {"years": [], "currency": {"all": [], "unique": [], "distinct_lines": 0}},
        "anchor_context": {"currency": []},
        "decision": None,
        "reason_code": None,
        "errors": [],
    }

    ok, code, detail = validate_input_path(input_path)
    if not ok:
        telemetry["decision"] = "FAIL"
        telemetry["reason_code"] = code
        telemetry["errors"].append({"type": code, "detail": detail})
        return f"FAIL:{code}", telemetry

    try:
        with open(detail, "r", encoding="utf-8") as f:
            text = f.read()
    except Exception as e:
        telemetry["decision"] = "FAIL"
        telemetry["reason_code"] = "file_read_error"
        telemetry["errors"].append({"type": "file_read_error", "detail": str(e)})
        return "FAIL:file_read_error", telemetry

    if not text.strip():
        telemetry["decision"] = "FAIL"
        telemetry["reason_code"] = "empty_input"
        return "FAIL:empty_input", telemetry

    year_ceiling = datetime.now(timezone.utc).year + cfg.horizon_years_forward
    years = extract_year_anchors(text, cfg.year_floor, year_ceiling)
    telemetry["anchors_found"]["years"] = years

    currency_re = build_currency_pattern(cfg.currency_symbols)
    all_vals, ctxs, distinct = extract_currency_anchors(
        text, currency_re, cfg.capture_context, cfg.max_context_chars
    )

    unique = sorted(set(all_vals))
    telemetry["anchors_found"]["currency"] = {
        "all": all_vals,
        "unique": unique,
        "distinct_lines": distinct,
    }

    if cfg.capture_context:
        telemetry["anchor_context"]["currency"] = ctxs[:200]

    if len(years) < cfg.min_year_anchors:
        telemetry["decision"] = "ABSTAIN"
        telemetry["reason_code"] = "insufficient_temporal_anchors"
    elif len(unique) < cfg.min_fiscal_anchors_unique:
        telemetry["decision"] = "ABSTAIN"
        telemetry["reason_code"] = "insufficient_fiscal_anchors_unique"
    elif distinct < cfg.min_fiscal_anchor_lines:
        telemetry["decision"] = "ABSTAIN"
        telemetry["reason_code"] = "insufficient_fiscal_anchor_lines"
    else:
        telemetry["decision"] = "PASS"
        telemetry["reason_code"] = "sufficient_anchors"

    return f"{telemetry['decision']}:{telemetry['reason_code']}", telemetry

def parse_args():
    p = argparse.ArgumentParser(description="Document Gate v1.5")
    p.add_argument("input_file", nargs="?", default="input/real_document.txt")
    p.add_argument("--min-year-anchors", type=int, default=DEFAULT_CONFIG.min_year_anchors)
    p.add_argument("--min-fiscal-unique", type=int, default=DEFAULT_CONFIG.min_fiscal_anchors_unique)
    p.add_argument("--min-fiscal-lines", type=int, default=DEFAULT_CONFIG.min_fiscal_anchor_lines)
    p.add_argument("--horizon-years-forward", type=int, default=DEFAULT_CONFIG.horizon_years_forward)
    p.add_argument("--year-floor", type=int, default=DEFAULT_CONFIG.year_floor)
    p.add_argument("--currency-symbols", type=str, default="$")
    p.add_argument("--no-context", action="store_true")
    p.add_argument("--max-context-chars", type=int, default=DEFAULT_CONFIG.max_context_chars)
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()

def main():
    args = parse_args()
    cfg = GateConfig(
        min_year_anchors=max(0, args.min_year_anchors),
        min_fiscal_anchors_unique=max(0, args.min_fiscal_unique),
        min_fiscal_anchor_lines=max(0, args.min_fiscal_lines),
        horizon_years_forward=max(0, args.horizon_years_forward),
        year_floor=args.year_floor,
        capture_context=not args.no_context,
        max_context_chars=max(40, args.max_context_chars),
        currency_symbols=tuple(s.strip() for s in args.currency_symbols.split(",") if s.strip()),
    )

    if args.dry_run:
        print(json.dumps({"tool_version": TOOL_VERSION, "config": cfg.__dict__}, indent=2))
        return 0

    result, telemetry = run_gate(args.input_file, cfg)

    if ensure_dir("output"):
        print(json.dumps(telemetry, indent=2))
        return 2

    write_text("output/result.txt", result)
    write_json("rejection.log", telemetry)
    print(f"Gate Terminal State: {result}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
