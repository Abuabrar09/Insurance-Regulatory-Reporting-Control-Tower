-- RPT-04 Fraud Referral Summary by state (BR-08 fraud referral = fraud_reported 'Y')
SELECT
    p.policy_state                                                  AS state,
    COUNT(*)                                                        AS claims,
    SUM(p.fraud_reported = 'Y')                                     AS fraud_referrals,
    ROUND(100.0 * SUM(p.fraud_reported = 'Y') / COUNT(*), 1)        AS referral_rate_pct,
    SUM(CASE WHEN p.fraud_reported = 'Y' THEN p.total_claim_amount ELSE 0 END) AS referred_claim_amount,
    SUM(p.fraud_reported = 'Y' AND s.claim_status = 'CLOSED_WITHOUT_PAYMENT')  AS referred_closed_without_payment
FROM policy_claims_clean p
JOIN claim_status s ON s.policy_number = p.policy_number
GROUP BY p.policy_state
ORDER BY p.policy_state;
