# dego-project-team4
DEGO Course Project — Team 4

## Team Members
- Henrik Peuker
- Ole Eiane

## Project Description
Credit scoring bias analysis for the DEGO course. We act as a Data Governance Task Force
at fintech company NovaCred, auditing a credit application dataset for data quality issues,
fairness/bias, and GDPR/AI Act compliance.

## Setup


## Structure
| Path | Purpose |
|---|---|
| `data/` | Raw dataset (`raw_credit_applications.json`) |
| `notebooks/` | Jupyter analysis notebooks — run in order: 01 → 03 |
| `src/fairness_utils.py` | 
| `presentation/` | Final slide deck deliverable |

## Notebooks
| Notebook | Role | Purpose |
|---|---|---|
| `01-data-quality.ipynb` | Data Engineer | DQ audit, cleaning pipeline, `df_clean` |
| `02-bias-analysis.ipynb` | Data Analyst | Fairness metrics, demographic parity |
| `03-privacy-demo.ipynb` | DPO | GDPR pseudonymisation, access controls |

## Key Findings

## 📊 Data Quality Assessment

> **Role:** Data Engineer  
> **Notebook:** `notebooks/01-data-quality.ipynb`  
> **Dataset:** `data/cleaned_credit_applications.csv` — 500 records, 29 columns

---

### Overview

The dataset was audited across four data quality dimensions: **completeness**, **validity**, **consistency**, and **accuracy**. A total of **7 distinct issue categories** were identified, affecting approximately **35+ unique records**. All findings were quantified and remediated programmatically. No records were silently dropped — all decisions are documented below and reflected in the notebook.

| Issue | Dimension | Records Affected | Severity | Action |
|---|---|---|---|---|
| Missing values | Completeness | 18 (3.6%) | Critical | Flagged + targeted imputation |
| Duplicate SSNs | Validity / Consistency | 4 (2 pairs) | Critical | First occurrence kept, duplicate dropped |
| Invalid email formats | Validity | 4 (0.8%) | High | Email nulled out, record retained |
| Impossible credit history | Validity / Accuracy | 1 (0.2%) | High | Capped at age-derived maximum |
| Unknown gender encoding | Consistency | 3 (0.6%) | Medium | Retained, excluded from bias analysis |
| Zero savings balance | Validity | 4 (0.8%) | Medium | Flagged, retained |
| Extreme credit history | Accuracy | 7 (1.4%) | Medium | Flagged as outliers, retained |

---

### Issue 1 — Missing Values *(Completeness)*

**Finding:** 18 records (3.6%) contained at least one missing field. The most affected columns were `applicant_info_email` (7 missing), `financials_annual_income` (6 missing), `applicant_info_ssn` (5), `applicant_info_ip_address` (5), and `applicant_info_date_of_birth` (5). Notable cases include `app_075` and `app_120`, which were each missing 5+ fields simultaneously.

**Action — tiered by field type:**

- **PII fields** (`email`, `ssn`, `ip_address`): A boolean flag column was added (e.g., `applicant_info_email_missing = True`) to preserve missingness as a signal. These fields were **not imputed** — guessing identity information would be both analytically misleading and ethically inappropriate in a credit context.
- **Financial fields** (`annual_income`, `savings_balance`, `debt_to_income`): Imputed with the **column median**, which is robust to the income outliers present in this dataset. A flag column was added before imputation to track which values were filled.
- **`applicant_info_age`**: Derived from `applicant_info_date_of_birth` where the DOB was available. This is a deterministic fix that introduces no assumptions.
- **`financials_credit_history_months`**: Imputed with `0`, reflecting the assumption that no recorded history equals zero months of history. Documented as an assumption.

---

### Issue 2 — Duplicate SSNs *(Validity / Consistency)*

**Finding:** Two pairs of distinct applicants share the same Social Security Number:
- `app_088` (Susan Martinez, Female) and `app_016` (Gary Wilson, Male) — SSN `780-24-9300`
- `app_101` (Sandra Smith, Female) and `app_234` (Samuel Hill, Male) — SSN `937-72-8731`

