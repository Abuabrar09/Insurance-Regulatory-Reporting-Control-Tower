"""
controls.py - Step 7 of the reporting cycle

Executes the control matrix (config/control_matrix.csv) by reading the evidence
each earlier step produced, and writes:
  outputs/filing_calendar.csv   due dates, business days left, status (CTL-07)
  outputs/control_log.csv       one row per control: result, evidence, timestamp

CTL-08 (file integrity) is executed by submit.py when the package is built.
CTL-09 (segregation of duties) is a manual sign-off.
"""
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config"
OUT = ROOT / "outputs"
EVIDENCE = OUT / "evidence"
REPORTS = OUT / "reports"

MIN_BUSINESS_DAYS = 5  # CTL-07: ready at least 5 business days before due


def filing_calendar(as_of):
    inv = pd.read_csv(CONFIG / "report_inventory.csv")
    cal = inv[["report_id", "report_name", "recipient", "frequency", "due_date_2015Q1",
               "preparer_team", "reviewer_team"]].rename(columns={"due_date_2015Q1": "due_date"})
    cal["as_of"] = as_of
    cal["business_days_left"] = np.busday_count(
        np.datetime64(as_of), cal["due_date"].to_numpy(dtype="datetime64[D]"))
    cal["status"] = np.select(
        [cal["business_days_left"] < 0, cal["business_days_left"] < MIN_BUSINESS_DAYS],
        ["Overdue", "At risk"], default="On track")
    produced = {p.name.split("_")[0] for p in REPORTS.glob("RPT-*.csv")}
    cal["report_produced"] = cal["report_id"].isin(produced).map({True: "Yes", False: "No"})
    cal.to_csv(OUT / "filing_calendar.csv", index=False)
    return cal


def git_commit():
    try:
        return subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                              capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2015Q1")
    parser.add_argument("--as-of", default="2015-04-06", help="date the cycle is run (simulated)")
    args = parser.parse_args()

    load = pd.read_csv(EVIDENCE / "load_log.csv")
    dq = pd.read_csv(OUT / "dq_results.csv")
    totals = pd.read_csv(REPORTS / "report_control_totals.csv")
    recon = pd.read_csv(OUT / "recon_results.csv")
    cross = pd.read_csv(OUT / "cross_report_check.csv")
    cal = filing_calendar(args.as_of)
    commit = git_commit()

    blocking_fail = dq[(dq["severity"] == "Blocking") & (dq["result"] == "FAIL")]
    warn_fail = dq[(dq["severity"] == "Warning") & (dq["result"] == "FAIL")]
    unexplained = recon[recon["ctl05_result"] == "BREAK - UNEXPLAINED"]
    explained = recon[recon["ctl05_result"] == "BREAK - EXPLAINED"]
    late = cal[cal["status"] != "On track"]

    def r(ok):
        return "PASS" if ok else "FAIL"

    results = {
        "CTL-01": (r((load["ctl01_result"] == "PASS").all()),
                   f"{load['loaded_rows'].sum()} rows loaded across {len(load)} tables"),
        "CTL-02": (r(blocking_fail.empty and (dq["table_checked"] == "policy_claims_clean").all()),
                   f"{(dq['result'] == 'PASS').sum()} of {len(dq)} rules pass on policy_claims_clean"),
        "CTL-03": (r(warn_fail.empty), f"{len(warn_fail)} warning(s) open"),
        "CTL-04": (r(~totals["ctl04_result"].eq("FAIL").any()),
                   f"{len(totals)} reports tie to source; "
                   f"{totals['ctl04_result'].eq('PASS (rounding)').sum()} within rounding tolerance"),
        "CTL-05": (r(unexplained.empty),
                   f"{len(recon) - len(explained) - len(unexplained)} of {len(recon)} GL lines tie; "
                   f"{len(explained)} explained break(s)"),
        "CTL-06": (r((cross["ctl06_result"] == "PASS").all()), f"{len(cross)} cross-report checks"),
        "CTL-07": (r(late.empty), f"{len(cal) - len(late)} of {len(cal)} reports on track as of {args.as_of}"),
        "CTL-08": ("PENDING", "Executed by submit.py when the package is built"),
        "CTL-09": ("PENDING SIGN-OFF", "Preparer and reviewer sign signoff_checklist.md"),
        "CTL-10": (r(bool(commit)), f"Code version {commit}" if commit else "No git commit found"),
    }

    matrix = pd.read_csv(CONFIG / "control_matrix.csv")
    ts = datetime.now().isoformat(timespec="seconds")
    log = matrix[["control_id", "control_name", "control_type", "automated",
                  "performed_by", "reviewed_by", "evidence"]].copy()
    log.insert(0, "period", args.period)
    log["result"] = log["control_id"].map(lambda c: results[c][0])
    log["detail"] = log["control_id"].map(lambda c: results[c][1])
    log["executed_at"] = ts
    log.to_csv(OUT / "control_log.csv", index=False)

    print("Filing calendar (CTL-07)")
    print(cal[["report_id", "due_date", "business_days_left", "status"]].to_string(index=False))
    print("\nControl log")
    print(log[["control_id", "control_name", "result", "detail"]].to_string(index=False))

    if (log["result"] == "FAIL").any():
        raise SystemExit("\nOne or more controls FAILED. Submission is blocked.")
    print("\nAll automated controls PASS. Ready to build the submission package.")


if __name__ == "__main__":
    main()
