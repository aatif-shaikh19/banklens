# BankLens — Architecture & App Flow

---

## 1. High-Level Architecture

```
╔══════════════════════════════════════════════════════════════════════════╗
║                          RAW DATA SOURCES                               ║
║                                                                          ║
║  ┌─────────────────┐  ┌──────────────────┐  ┌─────────────────────┐    ║
║  │  IEEE-CIS Fraud │  │  UCI Bank        │  │  FDIC Statistics    │    ║
║  │  (Kaggle)       │  │  Marketing (UCI) │  │  (fdic.gov)         │    ║
║  │  590K rows      │  │  45K rows        │  │  Quarterly CSV      │    ║
║  │  train_txn.csv  │  │  bank-additional │  │  ~2K institutions   │    ║
║  │  train_id.csv   │  │  -full.csv       │  │                     │    ║
║  └────────┬────────┘  └────────┬─────────┘  └──────────┬──────────┘    ║
╚═══════════╪═══════════════════╪════════════════════════╪═══════════════╝
            │                   │                         │
            ▼                   ▼                         ▼
╔═══════════════════════════════════════════════════════════════════════════╗
║                        INGESTION LAYER (Python ETL)                      ║
║                                                                           ║
║  etl/load_transactions.py    etl/load_campaigns.py    etl/load_fdic.py   ║
║  (IEEE-CIS → BigQuery)       (Marketing → BigQuery)   (FDIC → Snowflake) ║
║  • Chunked loading           • Schema validation      • Quarterly upsert  ║
║  • Duplicate guard           • Type coercion          • Type coercion     ║
║  • Progress logging          • Null handling                              ║
╚══════════════╦════════════════╦══════════════════════════╦═══════════════╝
               │                │                          │
               ▼                ▼                          ▼
╔══════════════════════════╗  ╔════════════════════════════════════════════╗
║  GCP BigQuery            ║  ║  Snowflake                                 ║
║  banklens_raw dataset    ║  ║  BANKLENS_DB.RAW schema                    ║
║                          ║  ║                                            ║
║  • raw.transactions      ║  ║  • raw.regulatory (FDIC)                   ║
║    (590K rows)           ║  ║  • raw.customer_dim (enrichment)           ║
║  • raw.campaigns         ║  ║                                            ║
║    (45K rows)            ║  ║  Free trial: 30 days                       ║
║                          ║  ║  Storage: unlimited                        ║
║  10GB free/month         ║  ║                                            ║
╚═══════════╦══════════════╝  ╚════════════════╦═══════════════════════════╝
            │                                  │
            └──────────────┬───────────────────┘
                           ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                       DBT CORE TRANSFORMATION                            ║
║                                                                          ║
║  ┌─────────────────────────────────────────────────────────────────┐    ║
║  │  LAYER 1: staging/                                              │    ║
║  │  stg_transactions.sql  ──► rename cols, cast types, filter null │    ║
║  │  stg_campaigns.sql     ──► clean, encode target, snake_case     │    ║
║  │  stg_regulatory.sql    ──► FDIC column mapping + typing         │    ║
║  └─────────────────────────┬───────────────────────────────────────┘    ║
║                            │ refs                                        ║
║  ┌─────────────────────────▼───────────────────────────────────────┐    ║
║  │  LAYER 2: intermediate/                                          │    ║
║  │  int_customer_risk_profile.sql  ──► z-score, risk_band macro    │    ║
║  │  int_campaign_response.sql      ──► response rate, age_segment  │    ║
║  │  int_customer_360.sql           ──► join risk + campaign data   │    ║
║  └─────────────────────────┬───────────────────────────────────────┘    ║
║                            │ refs                                        ║
║  ┌─────────────────────────▼───────────────────────────────────────┐    ║
║  │  LAYER 3: marts/  (final, BI-ready tables)                      │    ║
║  │  mart_fraud_dashboard.sql      ──► Power BI source              │    ║
║  │  mart_campaign_performance.sql ──► Looker Studio source         │    ║
║  │  mart_customer_360.sql         ──► Query 5 "killer query"       │    ║
║  │  mart_regulatory_summary.sql   ──► Power BI regulatory page     │    ║
║  └─────────────────────────────────────────────────────────────────┘    ║
║                                                                          ║
║  Column-level lineage tracked automatically. Run:                        ║
║  dbt docs generate && dbt docs serve  → browse at localhost:8080         ║
╚═══════════════════════════╦══════════════════════════════════════════════╝
                            │
                            ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                    GREAT EXPECTATIONS DATA QUALITY                       ║
║                                                                          ║
║  transactions_checkpoint:              campaigns_checkpoint:             ║
║  • transaction_id: not null, unique    • subscribed: values in [0,1]    ║
║  • transaction_amt: 0.01 ≤ x ≤ 50000  • response rate: 0-100%          ║
║  • is_fraud mean: 0.01 – 0.06         • contact_channel: in valid set  ║
║  • risk_band: in [Low,Med,High,Crit]  • not null on key columns         ║
║                                                                          ║
║  FAIL → Airflow stops. Alert email sent. No bad data reaches BI.        ║
╚═══════════════════════════╦══════════════════════════════════════════════╝
                            │
                            ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                    APACHE AIRFLOW ORCHESTRATION                          ║
║                                                                          ║
║  DAG: banklens_weekly_pipeline                                           ║
║  Schedule: 0 6 * * 1  (Every Monday 06:00 UTC)                         ║
║                                                                          ║
║  [fetch_transactions] ─┐                                                 ║
║  [fetch_campaigns]    ─┼──► [dbt_run] ──► [dbt_test] ──►               ║
║  [fetch_fdic]         ─┘    [ge_validate] ──► [refresh_powerbi]         ║
║                                                                          ║
║  Retries: 2 attempts | Retry delay: 5 min | Email on failure            ║
╚═════════╦════════════════════════════════════════════════╦══════════════╝
          │                                                │
          ▼                                                ▼
╔═════════════════════════╗                  ╔════════════════════════════╗
║   ML / FRAUD SCORING    ║                  ║  BI & DASHBOARDS            ║
║                         ║                  ║                             ║
║  XGBoost Classifier     ║                  ║  Power BI Desktop (4 pages)║
║  • 500 estimators       ║                  ║  • Executive Overview       ║
║  • scale_pos_weight     ║                  ║  • Risk Intelligence        ║
║    (handles 97:3 ratio) ║                  ║  • Customer 360             ║
║  • AUC-ROC ≥ 0.85       ║                  ║  • Regulatory Compliance    ║
║                         ║                  ║  + Copilot AI summaries     ║
║  SHAP TreeExplainer     ║                  ║                             ║
║  • Force plots          ║                  ║  Looker Studio (3 pages)    ║
║  • Summary bar plot     ║                  ║  • Campaign Overview         ║
║                         ║                  ║  • Customer Response         ║
║  FastAPI /predict       ║                  ║  • Performance Tiers        ║
║  • Input: 11 features   ║                  ║                             ║
║  • Output: probability  ║                  ║  Streamlit (optional)       ║
║    + risk_band          ║                  ║  • Real-time fraud scorer   ║
║    + recommendation     ║                  ║                             ║
╚═════════════════════════╝                  ╚═══════════════╦════════════╝
                                                             │
                                                             ▼
╔══════════════════════════════════════════════════════════════════════════╗
║                           AI LAYER                                       ║
║                                                                          ║
║  ┌───────────────────────┐ ┌──────────────────┐ ┌────────────────────┐ ║
║  │ Snowflake Cortex      │ │   PandasAI 2.4   │ │  Power BI Copilot  │ ║
║  │ Analyst               │ │                  │ │                    │ ║
║  │ • semantic_model.yaml │ │ • pai.DataFrame  │ │ • AI narratives    │ ║
║  │ • NL → SQL            │ │ • pai.chat()     │ │ • "Summarise this  │ ║
║  │ • Runs on Snowflake   │ │ • OpenAI backend │ │   month's perf"    │ ║
║  │   warehouse           │ │ • No litellm!    │ │ • Requires Fabric  │ ║
║  └───────────────────────┘ └──────────────────┘ └────────────────────┘ ║
╚══════════════════════════════════════════════════════════════════════════╝
```

