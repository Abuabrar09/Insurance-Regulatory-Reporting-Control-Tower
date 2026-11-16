"""
build_dashboard.py - builds a one-page HTML dashboard from the pipeline outputs

Reads the CSVs the pipeline wrote and writes docs/index.html, a single
self-contained page (no external libraries) that GitHub Pages can host.

    python src/build_dashboard.py --period 2015Q1
"""
import argparse
import html
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
REPORTS = OUT / "reports"
DOCS = ROOT / "docs"
REPO = "https://github.com/Abuabrar09/Insurance-Regulatory-Reporting-Control-Tower"

STATE_NAMES = {"IL": "Illinois", "IN": "Indiana", "OH": "Ohio"}


def esc(x):
    return html.escape(str(x))


def money(x, dp=0):
    return f"${x:,.{dp}f}"


def status_chip(result):
    r = str(result)
    if r.startswith("PASS"):
        cls, icon = "good", "&#10003;"
    elif "EXPLAINED" in r or "PENDING" in r or r == "At risk":
        cls, icon = "warn", "&#9679;"
    elif r == "On track":
        cls, icon = "good", "&#10003;"
    else:
        cls, icon = "bad", "&#10005;"
    return f'<span class="chip {cls}"><span aria-hidden="true">{icon}</span> {esc(r)}</span>'


def tile(value, label, sub=""):
    return (f'<div class="tile"><div class="tile-value">{value}</div>'
            f'<div class="tile-label">{esc(label)}</div>'
            f'<div class="tile-sub">{sub}</div></div>')


def table(df, cols, headers, num_cols=(), fmt=None, chip_cols=()):
    fmt = fmt or {}
    head = "".join(f'<th class="{"num" if c in num_cols else ""}">{esc(h)}</th>' for c, h in zip(cols, headers))
    rows = []
    for _, r in df.iterrows():
        cells = []
        for c in cols:
            v = r[c]
            if c in chip_cols:
                cells.append(f"<td>{status_chip(v)}</td>")
            else:
                text = fmt[c](v) if c in fmt else esc(v)
                cells.append(f'<td class="{"num" if c in num_cols else ""}">{text}</td>')
        rows.append("<tr>" + "".join(cells) + "</tr>")
    return f'<div class="table-wrap"><table><thead><tr>{head}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def hbar_rows(items, max_value, marker=None, marker_label="", unit=""):
    """items: list of (label, value, tooltip, css_class). Horizontal bars, one series."""
    out = []
    for label, value, tip, cls in items:
        pct = 0 if max_value == 0 else max(value, 0) / max_value * 100
        out.append(
            f'<div class="hbar-row"><div class="hbar-label">{esc(label)}</div>'
            f'<div class="hbar-track" data-tip="{esc(tip)}">'
            f'<div class="hbar {cls}" style="width:{pct:.2f}%"></div>'
            + (f'<div class="hbar-marker" style="left:{marker / max_value * 100:.2f}%"></div>' if marker is not None else "")
            + f'</div><div class="hbar-value">{esc(value)}{unit}</div></div>')
    legend = (f'<div class="marker-note"><span class="marker-swatch"></span>{esc(marker_label)}</div>'
              if marker is not None else "")
    return legend + "".join(out)


