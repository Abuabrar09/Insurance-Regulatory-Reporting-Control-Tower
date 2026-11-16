-- RPT-01 State Premium & Loss Summary (modeled on the Annual Statement state page)
-- Business rules: BR-02 reporting state, BR-03 earned premium = annual / 4, BR-04 losses
SELECT
    p.policy_state                               AS state,
    COUNT(*)                                     AS policies_with_claims,
    ROUND(SUM(p.policy_annual_premium) / 4.0, 2) AS earned_premium,
    SUM(p.total_claim_amount)                    AS incurred_losses,
    ROUND(SUM(s.paid_amount), 2)                 AS paid_losses,
    ROUND(SUM(s.reserve_amount), 2)              AS loss_reserves
FROM policy_claims_clean p
JOIN claim_status s ON s.policy_number = p.policy_number
GROUP BY p.policy_state
ORDER BY p.policy_state;
