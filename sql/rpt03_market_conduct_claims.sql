-- RPT-03 Market Conduct-style Claims Report
-- BR-06 closed without payment, BR-07 days to close = close_date - report_date
SELECT
    p.policy_state                                                         AS state,
    COUNT(*)                                                               AS claims_reported,
    SUM(s.claim_status = 'CLOSED_WITH_PAYMENT')                            AS closed_with_payment,
    SUM(s.claim_status = 'CLOSED_WITHOUT_PAYMENT')                         AS closed_without_payment,
    SUM(s.claim_status = 'OPEN')                                           AS open_at_period_end,
    ROUND(AVG(CASE WHEN s.close_date <> ''
              THEN julianday(s.close_date) - julianday(s.report_date) END), 1) AS avg_days_to_close,
    ROUND(100.0 * SUM(s.close_date <> ''
              AND julianday(s.close_date) - julianday(s.report_date) <= 30)
          / SUM(s.close_date <> ''), 1)                                    AS pct_closed_within_30_days
FROM policy_claims_clean p
JOIN claim_status s ON s.policy_number = p.policy_number
GROUP BY p.policy_state
ORDER BY p.policy_state;