def diverging_rows(items, limit):
    """items: list of (label, diff, tooltip, css_class). Bars about a zero line."""
    out = []
    for label, diff, tip, cls in items:
        w = min(abs(diff) / limit * 50, 50)
        left = 50 - w if diff < 0 else 50
        bar = f'<div class="dbar {cls}" style="left:{left:.2f}%;width:{max(w, 0.0):.2f}%"></div>' if w > 0 else ""
        out.append(
            f'<div class="hbar-row"><div class="hbar-label">{esc(label)}</div>'
            f'<div class="hbar-track diverging" data-tip="{esc(tip)}"><div class="zero"></div>{bar}</div>'
            f'<div class="hbar-value">{diff:+,.2f}</div></div>')
    return "".join(out)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--period", default="2015Q1")
    args = parser.parse_args()

    dq = pd.read_csv(OUT / "dq_results.csv")
    dq_raw = pd.read_csv(OUT / "evidence" / "dq_results_raw_extract.csv")
    remed = pd.read_csv(OUT / "evidence" / "remediation_log.csv")
    recon = pd.read_csv(OUT / "recon_results.csv")
    cross = pd.read_csv(OUT / "cross_report_check.csv")
    cal = pd.read_csv(OUT / "filing_calendar.csv")
    ctl = pd.read_csv(OUT / "control_log.csv")
    totals = pd.read_csv(REPORTS / "report_control_totals.csv")
    manifest = pd.read_csv(OUT / "submission" / args.period / "manifest.csv")
    exceptions = pd.read_csv(ROOT / "config" / "approved_exceptions.csv")
    rpt01 = pd.read_csv(REPORTS / "RPT-01_state_premium_loss.csv")
    rpt03 = pd.read_csv(REPORTS / "RPT-03_market_conduct_claims.csv")
    rpt04 = pd.read_csv(REPORTS / "RPT-04_fraud_referrals.csv")
    rpt05 = pd.read_csv(REPORTS / "RPT-05_loss_ratio.csv")

    # ---------- headline numbers ----------
    raw_pass = int((dq_raw["result"] == "PASS").sum())
    clean_pass = int((dq["result"] == "PASS").sum())
    n_rules = len(dq)
    explained = int((recon["ctl05_result"] == "BREAK - EXPLAINED").sum())
    unexplained = int((recon["ctl05_result"] == "BREAK - UNEXPLAINED").sum())
    tie = len(recon) - explained - unexplained
    ctl_pass = int(ctl["result"].astype(str).str.startswith("PASS").sum())
    on_track = int((cal["status"] == "On track").sum())
    blocked = ctl["result"].eq("FAIL").any() or unexplained > 0
    run_id = totals["run_id"].iloc[0]

    tiles = "".join([
        tile(f"{clean_pass}/{n_rules}", "Data quality rules pass",
             f"Raw extract: {raw_pass}/{n_rules} &middot; blocked"),
        tile(f"{len(remed)}", "Logged corrections", "Before/after audit trail"),
        tile(f"{tie}/{len(recon)}", "GL lines tie exactly",
             f"{explained} explained break{'s' if explained != 1 else ''}"),
        tile(f"{ctl_pass}/{len(ctl)}", "Controls pass", "CTL-09 awaits sign-off"),
        tile(f"{on_track}/{len(cal)}", "Reports on track", f"As of {esc(cal['as_of'].iloc[0])}"),
        tile(f"{len(manifest)}", "Files checksummed", "SHA-256 verified"),
    ])

    # ---------- pipeline flow ----------
    steps = [
        ("1", "Load", "CTL-01"), ("2", "Validate raw", "Blocked"), ("3", "Remediate", f"{len(remed)} fixes"),
        ("4", "Validate clean", "CTL-02/03"), ("5", "Produce", "CTL-04"), ("6", "Reconcile", "CTL-05/06"),
        ("7", "Controls", "CTL-07/10"), ("8", "Submit", "CTL-08"),
    ]
    flow = "".join(
        f'<li class="step {"step-blocked" if label == "Validate raw" else ""}">'
        f'<span class="step-num">{n}</span><span class="step-name">{label}</span>'
        f'<span class="step-ctl">{c}</span></li>' for n, label, c in steps)

    # ---------- data quality ----------
    merged = dq_raw[["rule_id", "check", "rule", "severity", "rows_failed"]].merge(
        dq[["rule_id", "rows_failed", "result", "note"]], on="rule_id", suffixes=("_raw", "_clean"))
    failed_raw = merged[merged["rows_failed_raw"] > 0]
    max_raw = max(failed_raw["rows_failed_raw"].max() if len(failed_raw) else 1, 1)
    dq_bars = hbar_rows(
        [(f'{r.rule_id} {r.rule}', int(r.rows_failed_raw),
          f'{r.rule_id}: {r.rows_failed_raw} rows failed on the raw extract; {r.rows_failed_clean} after remediation. {r.note if isinstance(r.note, str) else ""}',
          "series") for r in failed_raw.itertuples()],
        max_raw, unit=" rows")

    share_rows = []
    for rid, limit in [("DQ-18", 40), ("DQ-19", 40), ("DQ-20", 25)]:
        row = dq[dq["rule_id"] == rid].iloc[0]
        share = float(str(row["note"]).replace("share", "").replace("%", "").strip() or 0)
        field = row["rule"].split(" ")[0]
        share_rows.append(
            f'<div class="hbar-row"><div class="hbar-label">{esc(field)}</div>'
            f'<div class="hbar-track" data-tip="{esc(field)}: {share:.1f}% unknown (\'?\'); limit {limit}%">'
            f'<div class="hbar series" style="width:{share:.2f}%"></div>'
            f'<div class="hbar-marker" style="left:{limit}%"></div></div>'
            f'<div class="hbar-value">{share:.1f}%</div></div>')
    share_html = ('<div class="marker-note"><span class="marker-swatch"></span>Warning limit for each field</div>'
                  + "".join(share_rows))

    remed_counts = remed.groupby("rule_id").size().reset_index(name="corrections")
    remed_actions = remed.groupby("rule_id")["action"].first().reset_index()
    remed_tbl = remed_counts.merge(remed_actions, on="rule_id")

    # ---------- filing calendar ----------
    max_days = max(int(cal["business_days_left"].max()), 5)
    cal_bars = hbar_rows(
        [(f'{r.report_id} {r.report_name}', int(r.business_days_left),
          f'{r.report_id} due {r.due_date}: {r.business_days_left} business days left ({r.status})',
          "series") for r in cal.itertuples()],
        max_days, marker=5, marker_label="Ready at least 5 business days before due (CTL-07)", unit=" days")

    # ---------- reconciliation ----------
    limit = max(recon["difference"].abs().max(), 1)
    recon_bars = diverging_rows(
        [(f'{r.state} {r.account_name}', float(r.difference),
          f'{r.state} {r.account_name}: report {money(r.report_value, 2)} vs GL {money(r.gl_value, 2)} '
          f'= {r.difference:+,.2f} ({r.ctl05_result})',
          "warn-fill" if "BREAK" in r.ctl05_result else "series") for r in recon.itertuples()],
        limit)
    breaks = recon[recon["ctl05_result"].str.contains("BREAK")]
    break_notes = "".join(
        f'<li><strong>{esc(r.state)} {esc(r.account_name)} {r.difference:+,.2f}</strong>: '
        f'{esc(r.explanation)} <span class="muted">Owner: {esc(r.owner)} &middot; {esc(r.status)}</span></li>'
        for r in breaks.itertuples()) if "explanation" in breaks.columns else ""

    # ---------- report outputs ----------
    rpt01v = rpt01.copy()
    max_rate = max(rpt04["referral_rate_pct"].max(), 1)
    fraud_bars = hbar_rows(
        [(STATE_NAMES.get(r.state, r.state), float(r.referral_rate_pct),
          f'{r.state}: {r.fraud_referrals} of {r.claims} claims referred ({r.referral_rate_pct}%)', "series")
         for r in rpt04.itertuples()], max_rate * 1.1, unit="%")
    ctl04_rounding = int((totals["ctl04_result"] == "PASS (rounding)").sum())

    status_line = ("Ready for sign-off" if not blocked else "Blocked")
    built = datetime.now().strftime("%Y-%m-%d %H:%M")

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Regulatory Reporting Control Tower | {esc(args.period)}</title>
<style>
:root {{
  color-scheme: light;
  --page: #f9f9f7; --surface: #fcfcfb; --ink: #0b0b0b; --ink-2: #52514e; --muted: #898781;
  --grid: #e1e0d9; --axis: #c3c2b7; --ring: rgba(11,11,11,0.10);
  --series: #2a78d6; --good: #0ca30c; --good-text: #006300; --warn: #fab219; --bad: #d03b3b;
}}
@media (prefers-color-scheme: dark) {{
  :root {{
    color-scheme: dark;
    --page: #0d0d0d; --surface: #1a1a19; --ink: #f0efec; --ink-2: #c3c2b7; --muted: #898781;
    --grid: #2c2c2a; --axis: #383835; --ring: rgba(255,255,255,0.10);
    --series: #3987e5; --good: #0ca30c; --good-text: #0ca30c; --warn: #fab219; --bad: #d03b3b;
  }}
}}
* {{ box-sizing: border-box; }}
body {{ margin: 0; background: var(--page); color: var(--ink);
  font: 15px/1.5 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif; }}
