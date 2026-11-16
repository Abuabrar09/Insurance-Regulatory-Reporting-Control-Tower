"""
run_pipeline.py - runs the full quarterly regulatory reporting cycle with one command

    python run_pipeline.py --period 2015Q1

Steps (see docs/SOP.md):
  1. load            load source extracts into SQLite              CTL-01
  2. validate raw    check the raw extract (expected to be blocked) CTL-02
  3. remediate       apply logged, approved corrections
  4. validate clean  all blocking rules must pass                   CTL-02, CTL-03
  5. produce         6 SQL reports with control totals              CTL-04
  6. reconcile       tie to GL and across reports                   CTL-05, CTL-06
  7. controls        filing calendar and control log                CTL-07, CTL-10
  8. submit          package with checksums and sign-off checklist  CTL-08
"""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
OUT = ROOT / "outputs"


def run(name, args, allow_fail=False):
    start = time.time()
    print(f"\n{'=' * 70}\n{name}\n{'=' * 70}", flush=True)
    result = subprocess.run([sys.executable, *args], cwd=ROOT)
    secs = time.time() - start
    if result.returncode != 0 and not allow_fail:
        print(f"\nPIPELINE STOPPED at '{name}'. Fix the issue above and rerun.")
        sys.exit(1)
    return result.returncode, secs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2015Q1")
    parser.add_argument("--as-of", default="2015-04-06")
    args = parser.parse_args()
    p = ["--period", args.period]

    timings = []
    t0 = time.time()

    timings.append(("1. Load", run("1. Load source data", [str(SRC / "load.py")])[1]))

    code, secs = run("2. Validate raw extract (expected: blocked)",
                     [str(SRC / "validate.py")], allow_fail=True)
    timings.append(("2. Validate raw", secs))
    # keep evidence of the blocked raw run before it is overwritten
    shutil.copy2(OUT / "dq_results.csv", OUT / "evidence" / "dq_results_raw_extract.csv")
    print("Raw-run results saved to outputs/evidence/dq_results_raw_extract.csv"
          + (" (blocked, as expected)" if code else ""))

    timings.append(("3. Remediate", run("3. Remediate", [str(SRC / "remediate.py")])[1]))
    timings.append(("4. Validate clean", run("4. Validate clean data",
                    [str(SRC / "validate.py"), "--table", "policy_claims_clean"])[1]))
    timings.append(("5. Produce reports", run("5. Produce reports", [str(SRC / "produce_reports.py"), *p])[1]))
    timings.append(("6. Reconcile", run("6. Reconcile", [str(SRC / "reconcile.py"), *p])[1]))
    timings.append(("7. Controls", run("7. Execute controls",
                    [str(SRC / "controls.py"), *p, "--as-of", args.as_of])[1]))
    timings.append(("8. Submit", run("8. Build submission package", [str(SRC / "submit.py"), *p])[1]))

    print(f"\n{'=' * 70}\nPIPELINE COMPLETE: {args.period}\n{'=' * 70}")
    for step, secs in timings:
        print(f"  {step:<20} {secs:6.1f}s")
    print(f"  {'Total':<20} {time.time() - t0:6.1f}s")
    print(f"\nPackage: outputs/submission/{args.period}/")


if __name__ == "__main__":
    main()
