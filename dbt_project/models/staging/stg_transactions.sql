WITH source AS (
    SELECT * FROM {{ source('raw', 'transactions') }}
),
renamed AS (
    SELECT
        TransactionID                                       AS transaction_id,
        CAST(TransactionDT AS INT64)                        AS transaction_dt_seconds,
        TIMESTAMP_ADD(
            TIMESTAMP '2017-11-30 00:00:00 UTC',
            INTERVAL CAST(TransactionDT AS INT64) SECOND
        )                                                   AS transaction_ts,
        CAST(TransactionAmt AS FLOAT64)                     AS transaction_amt,
        COALESCE(CAST(ProductCD AS STRING), 'unknown')      AS product_code,
        COALESCE(CAST(card4 AS STRING), 'unknown')          AS card_network,
        COALESCE(CAST(card6 AS STRING), 'unknown')          AS card_type,
        CAST(addr1 AS STRING)                               AS billing_zip,
        CAST(addr2 AS STRING)                               AS billing_country_code,
        CAST(P_emaildomain AS STRING)                       AS purchaser_email_domain,
        CAST(R_emaildomain AS STRING)                       AS recipient_email_domain,
        COALESCE(CAST(C1 AS FLOAT64), 0)                   AS c1_recipient_count,
        COALESCE(CAST(C6 AS FLOAT64), 0)                   AS c6_addr_count,
        COALESCE(CAST(C13 AS FLOAT64), 0)                  AS c13_count,
        COALESCE(CAST(D1 AS FLOAT64), -999)                AS d1_days_since_last,
        COALESCE(CAST(D15 AS FLOAT64), -999)               AS d15_days_feature,
        COALESCE(CAST(V258 AS FLOAT64), 0)                 AS v258_vesta,
        COALESCE(CAST(V201 AS FLOAT64), 0)                 AS v201_vesta,
        CAST(isFraud AS INT64)                              AS is_fraud
    FROM source
    WHERE TransactionID IS NOT NULL
      AND TransactionAmt > 0
      AND isFraud IS NOT NULL
)
SELECT * FROM renamed
