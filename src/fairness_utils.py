"""
src/fairness_utils.py
=====================
Placeholder — reserved for shared utilities used by bias and privacy notebooks.

The data cleaning pipeline for Task 1 lives in:
    notebooks/01-data-quality.ipynb  (Full Cleaning Pipeline cell)

If shared helper functions are needed across notebooks in future tasks,
they can be added here.
"""

import pandas as pd
import numpy as np

def add_age_years_from_dob(
    df: pd.DataFrame,
    dob_col: str = "applicant_info_date_of_birth",
    out_col: str = "age_years",
    as_of: str = "2026-03-05",
) -> pd.DataFrame:
    """
    Add integer age (completed years) derived from DOB, as of a fixed date.

    This avoids float rounding issues (e.g., 24.95 is still 24).
    """
    df_out = df.copy()
    dob = pd.to_datetime(df_out[dob_col], errors="coerce")
    as_of_dt = pd.Timestamp(as_of)

    # years difference
    age = as_of_dt.year - dob.dt.year

    # has birthday occurred yet this year?
    had_bday = (as_of_dt.month > dob.dt.month) | (
        (as_of_dt.month == dob.dt.month) & (as_of_dt.day >= dob.dt.day)
    )

    age = age - (~had_bday).astype(int)

    # keep missing as <NA> (nullable integer)
    df_out[out_col] = age.astype("Int64")
    return df_out
