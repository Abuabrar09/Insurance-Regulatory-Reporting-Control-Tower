"""
produce_reports.py - Step 5 of the reporting cycle (control CTL-04)

Runs one SQL file per report against the validated table policy_claims_clean,
writes each report to outputs/reports/, and proves each report's control total
equals the same total calculated independently from the source data.

  outputs/reports/RPT-0x_<name>.csv
  outputs/reports/report_control_totals.csv   (CTL-04 evidence)
"""
import argparse
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "reg_reporting.db"
SQL = ROOT / "sql"
REPORTS = ROOT / "outputs" / "reports"
# Rounding each state then summing can differ from rounding the total by a few cents
ROUNDING_TOLERANCE = 0.05

# report_id: (sql file, output name, column used as control total)
REPORTS_TO_RUN = {
    "RPT-01": ("rpt01_state_premium_loss.sql", "state_premium_loss", "incurred_losses"),
    "RPT-02": ("rpt02_claims_statistical.sql", "claims_statistical", "total_amount"),
    "RPT-03": ("rpt03_market_conduct_claims.sql", "market_conduct_claims", "claims_reported"),
    "RPT-04": ("rpt04_fraud_referrals.sql", "fraud_referrals", "fraud_referrals"),
    "RPT-05": ("rpt05_loss_ratio.sql", "loss_ratio", "earned_premium"),
    "RPT-06": ("rpt06_data_call.sql", "data_call_OH_over_50k", "total_claim_amount"),
}


def source_totals(c):
    """The same control totals, calculated a second way (pandas, not SQL)."""
    oh_big = c[(c["policy_state"] == "OH") & (c["total_claim_amount"] > 50000)]
    return {
        "RPT-01": c["total_claim_amount"].sum(),
        "RPT-02": c["total_claim_amount"].sum(),
        "RPT-03": len(c),
        "RPT-04": (c["fraud_reported"] == "Y").sum(),
        "RPT-05": round(c["policy_annual_premium"].sum() / 4, 2),
        "RPT-06": oh_big["total_claim_amount"].sum(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2015Q1")
    args = parser.parse_args()
    run_id = f"{args.period}-{datetime.now():%Y%m%d-%H%M%S}"

    REPORTS.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB) as con:
        clean = pd.read_sql("SELECT * FROM policy_claims_clean", con)
        expected = source_totals(clean)
        checks = []
        for report_id, (sql_file, name, total_col) in REPORTS_TO_RUN.items():
            report = pd.read_sql((SQL / sql_file).read_text(), con)
            out = REPORTS / f"{report_id}_{name}.csv"
            report.to_csv(out, index=False)

            report_total = round(float(report[total_col].sum()), 2)
            source_total = round(float(expected[report_id]), 2)
            diff = round(report_total - source_total, 2)
            checks.append({
                "run_id": run_id, "period": args.period, "report_id": report_id,
                "report_file": out.relative_to(ROOT).as_posix(), "rows": len(report),
                "control_total_field": total_col, "report_total": report_total,
                "source_total": source_total, "difference": diff,
                "ctl04_result": "PASS" if diff == 0 else ("PASS (rounding)" if abs(diff) <= ROUNDING_TOLERANCE else "FAIL"),
            })

    checks = pd.DataFrame(checks)
    checks.to_csv(REPORTS / "report_control_totals.csv", index=False)
    print(checks[["report_id", "rows", "control_total_field", "report_total",
                  "source_total", "ctl04_result"]].to_string(index=False))

    if (checks["ctl04_result"] == "FAIL").any():
        raise SystemExit("\nCTL-04 FAIL: a report total does not match the source. Do not submit.")
    print(f"\nCTL-04 PASS: all 6 reports tie to source. Run ID {run_id}")


if __name__ == "__main__":
    main()
