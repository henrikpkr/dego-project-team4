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

def add_age_years_from_dob(
    df: pd.DataFrame,
    dob_col: str = "applicant_info_date_of_birth",
    out_col: str = "age_years",
    as_of: str = "2024-01-15",
) -> pd.DataFrame:
    """
    Add an age column (in years) derived from date of birth column.

    - Uses a fixed 'as_of' date for reproducibility in the course project.
    - Returns a COPY of df with the new column.

    Example:
        df = add_age_years_from_dob(df, "applicant_info_date_of_birth")
    """
    df_out = df.copy()
    dob = pd.to_datetime(df_out[dob_col], errors="coerce")
    df_out[out_col] = (pd.Timestamp(as_of) - dob).dt.days / 365.25
    return df_out
