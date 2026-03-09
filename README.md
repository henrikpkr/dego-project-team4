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
| `02-bias-analysis.ipynb` | Data Scientist | Fairness metrics, demographic parity |
| `03-privacy-demo.ipynb` | DPO | GDPR pseudonymisation, access controls |

## Key Findings

## Data Quality Assessment

> **Role:** Data Engineer
> **Notebook:** `notebooks/01-data-quality.ipynb`
> **Dataset:** `data/cleaned_credit_applications.csv` — 500 records, 37 columns

---

### Overview

The dataset was audited across four data quality dimensions: completeness, consistency, validity, and accuracy. All issues were identified programmatically, quantified against the raw source, and remediated with explicit, documented decisions. No records were silently dropped. Every affected record is traceable through a boolean flag column in `df_clean`.

**Dataset size progression:**

| Stage | Rows | Notes |
|---|---|---|
| Raw (`df_raw`) | 502 | After loading `raw_credit_applications.json` |
| After Completeness | 502 | No rows dropped — flags only |
| After Consistency | 502 | No rows dropped — normalised in place |
| After Validity | 502 | No rows dropped — impossible values set to NaN |
| After Accuracy | 500 | 2 duplicate `_id` rows removed |
| **Final (`df_clean`)** | **500** | **99.6% data retention** |

**Flag columns in `df_clean`:**

| Flag | True | False | Dimension |
|---|---|---|---|
| `email_missing` | 7 | 493 | Completeness |
| `email_malformed` | 4 | 496 | Validity |
| `gender_missing` | 2 | 498 | Completeness |
| `ssn_missing` | 4 | 496 | Completeness |
| `dob_missing` | 4 | 496 | Completeness |
| `annual_income_missing` | 0 | 500 | Completeness |
| `debt_to_income_missing` | 1 | 499 | Validity |
| `savings_balance_negative` | 1 | 499 | Validity |
| `savings_balance_missing` | 1 | 499 | Validity |
| `savings_balance_zero` | 4 | 496 | Notable |
| `timestamp_missing` | 438 | 62 | Pipeline |
| `credit_history_suspicious` | 0 | 500 | Validity |
| `ssn_duplicate` | 4 | 496 | Accuracy |
| `needs_review` | 17 | 483 | Composite |

`needs_review` is a composite quarantine flag set to `True` for any record that carries at least one of the following: a missing PII field (`email`, `dob`, `ssn`, `gender`), a missing or invalid financial field (`debt_to_income`, `savings_balance`), or an SSN collision. 17 records (3.4%) are quarantined from model training. `timestamp_missing` is tracked separately as a pipeline defect and does not trigger `needs_review`.

The `needs_review` trigger breakdown is:

| Flag | Records |
|---|---|
| `email_missing` | 7 |
| `email_malformed` | 4 |
| `gender_missing` | 2 |
| `ssn_missing` | 4 |
| `dob_missing` | 4 |
| `debt_to_income_missing` | 1 |
| `savings_balance_missing` | 1 |
| `ssn_duplicate` | 4 |

Note: records may trigger multiple flags simultaneously, so the per-flag totals above sum to more than 17.

---

### Completeness

#### Issue 1 — Missing `processing_timestamp` (438 records, 87.6%)

**Finding:** 438 of 500 clean records have no `processing_timestamp`. The field was not populated for the vast majority of applications, indicating a systemic upstream pipeline defect rather than individual data-entry errors.

**Remediation:** Flagged `timestamp_missing = True`. No imputation and no `needs_review` trigger, because `processing_timestamp` has no downstream model or identity-verification dependency. The volume and uniformity of the gap make this a known infrastructure issue, not an application-level anomaly. The field is tracked separately in the scorecard so it remains visible without inflating the quarantine count.

---

#### Issue 2 — Missing `email` (7 records, 1.4%)

**Finding:** 7 records have no email address. Empty string values were present in the raw data alongside genuine nulls; both were normalised to `NaN` to enforce a single missing-value representation.

