# SOP: Quarterly Regulatory Reporting Cycle

| Item | Detail |
|---|---|
| Owner | Regulatory Reporting |
| Frequency | Quarterly (plus ad hoc data calls) |
| Inputs | `data/raw/insurance_claims.csv`, `data/generated/*`, `config/*` |
| Outputs | `outputs/submission/<period>/` |
| Version | 1.0 |

## 1. Purpose
Produce accurate, timely, well-controlled regulatory and statistical reports, with evidence that supports audits and regulatory examinations.

## 2. Scope
The 6 reports listed in `config/report_inventory.csv`.

## 3. Procedure
| Step | Action | Command / file | Control |
|---|---|---|---|
| 1 | Confirm reporting period and due dates | `outputs/filing_calendar.csv` | CTL-07 |
| 2 | Load source data and confirm row counts | `src/load.py` | CTL-01 |
| 3 | Run data quality checks; stop on any blocking failure | `src/validate.py` | CTL-02 |
| 4 | Review warnings and record a disposition for each | `outputs/dq_warnings_review.csv` | CTL-03 |
| 5 | Produce reports | `src/produce_reports.py` | CTL-04 |
| 6 | Reconcile to GL and across reports; explain every break | `src/reconcile.py` | CTL-05, CTL-06 |
| 7 | Execute controls and write the control log | `src/controls.py` | All |
| 8 | Build submission package with checksums | `src/submit.py` | CTL-08 |
| 9 | Independent review and sign-off | `signoff_checklist.md` | CTL-09 |
| 10 | Submit and archive evidence | `outputs/evidence/` | CTL-10 |

Steps 2–8 run with one command: `python run_pipeline.py --period 2015Q1`

## 4. Exception handling
- **Blocking DQ failure:** pipeline stops. Failing rows are written to `outputs/exceptions/`. Fix at the source, rerun, and log the root cause.
- **Reconciliation break above tolerance:** document the cause and the owner. Reports cannot be submitted until it's explained or resolved.
- **Late risk:** if a report won't be ready 5 business days before its due date, escalate to Compliance.

## 5. Evidence retention
Each submission folder keeps the reports, manifest with checksums, DQ results, reconciliation results, control log, and sign-off. Nothing in a submitted folder is edited after sign-off.

## 6. Regulatory inquiries and data calls
Confirm the request with Legal/Compliance, document the definition used, run `src/data_call.py`, reconcile to RPT-01 for the same state, then review and archive.