In both pairs, the applicants have different names, genders, and financial profiles, confirming these are not the same individual. This represents a data integrity failure — either a data entry error or a pipeline corruption during collection.

**Action:** Since the source data cannot be re-verified, the **first occurrence of each SSN was retained** and the duplicate record was removed. The 2 dropped records were exported to `data/dropped_duplicate_ssn.csv` for auditability. This decision preserves the analytical dataset while transparently documenting what was removed.

---

### Issue 3 — Invalid Email Formats *(Validity)*

**Finding:** 4 records contained structurally invalid email addresses, all of which also had a name/email mismatch (the email address does not correspond to the named applicant):

| Record | Name | Invalid Email | Problem |
|---|---|---|---|
| `app_204` | Jonathan Carter | `mike johnson@gmail.com` | Space in local part |
| `app_299` | Samuel Gonzalez | `test.user.outlook.com` | Missing `@` symbol |
| `app_068` | Emily Lopez | `john.doe@invalid` | Invalid TLD |
| `app_146` | Amy Flores | `sarah.smith@` | Truncated, no domain |

**Action:** Invalid email values were replaced with `NaN` and flagged via a boolean `email_valid` column. The full records were **retained** for all financial and bias analyses, as the rest of the data in these records is valid. Removing the records entirely over a single malformed field would unnecessarily reduce the dataset.

---

### Issue 4 — Impossible Credit History *(Validity / Accuracy)*

**Finding:** `app_049` (Donna Gonzalez, age 25) has `financials_credit_history_months = 92` (7.6 years). Assuming credit history begins at age 18, the maximum physically possible value for this applicant is `(25 - 18) × 12 = 84 months`. The recorded value exceeds this ceiling by 8 months.

**Action:** The value was **capped** at the age-derived maximum of 84 months using the formula `max_possible_credit = (age - 18) × 12`. A `credit_history_impossible` flag column was added before correction. This is a conservative fix that does not introduce arbitrary values.

---

### Issue 5 — Inconsistent Gender Encoding *(Consistency)*

**Finding:** 3 records use the value `"Unknown"` for `applicant_info_gender` rather than `"Male"` or `"Female"`. This breaks the binary assumption required for the Disparate Impact ratio calculation.

**Action:** The `"Unknown"` category was **preserved as a valid third category** — gender was not imputed, as randomly assigning a gender would itself introduce bias into the very metric we are trying to measure. These 3 records are included in all analyses except the Disparate Impact calculation, from which they are explicitly excluded. The exclusion is documented in `notebooks/02-bias-analysis.ipynb`.

---

### Issue 6 — Zero Savings Balance *(Validity)*

**Finding:** 4 records report exactly `$0` in `financials_savings_balance`: `app_024` ($103k income), `app_006` ($82k income), `app_411` ($64k income), and `app_001` ($102k income). While a $0 savings balance is not impossible, it is statistically anomalous for applicants with high annual incomes and may reflect a missing value that was substituted with a default of `0` during an upstream data entry step.

**Action:** A boolean flag column `savings_zero_flag` was added to identify these records. The values were **retained as-is** since there is no principled basis to change them without external verification. The flag allows downstream analyses to assess whether these records skew any financial correlations.

---

### Issue 7 — Extreme Credit History >120 months *(Accuracy)*

**Finding:** 7 records report more than 120 months (10 years) of credit history, with the highest values being `app_230` (133 months, age 62) and `app_391` (131 months, age 62). While extreme, these values are **not impossible** — all 7 applicants are aged between 41 and 66, making a 10+ year credit history plausible.

**Action:** These records were **not modified**. A boolean flag column `credit_history_outlier` was added to make them identifiable for statistical testing. This flag was shared with the Data Scientist for consideration in bias and fairness analyses.

---