**Remediation:** Flagged `email_missing = True`. Not imputed. PII fields such as email are used in identity verification and regulatory correspondence. Fabricating an address would corrupt those pipelines and would introduce false accuracy, violating the GDPR accuracy principle (Art. 5(1)(d)). These records are quarantined via `needs_review`.

---

#### Issue 3 — Missing `date_of_birth` (5 in raw, 4 in `df_clean`)

**Finding:** 5 raw records had no date of birth (4 empty strings, 1 null). One of those records was removed during the accuracy phase as a duplicate entry, leaving 4 missing DOBs in `df_clean`.

**Remediation:** Empty strings normalised to `NaN`. Flagged `dob_missing = True`. Not imputed. DOB is PII and is the direct input to the age-derived credit history cap; an imputed value would produce silently incorrect downstream constraints. These records are quarantined via `needs_review`.

---

#### Issue 4 — Missing `ssn` (5 in raw, 4 in `df_clean`)

**Finding:** 5 raw records had no SSN. One was removed during the accuracy phase, leaving 4 in `df_clean`.

**Remediation:** Flagged `ssn_missing = True`. Not imputed. SSN is the primary applicant identity key and is required for duplicate and fraud detection. Fabricating or carrying forward a blank value would undermine both. These records are quarantined via `needs_review`.

---

#### Issue 5 — Missing `annual_income` resolved by field coalesce (5 records)

**Finding:** 5 records had `annual_income = null` because the applicant had populated `annual_salary` instead. The two fields are mutually exclusive across the dataset — no record has both populated — confirming this is a data-entry naming error rather than genuinely missing income data.

**Remediation:** `annual_salary` coalesced into `annual_income` for these 5 records. No flag raised (`annual_income_missing` remains 0 after coalesce). The coalesce is the correct approach because the information is present in the dataset; the issue is only which field it was written to. Discarding or imputing would lose real data unnecessarily.

---

#### Issue 6 — Missing `gender` (2 records in `df_clean`, 0.4%)

**Finding:** 2 records in `df_clean` have no gender value (empty string in raw data). A third raw record with a null gender was removed during the accuracy phase as a duplicate entry and does not appear in `df_clean`.

**Remediation:** Empty strings and nulls normalised to the controlled vocabulary value `Unknown`. Flagged `gender_missing = True`. Not imputed. Gender is a protected attribute under EU anti-discrimination law and the EU AI Act. Imputing the majority class would silently encode a demographic assumption that could skew fairness metrics and bias model training. These records are quarantined via `needs_review`.

---

### Consistency

#### Issue 7 — Inconsistent gender coding (114 non-standard records, 22.7%)

**Finding:** The `gender` field uses four surface representations for two logical values: `Male`, `M`, `Female`, `F`, plus empty string and null. 114 records used the abbreviated forms. Without normalisation, group-level fairness analysis would produce incorrect counts and approval-rate calculations.

**Remediation:** Normalised via `GENDER_MAP` to a controlled vocabulary of `Male`, `Female`, and `Unknown`. After normalisation: Female 251 (50.2%), Male 247 (49.4%), Unknown 2 (0.4%). Normalisation is the correct approach here — the intended meaning is unambiguous; only the encoding differs.

---

#### Issue 8 — `annual_income` stored as string (8 records, 1.6%)

**Finding:** 8 records stored income as a plain string (e.g. `"55000"`) rather than a numeric type. All 8 values are clean integers without currency symbols or separators.

**Remediation:** Coerced to `float` via `_coerce_income()`. All 8 were parseable with no information loss; mean income after coercion is $82,705. Type coercion is appropriate because the values are unambiguously numeric — the only defect is the storage type, not the content.

---

#### Issue 9 — Inconsistent `date_of_birth` formats (161 records, 32.2%)

**Finding:** DOB is stored in five formats across the dataset:

| Format | Count |
|---|---|
| ISO `YYYY-MM-DD` | 339 |
| `YYYY/MM/DD` | 56 |
| Ambiguous `XX/XX/YYYY` | 39 |
| EU `DD/MM/YYYY` (unambiguous) | 36 |
| US `MM/DD/YYYY` (unambiguous) | 26 |
| Null or empty | 4 |

