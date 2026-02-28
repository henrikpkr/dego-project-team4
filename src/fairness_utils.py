"""
src/fairness_utils.py
=====================
Single source of truth for the NovaCred data cleaning pipeline.

Usage (from any notebook):
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path("../src").resolve()))
    from fairness_utils import load_raw, build_clean_df

    raw_data = load_raw()
    df_clean = build_clean_df(raw_data)
"""

from __future__ import annotations

import copy
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

# ── Paths ─────────────────────────────────────────────────────────────────────
_SRC_DIR  = Path(__file__).parent
DATA_DIR  = _SRC_DIR.parent / "data"
DATA_FILE = DATA_DIR / "raw_credit_applications.json"

# ── Audit reference date ──────────────────────────────────────────────────────
# Hardcoded so age calculations are reproducible regardless of when the
# notebook is re-run. Change only if reprocessing a newer data extract.
AUDIT_DATE = pd.Timestamp("2026-02-28")

# ── Constants ─────────────────────────────────────────────────────────────────
GENDER_MAP: dict[str | None, str] = {
    "Male": "Male", "M": "Male",
    "Female": "Female", "F": "Female",
    "": "Unknown", None: "Unknown",
}

# (field, operator, threshold) — used by clamp_financials and clean_record
INVALID_THRESHOLDS: list[tuple[str, str, float]] = [
    ("credit_history_months", "<",  0),
    ("debt_to_income",        ">",  1.0),
    ("savings_balance",       "<",  0),
    ("annual_income",         "<=", 0),
]

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SSN_RE   = re.compile(r"^\d{3}-\d{2}-\d{4}$")
_SLASH4  = re.compile(r"^(\d{2})/(\d{2})/(\d{4})$")

# Columns to drop before modelling (sparse or outcome-leakage)
COLS_TO_DROP: list[str] = [
    "financials_annual_salary",
    "notes",
    "loan_purpose",
    "processing_timestamp",
    "decision_rejection_reason",
    "decision_interest_rate",
    "decision_approved_amount",
]


# ── I/O ───────────────────────────────────────────────────────────────────────