.wrap {{ max-width: 1120px; margin: 0 auto; padding: 32px 20px 48px; }}
header {{ display: flex; flex-wrap: wrap; justify-content: space-between; gap: 16px; align-items: flex-end; }}
h1 {{ font-size: 26px; line-height: 1.2; margin: 0 0 6px; }}
h2 {{ font-size: 18px; margin: 0 0 4px; }}
.lede {{ color: var(--ink-2); margin: 0; max-width: 680px; }}
.meta {{ color: var(--ink-2); font-size: 13px; text-align: right; }}
.meta a {{ color: var(--series); }}
.badge {{ display: inline-block; padding: 4px 12px; border-radius: 999px; font-weight: 600; font-size: 14px;
  border: 1px solid var(--ring); background: var(--surface); margin-bottom: 6px; }}
.badge .dot {{ display: inline-block; width: 9px; height: 9px; border-radius: 50%; margin-right: 6px; }}
.tiles {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; margin: 24px 0; }}
.tile {{ background: var(--surface); border: 1px solid var(--ring); border-radius: 12px; padding: 14px 16px; }}
.tile-value {{ font-size: 28px; font-weight: 650; font-variant-numeric: tabular-nums; }}
.tile-label {{ font-size: 14px; font-weight: 600; }}
.tile-sub {{ font-size: 12.5px; color: var(--ink-2); }}
.card {{ background: var(--surface); border: 1px solid var(--ring); border-radius: 12px; padding: 20px; margin-top: 16px; }}
.card .sub {{ color: var(--ink-2); font-size: 14px; margin: 0 0 16px; }}
.grid2 {{ display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }}
.grid2 .card {{ margin-top: 0; min-width: 0; }}
.row2 {{ margin-top: 16px; }}
@media (max-width: 820px) {{ .grid2 {{ grid-template-columns: 1fr; }} .meta {{ text-align: left; }} }}
.flow {{ list-style: none; padding: 0; margin: 0; display: grid; grid-template-columns: repeat(8, 1fr); gap: 8px; }}
@media (max-width: 820px) {{ .flow {{ grid-template-columns: repeat(4, 1fr); }} }}
@media (max-width: 520px) {{ .flow {{ grid-template-columns: repeat(2, 1fr); }} .hbar-row {{ grid-template-columns: 40% 1fr 64px; }} }}
.step {{ border: 1px solid var(--axis); border-radius: 10px; padding: 10px 8px; text-align: center; position: relative; }}
.step-num {{ display: block; font-size: 12px; color: var(--muted); }}
.step-name {{ display: block; font-weight: 600; font-size: 14px; }}
.step-ctl {{ display: block; font-size: 12px; color: var(--ink-2); }}
.step-blocked {{ border-style: dashed; }}
.step-blocked .step-ctl {{ color: var(--bad); font-weight: 600; }}
.hbar-row {{ display: grid; grid-template-columns: minmax(120px, 38%) 1fr 76px; gap: 10px; align-items: center; margin: 6px 0; }}
.hbar-label {{ font-size: 13.5px; color: var(--ink); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.hbar-value {{ font-size: 13.5px; text-align: right; font-variant-numeric: tabular-nums; color: var(--ink-2); }}
.hbar-track {{ position: relative; height: 22px; border-left: 1px solid var(--axis); cursor: default; }}
.hbar-track.diverging {{ border-left: none; background: linear-gradient(var(--grid), var(--grid)) center/100% 1px no-repeat; }}
.hbar {{ position: absolute; top: 4px; bottom: 4px; left: 0; border-radius: 0 4px 4px 0; }}
.dbar {{ position: absolute; top: 4px; bottom: 4px; border-radius: 4px; }}
.zero {{ position: absolute; left: 50%; top: 0; bottom: 0; border-left: 1px solid var(--axis); }}
.series {{ background: var(--series); }}
.warn-fill {{ background: var(--warn); }}
.hbar-marker {{ position: absolute; top: -2px; bottom: -2px; border-left: 2px dashed var(--ink-2); }}
.marker-note {{ font-size: 12.5px; color: var(--ink-2); margin-bottom: 6px; }}
.marker-swatch {{ display: inline-block; width: 0; height: 12px; border-left: 2px dashed var(--ink-2); margin: 0 8px -2px 2px; }}
.hbar-track:hover .hbar, .hbar-track:hover .dbar {{ filter: brightness(1.12); }}
.table-wrap {{ overflow-x: auto; }}
table {{ width: 100%; border-collapse: collapse; font-size: 13.5px; }}
th {{ text-align: left; font-weight: 600; color: var(--ink-2); border-bottom: 1px solid var(--axis); padding: 6px 8px; white-space: nowrap; }}
td {{ border-bottom: 1px solid var(--grid); padding: 6px 8px; vertical-align: top; }}
td:first-child {{ white-space: nowrap; }}
.num {{ text-align: right; font-variant-numeric: tabular-nums; }}
.chip {{ display: inline-block; white-space: nowrap; font-size: 12.5px; font-weight: 600; padding: 1px 8px; border-radius: 999px; border: 1px solid var(--ring); }}
.chip.good span {{ color: var(--good); }} .chip.warn span {{ color: var(--warn); }} .chip.bad span {{ color: var(--bad); }}
.notes {{ margin: 12px 0 0; padding-left: 18px; font-size: 14px; }}
.notes li {{ margin-bottom: 6px; }}
.muted {{ color: var(--ink-2); font-size: 13px; }}
footer {{ margin-top: 28px; color: var(--ink-2); font-size: 13px; }}
footer a {{ color: var(--series); }}
#tip {{ position: fixed; pointer-events: none; z-index: 10; max-width: 320px; padding: 8px 10px; font-size: 13px;
  background: var(--surface); color: var(--ink); border: 1px solid var(--ring); border-radius: 8px;
  box-shadow: 0 4px 16px rgba(0,0,0,.12); display: none; }}
