-- BankLens 2.0 — Advanced Analytics Queries
-- These 5 queries demonstrate window functions, CTEs, and complex joins.
-- Run directly in BigQuery Console. All tables reference banklens-499408.

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 1: Rolling 30-day fraud rate per card network (window function)
-- Skill: SUM() OVER (ORDER BY date ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
-- ─────────────────────────────────────────────────────────────────────────────
WITH daily AS (
    SELECT
        DATE(transaction_ts)    AS txn_date,
        card_network,
        COUNT(*)                AS daily_txns,
        SUM(is_fraud)           AS daily_frauds
    FROM `banklens-499408.banklens_raw.transactions`
    GROUP BY 1, 2
)
SELECT
    txn_date,
    card_network,
    SUM(daily_txns) OVER (
        PARTITION BY card_network
        ORDER BY txn_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )                           AS rolling_30d_txns,
    SUM(daily_frauds) OVER (
        PARTITION BY card_network
        ORDER BY txn_date
        ROWS BETWEEN 29 PRECEDING AND CURRENT ROW
    )                           AS rolling_30d_frauds,
    ROUND(
        SAFE_DIVIDE(
            SUM(daily_frauds) OVER (
                PARTITION BY card_network
                ORDER BY txn_date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW),
            SUM(daily_txns) OVER (
                PARTITION BY card_network
                ORDER BY txn_date
                ROWS BETWEEN 29 PRECEDING AND CURRENT ROW)
        ) * 100, 4
    )                           AS rolling_30d_fraud_rate_pct
FROM daily
ORDER BY txn_date DESC, card_network
LIMIT 100;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 2: RFM Segmentation with NTILE window function
-- Skill: NTILE(), multi-condition CASE, customer segmentation
-- ─────────────────────────────────────────────────────────────────────────────
WITH rfm_base AS (
    SELECT
        billing_zip                                 AS customer_proxy,
        DATE_DIFF(DATE '2019-12-01',
                  MAX(DATE(transaction_ts)), DAY)   AS recency_days,
        COUNT(*)                                    AS frequency,
        ROUND(SUM(transaction_amt), 2)             AS monetary
    FROM `banklens-499408.banklens_raw.transactions`
    WHERE billing_zip IS NOT NULL
    GROUP BY 1
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC)  AS r_score,
        NTILE(5) OVER (ORDER BY frequency)           AS f_score,
        NTILE(5) OVER (ORDER BY monetary)            AS m_score
    FROM rfm_base
)
SELECT
    customer_proxy,
    r_score, f_score, m_score,
    r_score + f_score + m_score                      AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4                  THEN 'Recent Customers'
        WHEN f_score >= 4                  THEN 'Potential Loyalists'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'At Risk'
        ELSE 'Needs Attention'
    END                                              AS rfm_segment
FROM rfm_scored
ORDER BY rfm_total DESC
LIMIT 200;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 3: Month-over-Month volume variance with LAG()
-- Skill: LAG() window function, percentage change calculation
-- ─────────────────────────────────────────────────────────────────────────────
WITH monthly AS (
    SELECT
        FORMAT_DATE('%Y-%m', DATE(transaction_ts))   AS month_key,
        card_network,
        COUNT(*)                                      AS total_txns,
        ROUND(SUM(transaction_amt), 2)               AS total_volume,
        SUM(is_fraud)                                 AS fraud_count
    FROM `banklens-499408.banklens_raw.transactions`
    GROUP BY 1, 2
)
SELECT
    month_key,
    card_network,
    total_txns,
    total_volume,
    fraud_count,
    LAG(total_volume) OVER (
        PARTITION BY card_network ORDER BY month_key) AS prev_month_volume,
    ROUND(
        SAFE_DIVIDE(
            total_volume - LAG(total_volume) OVER (
                PARTITION BY card_network ORDER BY month_key),
            LAG(total_volume) OVER (
                PARTITION BY card_network ORDER BY month_key)
        ) * 100, 2
    )                                                 AS mom_volume_change_pct