---

## 2. Data Flow — Transaction Risk Path

```
Kaggle: IEEE-CIS Fraud Dataset
│
├── train_transaction.csv (530MB, 590K rows, 393 columns)
│   columns: TransactionID, TransactionDT, TransactionAmt, ProductCD,
│            card1-6, addr1/addr2, P_emaildomain, R_emaildomain,
│            C1-C14 (count features), D1-D15 (time deltas),
│            M1-M9 (match features), V1-V339 (Vesta features), isFraud
│
└── train_identity.csv (65MB, 144K rows, 41 columns)
    columns: TransactionID, DeviceType, DeviceInfo, id_01..38
    (only 144K of 590K transactions have identity records)

        │ JOIN on TransactionID
        ▼
load_transactions.py
  ├── Read in 10K-row chunks (memory safe for 530MB file)
  ├── Fill NA with sentinel (-999 for numerics, 'unknown' for strings)
  ├── Deduplicate on TransactionID
  └── Upload to BigQuery raw.transactions via google-cloud-bigquery

        │
        ▼
stg_transactions.sql (dbt)
  ├── Rename: TransactionID → transaction_id, TransactionAmt → transaction_amt
  ├── Cast: CAST(TransactionDT AS INT64), CAST(isFraud AS INT64)
  ├── Derive: TIMESTAMP_ADD('2017-11-30', INTERVAL TransactionDT SECOND) → transaction_ts
  └── Filter: WHERE TransactionID IS NOT NULL AND TransactionAmt > 0

        │
        ▼
int_customer_risk_profile.sql (dbt)
  ├── Group by billing_zip + card_network
  ├── Compute z-score: (fraud_rate - avg_fraud_rate) / stddev_fraud_rate
  └── Apply risk_band macro: z > 3 → Critical, z > 2 → High, etc.

        │
        ▼
mart_fraud_dashboard.sql (dbt)
  ├── Aggregate by date, product_code, card_network, card_type, risk_band
  ├── Compute: total_transactions, fraud_count, fraud_rate_pct, total_volume
  └── Power BI connects directly to this table

        │
        ▼
ml/fraud_model.py
  ├── Load from mart or raw CSV
  ├── Encode categoricals (ProductCD, card4, card6)
  ├── XGBoost: 500 trees, scale_pos_weight handles 97:3 imbalance
  ├── Evaluate: AUC-ROC, precision, recall, F1
  ├── SHAP: explain which features drive each prediction
  └── Save: model_artifacts/fraud_model_xgb.pkl

        │
        ▼
api/main.py (FastAPI)
  └── POST /predict: receive 11 features, return {probability, risk_band, recommendation}
```

