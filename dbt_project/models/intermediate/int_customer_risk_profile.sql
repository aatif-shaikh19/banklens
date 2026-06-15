WITH base AS (
    SELECT
        billing_zip,
        card_network,
        COUNT(*)                                AS total_transactions,
        SUM(is_fraud)                           AS fraud_count,
        SAFE_DIVIDE(SUM(is_fraud), COUNT(*))    AS fraud_rate,
        SUM(transaction_amt)                    AS total_amt,
        AVG(transaction_amt)                    AS avg_amt
    FROM {{ ref('stg_transactions') }}
    WHERE billing_zip IS NOT NULL
      AND card_network NOT IN ('unknown', 'nan')
    GROUP BY 1, 2
),
stats AS (
    SELECT
        AVG(fraud_rate)    AS mean_fraud_rate,
        STDDEV(fraud_rate) AS std_fraud_rate
    FROM base
),
scored AS (
    SELECT
        b.*,
        SAFE_DIVIDE(
            b.fraud_rate - s.mean_fraud_rate,
            NULLIF(s.std_fraud_rate, 0)
        ) AS fraud_z_score
    FROM base b CROSS JOIN stats s
)
SELECT
    billing_zip,
    card_network,
    total_transactions,
    fraud_count,
    ROUND(fraud_rate * 100, 4)  AS fraud_rate_pct,
    ROUND(total_amt, 2)         AS total_amt,
    ROUND(avg_amt, 2)           AS avg_amt,
    ROUND(fraud_z_score, 4)     AS risk_z_score,
    {{ risk_band('fraud_z_score') }} AS risk_band
FROM scored
