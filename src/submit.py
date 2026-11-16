"""
submit.py - Step 8 of the reporting cycle (control CTL-08)

Builds outputs/submission/<period>/ containing the reports and all evidence,
a manifest with SHA-256 checksums, and a sign-off checklist.
CTL-08: every file in the package is re-hashed and must match its manifest entry.
Refuses to build if any control in outputs/control_log.csv has FAILED.
"""
import argparse
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
CONFIG = ROOT / "config"


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def rows(path):
    try:
        return len(pd.read_csv(path))
    except Exception:
        return ""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2015Q1")
    args = parser.parse_args()

    log = pd.read_csv(OUT / "control_log.csv")
    if (log["result"] == "FAIL").any():
        raise SystemExit("Submission blocked: a control has FAILED. See outputs/control_log.csv.")

    pkg = OUT / "submission" / args.period
    if pkg.exists():
        shutil.rmtree(pkg)
    (pkg / "reports").mkdir(parents=True)
    (pkg / "evidence").mkdir()

    reports = sorted((OUT / "reports").glob("RPT-*.csv"))
    evidence = [
        OUT / "filing_calendar.csv", OUT / "dq_results.csv", OUT / "recon_results.csv",
        OUT / "cross_report_check.csv", OUT / "reports" / "report_control_totals.csv",
        OUT / "evidence" / "load_log.csv", OUT / "evidence" / "remediation_log.csv",
        CONFIG / "approved_exceptions.csv", CONFIG / "recon_explanations.csv",
    ]
    evidence += sorted((OUT / "evidence").glob("dq_results_raw_extract.csv"))

    manifest = []
    for src, folder in [(p, "reports") for p in reports] + [(p, "evidence") for p in evidence]:
        dest = pkg / folder / src.name
        shutil.copy2(src, dest)
        manifest.append({"file": f"{folder}/{src.name}", "rows": rows(src), "sha256": sha256(src)})

    # CTL-08: re-hash every packaged file and compare to the manifest
    manifest = pd.DataFrame(manifest)
    manifest["verified_sha256"] = manifest["file"].map(lambda f: sha256(pkg / f))
    manifest["ctl08_result"] = (manifest["sha256"] == manifest["verified_sha256"]).map(
        {True: "PASS", False: "FAIL"})
    manifest.drop(columns="verified_sha256").to_csv(pkg / "manifest.csv", index=False)

    ctl08 = "PASS" if (manifest["ctl08_result"] == "PASS").all() else "FAIL"
    log.loc[log["control_id"] == "CTL-08", ["result", "detail"]] = [
        ctl08, f"{len(manifest)} files checksummed and verified"]
    log.to_csv(OUT / "control_log.csv", index=False)
    log.to_csv(pkg / "control_log.csv", index=False)

    built = datetime.now().isoformat(timespec="seconds")
    checklist = f"""# Sign-off Checklist: {args.period}

Package built: {built}
Files in package: {len(manifest)} (see manifest.csv for SHA-256 checksums)

## Control results
| Control | Name | Result | Detail |
|---|---|---|---|
""" + "\n".join(f"| {r.control_id} | {r.control_name} | {r.result} | {r.detail} |" for r in log.itertuples()) + """

## Reviewer checklist
- [ ] All blocking data quality rules pass (CTL-02)
- [ ] Every DQ remediation in evidence/remediation_log.csv is supported
- [ ] Approved exceptions are current and within their review date
- [ ] Every GL reconciliation break is explained with an owner (CTL-05)
- [ ] Report totals tie to source (CTL-04) and to each other (CTL-06)
- [ ] Checksums in manifest.csv verified (CTL-08)

## Sign-off (CTL-09: preparer and reviewer must be different people)
| Role | Name | Date | Signature |
|---|---|---|---|
| Preparer (Regulatory Reporting) | | | |
| Reviewer (Accounting) | | | |
| Approver (Compliance) | | | |
"""
    (pkg / "signoff_checklist.md").write_text(checklist)

    print(manifest[["file", "rows", "ctl08_result"]].to_string(index=False))
    if ctl08 == "FAIL":
        raise SystemExit("\nCTL-08 FAIL: a packaged file does not match its checksum.")
    print(f"\nCTL-08 PASS. Submission package ready: outputs/submission/{args.period}/")
    print("Next: preparer and reviewer complete signoff_checklist.md (CTL-09).")


if __name__ == "__main__":
    main()
