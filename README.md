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
```bash
pip install -r requirements.txt
```

## Structure
| Path | Purpose |
|---|---|
| `data/` | Raw dataset (`raw_credit_applications.json`) |
| `notebooks/` | Jupyter analysis notebooks — run in order: 01 → 03 |
| `src/fairness_utils.py` | Shared cleaning pipeline — single source of truth |
| `presentation/` | Final slide deck deliverable |

## Notebooks
| Notebook | Role | Purpose |
|---|---|---|
| `01-data-quality.ipynb` | Data Engineer | DQ audit, cleaning pipeline, `df_clean` |
| `02-bias-analysis.ipynb` | Data Analyst | Fairness metrics, demographic parity |
| `03-privacy-demo.ipynb` | DPO | GDPR pseudonymisation, access controls |

## Key Findings
The dataset (`raw_credit_applications.json`, 502 records) contains 14 documented data quality
issues across all six DQ dimensions. After cleaning, `df_clean` has 500 rows × 29 columns
and is ready for fairness analysis. See `01-data-quality.ipynb` for the full scorecard.
