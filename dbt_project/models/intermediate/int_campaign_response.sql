WITH base AS (
    SELECT
        contact_channel,
        contact_month,
        contact_day,
        CASE
            WHEN customer_age < 25 THEN 'Youth (<25)'
            WHEN customer_age < 35 THEN 'Young Adult (25-34)'
            WHEN customer_age < 50 THEN 'Middle-Aged (35-49)'
            WHEN customer_age < 65 THEN 'Senior (50-64)'
            ELSE 'Retired (65+)'
        END                         AS age_segment,
        job_category,
        marital_status,
        education_level,
        prev_campaign_outcome,
        subscribed,
        call_duration_seconds,
        num_contacts_this_campaign,
        euribor_3m_rate,
        consumer_price_idx
    FROM {{ ref('stg_campaigns') }}
)
SELECT
    contact_channel,
    contact_month,
    contact_day,
    age_segment,
    job_category,
    marital_status,
    education_level,
    prev_campaign_outcome,
    COUNT(*)                                                        AS total_contacts,
    SUM(subscribed)                                                 AS total_subscribed,
    ROUND(SAFE_DIVIDE(SUM(subscribed), COUNT(*)) * 100, 4)         AS response_rate_pct,
    ROUND(AVG(call_duration_seconds), 0)                           AS avg_call_duration_s,
    ROUND(AVG(num_contacts_this_campaign), 2)                      AS avg_contacts,
    ROUND(AVG(euribor_3m_rate), 4)                                 AS avg_euribor_rate,
    ROUND(AVG(consumer_price_idx), 4)                              AS avg_cpi
FROM base
GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
