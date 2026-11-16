"""
load.py - Step 2 of the reporting cycle (control CTL-01)

Loads the source extracts into a SQLite database and proves that
every row in each file made it into the database.
"""
import hashlib
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "data" / "generated"
DB = ROOT / "data" / "reg_reporting.db"
EVIDENCE = ROOT / "outputs" / "evidence"

SOURCES = {
    "policy_claims": GEN / "policy_claims.csv",
    "claim_status": GEN / "claim_status.csv",
    "gl_trial_balance": GEN / "gl_trial_balance.csv",
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    run_ts = datetime.now().isoformat(timespec="seconds")
    log = []

    with sqlite3.connect(DB) as con:
        for table, path in SOURCES.items():
            df = pd.read_csv(path, dtype={"account_code": str})
            df.to_sql(table, con, if_exists="replace", index=False)
            loaded = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            log.append({
                "run_timestamp": run_ts,
                "table": table,
                "source_file": path.relative_to(ROOT).as_posix(),
                "source_sha256": sha256(path),
                "source_rows": len(df),
                "loaded_rows": loaded,
                "ctl01_result": "PASS" if loaded == len(df) else "FAIL",
            })

    log = pd.DataFrame(log)
    log.to_csv(EVIDENCE / "load_log.csv", index=False)
    print(log[["table", "source_rows", "loaded_rows", "ctl01_result"]].to_string(index=False))

    if (log["ctl01_result"] == "FAIL").any():
        raise SystemExit("CTL-01 FAILED: row counts do not match. Stop and investigate.")
    print(f"\nCTL-01 PASS. Database: {DB.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
    