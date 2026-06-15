WITH daily AS (
    SELECT
        DATE(t.transaction_ts) AS txn_date,
        t.product_code,
        t.card_network,
        t.card_type,
        r.risk_band
    FROM {{ ref('stg_transactions') }} t
    LEFT JOIN {{ ref('int_customer_risk_profile') }} r
        ON  t.billing_zip   = r.billing_zip
        AND t.card_network  = r.card_network
)
SELECT
    txn_date,
    product_code,
    card_network,
    card_type,
    COALESCE(risk_band, 'Unknown')              AS risk_band,
    COUNT(*)                                     AS total_transactions,
    COUNT(*)                                     AS fraud_count,
    0.035                                        AS fraud_rate_pct,
    COUNT(*) * 250.0                             AS total_volume,
    250.0                                        AS avg_transaction_amt
FROM daily
GROUP BY 1, 2, 3, 4, 5

-- NOTE: The above is a simplified aggregation. In Phase 4 the ML model
-- will write fraud_probability back to BigQuery and this model will read it.
-- For now the placeholder values let Power BI connect and we build the
-- full version after the ML model is trained on Colab.
