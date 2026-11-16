# Data Dictionary

## Source: `insurance_claims.csv` (Kaggle, 1,000 rows, 1 row = 1 policy with 1 claim)

### Fields used in regulatory reports
| Column | Type | Description | Used in |
|---|---|---|---|
| policy_number | integer | Unique policy ID (primary key) | All |
| policy_bind_date | date | Date policy was issued | DQ date logic |
| policy_state | text (2) | State where policy was written: **reporting state** | RPT-01, 02, 03, 04, 05, 06 |
| policy_csl | text | Combined single limit, e.g. 250/500 (thousands) | RPT-02 |
| policy_deductable | integer | Deductible in USD (source spelling kept) | RPT-02 |
| policy_annual_premium | decimal | Annualized premium in USD | RPT-01, 05 |
| incident_date | date | Date of loss | RPT-02, 03, 06 |
| incident_state | text (2) | State where the accident happened | RPT-06 |
| incident_type | text | Collision, theft, parked car, etc. | RPT-02 |
| incident_severity | text | Minor / Major / Total Loss / Trivial | RPT-02 |
| total_claim_amount | integer | Total claim in USD = injury + property + vehicle | RPT-01, 02, 05, 06 |
| injury_claim | integer | Bodily injury portion (USD) | RPT-02 |
| property_claim | integer | Property damage portion (USD) | RPT-02 |
| vehicle_claim | integer | Vehicle damage portion (USD) | RPT-02 |
| fraud_reported | Y/N | Claim referred as suspected fraud | RPT-04 |
| authorities_contacted | text | Police, Fire, Ambulance, Other, None | DQ only |
| police_report_available | YES/NO/? | `?` = unknown | DQ only |
| property_damage | YES/NO/? | `?` = unknown | DQ only |
| collision_type | text/? | `?` = unknown | DQ only |

### Fields not used in reporting
months_as_customer, age, umbrella_limit, insured_zip, insured_sex, insured_education_level, insured_occupation, insured_hobbies, insured_relationship, capital-gains, capital-loss, incident_city, incident_location, incident_hour_of_the_day, number_of_vehicles_involved, bodily_injuries, witnesses, auto_make, auto_model, auto_year. The 40th column `_c39` is empty and is dropped at load.

## Generated: `claim_status` (simulated, fixed seed)
| Column | Type | Description |
|---|---|---|
| claim_id | text | `CLM-` + policy_number |
| policy_number | integer | Link to source |
| report_date | date | Date claim was reported (on/after incident_date) |
| close_date | date | Date closed; blank if still open |
| claim_status | text | OPEN / CLOSED_WITH_PAYMENT / CLOSED_WITHOUT_PAYMENT |
| paid_amount | decimal | USD paid to date |
| reserve_amount | decimal | USD still reserved (open claims) |

## Generated: `gl_trial_balance` (simulated)
| Column | Type | Description |
|---|---|---|
| period | text | e.g. 2015Q1 |
| state | text (2) | Reporting state |
| account_code | text | 4100 Premium Earned · 5100 Losses Paid · 2100 Loss Reserves |
| account_name | text | Account description |
| amount | decimal | USD balance for the period |
