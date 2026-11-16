-- RPT-06 Regulator Data Call (example request)
-- "List every Ohio-written auto claim over $50,000 with a loss date in 2015Q1."
SELECT
    p.policy_number,
    p.policy_state                AS state,
    p.incident_date,
    p.incident_type,
    p.incident_severity,
    p.total_claim_amount,
    s.claim_status,
    s.paid_amount,
    s.reserve_amount
FROM policy_claims_clean p
JOIN claim_status s ON s.policy_number = p.policy_number
WHERE p.policy_state = 'OH'
  AND p.total_claim_amount > 50000
  AND p.incident_date BETWEEN '2015-01-01' AND '2015-03-31'
ORDER BY p.total_claim_amount DESC;
