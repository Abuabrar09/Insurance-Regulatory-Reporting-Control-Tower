-- RPT-05 Quarterly Loss Ratio Report to Finance (BR-05 loss ratio = incurred / earned premium)
-- Note: every policy in this dataset has a claim, so loss ratios are far above real-world levels.
SELECT
    policy_state                                                   AS state,
    ROUND(SUM(policy_annual_premium) / 4.0, 2)                     AS earned_premium,
    SUM(total_claim_amount)                                        AS incurred_losses,
    ROUND(SUM(total_claim_amount) / (SUM(policy_annual_premium) / 4.0), 2) AS loss_ratio
FROM policy_claims_clean
GROUP BY policy_state
ORDER BY policy_state;
