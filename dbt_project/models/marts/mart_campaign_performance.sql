SELECT
    contact_channel,
    contact_month,
    age_segment,
    job_category,
    prev_campaign_outcome,
    total_contacts,
    total_subscribed,
    response_rate_pct,
    avg_call_duration_s,
    avg_contacts,
    avg_euribor_rate,
    avg_cpi,
    CASE
        WHEN response_rate_pct >= 20 THEN 'High Performer'
        WHEN response_rate_pct >= 10 THEN 'Average'
        ELSE 'Underperforming'
    END                         AS performance_tier
FROM {{ ref('int_campaign_response') }}
