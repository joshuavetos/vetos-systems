from __future__ import annotations

import re
import json
import hashlib
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import date


@dataclass(frozen=True)
class Filing:
    identifier: str
    filing_type: str
    accepted_date: date
    processed_text: str

# --- 1. Hardened Telemetry ---
class Telemetry:
    def __init__(self):
        self.rejections = []
        self.extraction_stats = {}
        self.filing_stats = {}

    def log_rejection(self, entry: dict):
        self.rejections.append(entry)

    def update_stats(self, filing_id: str, filing_type: str, count: int):
        self.extraction_stats.setdefault(filing_type, {"total_matches": 0})["total_matches"] += count
        self.filing_stats.setdefault(filing_id, {"total_matches": 0})["total_matches"] += count

    def get_summary(self):
        rejection_counts = {}
        for entry in self.rejections:
            f_type = entry.get('filing_type', 'UNKNOWN')
            rejection_counts[f_type] = rejection_counts.get(f_type, 0) + 1
        
        rankings = []
        for f_type, stats in self.extraction_stats.items():
            total = stats.get('total_matches', 0)
            rej = rejection_counts.get(f_type, 0)
            # Reliability is 0 if no data found
            score = round(1.0 - (rej / total), 4) if total > 0 else 0.0
            rankings.append({'filing_type': f_type, 'reliability_score': score})
        
        return {
            "total_rejections": len(self.rejections),
            "reliability_rankings": sorted(rankings, key=lambda x: x['reliability_score'], reverse=True)
        }

# --- 2. Final Consolidated Auditor ---
class FilingAuditor:
    def __init__(self, target_years: List[int]):
        self.target_years = target_years
        self.coverage = {y: 0 for y in target_years}
        self.telemetry = Telemetry()
        
    def _resolve_year_token(self, token: str, reference_date: date) -> int:
        clean_token = re.sub(r"\D", "", token)
        if not clean_token: raise ValueError("Empty token")
        if len(clean_token) == 4: return int(clean_token)
        if len(clean_token) == 2:
            pivot_year = reference_date.year
            century = (pivot_year // 100) * 100
            year_val = century + int(clean_token)
            if year_val > pivot_year + 20: year_val -= 100
            return year_val
        raise ValueError(f"Ambiguous: {token}")

    def _normalize_reference_date(self, accepted_date: date | str) -> date:
        if isinstance(accepted_date, date):
            return accepted_date
        if isinstance(accepted_date, str):
            return date.fromisoformat(accepted_date)
        raise TypeError("accepted_date must be a date or ISO-8601 string")

    def _extract_currency(self, text: str) -> List[Dict]:
        multipliers = {'m': 1e6, 'million': 1e6, 'b': 1e9, 'billion': 1e9}
        # Hardened pattern with forced boundary for shorthand units
        pattern = r"(?i)(?<![\w.])(?P<sign>-?)\$((?P<value>(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d{2})?)(?:\s*(?P<unit>million|billion|m|b))?)(?![\d])"
        results = []
        for match in re.finditer(pattern, text):
            g = match.groupdict()
            try:
                val = float(g['value'].replace(",", ""))
                if g['sign'] == '-': val = -val
                if g['unit']: val *= multipliers.get(g['unit'].lower(), 1)
                
                # Memory-safe line extraction
                start = text.rfind('\n', 0, match.start()) + 1
                end = text.find('\n', match.end())
                if end == -1: end = len(text)
                snippet = text[start:end].strip()
                if len(snippet) > 500: snippet = f"{snippet[:250]} [...] {snippet[-250:]}"
                
                results.append({'amount': val, 'snippet': snippet})
            except (ValueError, TypeError): continue
        return results

    def audit_filing(self, filing: Filing):
        text = filing.processed_text
        if not text: return
        is_outlook = any(kw in text.lower() for kw in ['outlook', 'forecast', 'projection', 'planned'])
        max_yr_limit = 2200 if is_outlook else 2100
        reference_date = self._normalize_reference_date(filing.accepted_date)
        
        # 1. Scale Learning
        currency_info = self._extract_currency(text)
        abs_amounts = [abs(i['amount']) for i in currency_info if abs(i['amount']) > 0]
        baseline = sorted(abs_amounts)[:5]
        dynamic_cap = (baseline[len(baseline) // 2] * 10.0) if baseline else 1e12

        # 2. Year Extraction
        pattern = r"(?i)\b(?:year|period|fy)\s*(?P<val>\d{2,4}(?:[-/]\d{2,4})?)\b"
        for match in re.finditer(pattern, text):
            token = match.group('val')
            root_part = re.split(r'[-/]', token)[0]
            try:
                yr = self._resolve_year_token(root_part, reference_date)
                if 1900 <= yr <= max_yr_limit:
                    if yr in self.coverage: self.coverage[yr] = 1
                    self.telemetry.update_stats(filing.identifier, filing.filing_type, 1)
                else:
                    self.telemetry.log_rejection({"year": yr, "filing_id": filing.identifier, "filing_type": filing.filing_type, "context": "out_of_bounds"})
            except (ValueError, TypeError): continue

        # 3. Currency Audit
        for info in currency_info:
            self.telemetry.update_stats(filing.identifier, filing.filing_type, 1)
            if abs(info['amount']) > dynamic_cap:
                self.telemetry.log_rejection({
                    "value": info['amount'], "filing_id": filing.identifier, 
                    "filing_type": filing.filing_type, "context": "financial_outlier", "snippet": info['snippet']
                })

    def get_report(self, issuer_name: str) -> Dict:
        return {
            "issuer": issuer_name,
            "coverage_vector": self.coverage,
            "gaps": [y for y, v in self.coverage.items() if v == 0],
            "telemetry_audit": self.telemetry.get_summary()
        }