FROM monthly
ORDER BY card_network, month_key;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 4: Campaign response rate by age segment and contact channel
-- Skill: Multi-condition CASE, conditional aggregation, HAVING filter
-- ─────────────────────────────────────────────────────────────────────────────
SELECT
    CASE
        WHEN CAST(age AS INT64) < 25 THEN 'Youth (<25)'
        WHEN CAST(age AS INT64) < 35 THEN 'Young Adult (25-34)'
        WHEN CAST(age AS INT64) < 50 THEN 'Middle-Aged (35-49)'
        WHEN CAST(age AS INT64) < 65 THEN 'Senior (50-64)'
        ELSE 'Retired (65+)'
    END                                              AS age_segment,
    contact                                          AS contact_channel,
    COUNT(*)                                         AS total_contacts,
    SUM(CASE WHEN y = 'yes' THEN 1 ELSE 0 END)      AS total_subscribed,
    ROUND(
        SUM(CASE WHEN y = 'yes' THEN 1 ELSE 0 END) /
        COUNT(*) * 100, 2
    )                                                AS response_rate_pct,
    ROUND(AVG(CAST(duration AS INT64)), 0)           AS avg_call_duration_s
FROM `banklens-499408.banklens_raw.campaigns`
GROUP BY 1, 2
HAVING COUNT(*) >= 50
ORDER BY response_rate_pct DESC;

-- ─────────────────────────────────────────────────────────────────────────────
-- QUERY 5: High-risk customers who received campaign offers (THE KILLER QUERY)
-- Skill: Multi-CTE, CROSS JOIN for lookup, business insight surfacing
-- THIS IS THE BUSINESS JUSTIFICATION FOR BANKLENS 2.0
-- These customers should have been suppressed but were not.
-- The gap between the risk team and marketing team in action.
-- ─────────────────────────────────────────────────────────────────────────────
WITH transaction_risk AS (
    SELECT
        CAST(addr1 AS STRING)           AS billing_zip,
        card4                           AS card_network,
        COUNT(*)                        AS total_transactions,
        SUM(isFraud)                    AS total_frauds,
        ROUND(
            SAFE_DIVIDE(SUM(isFraud), COUNT(*)) * 100, 4
        )                               AS fraud_rate_pct,
        CASE
            WHEN SAFE_DIVIDE(SUM(isFraud), COUNT(*)) > 0.10 THEN 'Critical'
            WHEN SAFE_DIVIDE(SUM(isFraud), COUNT(*)) > 0.05 THEN 'High'
            WHEN SAFE_DIVIDE(SUM(isFraud), COUNT(*)) > 0.02 THEN 'Medium'
            ELSE 'Low'
        END                             AS risk_band
    FROM `banklens-499408.banklens_raw.transactions`
    WHERE addr1 IS NOT NULL
    GROUP BY 1, 2
    HAVING COUNT(*) >= 30
),
campaign_summary AS (
    SELECT
        contact                         AS channel,
        COUNT(*)                        AS contacts,
        ROUND(
            SUM(CASE WHEN y='yes' THEN 1 ELSE 0 END) /
            COUNT(*) * 100, 2
        )                               AS response_rate_pct
    FROM `banklens-499408.banklens_raw.campaigns`
    GROUP BY 1
)
SELECT
    tr.billing_zip,
    tr.card_network,
    tr.fraud_rate_pct,
    tr.risk_band,
    tr.total_transactions,
    tr.total_frauds,
    cs.channel                          AS best_campaign_channel,
    cs.response_rate_pct               AS channel_response_rate,
    'SHOULD HAVE BEEN SUPPRESSED'       AS banklens_flag
FROM transaction_risk tr
CROSS JOIN campaign_summary cs
WHERE tr.risk_band IN ('High', 'Critical')
  AND cs.channel = 'cellular'
ORDER BY tr.fraud_rate_pct DESC
LIMIT 50;