The `DD/MM/YYYY` and `MM/DD/YYYY` patterns overlap when the day value is 12 or below, making 39 records ambiguous by format alone.

**Remediation:** All values normalised to `pd.Timestamp` (ISO 8601) via `parse_date()`. Ambiguous dates treated as European convention (`DD/MM/YYYY`). This is the documented default because NovaCred is a European-facing application and EU convention is therefore the statistically safer assumption. 496 of 500 records were parsed successfully. Unparseable or null values remain `NaT` and are caught by `dob_missing`.

---

### Validity

#### Issue 10 — `credit_history_months` < 0 (2 records, 0.4%)

**Finding:** 2 records had negative credit history values (`app_043: -10`, `app_156: -3`). A negative credit history duration has no valid interpretation and is consistent with a data-entry sign error.

**Remediation:** Set to `NaN`, then imputed with 0 (documented assumption: no verifiable history is treated as zero months). Nulling and zero-imputation is justified because the negative value is definitionally impossible, and zero is the conservative lower bound — it neither fabricates a history nor discards the record.

---

#### Issue 11 — `debt_to_income` > 1.0 (1 record, 0.2%)

**Finding:** 1 record (`app_402`) had a DTI ratio of 1.85. A DTI above 1.0 means total debt exceeds total income, which is not a valid financial state in the context of this dataset's DTI definition.

**Remediation:** Set to `NaN`. Flagged `debt_to_income_missing = True`. Not imputed. Unlike credit history months, there is no defensible conservative substitute value for DTI — imputing the mean or median would silently alter a financially significant input. The record is quarantined via `needs_review` so it is excluded from model training but retained in the dataset for audit purposes.

---

#### Issue 12 — `savings_balance` < 0 (1 record, 0.2%)

**Finding:** 1 record (`app_290`) had a savings balance of -5000. A negative savings balance is not a valid value in this dataset — savings balance represents the balance of a deposit account, which cannot be negative.

**Remediation:** Flagged `savings_balance_negative = True` (derived from the raw source to ensure this flag is idempotent across pipeline re-runs). Value set to `NaN`. Also flagged `savings_balance_missing = True`. Not imputed for the same reason as DTI — there is no conservative substitute value. The record is quarantined via `needs_review`.

---

#### Issue 13 — `savings_balance` == 0 (4 records, notable)

**Finding:** 4 records have a savings balance of exactly 0. This is a valid value and not a data quality defect, but it is flagged for analyst awareness because zero savings is a financially meaningful edge case that may affect model behaviour.

**Remediation:** Flagged `savings_balance_zero = True`. No nulling, no quarantine. This flag exists solely to make the zero-savings segment visible to downstream analysts without interfering with the pipeline.

---

#### Issue 14 — `credit_history_months` exceeds age-derived maximum (0 records after pipeline enforcement)

**Finding:** No records in `df_clean` have a credit history that exceeds the maximum possible given the applicant's age (months since 18th birthday as of the audit date 2026-02-28). The cap was enforced during cleaning; any future records that breach it will be clamped and flagged `credit_history_suspicious = True`.

**Remediation:** Cap logic is encoded in the pipeline. If a value exceeds the age-derived maximum, it is clamped to that maximum and flagged. This is preferable to nulling because a plausible upper bound exists and clamping preserves the record's usability while correcting the impossible value.

---

#### Issue 15 — Malformed email with name/identity mismatch (4 records, 0.8%)

**Finding:** 4 records contain structurally invalid email addresses, each of which also contains a different person's name in the local part — a simultaneous format validity failure and an identity consistency failure:

| Record | Name | Email | Problem |
|---|---|---|---|
| `app_204` | Jonathan Carter | `mike johnson@gmail.com` | Space in local part |
| `app_299` | Samuel Gonzalez | `test.user.outlook.com` | Missing @ symbol |
| `app_068` | Emily Lopez | `john.doe@invalid` | Invalid TLD |
| `app_146` | Amy Flores | `sarah.smith@` | Truncated, no domain |