---

## 3. Data Flow — Campaign Performance Path

```
UCI: Bank Marketing Dataset
│
└── bank-additional-full.csv (45K rows, semicolon-separated)
    columns: age, job, marital, education, default, housing, loan,
             contact, month, day_of_week, duration, campaign, pdays,
             previous, poutcome, emp.var.rate, cons.price.idx,
             cons.conf.idx, euribor3m, nr.employed, y (target: yes/no)

        │
        ▼
load_campaigns.py
  ├── Read CSV with sep=';'
  ├── Validate: assert y.isin(['yes','no']).all()
  └── Upload to BigQuery raw.campaigns

        │
        ▼
stg_campaigns.sql (dbt)
  ├── Rename: y → subscribed (1/0), duration → call_duration_seconds
  ├── Clean: LOWER(TRIM(job)), LOWER(TRIM(contact))
  ├── Derive: ROW_NUMBER() as campaign_contact_id
  └── Encode: CASE WHEN y='yes' THEN 1 ELSE 0 END AS subscribed

        │
        ▼
int_campaign_response.sql (dbt)
  ├── Group by: contact_channel, age_segment, job_category, month
  ├── Compute: total_contacts, total_subscribed, response_rate_pct
  └── Add: age_segment CASE (Youth/Young Adult/Middle-Aged/Senior)

        │
        ▼
mart_campaign_performance.sql (dbt)
  ├── Select all campaign metrics + calculated fields
  ├── Add: campaign_performance_tier (High/Average/Underperforming)
  └── Looker Studio connects directly to this table
```

