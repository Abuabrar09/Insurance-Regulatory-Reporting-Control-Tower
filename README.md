# Insurance Regulatory Reporting Control Tower

**An end-to-end, audit-ready regulatory and statistical reporting pipeline for an auto insurer:** reporting inventory, filing calendar, data validation, report production, reconciliation to the general ledger, control execution, and submission packaging.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![SQL](https://img.shields.io/badge/SQL-SQLite-003B57?logo=sqlite&logoColor=white) ![Tableau](https://img.shields.io/badge/Tableau-E97627?logo=tableau&logoColor=white) ![Status](https://img.shields.io/badge/status-in%20progress-yellow)

---

## Business Problem
Insurers file dozens of recurring state, statistical, and regulatory reports. A late filing or a number that doesn't tie to the financial statements can lead to regulatory findings, fines, and costly re-filings. Most of the risk isn't in the analysis but in the **process**: unclear requirements, manual checks, missing reconciliations, and no audit trail.

## Solution
A one-command pipeline that turns raw policy and claims data into **validated, reconciled, and controlled** regulatory reports, with the evidence an auditor or examiner would ask for.

| Capability | What it does |
|---|---|
| Reporting inventory & filing calendar | Register of 6 reports with regulator, frequency, owner, and due dates |
| Requirements & business rules | Data dictionary, business rules, and RACI across Legal, Accounting, Actuarial, Claims |
| Data validation | 20+ automated data quality checks with blocking and warning severities |
| Report production | State premium & loss summary, claims statistical report, market conduct claims report, and more |
| Reconciliation | Report totals tied to the general ledger by state, with tolerances and variance explanations |
| Controls & audit trail | Control matrix, execution log, SHA-256 checksums, sign-off checklist |
| Submission package | Reports + manifest + control evidence per reporting period |

## Reports in Scope
1. State Premium & Loss Summary (modeled on the Annual Statement state page)
2. Claims Statistical Report by coverage and state
3. Market Conduct-style Claims Report (opened, closed, closed without payment, days to close)
4. Fraud Referral Summary by state
5. Quarterly Loss Ratio Report to Finance
6. Ad hoc Regulator Data Call

## Data
- **Policy & claims data:** [Auto Insurance Claims Data](https://www.kaggle.com/datasets/buntyshah/auto-insurance-claims-data) by buntyshah on Kaggle: 1,000 policies, 40 columns
- **Simulated tables:** claim status/timing and general ledger trial balance, generated in Python with a fixed seed

> Note: Report formats are simplified educational versions of real filings, not official regulatory submissions. GL and claim status data are simulated for demonstration.

## Project Structure
```
├── run_pipeline.py      # one command runs the full cycle
├── config/              # report inventory, control matrix, DQ rules
├── data/raw/            # source data
├── data/generated/      # simulated GL and claim status
├── sql/                 # one query per report
├── src/                 # load, validate, produce, reconcile, controls, submit
├── docs/                # SOP, RACI, data dictionary, business rules
├── outputs/             # reports, exceptions, evidence, submission packages
└── tests/               # pytest checks
```

## How to Run
```bash
pip install -r requirements.txt
python run_pipeline.py --period 2015Q1
```

## Results
_Coming soon: data quality results, reconciliation results, and dashboard._

## Author
**Abrar Ahmed Syed**, Business Data / Financial & AI Analyst
[LinkedIn](https://www.linkedin.com/in/abrar313) · [Portfolio](https://abuabrar09.github.io) · [GitHub](https://github.com/Abuabrar09)