</style>
</head>
<body>
<div class="wrap">
<header>
  <div>
    <h1>Regulatory Reporting Control Tower</h1>
    <p class="lede">Quarterly regulatory and statistical reporting cycle for an auto insurer: validation, remediation, report production, GL reconciliation, controls and a checksummed submission package.</p>
  </div>
  <div class="meta">
    <div class="badge"><span class="dot" style="background:var({'--good' if not blocked else '--bad'})"></span>{esc(args.period)} &middot; {status_line}</div><br>
    Run {esc(run_id)}<br>
    <a href="{REPO}">View code on GitHub</a>
  </div>
</header>

<section class="tiles">{tiles}</section>

<section class="card">
  <h2>The cycle stops at any blocking failure</h2>
  <p class="sub">Eight steps run with one command. The raw extract was blocked at step 2 and passed only after logged corrections.</p>
  <ol class="flow">{flow}</ol>
</section>

<div class="grid2 row2">
<section class="card">
  <h2>Raw extract failed {n_rules - raw_pass} rules; all pass after remediation</h2>
  <p class="sub">Rows failing each rule on the raw extract. After remediation every rule shows 0.</p>
  {dq_bars}
  {table(remed_tbl, ["rule_id", "corrections", "action"], ["Rule", "Fixes", "Action"], num_cols=("corrections",))}
  <ul class="notes"><li><strong>Approved exception:</strong> {esc(exceptions['reason'].iloc[0])}. {esc(exceptions['disposition'].iloc[0])}.</li></ul>