**Remediation:** Flagged `email_malformed = True`. Records retained in full — the financial data is intact and unaffected. Only processing steps that depend on a valid email address must exclude these 4 records. Dropping the records entirely would discard valid financial information and is disproportionate to the nature of the defect. These records are quarantined via `needs_review`.

---

### Accuracy

#### Issue 16 — Duplicate `_id` records (2 pairs, 2 rows removed)

**Finding:** 2 application IDs (`app_001`, `app_042`) each appear twice in the raw dataset with conflicting field values. Both duplicate copies were identifiable via `notes` values of `DUPLICATE_ENTRY_ERROR` and `RESUBMISSION`, confirming these are submission-level duplicates rather than data corruption.

**Remediation:** The notes-flagged copy of each pair was removed. Dataset reduced from 502 to 500 rows (99.6% retention). The specifically flagged copy was removed in each case, which is more precise than a positional last-write-wins strategy and is fully documented.

---

#### Issue 17 — SSN shared by multiple distinct applicants (2 SSNs, 4 records, 0.8%)

**Finding:** Two SSN values appear on records belonging to demonstrably different individuals (different names, emails, genders, and financial profiles). A third SSN collision exists for the `app_042` duplicate pair but is resolved by deduplication. The two genuine cross-applicant collisions are:

| SSN | Records |
|---|---|
| `937-72-8731` | `app_101` (Sandra Smith) and `app_234` (Samuel Hill) |
| `780-24-9300` | `app_088` (Susan Martinez) and `app_016` (Gary Wilson) |

**Remediation:** All 4 affected records flagged `ssn_duplicate = True` and quarantined via `needs_review`. Records are retained rather than dropped — removing them would destroy potentially valid financial data and could obstruct fraud investigation. This incident must be escalated for manual review. A `UNIQUE` constraint on the `ssn` field at the data ingestion layer is recommended to prevent recurrence.

---

#### Issue 18 — PII stored in plaintext (500 records, 100%)

**Finding:** SSN, email address, date of birth, and full name are all stored in plaintext in the raw dataset. This represents a GDPR compliance risk — exposure of this file would constitute a personal data breach.

**Remediation:** Pseudonymisation and access control are addressed in `notebooks/03-privacy-demo.ipynb`. The cleaned export (`data/cleaned_credit_applications.csv`) retains these fields for internal audit use only and must not be distributed without pseudonymisation.

---

### Post-Cleaning Dataset Summary

| Metric | Value |
|---|---|
| Raw records | 502 |
| Records after deduplication | 500 |
| Columns in `df_clean` | 37 |
| Records flagged `needs_review = True` | 17 (3.4%) |
| Records flagged `ssn_duplicate = True` | 4 |
| Records flagged `email_malformed = True` | 4 |
| Records flagged `email_missing = True` | 7 |
| Records flagged `gender_missing = True` | 2 |
| Records flagged `dob_missing = True` | 4 |
| Records flagged `savings_balance_negative = True` | 1 |
| Records flagged `timestamp_missing = True` | 438 (pipeline defect, tracked separately) |
| Records flagged `credit_history_suspicious = True` | 0 |
| Records ready for analysis | 483 (96.6%) |

---

### Bias & Fairness Analysis

> **Role:** Data Scientist
> **Notebook:** `notebooks/02-bias-analysis.ipynb`
> **Dataset:** `data/cleaned_credit_applications.csv` — 500 records (483 after quality filtering)

---

#### Overview

This notebook evaluates **fairness risks in the NovaCred automated credit scoring system**. It analyses approval-rate disparities across protected and quasi-protected attributes — gender, age, and ZIP code — using standard fairness metrics, statistical tests, and visual diagnostics. All analysis is performed on the cleaned dataset produced by `01-data-quality.ipynb`. Direct identifiers (name, email, SSN, IP) are intentionally excluded from all outputs.

---

#### Notebook Structure

