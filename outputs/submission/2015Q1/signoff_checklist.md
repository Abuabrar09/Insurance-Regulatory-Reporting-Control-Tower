# Sign-off Checklist: 2015Q1

Package built: 2026-11-16T17:28:54
Files in package: 16 (see manifest.csv for SHA-256 checksums)

## Control results
| Control | Name | Result | Detail |
|---|---|---|---|
| CTL-01 | Source load completeness | PASS | 2011 rows loaded across 3 tables |
| CTL-02 | Blocking data quality checks | PASS | 22 of 22 rules pass on policy_claims_clean |
| CTL-03 | Warning review | PASS | 0 warning(s) open |
| CTL-04 | Report control totals | PASS | 6 reports tie to source; 1 within rounding tolerance |
| CTL-05 | GL reconciliation | PASS | 7 of 9 GL lines tie; 2 explained break(s) |
| CTL-06 | Cross-report consistency | PASS | 5 cross-report checks |
| CTL-07 | Filing timeliness | PASS | 6 of 6 reports on track as of 2015-04-06 |
| CTL-08 | File integrity | PASS | 16 files checksummed and verified |
| CTL-09 | Segregation of duties | PENDING SIGN-OFF | Preparer and reviewer sign signoff_checklist.md |
| CTL-10 | Change control | PASS | Code version f473d7c |

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