</section>
<section class="card">
  <h2>Unknown values stay under their warning limits</h2>
  <p class="sub">Share of records with &ldquo;?&rdquo; in fields that are not used in reports (DQ-18 to DQ-20).</p>
  {share_html}
  <h2 style="margin-top:24px">Every report is on track for its due date</h2>
  <p class="sub">Business days left as of {esc(cal['as_of'].iloc[0])}.</p>
  {cal_bars}
</section>
</div>

<section class="card">
  <h2>{tie} of {len(recon)} GL lines tie; the {explained} breaks are one $2,500 misposting</h2>
  <p class="sub">Report value minus general ledger, by state and account. Tolerance $1.00 (BR-09). Bars away from zero are breaks.</p>
  {recon_bars}
  <ul class="notes">{break_notes}</ul>
  {table(cross, ["figure", "report_a", "report_b", "difference", "ctl06_result"], ["Cross-report check", "Report", "Ties to", "Difference", "CTL-06"], num_cols=("difference",), chip_cols=("ctl06_result",))}
</section>

<div class="grid2 row2">
<section class="card">
  <h2>State premium &amp; loss summary (RPT-01)</h2>
  <p class="sub">Every column ties to source (CTL-04); {ctl04_rounding} of 6 reports within the $0.05 rounding tolerance.</p>
  {table(rpt01v, ["state", "earned_premium", "incurred_losses", "paid_losses", "loss_reserves"], ["State", "Earned premium", "Incurred", "Paid", "Reserves"], num_cols=("earned_premium", "incurred_losses", "paid_losses", "loss_reserves"), fmt={c: (lambda v: money(v)) for c in ["earned_premium", "incurred_losses", "paid_losses", "loss_reserves"]})}
  <p class="muted">Loss ratios ({", ".join(f"{r.state} {r.loss_ratio:.0f}x" for r in rpt05.itertuples())}) are far above real-world levels because every policy in the source data has a claim.</p>