| Section | Title |
|---------|-------|
| **0** | Setup & Imports |
| **1** | Load Cleaned Dataset |
| **2** | Pre-analysis Quality Filtering |
| **3** | Scope: Exclude Direct Identifiers |
| **4** | Sanity Checks — Group Counts |
| **5** | Issue 1: Gender Disparate Impact |
| **6** | Fairness Metric Cross-check (Fairlearn) |
| **7** | Statistical Test: Gender × Approval |
| **8** | Issue 2: Age-Based Patterns |
| **9** | Issue 3: Interaction Effects (Age × Gender) |
| **10** | Issue 4: ZIP Code Proxy Discrimination |
| **11** | Correlation Scan |
| **12** | Bias Analysis Summary |
| **13** | Implications for Fairness & Governance |

---

#### Pre-analysis Filtering

Before any fairness computation, three record categories are excluded:

| Flag | Records excluded | Reason |
|------|-----------------|--------|
| needs_review | 17 | Confirmed duplicates / name–email mismatch  could distort group-level rates |
| dob_missing | 0 (after DQ) | No DOB → age bucket impossible |
| gender = Unknown | 3 | No protected-attribute signal excluded to keep group comparisons clean |

**Analytical sample: 487 records** (96.6% of cleaned dataset).

---

#### Issue 1 — Gender Disparate Impact

| Group | N | Approval Rate |
|-------|---|--------------|
| Female | 242 | **50%** |
| Male | 241 | **66.8%** |
| **DI ratio (F/M)** | — | **0.75** |

The **four-fifths rule** threshold is 0.80. At **DI = 0.75**, female applicants fall below this threshold, flagging potential adverse impact.

A **chi-square test of independence** (χ² = 13.35, df = 1, p = 0.0003) confirms the association between gender and approval outcome is statistically significant at p < 0.001 — well below the 0.05 threshold.

A **Fairlearn demographic parity difference** cross-check is included as a complementary absolute-gap measure.

---

#### Issue 2 -- Age-Based Patterns

Applicants are bucketed into six age groups and approval rates compared:

| Age Group | Approx. Approval Rate |
|-----------|----------------------|
| 18--24 | ~50% |
| 25--34 | **~45%** (lowest) |
| 35--44 | **~65.7%** |
| 45--54 | **~65.9%** (highest) |
| 55--64 | ~61% |
| 65+ | ~58% |

The **25--34** group has a notably lower approval rate than the dataset average, while **45--54** applicants are approved at the highest rate, closely followed by **35--44**. The two youngest groups, **18--24** and **25--34**, have the lowest approval rates, while the oldest group, **65+**, sits in the middle at around 58%.

---

#### Issue 3 - Interaction Effects (Age x Gender)

Cross-tabulation of age bucket x gender reveals the gender gap is **not confined to one age group** and is consistent across almost all age buckets:

- **25--34:** Female 34.6% vs Male 57.1% -- largest gap (~22.5 pp)
- **55--64:** Female 51.7% vs Male 72.0% -- second largest gap (~20.3 pp)
- **65+:** Female 50.0% vs Male 75.0% -- gap of 25 pp (small sample, interpret with caution)
- **35--44:** Female 58.0% vs Male 72.5% -- gap of ~14.5 pp
- **45--54:** Female 62.5% vs Male 68.9% -- smallest gap (~6.4 pp)
- **18--24:** Female 50.0% vs Male 50.0% -- no gap (very small sample)

This indicates a **systemic pattern** rather than a localised anomaly, with male applicants consistently outperforming female applicants across nearly every age group.

---

#### Issue 4 — ZIP Code Proxy Discrimination

ZIP code is not a protected attribute, but geographic data can act as a proxy for demographics. Analysis steps:

1. Filter to ZIP codes with ≥ 5 applications (19 ZIP codes remain)
2. Compute approval rate and female share per ZIP
3. Correlate female share with approval rate across ZIPs

**Results:**
- Approval rates across filtered ZIPs range from ~0.20 to 1.00 — substantial geographic variation
- Correlation between female share and approval rate: **−0.22** (weak negative)
- No strong linear pattern in scatter plot — ZIP code is **not a clear gender proxy** in this dataset, but geographic disparity in outcomes warrants monitoring

---

#### Correlation Scan

