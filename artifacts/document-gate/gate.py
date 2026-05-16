#!/usr/bin/env python3
"""
Document Gate — v1.6 (LOCKED)

Deterministic, fail-closed validation gate for document ingestion.
Anchor-density based. Audit-safe. DoS-aware.
"""

import argparse
import json
import os
import re
import unicodedata
import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List, Optional, Tuple

TOOL_VERSION = "1.6.0"
TELEMETRY_SCHEMA_VERSION = "doc_gate_telemetry_v1"

MAX_FILE_BYTES = 5_000_000  # 5MB hard stop

# =========================
# CONFIG
# =========================
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
    currency_symbols=("$", "€", "£", "¥"),
)

# =========================
# NORMALIZATION
# =========================
def normalize_text(text: str) -> str:
    return unicodedata.normalize("NFC", text)

def normalize_unicode_currency(text: str) -> str:
    mappings = {
        "＄": "$", "¢": "$", "₿": "$",
        "€": "€", "£": "£", "¥": "¥",
    }
    for k, v in mappings.items():
        text = text.replace(k, v)
    return text

# =========================
# REGEX BUILDERS
# =========================
def build_currency_pattern(currency_symbols: Tuple[str, ...]) -> Optional[re.Pattern]:
    if not currency_symbols:
        return None
    sym = "|".join(re.escape(s) for s in currency_symbols)
    pat = rf"""
    (?<!\w)
    (?P<neg>\(|-)?     
    (?P<sym>{sym})
    \s*
    (?P<num>\d{{1,3}}(?:,\d{{3}})*|\d+)
    (?P<dec>\.\d{{2}})?
    \)?
    (?!\w)
    """
    return re.compile(pat, re.VERBOSE)

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
        r"(?:in|for)\s+(19\d{2})(?!\s+" + unit_blockers + r")"
        r")\b"
    )

YEAR_CTX_RE = build_year_pattern()

# =========================
# UTIL
# =========================
def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

def safe_trim(s: str, max_chars: int) -> str:
    s = s.strip().replace("\t", " ").replace("\n", " ")
    return s if len(s) <= max_chars else s[: max_chars - 3] + "..."

def validate_input_path(input_path: str):
    if not input_path or not input_path.strip():
        return False, "invalid_input_path", "empty_path"
    p = os.path.abspath(input_path)
    if not os.path.exists(p):
        return False, "input_not_found", p
    if not os.path.isfile(p):
        return False, "input_not_a_file", p
    if os.path.getsize(p) > MAX_FILE_BYTES:
        return False, "input_too_large", p
    return True, None, p

# =========================
# EXTRACTION
# =========================
def extract_year_anchors(text: str, year_floor: int, year_ceiling: int) -> List[int]:
    years = set()
    for line in text.splitlines():
        for m in YEAR_CTX_RE.finditer(line):
            y = m.group(2) or m.group(3) or m.group(4)
            if y:
                yi = int(y)
                if year_floor <= yi <= year_ceiling:
                    years.add(yi)
    return sorted(years)

def normalize_currency(sym: str, num: str, dec: Optional[str], neg: Optional[str]) -> str:
    val = f"{sym}{num.replace(',', '')}{dec if dec else '.00'}"
    return f"-{val}" if neg and neg != "(" else val

def extract_currency_anchors(text, currency_re, capture_context, max_context_chars):
    values, contexts, lines = [], [], set()
    if not currency_re:
        return values, contexts, 0

    for i, line in enumerate(text.splitlines()):
        matched = False
        for m in currency_re.finditer(line):
            norm = normalize_currency(
                m.group("sym"),
                m.group("num"),
                m.group("dec"),
                m.group("neg"),
            )
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

# =========================
# GATE
# =========================
def run_gate(input_path, cfg):
    telemetry = {
        "schema_version": TELEMETRY_SCHEMA_VERSION,
        "tool_version": TOOL_VERSION,
        "timestamp": utc_now_iso(),
        "input_file": input_path,
        "config": cfg.__dict__,
        "derived_limits": {},
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
            text = normalize_text(f.read())
            text = normalize_unicode_currency(text)
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
    telemetry["derived_limits"]["year_ceiling"] = year_ceiling

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
        telemetry["reason_code"] = "insufficient_fiscal_anchor_density"
    elif distinct < cfg.min_fiscal_anchor_lines:
        telemetry["decision"] = "ABSTAIN"
        telemetry["reason_code"] = "insufficient_fiscal_anchor_lines"
    else:
        telemetry["decision"] = "PASS"
        telemetry["reason_code"] = "sufficient_anchor_density"

    telemetry["telemetry_hash"] = hashlib.sha256(
        json.dumps(telemetry, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()

    return f"{telemetry['decision']}:{telemetry['reason_code']}", telemetry

# =========================
# CLI
# =========================
def main():
    p = argparse.ArgumentParser(description="Document Gate v1.6")
    p.add_argument("input_file", nargs="?", default="input/real_document.txt")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    cfg = DEFAULT_CONFIG

    if args.dry_run:
        print(json.dumps({"tool_version": TOOL_VERSION, "config": cfg.__dict__}, indent=2))
        return 0

    result, telemetry = run_gate(args.input_file, cfg)

    os.makedirs("output", exist_ok=True)
    with open("output/result.txt", "w", encoding="utf-8") as f:
        f.write(result)
    with open("output/rejection.log", "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2, ensure_ascii=False)

    print(f"Gate Terminal State: {result}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
