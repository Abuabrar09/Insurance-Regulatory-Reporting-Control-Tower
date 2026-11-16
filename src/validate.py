"""
validate.py - Step 3 of the reporting cycle (controls CTL-02 and CTL-03)

Runs the 22 data quality rules from docs/business_rules.md.
  outputs/dq_results.csv          one row per rule: tested, failed, PASS/FAIL
  outputs/exceptions/DQ-xx.csv    the failing rows for each failed rule

Usage:
  python src/validate.py                         # checks the raw extract
  python src/validate.py --table policy_claims_clean
Exit code 1 if any BLOCKING rule fails (the pipeline must stop).
"""
import argparse
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "reg_reporting.db"
OUTPUTS = ROOT / "outputs"
EXCEPTIONS = OUTPUTS / "exceptions"

PERIOD_START = pd.Timestamp("2015-01-01")
PERIOD_END = pd.Timestamp("2015-03-31")
VALID_STATES = {"IL", "IN", "OH"}


def share_rule(df, col, limit):
    """Rows with '?' fail only if their share reaches the limit."""
    unknown = df[df[col].astype(str).str.strip() == "?"]
    share = len(unknown) / len(df)
    return unknown if share >= limit else unknown.iloc[0:0], share


def run_rules(c, s):
    """c = policy/claims table, s = claim_status table. Returns rule results."""
    bind = pd.to_datetime(c["policy_bind_date"], errors="coerce")
    incident = pd.to_datetime(c["incident_date"], errors="coerce")
    rep = pd.to_datetime(s["report_date"], errors="coerce")
    close = pd.to_datetime(s["close_date"], errors="coerce")
    s_inc = s.merge(c[["policy_number", "incident_date"]].drop_duplicates("policy_number"),
                    on="policy_number", how="left")
    parts = c["injury_claim"] + c["property_claim"] + c["vehicle_claim"]
    closed = s["claim_status"].str.startswith("CLOSED")

    pr_fail, pr_share = share_rule(c, "police_report_available", 0.40)
    pd_fail, pd_share = share_rule(c, "property_damage", 0.40)
    ct_fail, ct_share = share_rule(c, "collision_type", 0.25)

    # (id, check, rule, severity, failing rows, rows tested, note)
    return [
        ("DQ-01", "Completeness", "policy_number not null", "Blocking", c[c["policy_number"].isna()], len(c), ""),
        ("DQ-02", "Completeness", "policy_state not null", "Blocking", c[c["policy_state"].isna()], len(c), ""),
        ("DQ-03", "Completeness", "policy_annual_premium not null", "Blocking", c[c["policy_annual_premium"].isna()], len(c), ""),
        ("DQ-04", "Completeness", "incident_date not null", "Blocking", c[c["incident_date"].isna()], len(c), ""),
        ("DQ-05", "Completeness", "total_claim_amount not null", "Blocking", c[c["total_claim_amount"].isna()], len(c), ""),
        ("DQ-06", "Uniqueness", "policy_number is unique", "Blocking", c[c["policy_number"].duplicated(keep=False)], len(c), ""),
        ("DQ-07", "Validity", "policy_state in IL, IN, OH", "Blocking",
         c[c["policy_state"].notna() & ~c["policy_state"].isin(VALID_STATES)], len(c), ""),
        ("DQ-08", "Validity", "policy_annual_premium > 0", "Blocking", c[c["policy_annual_premium"] <= 0], len(c), ""),
        ("DQ-09", "Validity", "total_claim_amount >= 0", "Blocking", c[c["total_claim_amount"] < 0], len(c), ""),
        ("DQ-10", "Consistency", "total_claim_amount = injury + property + vehicle", "Blocking",
         c[c["total_claim_amount"] != parts], len(c), ""),
        ("DQ-11", "Date logic", "incident_date >= policy_bind_date", "Blocking", c[incident < bind], len(c), ""),
        ("DQ-12", "Date logic", "incident_date within 2015Q1", "Blocking",
         c[(incident < PERIOD_START) | (incident > PERIOD_END)], len(c), ""),
        ("DQ-13", "Validity", "fraud_reported in (Y, N)", "Blocking", c[~c["fraud_reported"].isin(["Y", "N"])], len(c), ""),
        ("DQ-14", "Date logic", "report_date >= incident_date", "Warning",
         s[rep < pd.to_datetime(s_inc["incident_date"])], len(s), ""),
        ("DQ-15", "Date logic", "close_date >= report_date when present", "Warning", s[close < rep], len(s), ""),
        ("DQ-16", "Consistency", "CLOSED has close_date; OPEN does not", "Warning",
         s[(closed & close.isna()) | (~closed & close.notna())], len(s), ""),
        ("DQ-17", "Validity", "paid_amount and reserve_amount >= 0", "Warning",
         s[(s["paid_amount"] < 0) | (s["reserve_amount"] < 0)], len(s), ""),
        ("DQ-18", "Unknown values", "police_report_available '?' share < 40%", "Warning", pr_fail, len(c), f"share {pr_share:.1%}"),
        ("DQ-19", "Unknown values", "property_damage '?' share < 40%", "Warning", pd_fail, len(c), f"share {pd_share:.1%}"),
        ("DQ-20", "Unknown values", "collision_type '?' share < 25%", "Warning", ct_fail, len(c), f"share {ct_share:.1%}"),
        ("DQ-21", "Outliers", "total_claim_amount <= 150,000", "Warning", c[c["total_claim_amount"] > 150_000], len(c), ""),
        ("DQ-22", "Referential", "every claim_status row links to a policy", "Blocking",
         s[~s["policy_number"].isin(c["policy_number"])], len(s), ""),
    ]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--table", default="policy_claims")
    args = parser.parse_args()

    with sqlite3.connect(DB) as con:
        c = pd.read_sql(f"SELECT * FROM {args.table}", con)
        s = pd.read_sql("SELECT * FROM claim_status", con)

    EXCEPTIONS.mkdir(parents=True, exist_ok=True)
    for old in EXCEPTIONS.glob("DQ-*.csv"):
        old.unlink()

    results = []
    for rule_id, check, rule, severity, failing, tested, note in run_rules(c, s):
        status = "PASS" if failing.empty else "FAIL"
        if not failing.empty:
            failing.to_csv(EXCEPTIONS / f"{rule_id}.csv", index=False)
        results.append({
            "table_checked": args.table, "rule_id": rule_id, "check": check, "rule": rule,
            "severity": severity, "rows_tested": tested, "rows_failed": len(failing),
            "result": status, "note": note,
        })

    results = pd.DataFrame(results)
    results.to_csv(OUTPUTS / "dq_results.csv", index=False)
    print(results[["rule_id", "check", "severity", "rows_failed", "result", "note"]].to_string(index=False))

    blocking = results[(results["severity"] == "Blocking") & (results["result"] == "FAIL")]
    warnings = results[(results["severity"] == "Warning") & (results["result"] == "FAIL")]
    print(f"\nTable checked: {args.table}")
    print(f"Rules passed: {(results['result'] == 'PASS').sum()} of {len(results)}")
    print(f"Warnings needing review (CTL-03): {len(warnings)}")
    if not blocking.empty:
        print(f"CTL-02 FAIL: {len(blocking)} blocking rule(s) failed: {', '.join(blocking['rule_id'])}")
        print("Failing rows saved in outputs/exceptions/. Reports must NOT be produced.")
        raise SystemExit(1)
    print("CTL-02 PASS: no blocking failures. Safe to produce reports.")


if __name__ == "__main__":
    main()
    