Point-biserial correlations between numeric features and loan_approved:

| Feature | Correlation |
|---------|------------|
| annual_income | +0.172 |
| credit_history_months | +0.154 |
| savings_balance | +0.136 |
| zip_code | -0.133 |
| age_years | +0.131 |
| debt_to_income | +0.009 |

Income, credit history, and savings are the strongest legitimate predictors. ZIP code shows a small negative correlation consistent with the proxy analysis. Notably, debt-to-income ratio shows a near-zero correlation, suggesting little independent linear relationship with approval outcomes in this dataset.

---

#### Key Findings

| Finding | Metric | Flag |
|---------|--------|------|
| Gender DI below four-fifths threshold | DI = 0.75 | Adverse impact flag |
| Gender–approval association is statistically significant | p = 0.0003 | Significant |
| Gender gap is present across **all** age groups | Consistent direction | Systemic |
| 25–34 age group has lowest approval rate | ~45.3% | Monitor |
| ZIP code not a clear gender proxy | r = −0.22 | Weak signal only |
| Top predictors are legitimate financial variables | Income, credit history, savings | Expected |

---

#### Implications for Governance

The analysis identifies a material gender disparity in approval outcomes that falls below the standard four-fifths rule threshold and is confirmed by statistical testing. This does not prove intentional discrimination, but it does require:

1. **Root-cause investigation** — determine whether the disparity is driven by the model, the input features, or the underlying application population
2. **Feature audit** — assess whether any features used by the model are correlated with gender (proxy discrimination risk)
3. **Ongoing monitoring** — track DI metrics in production and alert when DI falls below 0.80
4. **GDPR Art. 22 / EU AI Act Art. 10** — fairness obligations must be documented as part of the DPIA and the high-risk AI system's technical documentation



## Privacy, GDPR, and AI Governance Assessment
 
 
## 1. Purpose
 The notebook evaluates how personal data is collected, processed, protected, retained, and governed under the **General Data Protection Regulation (GDPR)** and the **EU AI Act**.
 
The assessment is designed to demonstrate both legal interpretation and practical implementation controls for a high-risk AI-enabled financial decision system.
 
---
 
## 2. File Submitted

- **Notebook:** `03-privacy-demofinal.ipynb`
 
---
 
## 3. Assessment Scope

The notebook covers six main workstreams:
 
1. **PII identification and classification**  

2. **GDPR article mapping and compliance obligations**  

3. **Pseudonymization and anonymization controls**  

4. **Right to erasure simulation under GDPR Article 17**  

5. **EU AI Act classification of the credit scoring system**  

6. **Governance and oversight controls** including audit logging, RBAC, retention, consent, and human review
 
---
 
## 4. Input Data

The notebook loads the cleaned dataset:

- **Source dataset:** `../data/cleaned_credit_applications.csv`
 
### Dataset Profile

- **Rows:** 500 credit applications

- **Columns:** 32

- **System assessed:** NovaCred automated credit approval / credit scoring workflow
 
### Personal Data Fields Identified

The notebook identifies **7 PII fields** in the dataset:

- `applicant_info_full_name`

- `applicant_info_email`

- `applicant_info_ssn`

- `applicant_info_ip_address`

- `applicant_info_date_of_birth`

- `applicant_info_zip_code`

- `applicant_info_gender`
 
### Other Key Operational / Decision Fields

Examples of non-PII fields used in the assessment include:

- `financials_annual_income`

- `financials_credit_history_months`

- `financials_debt_to_income`

- `financials_savings_balance`

- `decision_loan_approved`

- `decision_interest_rate`

- `decision_approved_amount`

- `decision_rejection_reason`

- `needs_review`

- `processing_timestamp`
 
---
 
## 5. Analytical and Compliance Approach

The notebook applies a structured privacy and governance review using both legal and technical controls.
 
### 5.1 PII Identification and Sensitivity Classification

Each PII field is classified by data type, legal category, and sensitivity level.
 
#### Classification Logic

- **Direct identifiers:** name, email

- **Highly sensitive direct identifier:** SSN

- **Online identifier:** IP address