def load_raw(path: Path | str = DATA_FILE) -> list[dict[str, Any]]:
    """Load raw JSON array from disk."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# ── Date parsing ──────────────────────────────────────────────────────────────

def parse_dob(dob_str: str | None) -> str | None:
    """
    Parse a date-of-birth string in any of four formats to ISO 8601.

    Formats handled:
      YYYY-MM-DD  — ISO 8601 (standard)
      YYYY/MM/DD  — treated as ISO with slash separators
      DD/MM/YYYY  — European; inferred when first part > 12 or both parts ≤ 12
      MM/DD/YYYY  — US; inferred when second part > 12

    Returns ISO string (YYYY-MM-DD) or None if unparseable.
    """
    if not dob_str:
        return None
    s = str(dob_str)

    # Unambiguous dash/slash year-first formats
    for fmt in ["%Y-%m-%d", "%Y/%m/%d"]:
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            continue

    # Two-digit day/month disambiguation
    m = _SLASH4.match(s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        fmt = "%m/%d/%Y" if b > 12 else "%d/%m/%Y"
        try:
            return datetime.strptime(s, fmt).date().isoformat()
        except ValueError:
            return None

    return None


# ── Record-level cleaning ─────────────────────────────────────────────────────

def clamp_financials(record: dict) -> dict:
    """Return a deep copy with all impossible financial values set to None."""
    r  = copy.deepcopy(record)
    fi = r.get("financials", {})
    for field, op, threshold in INVALID_THRESHOLDS:
        val = fi.get(field)
        if not isinstance(val, (int, float)):
            continue
        if   op == "<"  and val <  threshold: fi[field] = None
        elif op == ">"  and val >  threshold: fi[field] = None
        elif op == "<=" and val <= threshold: fi[field] = None
    r["financials"] = fi
    return r


def clean_record(record: dict) -> dict:
    """
    Apply the full set of cleaning rules to a single record.

    Rules applied (in order):
      1. Gender normalisation (M/Male/F/Female → Male/Female/Unknown)
      2. Income coercion (string → float; zero/negative → None)
      3. Impossible numeric values → None  (via INVALID_THRESHOLDS)
      4. Date-of-birth normalisation to ISO 8601

    Returns a deep copy — original record is not mutated.
    """
    r  = copy.deepcopy(record)
    ai = r.get("applicant_info", {})
    fi = r.get("financials", {})

    # 1. Gender
    ai["gender"] = GENDER_MAP.get(ai.get("gender"), "Unknown")

    # 2. Income
    inc = fi.get("annual_income")
    if isinstance(inc, str):
        try:
            fi["annual_income"] = float(inc.replace(",", "").strip())
        except ValueError:
            fi["annual_income"] = None

    # 3. Impossible values (reuses INVALID_THRESHOLDS — same logic as clamp_financials)
    for field, op, threshold in INVALID_THRESHOLDS:
        val = fi.get(field)
        if not isinstance(val, (int, float)):
            continue
        if   op == "<"  and val <  threshold: fi[field] = None
        elif op == ">"  and val >  threshold: fi[field] = None
        elif op == "<=" and val <= threshold: fi[field] = None

    # 4. DOB
    ai["date_of_birth"] = parse_dob(ai.get("date_of_birth"))

    r["applicant_info"] = ai
    r["financials"]     = fi
    return r


# ── Spending pivot ────────────────────────────────────────────────────────────

def pivot_spending(row: list | Any) -> dict[str, int]:
    """Convert a spending_behavior list into a flat spend_<category> dict."""
    items = row if isinstance(row, list) else []
    return {
        f"spend_{d['category'].lower()}": d["amount"]
        for d in items
        if isinstance(d, dict) and "category" in d and "amount" in d
    }


# ── Full pipeline ─────────────────────────────────────────────────────────────

def build_clean_df(raw_data: list[dict]) -> pd.DataFrame:
    """
    Run the full cleaning pipeline on the raw record list.

    Steps:
      1. Clean each record (gender, income, impossible values, DOB)
      2. Flatten JSON → DataFrame
      3. Deduplicate by _id (keep last occurrence)
      4. Cast date columns to datetime64
      5. Derive applicant_info_age
      6. Pivot spending_behavior into spend_* columns
      7. Drop sparse / outcome-leakage columns

    Returns df_clean — model-ready except for numeric imputation of remaining NaNs.
    """
    # Step 1 + 2: clean and flatten
    cleaned = [clean_record(r) for r in raw_data]
    df = pd.json_normalize(cleaned)
    df.columns = [c.replace(".", "_") for c in df.columns]

    # Step 3: deduplicate — keep last occurrence per _id
    df = df.drop_duplicates(subset="_id", keep="last").reset_index(drop=True)

    # Step 4: cast date columns
    df["applicant_info_date_of_birth"] = pd.to_datetime(
        df["applicant_info_date_of_birth"], errors="coerce"
    )
    df["processing_timestamp"] = pd.to_datetime(
        df["processing_timestamp"], errors="coerce", utc=True
    )
    df["applicant_info_zip_code"] = (
        df["applicant_info_zip_code"].astype(str).replace("nan", pd.NA)
    )

    # Step 5: age
    df["applicant_info_age"] = (
        (AUDIT_DATE - df["applicant_info_date_of_birth"]).dt.days // 365
    ).astype("Int64")

    # Step 6: spending pivot
    spending = (
        df["spending_behavior"]
        .apply(pivot_spending)
        .apply(pd.Series)
        .fillna(0)
        .astype(int)
    )
    df = pd.concat([df.drop(columns=["spending_behavior"]), spending], axis=1)

    # Step 7: drop sparse / leakage columns
    df = df.drop(columns=[c for c in COLS_TO_DROP if c in df.columns])

    return df


# ── Format validators (used in audit, not in cleaning) ───────────────────────

def audit_format_validity(raw_data: list[dict]) -> dict[str, list[tuple[str, str]]]:
    """
    Check email and SSN fields for format violations.

    Returns a dict with keys 'email_invalid' and 'ssn_invalid',
    each containing a list of (app_id, offending_value) tuples.
    """
    email_invalid: list[tuple[str, str]] = []
    ssn_invalid:   list[tuple[str, str]] = []
    for r in raw_data:
        ai    = r.get("applicant_info", {})
        email = ai.get("email")
        ssn   = ai.get("ssn")
        if email and not EMAIL_RE.match(str(email)):
            email_invalid.append((r["_id"], str(email)))
        if ssn and not SSN_RE.match(str(ssn)):
            ssn_invalid.append((r["_id"], str(ssn)))
    return {"email_invalid": email_invalid, "ssn_invalid": ssn_invalid}
