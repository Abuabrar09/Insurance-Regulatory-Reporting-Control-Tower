-- RPT-02 Claims Statistical Report by state, incident type and severity
SELECT
    policy_state                 AS state,
    incident_type,
    incident_severity,
    COUNT(*)                     AS claim_count,
    SUM(injury_claim)            AS injury_amount,
    SUM(property_claim)          AS property_amount,
    SUM(vehicle_claim)           AS vehicle_amount,
    SUM(total_claim_amount)      AS total_amount
FROM policy_claims_clean
GROUP BY policy_state, incident_type, incident_severity
ORDER BY policy_state, incident_type, incident_severity;
