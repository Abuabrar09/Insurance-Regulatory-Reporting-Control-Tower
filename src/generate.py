"""
generate.py - one-time setup script (Phase 3)

Builds the simulated "source system" files the pipeline reads:
  data/generated/policy_claims.csv      raw Kaggle data + planted data issues
  data/generated/claim_status.csv       simulated claim timing and payments
  data/generated/gl_trial_balance.csv   simulated general ledger by state
  data/generated/planted_issues_log.csv answer key of every planted issue

A fixed random seed makes every run produce identical files.
"""
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
PERIOD = "2015Q1"
PERIOD_END = pd.Timestamp("2015-03-31")

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "insurance_claims.csv"
OUT = ROOT / "data" / "generated"


def clean_columns(df):
    """Drop empty _c columns and make names SQL-friendly."""
    df = df.loc[:, ~df.columns.str.startswith("_c")]
    df.columns = df.columns.str.strip().str.replace("-", "_")
    return df


def build_claim_status(claims, rng):
    """Simulate when each claim was reported, closed and paid."""
    n = len(claims)
    incident = pd.to_datetime(claims["incident_date"])
    report_date = incident + pd.to_timedelta(rng.integers(0, 6, n), unit="D")
    days_to_close = rng.integers(5, 75, n)
    close_date = report_date + pd.to_timedelta(days_to_close, unit="D")

    # fraud-referred claims are more often closed without payment
    is_fraud = claims["fraud_reported"].eq("Y").to_numpy()
    no_pay_chance = np.where(is_fraud, 0.40, 0.08)
    closed_without_pay = rng.random(n) < no_pay_chance

    is_closed = close_date <= PERIOD_END
    total = claims["total_claim_amount"].to_numpy()

    status = np.where(
        ~is_closed, "OPEN",
        np.where(closed_without_pay, "CLOSED_WITHOUT_PAYMENT", "CLOSED_WITH_PAYMENT"),
    )
    paid = np.where(status == "CLOSED_WITH_PAYMENT", total, 0.0)
    # open claims: some partial payments, the rest held as reserve
    partial = np.round(total * rng.uniform(0, 0.5, n), 2)
    paid = np.where(status == "OPEN", partial, paid)
    reserve = np.where(status == "OPEN", total - paid, 0.0)

    return pd.DataFrame({
        "claim_id": "CLM-" + claims["policy_number"].astype(str),
        "policy_number": claims["policy_number"],
        "report_date": report_date.dt.strftime("%Y-%m-%d"),
        "close_date": pd.Series(close_date.dt.strftime("%Y-%m-%d")).where(is_closed, ""),
        "claim_status": status,
        "paid_amount": np.round(paid, 2),
        "reserve_amount": np.round(reserve, 2),
    })


def build_gl(claims, status):
    """GL balances by state, built from CLEAN data so they should tie."""
    df = claims[["policy_number", "policy_state", "policy_annual_premium"]].merge(
        status[["policy_number", "paid_amount", "reserve_amount"]], on="policy_number"
    )
    by_state = df.groupby("policy_state").agg(
        premium=("policy_annual_premium", "sum"),
        paid=("paid_amount", "sum"),
        reserve=("reserve_amount", "sum"),
    )
    rows = []
    for state, r in by_state.iterrows():
        rows += [
            (PERIOD, state, "4100", "Premium Earned", round(r.premium / 4, 2)),
            (PERIOD, state, "5100", "Losses Paid", round(r.paid, 2)),
            (PERIOD, state, "2100", "Loss Reserves", round(r.reserve, 2)),
        ]
    gl = pd.DataFrame(rows, columns=["period", "state", "account_code", "account_name", "amount"])
    return gl


def plant_issues(claims, status, gl, rng):
    """Inject realistic data problems and record each one in a log."""
    claims = claims.copy()
    log = []

    def pick(k):
        return rng.choice(claims.index, size=k, replace=False)

    for i in pick(5):  # DQ-02 missing state
        log.append(("DQ-02", claims.at[i, "policy_number"], "policy_state", claims.at[i, "policy_state"], ""))
        claims.at[i, "policy_state"] = np.nan

    for i in pick(3):  # DQ-08 negative premium (sign flipped in source system)
        old = claims.at[i, "policy_annual_premium"]
        log.append(("DQ-08", claims.at[i, "policy_number"], "policy_annual_premium", old, -old))
        claims.at[i, "policy_annual_premium"] = -old

    for i in pick(3):  # DQ-10 claim total does not equal its parts
        old = claims.at[i, "total_claim_amount"]
        log.append(("DQ-10", claims.at[i, "policy_number"], "total_claim_amount", old, old + 1000))
        claims.at[i, "total_claim_amount"] = old + 1000

    for i in pick(3):  # DQ-11 bind date keyed after the incident
        old = claims.at[i, "policy_bind_date"]
        log.append(("DQ-11", claims.at[i, "policy_number"], "policy_bind_date", old, "2015-03-15"))
        claims.at[i, "policy_bind_date"] = "2015-03-15"

    dupes = claims.loc[pick(2)]  # DQ-06 duplicate extract rows
    for _, r in dupes.iterrows():
        log.append(("DQ-06", r["policy_number"], "policy_number", "1 row", "2 rows"))
    claims = pd.concat([claims, dupes], ignore_index=True)

    # CTL-05 reconciliation break: $2,500 of losses posted to IL instead of IN
    gl = gl.copy()
    il = (gl.state == "IL") & (gl.account_code == "5100")
    inn = (gl.state == "IN") & (gl.account_code == "5100")
    gl.loc[il, "amount"] += 2500
    gl.loc[inn, "amount"] -= 2500
    log.append(("CTL-05", "", "GL 5100 Losses Paid", "IN / IL", "2,500 misposted from IN to IL"))

    log = pd.DataFrame(log, columns=["rule_id", "policy_number", "field", "original_value", "planted_value"])
    return claims, gl, log


def main():
    rng = np.random.default_rng(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    claims = clean_columns(pd.read_csv(RAW))
    status = build_claim_status(claims, rng)
    gl = build_gl(claims, status)
    claims_out, gl_out, log = plant_issues(claims, status, gl, rng)

    claims_out.to_csv(OUT / "policy_claims.csv", index=False)
    status.to_csv(OUT / "claim_status.csv", index=False)
    gl_out.to_csv(OUT / "gl_trial_balance.csv", index=False)
    log.to_csv(OUT / "planted_issues_log.csv", index=False)

    print(f"policy_claims.csv      {len(claims_out):>5} rows ({len(claims)} source + duplicates)")
    print(f"claim_status.csv       {len(status):>5} rows")
    print(status["claim_status"].value_counts().to_string())
    print(f"gl_trial_balance.csv   {len(gl_out):>5} rows")
    print(f"planted_issues_log.csv {len(log):>5} planted issues")


if __name__ == "__main__":
    main()
    