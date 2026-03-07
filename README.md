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
### Bias Analysis 


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

The notebook is not only descriptive; it includes practical implementation examples for:

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
 
Overall, the notebook is a strong compliance-focused prototype and a credible submission for demonstrating privacy, governance, and responsible AI oversight in an automated credit scoring context.
 
---
 
## 12. Executive Summary (One-Paragraph Version)

The submitted notebook evaluates the NovaCred automated credit scoring system against GDPR and EU AI Act requirements using a 500-row, 32-column cleaned credit application dataset. It identifies 7 PII fields, demonstrates pseudonymization, IP masking, data minimization, retention controls, audit logging, consent management, and right-to-erasure handling, and confirms that the system qualifies as a high-risk AI system under Annex III of the EU AI Act. The strongest findings are the successful implementation of privacy-preserving controls and governance prototypes; the main weakness is the absence of a live Article 22-compliant human review and explanation mechanism for fully automated credit decisions. The notebook reports an overall governance score of 86%, indicating substantial compliance progress but not full production readiness.

 