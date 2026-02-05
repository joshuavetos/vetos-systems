import hashlib
import re
import json
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import date

# 1. Global State Registries
REJECTED_YEARS_LOG = []
EXTRACTION_STATS = {}
FILING_STATS = {}
FILING_QUALITY_ALERTS = {}

# 2. System Constants and Configurations
MIN_VALID_YEAR = 1900
MAX_VALID_YEAR = 2100

CURRENCY_SANITY_BOUNDS = {
    'min': 0.0,
    'max': 10_000_000_000.0  # 10 Billion baseline
}

CONTEXT_SANITY_BOUNDS = {
    'ANNUAL_REPORT': {'min': 1800, 'max': 2100},
    'PRESS_RELEASE': {'min': 1900, 'max': 2100},
    'DEFAULT': {'min': 1900, 'max': 2100}
}

REJECTION_THRESHOLDS = {
    'ANNUAL_REPORT': 0.3,
    'PRESS_RELEASE': 0.5,
    'DEFAULT': 0.3
}

# 3. Utility Functions
def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

def canonicalize_text(text: str) -> str:
    return " ".join(text.split())

def hash_canonical_text(text: str) -> str:
    return sha256_bytes(canonicalize_text(text).encode("utf-8"))

def get_context_snippet(text: str, start_idx: int, end_idx: int, window: int = 25) -> str:
    snippet_start = max(0, start_idx - window)
    snippet_end = min(len(text), end_idx + window)
    return text[snippet_start:snippet_end]

def preprocess_temporal_metadata(text: str, filing_type: str, source_class: str) -> str:
    """
    Standardizes raw year tokens by injecting qualifiers (year/period).
    Ensures compatibility with hardened regex patterns.
    """
    if not text: return ""
    recognized = {'year', 'period', 'dates', 'through', 'covers', 'ending', 'starting', 'fy'}
    token_pattern = r"\b\d{4}(?:[-/]\d{2,4})?\b"
    def replacer(match):
        token = match.group(0)
        preceding = text[:match.start()].rstrip()
        prev_match = re.search(r"\b(\w+)\b$", preceding, re.IGNORECASE)
        if prev_match and prev_match.group(1).lower() in recognized: return token
        try:
            val = int(token[:4])
            if 1900 <= val <= 2100: 
                return f"{'period' if '-' in token or '/' in token else 'year'} {token}"
        except ValueError: pass
        return token
    return re.sub(token_pattern, replacer, text)

# 4. Data Model
@dataclass
class Filing:
    filing_type: str
    source_class: str
    identifier: str
    accepted_date: date
    raw_bytes: bytes
    text: Optional[str]
    raw_hash: str = field(init=False)
    canonical_hash: str = field(init=False)

    def __post_init__(self):
        if self.raw_bytes is None: raise ValueError("raw_bytes must not be None")
        self.raw_hash = sha256_bytes(self.raw_bytes)
        if self.text:
            self.text = preprocess_temporal_metadata(self.text, self.filing_type, self.source_class)
        self.canonical_hash = hash_canonical_text(self.text or "")

# 5. Core Extraction Logic
def extract_currency_amounts(text: str) -> List[Dict]:
    """
    Parses currency with sign detection and unit scaling (million/billion).
    """
    multipliers = {'m': 1e6, 'million': 1e6, 'b': 1e9, 'billion': 1e9}
    pattern = r"(?i)(?<![\w.])(?P<sign>-?)\$(?P<value>\d{1,3}(?:,\d{3})*(?:\.\d{2})?)(?:\s*(?P<unit>million|billion|m|b))?(?!\d)"
    results = []
    for match in re.finditer(pattern, text):
        sign, val_str, unit = match.group('sign'), match.group('value'), match.group('unit')
        try:
            amt = float(val_str.replace(",", ""))
            if sign == '-': amt = -amt
            if unit: amt *= multipliers.get(unit.lower(), 1)
            results.append({'amount': amt, 'start': match.start(), 'end': match.end()})
        except ValueError: continue
    return results

