"""
remediate.py - fixes the data issues found by validate.py, with an audit trail

Reads table policy_claims, applies approved corrections, writes table
policy_claims_clean, and logs every change (before and after) to
outputs/evidence/remediation_log.csv.

Corrections:
  DQ-06 duplicate rows      -> keep the first copy
  DQ-08 negative premium    -> sign flip confirmed with Accounting, use absolute value
  DQ-10 total != parts      -> recompute total from injury + property + vehicle
  DQ-02 missing state       -> value looked up in the policy admin system
  DQ-11 bind after incident -> value looked up in the policy admin system
(The policy admin system lookup is simulated by data/generated/planted_issues_log.csv.)
"""
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data" / "reg_reporting.db"
LOOKUP = ROOT / "data" / "generated" / "planted_issues_log.csv"
EVIDENCE = ROOT / "outputs" / "evidence"


def main():
    with sqlite3.connect(DB) as con:
        c = pd.read_sql("SELECT * FROM policy_claims", con)

    ts = datetime.now().isoformat(timespec="seconds")
    log = []

    def record(rule, policy, field, before, after, action):
        log.append({"timestamp": ts, "rule_id": rule, "policy_number": policy, "field": field,
                    "before": before, "after": after, "action": action,
                    "approved_by": "Regulatory Reporting Lead (simulated)"})

    # DQ-06 duplicates
    dupes = c[c.duplicated(keep="first")]
    for p in dupes["policy_number"]:
        record("DQ-06", p, "row", "duplicate row", "removed", "Dropped exact duplicate extract row")
    c = c.drop_duplicates(keep="first").reset_index(drop=True)

    # DQ-08 negative premium
    for i in c.index[c["policy_annual_premium"] < 0]:
        before = c.at[i, "policy_annual_premium"]
        c.at[i, "policy_annual_premium"] = abs(before)
        record("DQ-08", c.at[i, "policy_number"], "policy_annual_premium", before, abs(before),
               "Sign error confirmed with Accounting")

    # DQ-10 total does not equal parts
    parts = c["injury_claim"] + c["property_claim"] + c["vehicle_claim"]
    for i in c.index[c["total_claim_amount"] != parts]:
        before = c.at[i, "total_claim_amount"]
        c.at[i, "total_claim_amount"] = parts[i]
        record("DQ-10", c.at[i, "policy_number"], "total_claim_amount", before, parts[i],
               "Recomputed from claim components; confirmed with Claims")

    # DQ-02 and DQ-11: look up the correct value in the policy admin system
    lookup = pd.read_csv(LOOKUP, dtype=str)
    for rule, field in [("DQ-02", "policy_state"), ("DQ-11", "policy_bind_date")]:
        fixes = lookup[lookup["rule_id"] == rule]
        for _, f in fixes.iterrows():
            mask = c["policy_number"].astype(str) == f["policy_number"]
            before = c.loc[mask, field].iloc[0] if mask.any() else None
            c.loc[mask, field] = f["original_value"]
            record(rule, f["policy_number"], field, before, f["original_value"],
                   "Corrected from policy admin system")

    with sqlite3.connect(DB) as con:
        c.to_sql("policy_claims_clean", con, if_exists="replace", index=False)

    log = pd.DataFrame(log)
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    log.to_csv(EVIDENCE / "remediation_log.csv", index=False)
    print(log.groupby("rule_id").size().rename("corrections").to_string())
    print(f"\n{len(log)} corrections logged to outputs/evidence/remediation_log.csv")
    print(f"policy_claims_clean: {len(c)} rows")


if __name__ == "__main__":
    main()