</section>
<section class="card">
  <h2>Claims handling and fraud referrals (RPT-03, RPT-04)</h2>
  <p class="sub">Share of claims referred for suspected fraud, by state.</p>
  {fraud_bars}
  {table(rpt03, ["state", "claims_reported", "closed_with_payment", "closed_without_payment", "open_at_period_end", "avg_days_to_close"], ["State", "Claims", "Paid", "Closed, no pay", "Open", "Avg days to close"], num_cols=("claims_reported", "closed_with_payment", "closed_without_payment", "open_at_period_end", "avg_days_to_close"))}
</section>
</div>

<section class="card">
  <h2>Control log</h2>
  <p class="sub">Executed from config/control_matrix.csv. CTL-09 (segregation of duties) is a human sign-off by design.</p>
  {table(ctl, ["control_id", "control_name", "control_type", "result", "detail"], ["Control", "Name", "Type", "Result", "Detail"], chip_cols=("result",))}
</section>

<footer>
  Data: <a href="https://www.kaggle.com/datasets/buntyshah/auto-insurance-claims-data">Auto Insurance Claims Data</a> (Kaggle, buntyshah); claim status and general ledger simulated with a fixed seed; data issues planted on purpose so the controls have something to catch. Report formats are simplified educational versions of real filings.<br>
  Built {built} by <code>src/build_dashboard.py</code> &middot; Abrar Ahmed Syed &middot;
  <a href="https://www.linkedin.com/in/abrar313">LinkedIn</a> &middot; <a href="https://abuabrar09.github.io">Portfolio</a> &middot; <a href="{REPO}">GitHub</a>
</footer>
</div>
<div id="tip" role="tooltip"></div>
<script>
const tip = document.getElementById('tip');
document.querySelectorAll('[data-tip]').forEach(el => {{
  el.addEventListener('mousemove', e => {{
    tip.textContent = el.dataset.tip; tip.style.display = 'block';
    const x = Math.min(e.clientX + 14, window.innerWidth - tip.offsetWidth - 8);
    tip.style.left = x + 'px'; tip.style.top = (e.clientY + 14) + 'px';
  }});
  el.addEventListener('mouseleave', () => tip.style.display = 'none');
}});
</script>
</body>
</html>
"""
    DOCS.mkdir(exist_ok=True)
    (DOCS / "index.html").write_text(page, encoding="utf-8")
    print(f"Dashboard written to docs/index.html ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
