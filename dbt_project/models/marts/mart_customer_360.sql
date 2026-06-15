-- The central insight of BankLens 2.0:
-- Which customers are high fraud risk but would still receive campaign offers?
-- campaign_eligibility = 'Suppress — High Risk' answers this question.

WITH risk AS (
    SELECT
        billing_zip,
        card_network,
        ROUND(AVG(risk_z_score), 4)     AS avg_risk_z_score,
        SUM(fraud_count)                 AS total_fraud_events,
        SUM(total_transactions)          AS total_transactions,
        ROUND(SUM(total_amt), 2)         AS total_transaction_value,
        MAX(CASE risk_band
                WHEN 'Critical' THEN 4
                WHEN 'High'     THEN 3
                WHEN 'Medium'   THEN 2
                ELSE 1
            END)                         AS worst_risk_score
    FROM {{ ref('int_customer_risk_profile') }}
    GROUP BY 1, 2
)
SELECT
    billing_zip,
    card_network,
    avg_risk_z_score,
    total_fraud_events,
    total_transactions,
    total_transaction_value,
    CASE worst_risk_score
        WHEN 4 THEN 'Critical'
        WHEN 3 THEN 'High'
        WHEN 2 THEN 'Medium'
        ELSE 'Low'
    END                                  AS risk_band,
    CASE
        WHEN worst_risk_score >= 3 THEN 'Suppress — High Risk'
        WHEN worst_risk_score = 2  THEN 'Review Before Contact'
        ELSE 'Campaign Eligible'
    END                                  AS campaign_eligibility
FROM risk