- **Quasi-identifiers:** date of birth, ZIP code

- **Protected / special category risk:** gender
 
#### Main Finding

`applicant_info_gender` is treated as a **special-category / protected-attribute risk**. Its use in a credit decision system creates heightened GDPR Article 9 and anti-discrimination concerns and should not be used as a model feature without a valid legal basis.
 
### 5.2 GDPR Article Mapping

The notebook maps each field and processing activity to core GDPR requirements, including:

- **Art. 5(1)(b):** purpose limitation

- **Art. 5(1)(c):** data minimization

- **Art. 5(1)(e):** storage limitation

- **Art. 6:** lawful basis

- **Art. 7:** consent

- **Art. 9:** special categories

- **Art. 17:** right to erasure

- **Art. 22:** automated decision-making

- **Art. 25:** privacy by design

- **Art. 32:** security of processing

- **Art. 35:** data protection impact assessment
 
### 5.3 Pseudonymization and Anonymization

The notebook demonstrates privacy-preserving transformation techniques:

- **SHA-256 pseudonymization** for name, email, and SSN

- **IP masking** by zeroing the final octet

- **DOB generalization** into age bands

- Creation of a **privacy-safe analytics dataset** with raw PII removed
 
### 5.4 Right to Erasure Simulation

The notebook simulates erasure under **GDPR Art. 17** while preserving records subject to legal hold.
 
### 5.5 EU AI Act Assessment

Because the system performs **creditworthiness assessment / credit scoring of natural persons**, it is classified as a **high-risk AI system** under **Annex III, Point 5(b)** of the EU AI Act.
 
### 5.6 Governance Controls Implemented

The notebook includes demonstration implementations for:

- **PII access audit logging**

- **Role-based access control (RBAC)**

- **Data retention scheduling**

- **Consent logging and withdrawal**

- **Human oversight escalation queue**

- **Model decision logging**
 
---
 
## 6. Key Results and Findings
 
### 6.1 Dataset and Decision Statistics

- **Applications processed:** 500

- **Automated approvals:** 292 (**58.4%**)

- **Automated rejections:** 208 (**41.6%**)

- **Human-reviewed decisions:** 0 (**0.0%**) → clear compliance gap
 
### 6.2 Privacy Transformation Results

- **PII fields identified:** 7

- **Records pseudonymized:** 500

- **Records IP-masked:** 495

- **Privacy-safe dataset columns retained:** 30

- **Raw PII removed from analytics dataset:** 7 columns
 
### 6.3 Article 22 Compliance Finding

The system makes fully automated decisions but, at the time of assessment, lacks critical safeguards required by **GDPR Art. 22(3)**:

- no live mechanism for applicants to request human review

- no applicant-facing explanation for rejected decisions

- no documented safeguard workflow for automated decision challenge
 
This is one of the most important compliance gaps identified.
 
### 6.4 Erasure Simulation Results

- **Successful erasures completed:** 1

- **Erasures blocked due to legal hold (Art. 17(3)):** 1
 
The notebook demonstrates that direct PII can be removed while preserving legally required operational decision records.
 
### 6.5 Retention Results

Defined retention periods include:

- **Name / email / DOB / ZIP / gender:** 5 years

- **SSN:** 7 years

- **IP address:** 90 days

- **Decision records:** 7 years

- **Audit logs:** 10 years
 
At the time of execution:

- **Expired records identified:** 0

- **Active records:** 500
 
### 6.6 Consent and Accountability Results

- **Consent records logged:** 6 across 3 applicants

- **Audit log entries captured:** 10

- **Model decision log entries captured:** 3
 
These controls demonstrate accountability and traceability, but they remain prototype-level and would need production hardening.
 
### 6.7 Human Oversight Results

- **Applications escalated for human review:** 14 (**2.8%**)

- All escalations shown were **HIGH priority**
 
The notebook establishes the structure for a human review queue, but the summary explicitly notes that the pipeline is not yet live in production.
 
### 6.8 Overall Governance Outcome

- **Overall governance score:** 86%
 
This indicates strong conceptual and technical progress, but not full operational compliance.
 
