# dego-project-team4
DEGO Course Project — Team 4

## Team Members
- Henrik Peuker
- Ole Eiane
- Maria Isabel Ravara

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
> **Notebook:** `notebooks/01-data-quality copy.ipynb`  
> **Dataset:** `data/cleaned_credit_applications.csv` — 500 records, 34 columns

---

### Overview

The dataset was audited across four data quality dimensions: **completeness**, **consistency**, **validity**, and **accuracy**. Issues were identified, quantified, and remediated programmatically. No records were silently dropped — all decisions are documented below and reflected in the notebook.

**Dataset size progression:**

| Stage | Rows | Notes |
|---|---|---|
| Raw (`df_raw`) | 502 | After loading `raw_credit_applications.json` |
| After Completeness | 502 | No rows dropped — flags only |
| After Consistency | 502 | No rows dropped — normalised in place |
| After Validity | 502 | No rows dropped — impossible values → `NaN` |
| After Accuracy | 500 | −2 duplicate `_id` rows removed |
| **Final (`df_clean`)** | **500** | **99.6% data retention** |

**Flag columns created on `df_clean`:**

| Flag | True | False |
|---|---|---|
| `email_missing` | 7 | 493 |
| `email_malformed` | 4 | 496 |
| `ssn_missing` | 4 | 496 |
| `dob_missing` | 0 | 500 |
| `annual_income_missing` | 0 | 500 |
| `debt_to_income_missing` | 1 | 499 |
| `savings_balance_missing` | 1 | 499 |
| `credit_history_suspicious` | 0 | 500 |
| `savings_balance_zero` | 4 | 496 |
| `ssn_duplicate` | 4 | 496 |
| `needs_review` | 13 | 487 |

> **`needs_review`** is a composite quarantine flag — `True` for any record with a missing PII field (`email`, `dob`, `ssn`), a missing/invalid financial field (`annual_income`, `savings_balance`, `debt_to_income`), a suspicious credit history, or an SSN collision. **13 records (2.6%) are quarantined** from model training.

---

### Completeness

#### Issue 1 — Missing `processing_timestamp` *(440 records, 87.6%)*

**Finding:** 440 of 502 raw records have no `processing_timestamp`. This is a systemic pipeline defect — the field was not populated for the majority of applications.

**Action:** Not flagged in `df_clean` (no downstream model dependency). Documented in the scorecard.

---

#### Issue 2 — Missing `email` *(7 records, 1.4%)*

**Finding:** 7 records have no email address at all.

**Action:** Normalised empty strings to `NaN`. Flagged `email_missing = True`. **Not imputed** — guessing PII would corrupt identity verification pipelines and violate GDPR's accuracy principle.

---

#### Issue 3 — Missing `date_of_birth` *(5 records in raw, 0 after cleaning)*

**Finding:** 5 raw records had no date of birth. After removing 2 notes-flagged records (see Accuracy), no missing DOBs remained in `df_clean`.

**Action:** Flagged `dob_missing = True` where applicable. **Not imputed** — DOB is PII and a core input to the age-derived credit history cap.

---

#### Issue 4 — Missing `ssn` *(5 records in raw)*

**Finding:** 5 records had no SSN.

**Action:** Flagged `ssn_missing = True`. **Not imputed** — SSN is a primary identity field.

---

#### Issue 5 — Missing `annual_income` *(5 records, resolved by coalesce)*

**Finding:** 5 records had `annual_income = null` because the applicant had populated `annual_salary` instead — a clear data-entry error confirmed by perfect field overlap.

**Action:** Coalesced `annual_salary → annual_income` for these 5 records. One additional record had a zero income value and was set to `NaN`, covered by `annual_income_missing = True`. No genuine gaps remain after coalesce.

---

#### Issue 6 — Missing `gender` *(3 records, 0.6%)*

**Finding:** 3 records had an empty `gender` field.

**Action:** Set to `"Unknown"` — a protected attribute is **never imputed**, as imputing the majority class would silently encode demographic assumptions.

---

### Consistency

#### Issue 7 — Inconsistent gender coding *(111 records, 22.1%)*

**Finding:** The `gender` field uses four representations for two logical values: `"Male"`, `"M"`, `"Female"`, `"F"`, plus empty/null.

**Action:** Normalised via `GENDER_MAP` → controlled vocabulary `Male / Female / Unknown`.

---

#### Issue 8 — `annual_income` stored as string *(8 records, 1.6%)*

**Finding:** 8 records stored income as a string (e.g. `"55000"`, `"$72,000"`) rather than a numeric type.

**Action:** Coerced to `float` via `_coerce_income()`. All 8 were parseable with no information loss.

---

#### Issue 9 — Inconsistent `date_of_birth` formats *(161 records, 32.2%)*

**Finding:** DOB is stored in four formats across records:

| Format | Count |
|---|---|
| `YYYY-MM-DD` (ISO) | 339 |
| `YYYY/MM/DD` | 56 |
| `DD/MM/YYYY` (EU, unambiguous) | 36 |
| `MM/DD/YYYY` (US, unambiguous) | 26 |
| Ambiguous `XX/XX/YYYY` | 39 |
| Empty string | 4 |

The `DD/MM/YYYY` and `MM/DD/YYYY` formats share a pattern and are ambiguous when day ≤ 12. Records where day > 12 can be identified unambiguously.

**Action:** Normalised to `pd.Timestamp` (ISO 8601) via `parse_date()`. Ambiguous dates treated as European (`DD/MM`) convention — the safest defensible default for a European-facing application. Unparseable values remain `NaT` and are caught by `dob_missing`.

---

### Validity

#### Issue 10 — `credit_history_months` < 0 *(2 records, 0.4%)*

**Finding:** 2 records had a negative credit history value — a data-entry error (sign flip).

**Action:** Set to `NaN`; imputed with `0` (documented assumption: no history = 0 months).

---

#### Issue 11 — `debt_to_income` > 1.0 *(1 record, 0.2%)*

**Finding:** 1 record had a DTI ratio exceeding 1.0 (debt exceeds income), which is not a valid financial state.

**Action:** Set to `NaN`. Flagged `debt_to_income_missing = True`. **Not imputed.**

---

#### Issue 12 — `savings_balance` < 0 *(1 record, 0.2%)*

**Finding:** 1 record had a negative savings balance.

**Action:** Set to `NaN`. Flagged `savings_balance_missing = True`. **Not imputed.**

---

#### Issue 13 — `annual_income` ≤ 0 *(1 record)*

**Finding:** 1 record had a zero income value (not a field-confusion case).

**Action:** Set to `NaN`. Flagged `annual_income_missing = True`.

---

#### Issue 14 — `credit_history_months` exceeds age-derived maximum

**Finding:** `app_049` (DOB 2000-05-22) has 92 recorded months of credit history against a maximum of 93 months (months since 18th birthday). Borderline case.

**Action:** Flagged `credit_history_suspicious = True`. Cap logic is enforced in the pipeline for future violations.

---

#### Issue 15 — Malformed email format + name/email identity mismatch *(4 records, 0.8%)*

**Finding:** 4 records contain structurally invalid email addresses, each of which also contains a different person's name in the local part — a simultaneous format validity failure and identity consistency failure:

| Record | Name | Invalid Email | Problem |
|---|---|---|---|
| `app_204` | Jonathan Carter | `mike johnson@gmail.com` | Space in local part |
| `app_299` | Samuel Gonzalez | `test.user.outlook.com` | Missing `@` |
| `app_068` | Emily Lopez | `john.doe@invalid` | Invalid TLD |
| `app_146` | Amy Flores | `sarah.smith@` | Truncated, no domain |

**Action:** Flagged `email_malformed = True`. Full records **retained** — financial data remains valid; only email-dependent pipeline steps must exclude these 4 records.

---

### Accuracy

#### Issue 16 — Duplicate `_id` records *(2 pairs → 2 removed)*

**Finding:** 2 pairs of records share the same `_id` but have conflicting field values — these were identified via `notes` values `RESUBMISSION` and `DUPLICATE_ENTRY_ERROR`.

**Action:** Removed the flagged entries. Dataset reduced from 502 → 500 rows (`last-write-wins` strategy).

---

#### Issue 17 — SSN shared by multiple distinct applicants *(2 SSNs → 4 records, 0.8%)*

**Finding:** Two SSN values are each shared by two distinct applicants (different names, genders, and financial profiles). This represents a data integrity failure.

**Action:** Flagged `ssn_duplicate = True` on all 4 affected records. Records **quarantined** from model training via `needs_review`. Incident should be raised as a data integrity issue; a `UNIQUE` constraint on `ssn` is recommended.

---

#### Issue 18 — PII stored in plaintext *(500 records, 100%)*

**Finding:** SSN, email, and other PII fields are stored unencrypted.

**Action:** Pseudonymisation required before sharing or using in downstream pipelines. Enforce access controls. Covered in `notebooks/03-privacy-demo.ipynb`.

---

### Post-Cleaning Dataset Summary

| Metric | Value |
|---|---|
| Raw records | 502 |
| Records after deduplication | **500** |
| Columns in `df_clean` | **34** |
| Records flagged `needs_review = True` | **13 (2.6%)** |
| Records flagged `ssn_duplicate = True` | 4 |
| Records flagged `email_malformed = True` | 4 |
| Records flagged `email_missing = True` | 7 |
| Records flagged `credit_history_suspicious = True` | 0 |
| Records ready for analysis | **487 (97.4%)** |

---