def expand_year_range(range_str: str, rollover_window: int = 20, filing_id: str = None, filing_type: str = None, min_year: int = 1900, max_year: int = 2100, snippet: str = None) -> List[int]:
    if rollover_window > 100: raise ValueError("rollover_window exceeds 100 years")
    match = re.match(r"(\d{4})[-/](\d{2,4})", range_str)
    if not match: return []
    start_year, end_val = int(match.group(1)), match.group(2)
    if len(end_val) == 2:
        century = (start_year // 100) * 100
        end_year = century + int(end_val)
        if end_year < start_year and (end_year + 100 - start_year) <= rollover_window: end_year += 100
    else: end_year = int(end_val)
    raw_years = list(range(start_year, end_year + 1)) if end_year >= start_year else [start_year]

    if filing_type: EXTRACTION_STATS.setdefault(filing_type, {"total_matches": 0})["total_matches"] += len(raw_years)
    if filing_id: FILING_STATS.setdefault(filing_id, {"total_matches": 0})["total_matches"] += len(raw_years)

    filtered = []
    for y in raw_years:
        if min_year <= y <= max_year: filtered.append(y)
        else: REJECTED_YEARS_LOG.append({'year': y, 'filing_id': filing_id, 'filing_type': filing_type, 'context': 'range_expansion', 'snippet': snippet})
    return filtered

def r3_classify(filing: Filing, required_years: List[int], rollover_window: int = 20) -> Tuple[str, Dict[int, bool]]:
    """
    Classifies filing, detects speculative intent, and applies context-aware bounds.
    """
    if not filing.text: return "R3_NON_PARSABLE", {y: False for y in required_years}
    f_id, f_type = filing.identifier, filing.filing_type
    FILING_STATS.setdefault(f_id, {"total_matches": 0})
    EXTRACTION_STATS.setdefault(f_type, {"total_matches": 0})

    is_speculative = any(kw in filing.text.lower() for kw in ['forecast', 'projection', 'outlook', 'future', 'planned'])
    bounds = CONTEXT_SANITY_BOUNDS.get(f_type, CONTEXT_SANITY_BOUNDS['DEFAULT'])
    min_y, max_y = bounds['min'], (2200 if is_speculative else bounds['max'])
    curr_min, curr_max = CURRENCY_SANITY_BOUNDS['min'], (100_000_000_000.0 if is_speculative else CURRENCY_SANITY_BOUNDS['max'])

    found_years = set()
    year_pattern = r"(?i)\b(?:FY\s*(?P<fy>\d{2,4})|(?:year|period|dates|through|covers|ending|starting)\s+(?P<range>\d{4}[-/]\d{2,4})|(?:year|period|dates|through|covers|ending|starting)\s+(?P<year>\d{4}))\b"
    for match in re.finditer(year_pattern, filing.text):
        snippet = get_context_snippet(filing.text, match.start(), match.end())
        if match.group('fy'):
            FILING_STATS[f_id]["total_matches"] += 1; EXTRACTION_STATS[f_type]["total_matches"] += 1
            yr = 2000 + int(match.group('fy')) if len(match.group('fy')) == 2 else int(match.group('fy'))
            if min_y <= yr <= max_y: found_years.add(yr)
            else: REJECTED_YEARS_LOG.append({'year': yr, 'filing_id': f_id, 'filing_type': f_type, 'context': 'fiscal_year', 'snippet': snippet})
        elif match.group('range'):
            found_years.update(expand_year_range(match.group('range'), rollover_window, f_id, f_type, min_y, max_y, snippet))
        elif match.group('year'):
            FILING_STATS[f_id]["total_matches"] += 1; EXTRACTION_STATS[f_type]["total_matches"] += 1
            yr = int(match.group('year'))
            if min_y <= yr <= max_y: found_years.add(yr)
            else: REJECTED_YEARS_LOG.append({'year': yr, 'filing_id': f_id, 'filing_type': f_type, 'context': 'standard_year', 'snippet': snippet})

    for info in extract_currency_amounts(filing.text):
        amt, snippet = info['amount'], get_context_snippet(filing.text, info['start'], info['end'])
        FILING_STATS[f_id]["total_matches"] += 1; EXTRACTION_STATS[f_type]["total_matches"] += 1
        if not (curr_min <= amt <= curr_max): REJECTED_YEARS_LOG.append({'year': amt, 'filing_id': f_id, 'filing_type': f_type, 'context': 'currency', 'snippet': snippet})

    evaluate_filing_quality(f_id, f_type)
    year_map = {y: y in found_years for y in required_years}
    status = "R3_PARSABLE_COMPLETE" if all(year_map.values()) else "R3_PARSABLE_PARTIAL" if any(year_map.values()) else "R3_NON_PARSABLE"
    return status, year_map

# 6. Analysis and Quality Engine
def compute_delta(years: List[int], primary_plan: Filing, other_filings: List[Filing]) -> Dict[int, int]:
    C = {y: 0 for y in years}
    _, p_years = r3_classify(primary_plan, years)
    for y, ok in p_years.items():
        if ok: C[y] = 1
    for f in other_filings:
        status, year_map = r3_classify(f, years)
        if status in ("R3_PARSABLE_COMPLETE", "R3_PARSABLE_PARTIAL"): 
            for y, ok in year_map.items():
                if ok: C[y] = 1
    return C

def evaluate_filing_quality(filing_id: str, filing_type: str) -> str:
    rejections = [e for e in REJECTED_YEARS_LOG if e['filing_id'] == filing_id]
    total = FILING_STATS.get(filing_id, {"total_matches": 0})["total_matches"]
    rate = (len(rejections) / total) if total > 0 else 0.0
    threshold = REJECTION_THRESHOLDS.get(filing_type, REJECTION_THRESHOLDS['DEFAULT'])
    status = "SIDELINE_FOR_REVIEW" if rate > threshold else "READY_FOR_PROCESSING"
    FILING_QUALITY_ALERTS[filing_id] = {"rejection_rate": round(rate, 4), "threshold_applied": threshold, "status": status, "rejections": len(rejections), "total_attempts": total}
    return status

def null_identifier_engine(issuer_name: str, target_years: List[int], primary_plan: Filing, supplemental_filings: List[Filing]) -> Dict:
    C_y = compute_delta(target_years, primary_plan, supplemental_filings)
    null_years = [y for y, val in C_y.items() if val == 0]
    all_involved = [primary_plan.identifier] + [f.identifier for f in supplemental_filings]
    fidelity = {fid: FILING_QUALITY_ALERTS.get(fid, {"status": "DATA_NOT_FOUND", "rejection_rate": None}) for fid in all_involved}
    return {"issuer_name": issuer_name, "coverage_vector": C_y, "null_years": null_years, "fidelity_report": fidelity}

# 7. Diagnostic Utilities
def generate_reliability_ranking() -> List[Dict]:
    rejection_counts = {}
    for entry in REJECTED_YEARS_LOG:
        f_type = entry.get('filing_type') or 'UNKNOWN'
        rejection_counts[f_type] = rejection_counts.get(f_type, 0) + 1
    rankings = []
    for f_type, stats in EXTRACTION_STATS.items():
        total = stats.get('total_matches', 0)
        rejections = rejection_counts.get(f_type, 0)
        score = 1.0 - (rejections / total) if total > 0 else 1.0
        rankings.append({'filing_type': f_type, 'total_matches': total, 'total_rejections': rejections, 'reliability_score': round(score, 4)})
    rankings.sort(key=lambda x: x['reliability_score'], reverse=True)
    return rankings

def generate_diagnostic_summary() -> Dict[str, int]:
    summary = {}
    for entry in REJECTED_YEARS_LOG:
        ctx = entry.get('context', 'unknown')
        summary[ctx] = summary.get(ctx, 0) + 1
    return summary

print('Filing Analysis System (MVP v1.0) Logic Loaded Verbatim.')


⸻

README.md

# Tessrax Engine — Boundary Declaration

This repository holds **executed mechanisms** for testing whether public claims are supported by disclosed capital allocation within bounded fiscal horizons.

It is not a rating system.
It is not an audit firm.
It does not issue judgments, scores, certifications, or recommendations.

## What This System Does

- Accepts **primary issuer artifacts** (e.g., SEC filings, adopted budgets).
- Extracts **explicit temporal and capital disclosures**.
- Computes mechanical gaps between:
  - stated vision horizons, and
  - disclosed funding horizons.
- Produces **deterministic receipts** or **halts** when evaluation is not possible.

Outputs are factual descriptions of what was found in the documents provided.
No inference is made about intent, ethics, compliance, or truthfulness.

## What This System Refuses to Do

- It does not determine whether a company is “good,” “bad,” “misleading,” or “compliant.”
- It does not estimate undisclosed capital.
- It does not interpolate missing data.
- It does not continue when required inputs are absent or ambiguous.
- It does not guarantee a result.

Silence, refusal, or “UNVERIFIED” are correct outcomes.

## Use by Anyone

Anyone may run the same test with the same inputs and obtain the same result.
Disagreement can only arise from:
- different documents, or
- violated input requirements.

Interpretation belongs to humans, downstream.

## Status

This repository prioritizes **mechanical honesty over coverage**.
If a claim cannot be tested, the system stops.

That behavior is intentional.


⸻

CANON.md

# CANON — Authority and Hierarchy

## Governing Theory

This repository operates under **Tessrax**, a contradiction-metabolism framework.

Tessrax treats unresolved appearance–reality mismatches as governance facts.
Refusal and silence are first-class, correct outcomes.

## Hierarchy (Enforced)

All content in this repository must declare its level:

1. Theory — Tessrax (governing, external to this repo)
2. Primitive — e.g., Null Identifier
3. Mechanism — executable engines implementing primitives
4. Case — receipts from executed runs

This repository contains **Mechanisms and Cases only**.

No file in this repository may redefine theory or primitives.

## Authority Rules

- Mechanisms do not gain authority by popularity, usage, or repetition.
- Reproducibility does not imply correctness beyond stated bounds.
- Absence of output is not failure.
- Expansion of scope requires a new mechanism, not reinterpretation.

## Contribution Constraint

Contributions that:
- add interpretation,
- add scoring or ranking,
- infer intent,
- soften refusal behavior,

are out of scope by definition.

This canon exists to prevent drift, not to encourage growth.


⸻

STATUS.md

# STATUS — Truth Table

This file records **what exists**, **what has been executed**, and **what is unknown**.
No projections. No guarantees.

## Mechanisms

- mvp_v1.py
  - Status: EXISTS
  - Execution: VERIFIED (field-tested)
  - Repo state: NOT YET COMMITTED
  - Scope: Filing analysis + planning gap detection
  - Guarantees: NONE

- money.md
  - Status: VERIFIED / OPERATIONAL
  - Classification: Mechanism
  - Notes: Preserved verbatim

## Cases

- Executed cases exist: YES
- Entities tested: YES (not enumerated here)
- Case files committed: NO

## Interfaces

- Public interface: NONE
- API: NONE
- Scores / ratings: NONE

## Unknowns / Not Declared

- External coverage limits
- Jurisdictional completeness
- Long-horizon edge cases

Any item not explicitly listed above is UNKNOWN.


⸻

