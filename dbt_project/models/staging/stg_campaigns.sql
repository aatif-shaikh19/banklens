WITH source AS (
    SELECT * FROM {{ source('raw', 'campaigns') }}
),
renamed AS (
    SELECT
        ROW_NUMBER() OVER (ORDER BY age, job)               AS campaign_contact_id,
        CAST(age AS INT64)                                  AS customer_age,
        LOWER(TRIM(CAST(job AS STRING)))                    AS job_category,
        LOWER(TRIM(CAST(marital AS STRING)))                AS marital_status,
        LOWER(TRIM(CAST(education AS STRING)))              AS education_level,
        LOWER(TRIM(CAST(contact AS STRING)))                AS contact_channel,
        LOWER(TRIM(CAST(month AS STRING)))                  AS contact_month,
        LOWER(TRIM(CAST(day_of_week AS STRING)))            AS contact_day,
        CAST(duration AS INT64)                             AS call_duration_seconds,
        CAST(campaign AS INT64)                             AS num_contacts_this_campaign,
        CAST(pdays AS INT64)                                AS days_since_prev_contact,
        CAST(previous AS INT64)                             AS num_prev_contacts,
        LOWER(TRIM(CAST(poutcome AS STRING)))               AS prev_campaign_outcome,
        CAST(emp_var_rate AS FLOAT64)                       AS emp_var_rate,
        CAST(cons_price_idx AS FLOAT64)                     AS consumer_price_idx,
        CAST(cons_conf_idx AS FLOAT64)                      AS consumer_conf_idx,
        CAST(euribor3m AS FLOAT64)                          AS euribor_3m_rate,
        CAST(nr_employed AS FLOAT64)                        AS num_employed,
        CASE WHEN LOWER(TRIM(CAST(y AS STRING))) = 'yes'
             THEN 1 ELSE 0 END                              AS subscribed
    FROM source
    WHERE y IS NOT NULL
)
SELECT * FROM renamed
