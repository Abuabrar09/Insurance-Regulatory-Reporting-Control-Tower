"""
reconcile.py - Step 6 of the reporting cycle (controls CTL-05 and CTL-06)

CTL-05  Ties RPT-01 premium, paid losses and reserves to the general ledger
        by state. Tolerance (BR-09): absolute difference <= $1.00.
        A break above tolerance must have an explanation in
        config/recon_explanations.csv, or submission is blocked (BR-10).
CTL-06  Checks that figures shared between reports agree with each other.

  outputs/recon_results.csv
  outputs/cross_report_check.csv
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "reg_reporting.db"
REPORTS = ROOT / "outputs" / "reports"
OUTPUTS = ROOT / "outputs"
EXPLANATIONS = ROOT / "config" / "recon_explanations.csv"

TOLERANCE = 1.00  # BR-09

# GL account -> RPT-01 column it must tie to
ACCOUNT_MAP = {
    "4100": "earned_premium",
    "5100": "paid_losses",
    "2100": "loss_reserves",
}


def gl_reconciliation(period):
    rpt01 = pd.read_csv(REPORTS / "RPT-01_state_premium_loss.csv")
    with sqlite3.connect(DB) as con:
        gl = pd.read_sql("SELECT * FROM gl_trial_balance WHERE period = ?", con,
                         params=(period,), dtype={"account_code": str})

    rows = []
    for _, g in gl.iterrows():
        col = ACCOUNT_MAP[g["account_code"]]
        report_value = rpt01.loc[rpt01["state"] == g["state"], col].sum()
        diff = round(report_value - g["amount"], 2)
        rows.append({
            "period": period, "state": g["state"], "account_code": g["account_code"],
            "account_name": g["account_name"], "report_value": round(report_value, 2),
            "gl_value": round(g["amount"], 2), "difference": diff,
            "within_tolerance": abs(diff) <= TOLERANCE,
        })
    recon = pd.DataFrame(rows)

    # attach explanations for breaks
    if EXPLANATIONS.exists():
        exp = pd.read_csv(EXPLANATIONS, dtype={"account_code": str})
        recon = recon.merge(exp, on=["state", "account_code"], how="left")
    else:
        recon["explanation"] = pd.NA
        recon["owner"] = pd.NA
        recon["status"] = pd.NA

    def result(r):
        if r["within_tolerance"]:
            return "PASS"
        if pd.notna(r.get("explanation")) and str(r.get("explanation")).strip():
            return "BREAK - EXPLAINED"
        return "BREAK - UNEXPLAINED"

    recon["ctl05_result"] = recon.apply(result, axis=1)
    return recon


def cross_report_checks():
    r = {name: pd.read_csv(f) for name, f in {
        "RPT-01": REPORTS / "RPT-01_state_premium_loss.csv",
        "RPT-02": REPORTS / "RPT-02_claims_statistical.csv",
        "RPT-03": REPORTS / "RPT-03_market_conduct_claims.csv",
        "RPT-04": REPORTS / "RPT-04_fraud_referrals.csv",
        "RPT-05": REPORTS / "RPT-05_loss_ratio.csv",
    }.items()}
    checks = [
        ("Incurred losses", "RPT-01", r["RPT-01"]["incurred_losses"].sum(),
         "RPT-02", r["RPT-02"]["total_amount"].sum()),
        ("Incurred losses", "RPT-01", r["RPT-01"]["incurred_losses"].sum(),
         "RPT-05", r["RPT-05"]["incurred_losses"].sum()),
        ("Earned premium", "RPT-01", r["RPT-01"]["earned_premium"].sum(),
         "RPT-05", r["RPT-05"]["earned_premium"].sum()),
        ("Claim count", "RPT-01", r["RPT-01"]["policies_with_claims"].sum(),
         "RPT-03", r["RPT-03"]["claims_reported"].sum()),
        ("Claim count", "RPT-03", r["RPT-03"]["claims_reported"].sum(),
         "RPT-04", r["RPT-04"]["claims"].sum()),
    ]
    out = pd.DataFrame(checks, columns=["figure", "report_a", "value_a", "report_b", "value_b"])
    out["difference"] = (out["value_a"] - out["value_b"]).round(2)
    out["ctl06_result"] = out["difference"].abs().le(0.05).map({True: "PASS", False: "FAIL"})
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2015Q1")
    args = parser.parse_args()

    recon = gl_reconciliation(args.period)
    recon.to_csv(OUTPUTS / "recon_results.csv", index=False)
    print("CTL-05 GL reconciliation (tolerance $1.00)")
    print(recon[["state", "account_name", "report_value", "gl_value", "difference",
                 "ctl05_result"]].to_string(index=False))

    cross = cross_report_checks()
    cross.to_csv(OUTPUTS / "cross_report_check.csv", index=False)
    print("\nCTL-06 cross-report consistency")
    print(cross.to_string(index=False))

    unexplained = recon[recon["ctl05_result"] == "BREAK - UNEXPLAINED"]
    explained = recon[recon["ctl05_result"] == "BREAK - EXPLAINED"]
    failed_cross = cross[cross["ctl06_result"] == "FAIL"]

    print()
    if not explained.empty:
        print(f"{len(explained)} break(s) explained and tracked in config/recon_explanations.csv")
    if not unexplained.empty or not failed_cross.empty:
        if not unexplained.empty:
            print(f"CTL-05 FAIL: {len(unexplained)} unexplained break(s). Investigate and document before submission.")
        if not failed_cross.empty:
            print("CTL-06 FAIL: reports disagree with each other.")
        raise SystemExit(1)
    print("CTL-05 PASS and CTL-06 PASS: reports reconcile to the GL and to each other.")


if __name__ == "__main__":
    main()