---
 
## 7. Compliance Position
 
### GDPR Summary

The notebook shows strong coverage of the core GDPR control areas:

- PII identification completed

- lawful basis documented

- minimization demonstrated

- retention controls implemented

- accountability controls implemented

- consent logging implemented

- erasure workflow implemented

- privacy-by-design controls demonstrated

- security controls demonstrated

- DPIA-style risk assessment completed
 
### Areas Still Partial or Incomplete

- **Article 22:** human intervention mechanism is not fully operational

- **Article 9 risk:** gender should be excluded from model features unless a valid special-category basis is established

- applicant-facing transparency and explanation mechanisms are still incomplete
 
### EU AI Act Summary

The system is correctly classified as **high-risk**. The notebook shows partial implementation readiness, but important obligations remain incomplete:

- ongoing risk management is not yet fully operational

- formal technical documentation is not yet complete

- applicant-facing transparency is missing

- human oversight is designed but not live

- a formal quality management system is not yet documented
 
---
 
## 8. Main Compliance Gaps Identified

1. **No operational human-review process for automated credit decisions**  

2. **No applicant-facing explanation / contestability workflow for rejected applications**  

3. **Use of gender presents a high legal and ethical risk**  

4. **EU AI Act technical documentation is not yet formalized**  

5. **Transparency disclosures to affected individuals are not yet implemented**  

6. **Continuous monitoring and quality management remain incomplete**
 
---
 
## 9. Final Recommendations

The notebook’s own concluding recommendations are well supported by the evidence and should be treated as priority actions:
 
1. **Remove `applicant_info_gender` from all model features immediately** unless a valid Article 9 basis can be proven.  

2. **Implement a GDPR Article 22(3) redress mechanism** so rejected applicants can request meaningful human review.  

3. **Formalize EU AI Act Article 11 technical documentation** covering model architecture, training data, assumptions, and performance.  

4. **Deploy automated deletion for raw IP addresses after 90 days** in line with the retention schedule.  

5. **Commission an independent formal DPIA / external review** before production deployment.  

6. **Operationalize human oversight** so escalations can be reviewed, overridden, and closed by authorized staff.  

7. **Add applicant-facing transparency notices** for AI-assisted credit decisions.
 
---
 
## 10. Deliverables Demonstrated in the Notebook

- PII classification

- GDPR obligation mapping

- DPIA-style risk register

- pseudonymization and masking

- privacy-safe analytics dataset generation

- erasure workflow and audit log

- model decision logging

- audit logging for field access

- RBAC enforcement

- retention control logic

- consent ledger and withdrawal handling

- human oversight escalation queue

- final compliance metrics dashboard
 
---
 
## 11. Conclusion

This submission provides a **well-structured, DPO-level privacy and AI governance assessment** of the NovaCred credit scoring system. It demonstrates a strong understanding of both **GDPR compliance requirements** and the **EU AI Act obligations** applicable to high-risk AI in financial services.
 
The work is strongest in its treatment of:

- privacy risk identification

- pseudonymization and data minimization

- erasure handling

- governance control design

- legal mapping to GDPR and EU AI Act provisions
 
The most significant remaining issue is that the system still relies on **fully automated decision-making without a live human intervention process**, which creates a material compliance gap under **GDPR Article 22** and weakens readiness under **EU AI Act Article 14**.
 
---
 
## 12. Executive Summary (One-Paragraph Version)

The submitted notebook evaluates the NovaCred automated credit scoring system against GDPR and EU AI Act requirements using a 500-row, 32-column cleaned credit application dataset. It identifies 7 PII fields, demonstrates pseudonymization, IP masking, data minimization, retention controls, audit logging, consent management, and right-to-erasure handling, and confirms that the system qualifies as a high-risk AI system under Annex III of the EU AI Act. The strongest findings are the successful implementation of privacy-preserving controls and governance prototypes; the main weakness is the absence of a live Article 22-compliant human review and explanation mechanism for fully automated credit decisions. The notebook reports an overall governance score of 86%, indicating substantial compliance progress but not full production readiness.

 