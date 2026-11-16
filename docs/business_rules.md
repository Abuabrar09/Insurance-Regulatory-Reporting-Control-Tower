# Business Rules

## Reporting definitions
| Rule | Definition |
|---|---|
| BR-01 | Reporting period = calendar quarter of `incident_date` (2015Q1 = Jan 1 – Mar 31, 2015) |
| BR-02 | Reporting state = `policy_state` (state where the policy was written) |
| BR-03 | Quarterly earned premium = `policy_annual_premium` / 4 for each in-force policy (simplifying assumption) |
| BR-04 | Incurred loss = `total_claim_amount`; paid loss = `paid_amount` from claim_status |
| BR-05 | Loss ratio = incurred loss / earned premium |
| BR-06 | Closed without payment = CLOSED status with `paid_amount` = 0 |
| BR-07 | Days to close = `close_date` − `report_date` |
| BR-08 | Fraud referral = `fraud_reported` = Y |
| BR-09 | Reconciliation tolerance: absolute variance ≤ $1 **or** ≤ 0.1% of GL balance |
| BR-10 | Any blocking DQ failure or unexplained reconciliation break stops submission |

## Data quality rules
| ID | Check | Rule | Severity |
|---|---|---|---|
| DQ-01 | Completeness | policy_number not null | Blocking |
| DQ-02 | Completeness | policy_state not null | Blocking |
| DQ-03 | Completeness | policy_annual_premium not null | Blocking |
| DQ-04 | Completeness | incident_date not null | Blocking |
| DQ-05 | Completeness | total_claim_amount not null | Blocking |
| DQ-06 | Uniqueness | policy_number is unique | Blocking |
| DQ-07 | Validity | policy_state in approved state list (IL, IN, OH) | Blocking |
| DQ-08 | Validity | policy_annual_premium > 0 | Blocking |
| DQ-09 | Validity | total_claim_amount ≥ 0 | Blocking |
| DQ-10 | Consistency | total_claim_amount = injury + property + vehicle | Blocking |
| DQ-11 | Date logic | incident_date ≥ policy_bind_date | Blocking |
| DQ-12 | Date logic | incident_date within reporting period | Blocking |
| DQ-13 | Validity | fraud_reported in (Y, N) | Blocking |
| DQ-14 | Date logic | report_date ≥ incident_date | Warning |
| DQ-15 | Date logic | close_date ≥ report_date when present | Warning |
| DQ-16 | Consistency | CLOSED claims have close_date; OPEN claims do not | Warning |
| DQ-17 | Validity | paid_amount ≥ 0 and reserve_amount ≥ 0 | Warning |
| DQ-18 | Unknown values | police_report_available = `?` share < 40% | Warning |
| DQ-19 | Unknown values | property_damage = `?` share < 40% | Warning |
| DQ-20 | Unknown values | collision_type = `?` share < 25% | Warning |
| DQ-21 | Outliers | total_claim_amount ≤ $150,000 (flag for review) | Warning |
| DQ-22 | Referential | every claim_status row links to a policy_number | Blocking |