---

## 4. The Killer Query — Why BankLens 2.0 Exists

```
mart_customer_360.sql
  ├── JOIN: stg_transactions + stg_campaigns via billing_zip proxy
  ├── Add: campaign_eligibility
  │   CASE WHEN max_risk_band IN ('High','Critical') THEN 'Suppress — High Risk'
  │        WHEN max_risk_band = 'Medium' THEN 'Standard Review'
  │        ELSE 'Campaign Eligible'
  └── This is the UNIFIED record — one row per customer proxy

        │
        ▼
analytics.sql — Query 5 (The Business Case)
  SELECT c360.billing_zip, c360.max_risk_band, c360.campaign_eligibility,
         cp.contact_channel, 'RISK CONTROL GAP' AS flag
  FROM mart_customer_360 c360
  JOIN mart_campaign_performance cp ON ...
  WHERE c360.max_risk_band IN ('High', 'Critical')
    AND c360.campaign_eligibility != 'Suppress — High Risk'
  ORDER BY c360.avg_risk_z_score DESC;

  → These customers SHOULD have been suppressed. They weren't.
  → This output IS the business justification for the whole project.
```

---

## 5. Repository Structure (Complete)

```
banklens/
│
├── README.md                          ← Architecture + screenshots + setup
├── .env.example                       ← Template (never commit .env)
├── .gitignore                         ← Must include: .env, *.pkl, data/raw/
├── requirements.txt                   ← Pinned versions (June 2026 edition)
├── requirements.lock                  ← Hash-pinned lock file (pip-compile)
├── docker-compose.yml                 ← Airflow local environment
│
├── data/
│   ├── download_instructions.md       ← Kaggle CLI commands + UCI link
│   ├── raw/                           ← .gitignored — raw CSVs live here
│   │   ├── train_transaction.csv      ← ~530MB
│   │   ├── train_identity.csv         ← ~65MB
│   │   ├── bank-additional-full.csv   ← ~5MB
│   │   └── fdic_data_YYYYQQ.csv       ← ~3MB
│   └── sample/                        ← 1,000-row sample for fast testing
│       ├── sample_transactions.csv
│       └── sample_campaigns.csv
│
├── etl/
│   ├── load_transactions.py           ← IEEE-CIS → BigQuery raw.transactions
│   ├── load_campaigns.py              ← Bank Marketing → BigQuery raw.campaigns
│   ├── load_fdic.py                   ← FDIC CSV → Snowflake raw.regulatory
│   └── utils.py                       ← GCP client, Snowflake connection helpers
│
├── dbt_project/
│   ├── dbt_project.yml
│   ├── profiles.yml.example           ← Template for BigQuery + Snowflake profiles
│   ├── packages.yml                   ← dbt_utils, dbt_expectations
│   │
│   ├── models/
│   │   ├── staging/
│   │   │   ├── sources.yml            ← Declares raw.transactions + raw.campaigns
│   │   │   ├── stg_transactions.sql
│   │   │   ├── stg_campaigns.sql
│   │   │   ├── stg_regulatory.sql
│   │   │   ├── stg_transactions.yml   ← column docs + tests
│   │   │   ├── stg_campaigns.yml
│   │   │   └── stg_regulatory.yml
│   │   │
│   │   ├── intermediate/
│   │   │   ├── int_customer_risk_profile.sql
│   │   │   ├── int_campaign_response.sql
│   │   │   ├── int_customer_360.sql
│   │   │   └── *.yml
│   │   │
│   │   └── marts/
│   │       ├── mart_fraud_dashboard.sql
│   │       ├── mart_campaign_performance.sql
│   │       ├── mart_regulatory_summary.sql
│   │       ├── mart_customer_360.sql
│   │       └── *.yml
│   │
│   ├── tests/
│   │   ├── assert_fraud_rate_reasonable.sql
│   │   └── assert_campaign_response_valid.sql
│   │
│   └── macros/
│       └── risk_band.sql              ← Reusable risk band macro
│
├── great_expectations/
│   ├── great_expectations.yml
│   └── checkpoints/
│       ├── transactions_checkpoint.py
│       └── campaigns_checkpoint.py
│
├── airflow/
│   └── dags/
│       └── banklens_pipeline.py       ← Full weekly DAG
│
├── ml/
│   ├── fraud_model.py                 ← XGBoost training
│   ├── shap_analysis.py              ← SHAP force plots + summary
│   ├── evaluate.py                   ← Metrics: AUC, precision, recall, F1
│   └── model_artifacts/              ← .gitignored — .pkl files live here
│       ├── fraud_model_xgb.pkl
│       └── shap_summary.png
│
├── api/
│   ├── main.py                        ← FastAPI app with /predict + /health
│   ├── schemas.py                     ← Pydantic request/response models
│   ├── middleware.py                  ← Rate limiting, CORS, security headers
│   └── test_api.py                    ← Pytest tests
│
├── notebooks/
│   ├── 01_EDA_transactions.ipynb      ← Fraud data exploration
│   ├── 02_EDA_campaigns.ipynb         ← Campaign response analysis
│   └── 03_customer_360.ipynb          ← Joined analysis
│
├── sql/
│   └── analytics.sql                  ← 5 standalone advanced SQL queries
│
├── semantic_model/
│   └── banklens_semantic_model.yaml   ← Snowflake Cortex Analyst config
│
├── chat/
│   └── chat_with_data.py             ← PandasAI natural language interface
│
├── dashboards/
│   ├── powerbi/
│   │   ├── banklens.pbix
│   │   └── README.md
│   ├── looker_studio/
│   │   ├── campaign_dashboard_export.json
│   │   └── screenshots/
│   └── tableau/
│       └── banklens.twbx
│
├── reports/
│   └── generate_excel_report.py
│
├── tests/
│   └── test_etl.py
│
└── .github/
    └── workflows/
        └── dbt_ci.yml                 ← dbt test on push to main
```

---

## 6. Airflow DAG Flow (Visual)

```
Monday 06:00 UTC — DAG triggers
         │
         ▼
┌────────────────────────────────────────────────────────────────────┐
│  PARALLEL FETCH (runs simultaneously)                              │
│  [fetch_ieee_cis_data] + [fetch_campaign_data] + [fetch_fdic_data] │
└──────────────────────────────┬─────────────────────────────────────┘
                               │ (all 3 must succeed)
                               ▼
                     ┌─────────────────┐
                     │   dbt_run        │
                     │ (runs all models)│
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   dbt_test       │
                     │ (tests all models│
                     └────────┬────────┘
                              │
                              ▼
                     ┌─────────────────────────┐
                     │  great_expectations_     │
                     │  validate               │
                     │  (HALT if checks fail)  │
                     └────────┬────────────────┘
                              │
                              ▼
                     ┌──────────────────────────┐
                     │  refresh_powerbi_dataset  │
                     │  (POST to Power BI API)   │
                     └──────────────────────────┘
                              │
                              ▼
                         ✅ Pipeline Complete
                    (or ❌ Alert email sent to aatif.shaikh2004@gmail.com)
```

---

*Architecture Doc — BankLens 1.0 | June 2026*
