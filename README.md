# Insurance Regulatory Reporting Control Tower

**An end-to-end, audit-ready regulatory and statistical reporting pipeline for an auto insurer:** reporting inventory, filing calendar, data validation, remediation with an audit trail, report production, reconciliation to the general ledger, control execution, and a checksummed submission package. One command runs the full quarterly cycle.

![Python](https://img.shields.io/badge/Python-3776AB?logo=python&logoColor=white) ![SQL](https://img.shields.io/badge/SQL-SQLite-003B57?logo=sqlite&logoColor=white) ![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white) ![Status](https://img.shields.io/badge/pipeline-passing-brightgreen)

```bash
python run_pipeline.py --period 2015Q1
```

---

## Results at a Glance (2015Q1 cycle)

| Area | Result |
|---|---|
| Data quality | Raw extract **blocked** on 5 of 22 rules → 16 logged corrections → **22 of 22 rules pass** |
| Real data finding | 1 claim with a loss date **20 days before** its policy was bound, routed to Claims & Underwriting as an approved exception |
| Report production | **6 reports** produced from SQL; every control total ties to an independent Python recalculation |
| Reconciliation | **7 of 9** GL lines tie exactly; offsetting **$2,500** IL/IN misposting found and explained |
| Controls | **9 of 10** controls pass automatically; CTL-09 awaits human sign-off by design |
| Integrity | **16 files** in the submission package, each with a verified SHA-256 checksum |
| Cycle time | Full cycle runs in **about 4 seconds** |

---

## Business Problem
Insurers file dozens of recurring state, statistical, and regulatory reports. A late filing or a number that doesn't tie to the financial statements can lead to regulatory findings, fines, and costly re-filings. Most of the risk isn't in the analysis but in the **process**: unclear requirements, manual checks, missing reconciliations, and no audit trail.

## Solution
A gated pipeline that turns raw policy and claims data into **validated, reconciled, and controlled** reports, with the evidence an auditor or examiner would ask for. A blocking failure at any gate stops the run before anything is submitted.

| Step | Script | Control |
|---|---|---|
| 1. Load source extracts into SQLite | `src/load.py` | CTL-01 row-count completeness |
| 2. Validate raw extract | `src/validate.py` | CTL-02 blocking DQ rules |
| 3. Remediate with audit trail | `src/remediate.py` | before/after log for every change |
| 4. Validate clean data | `src/validate.py --table policy_claims_clean` | CTL-02, CTL-03 |
| 5. Produce 6 reports | `src/produce_reports.py` + `sql/` | CTL-04 independent control totals |
| 6. Reconcile | `src/reconcile.py` | CTL-05 GL tie-out, CTL-06 cross-report |
| 7. Execute controls | `src/controls.py` | CTL-07 filing calendar, CTL-10 change control |
| 8. Build submission package | `src/submit.py` | CTL-08 SHA-256 checksums, CTL-09 sign-off |

## Findings and How They Were Handled

**1. Raw extract blocked (CTL-02).** The first validation run failed 5 blocking rules: missing states (5), duplicated policies (2), negative premiums (3), claim totals not equal to their parts (3), and bind dates after the loss date (4). Sixteen were source errors, corrected in `src/remediate.py`; the seventeenth is the genuine finding below. Every change is recorded with before and after values and an approver in `outputs/evidence/remediation_log.csv`.

**2. A genuine data issue in the source data (DQ-11).** Policy 794731 (Indiana, $51,090 claim) shows a loss on 2015-02-02 but a policy bind date of 2015-02-22. Instead of altering the record, it was referred to Claims and Underwriting for coverage review and logged as an **approved exception** with an owner and review date (`config/approved_exceptions.csv`).

**3. Rounding difference (CTL-04).** The loss ratio report's earned premium differed from the source total by $0.01, because each state was rounded before summing. A documented $0.05 rounding tolerance was added, and those results are labeled `PASS (rounding)` so reviewers can tell them apart from exact matches.

**4. GL misposting (CTL-05).** Reconciliation found offsetting breaks of −$2,500 in Illinois and +$2,500 in Indiana losses paid. The +/− pair pointed to a posting between states rather than missing data. The break is documented with an owner and a correcting-entry date in `config/recon_explanations.csv`.

**5. Tolerance rule tightened (BR-09).** The original rule allowed "$1 or 0.1% of the GL balance". On a $10M+ balance, 0.1% is over $10,000 and would have hidden the $2,500 misposting entirely. The rule was changed to a flat $1.00.

## Reports in Scope
| ID | Report | Recipient |
|---|---|---|
| RPT-01 | State Premium & Loss Summary (modeled on the Annual Statement state page) | State insurance departments |
| RPT-02 | Claims Statistical Report by state, incident type and severity | Statistical agent |
| RPT-03 | Market Conduct-style Claims Report (closed with/without payment, days to close) | State insurance departments |
| RPT-04 | Fraud Referral Summary by state | State fraud bureaus |
| RPT-05 | Quarterly Loss Ratio Report | Internal Finance |
| RPT-06 | Regulator Data Call: Ohio claims over $50,000 in 2015Q1 | State insurance department |

## Documentation (audit-ready)
| Document | Purpose |
|---|---|
| [`docs/SOP.md`](docs/SOP.md) | Step-by-step procedure, exception handling, evidence retention |
| [`docs/RACI.md`](docs/RACI.md) | Roles across Legal, Accounting, Actuarial, Claims, Compliance, Technology |
| [`docs/data_dictionary.md`](docs/data_dictionary.md) | Every field used, its type and which reports use it |
| [`docs/business_rules.md`](docs/business_rules.md) | 10 reporting definitions and 22 data quality rules |
| [`config/report_inventory.csv`](config/report_inventory.csv) | Reporting inventory and due dates |
| [`config/control_matrix.csv`](config/control_matrix.csv) | 10 controls with type, owner, reviewer and evidence |

## Submission Package
`outputs/submission/2015Q1/` contains the 6 reports, all evidence files, `manifest.csv` with SHA-256 checksums, `control_log.csv`, and `signoff_checklist.md` for preparer, reviewer and approver sign-off.

## Data
- **Policy & claims data:** [Auto Insurance Claims Data](https://www.kaggle.com/datasets/buntyshah/auto-insurance-claims-data) by buntyshah on Kaggle: 1,000 policies, 40 columns
- **Simulated tables:** claim status/timing and general ledger trial balance, generated in Python with a fixed seed (`src/generate.py`)
- **Planted issues:** realistic data errors and a GL misposting were injected on purpose so the controls have something to catch. The full list is in `data/generated/planted_issues_log.csv`.

### Known limitations
- Every policy in the source data has a claim, so loss ratios in RPT-05 are far above real-world levels. The pipeline logic is unaffected.
- Report formats are simplified educational versions of real filings, not official regulatory submissions.
- The "policy admin system" used to correct missing states and bind dates is simulated by the planted-issues log.

## Project Structure
```
├── run_pipeline.py      # one command runs the full cycle
├── config/              # report inventory, control matrix, approved exceptions, recon explanations
├── data/raw/            # Kaggle source data
├── data/generated/      # simulated extract, claim status, GL, planted-issues log
├── sql/                 # one query per report
├── src/                 # load, validate, remediate, produce, reconcile, controls, submit
├── docs/                # SOP, RACI, data dictionary, business rules
└── outputs/             # reports, evidence, control log, submission package
```

## How to Run
Runs in GitHub Codespaces with nothing to install locally.
```bash
pip install -r requirements.txt
python src/generate.py                  # one-time: build the simulated source files
python run_pipeline.py --period 2015Q1  # full cycle
```

## Author
**Abrar Ahmed Syed**, Business Data / Financial & AI Analyst
[LinkedIn](https://www.linkedin.com/in/abrar313) · [Portfolio](https://abuabrar09.github.io) · [GitHub](https://github.com/Abuabrar09)
