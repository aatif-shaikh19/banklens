-- mart_fraud_dashboard.sql
-- Daily aggregated fraud metrics with REAL values from stg_transactions.
-- Power BI Executive Overview and Risk Intelligence pages read this table.

WITH transactions_with_risk AS (
    SELECT
        t.transaction_id,
        DATE(t.transaction_ts)          AS txn_date,
        t.product_code,
        t.card_network,
        t.card_type,
        t.transaction_amt,
        t.is_fraud,
        COALESCE(r.risk_band, 'Unknown') AS risk_band
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
    risk_band,
    COUNT(*)                                            AS total_transactions,
    SUM(is_fraud)                                       AS fraud_count,
    ROUND(SAFE_DIVIDE(SUM(is_fraud), COUNT(*)) * 100, 4) AS fraud_rate_pct,
    ROUND(SUM(transaction_amt), 2)                      AS total_volume,
    ROUND(AVG(transaction_amt), 2)                      AS avg_transaction_amt
FROM transactions_with_risk
GROUP BY 1, 2, 3, 4, 5