# BankLens — Backend Structure Document
**Complete code templates for every backend file**

---

## Project Layout (Quick Reference)

```
banklens/
├── etl/               ← Data ingestion (Python → BigQuery/Snowflake)
├── dbt_project/       ← SQL transformations (staging → intermediate → marts)
├── great_expectations/← Data quality checkpoints
├── airflow/           ← Orchestration DAG
├── ml/                ← ML training, SHAP, model artifacts
├── api/               ← FastAPI fraud scoring endpoint
└── chat/              ← PandasAI NL interface
```

---

## 1. `etl/utils.py` — Shared Helpers

```python
# etl/utils.py
"""
Shared utility functions for BankLens 2.0 ETL layer.
Handles BigQuery and Snowflake connections.
"""
import os
import logging
from google.cloud import bigquery
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

def get_bq_client() -> bigquery.Client:
    """Return an authenticated BigQuery client."""
    project = os.getenv("GCP_PROJECT_ID")
    if not project:
        raise ValueError("GCP_PROJECT_ID not set in environment")
    return bigquery.Client(project=project)

def get_snowflake_conn() -> snowflake.connector.SnowflakeConnection:
    """Return an authenticated Snowflake connection."""
    required = ["SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
                "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"Missing Snowflake env vars: {missing}")
    
    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    )

def bq_table_exists(client: bigquery.Client, project: str, dataset: str, table: str) -> bool:
    """Check if a BigQuery table exists."""
    try:
        client.get_table(f"{project}.{dataset}.{table}")
        return True
    except Exception:
        return False

def bq_row_count(client: bigquery.Client, project: str, dataset: str, table: str) -> int:
    """Get row count for a BigQuery table."""
    result = client.query(f"SELECT COUNT(*) as cnt FROM `{project}.{dataset}.{table}`").result()
    return list(result)[0].cnt
```

---

## 2. `etl/load_fdic.py` — FDIC → Snowflake

```python
# etl/load_fdic.py
"""Load FDIC bank statistics into Snowflake regulatory table."""
import pandas as pd
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from etl.utils import get_snowflake_conn
import logging
import os
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

FDIC_FILE = "data/raw/fdic_institutions.csv"
TABLE_NAME = "REGULATORY"

def run():
    logger.info("Loading FDIC data to Snowflake...")
    
    conn = get_snowflake_conn()
    
    # Read FDIC data
    df = pd.read_csv(FDIC_FILE)
    logger.info(f"FDIC rows: {len(df):,} | Columns: {df.shape[1]}")
    
    # Select and rename key columns for our regulatory dashboard
    key_cols = {
        'REPDTE': 'report_date',
        'CERT': 'cert_number', 
        'INSTNAME': 'institution_name',
        'ASSET': 'total_assets_k',
        'DEP': 'total_deposits_k',
        'NETINC': 'net_income_k',
        'INTINC': 'interest_income_k',
        'NONII': 'noninterest_income_k',
        'LNLSNET': 'net_loans_k',
        'NPERFV': 'noncurrent_loans_k',
        'TIER1RBC': 'tier1_capital_ratio'
    }
    
    available = {k: v for k, v in key_cols.items() if k in df.columns}
    df_slim = df[list(available.keys())].rename(columns=available)
    
    # Type conversions
    df_slim['report_date'] = pd.to_datetime(df_slim['report_date'].astype(str), 
                                              format='%Y%m%d', errors='coerce')
    
    # Create table if it doesn't exist, then truncate and reload
    cur = conn.cursor()
    cur.execute(f"""
        CREATE TABLE IF NOT EXISTS REGULATORY (
            report_date DATE,
            cert_number VARCHAR,
            institution_name VARCHAR,
            total_assets_k FLOAT,
            total_deposits_k FLOAT,
            net_income_k FLOAT,
            interest_income_k FLOAT,
            noninterest_income_k FLOAT,
            net_loans_k FLOAT,
            noncurrent_loans_k FLOAT,
            tier1_capital_ratio FLOAT
        )
    """)
    cur.execute("TRUNCATE TABLE REGULATORY")
    
    success, nchunks, nrows, _ = write_pandas(conn, df_slim, TABLE_NAME)
    
    if success:
        logger.info(f"✅ Loaded {nrows:,} rows to Snowflake.REGULATORY")
    else:
        raise RuntimeError("Snowflake load failed")
    
    conn.close()

if __name__ == "__main__":
    run()
```

---

## 3. `ml/fraud_model.py` — Updated for XGBoost 3.x

```python
# ml/fraud_model.py
"""
BankLens 2.0 Fraud Detection Model
XGBoost 3.x (updated from 2.x in original spec)
Handles: class imbalance, feature encoding, AUC evaluation, model saving
"""
import pandas as pd
import numpy as np
from xgboost import XGBClassifier
from sklearn.model_selection import train_test_split, StratifiedKFold
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.preprocessing import LabelEncoder
from sklearn.pipeline import Pipeline
import joblib
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# ── Feature config ───────────────────────────────────────────────────
FEATURES = ['TransactionAmt', 'ProductCD', 'card4', 'card6',
            'C1', 'C6', 'C13', 'D1', 'D15', 'V258', 'V201']
CATEGORICAL = ['ProductCD', 'card4', 'card6']
TARGET = 'isFraud'

def encode_features(df: pd.DataFrame) -> pd.DataFrame:
    """Encode categorical features using LabelEncoder."""
    df = df.copy()  # pandas 3.x: always copy before modifying
    le = LabelEncoder()
    for col in CATEGORICAL:
        if col in df.columns:
            df[col] = le.fit_transform(df[col].fillna('unknown').astype(str))
    return df

def train(data_path: str = 'data/raw/train_transaction.csv',
          model_output: str = 'ml/model_artifacts/fraud_model_xgb.pkl') -> float:
    """
    Train XGBoost fraud model. Returns AUC-ROC score.
    """
    os.makedirs(os.path.dirname(model_output), exist_ok=True)
    
    logger.info(f"Loading training data from {data_path}...")
    # Load in chunks if full file, otherwise load sample
    if os.path.getsize(data_path) > 100_000_000:  # > 100MB = full file
        df = pd.read_csv(data_path, usecols=FEATURES + [TARGET])
    else:
        df = pd.read_csv(data_path)
    
    logger.info(f"Dataset shape: {df.shape} | Fraud rate: {df[TARGET].mean()*100:.2f}%")
    
    # Encode and prepare features
    df = encode_features(df)
    X = df[FEATURES].fillna(-999)
    y = df[TARGET]
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, stratify=y, random_state=42
    )
    
    # Class imbalance: scale fraud cases by the imbalance ratio
    fraud_count = (y_train == 1).sum()
    non_fraud   = (y_train == 0).sum()
    scale_weight = non_fraud / fraud_count
    logger.info(f"Class balance: {non_fraud:,} non-fraud, {fraud_count:,} fraud")
    logger.info(f"scale_pos_weight: {scale_weight:.1f}")
    
    # XGBoost 3.x model — note: use_label_encoder param removed in 3.x
    model = XGBClassifier(
        n_estimators=500,
        max_depth=6,
        learning_rate=0.05,
        scale_pos_weight=scale_weight,   # handles imbalance
        subsample=0.8,
        colsample_bytree=0.8,
        eval_metric='auc',               # in 3.x, this is set in constructor
        early_stopping_rounds=50,
        random_state=42,
        n_jobs=-1,
        device='cpu',                    # explicitly set in 3.x
        verbosity=1
    )
    
    logger.info("Training XGBoost model...")
    model.fit(
        X_train, y_train,
        eval_set=[(X_test, y_test)],
        verbose=100
    )
    
    # Evaluate
    y_pred_proba = model.predict_proba(X_test)[:, 1]
    auc = roc_auc_score(y_test, y_pred_proba)
    
    logger.info(f"\n{'='*50}")
    logger.info(f"AUC-ROC: {auc:.4f}")
    logger.info(f"{'='*50}")
    logger.info(f"\nClassification Report:\n{classification_report(y_test, model.predict(X_test))}")
    
    if auc < 0.85:
        logger.warning(f"⚠️  AUC {auc:.4f} is below target of 0.85. "
                        f"Consider adding more features or tuning hyperparameters.")
    else:
        logger.info(f"✅ AUC {auc:.4f} meets target of 0.85")
    
    # Save model
    joblib.dump(model, model_output)
    logger.info(f"✅ Model saved to {model_output}")
    
    return auc

if __name__ == "__main__":
    auc = train()
    print(f"\nFinal AUC-ROC: {auc:.4f}")
```

---

## 4. `api/schemas.py` — Pydantic Models

```python
# api/schemas.py
"""Pydantic schemas for BankLens 2.0 Fraud Scoring API."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional

class TransactionInput(BaseModel):
    """Input schema for fraud scoring endpoint."""
    TransactionAmt: float = Field(..., gt=0, le=50000,
                                   example=500.00,
                                   description="Transaction amount in USD (0.01 - 50,000)")
    ProductCD:      int   = Field(..., ge=0, le=4,
                                   example=0,
                                   description="Encoded product code (0=C, 1=H, 2=R, 3=S, 4=W)")
    card4:          int   = Field(..., ge=0, le=3,
                                   example=1,
                                   description="Encoded card network (0=amex, 1=discover, 2=mastercard, 3=visa)")
    card6:          int   = Field(..., ge=0, le=1,
                                   example=0,
                                   description="Encoded card type (0=credit, 1=debit)")
    C1:             float = Field(..., ge=0, example=3.0,
                                   description="Recipient count feature")
    C6:             float = Field(..., ge=0, example=1.0,
                                   description="Address count feature")
    C13:            float = Field(..., ge=0, example=2.0,
                                   description="Count feature 13")
    D1:             float = Field(..., ge=-1, example=5.0,
                                   description="Days since last transaction (-1 if first)")
    D15:            float = Field(..., ge=-1, example=10.0,
                                   description="Days feature 15")
    V258:           float = Field(..., example=0.5,
                                   description="Vesta risk feature 258")
    V201:           float = Field(..., example=0.3,
                                   description="Vesta risk feature 201")
    
    @field_validator('TransactionAmt')
    @classmethod
    def amount_positive(cls, v: float) -> float:
        return round(v, 2)

    model_config = {"json_schema_extra": {
        "example": {
            "TransactionAmt": 500.00, "ProductCD": 0, "card4": 3, "card6": 0,
            "C1": 3.0, "C6": 1.0, "C13": 2.0, "D1": 5.0, "D15": 10.0,
            "V258": 0.5, "V201": 0.3
        }
    }}

class FraudPrediction(BaseModel):
    """Output schema for fraud scoring endpoint."""
    fraud_probability: float = Field(..., ge=0, le=1,
                                      description="Probability of fraud (0-1)")
    risk_band:         str   = Field(..., description="Risk classification: Low/Medium/High/Critical")
    recommendation:    str   = Field(..., description="Action recommendation")
    model_version:     str   = Field(default="xgboost-v2.0",
                                      description="Model version identifier")

class HealthResponse(BaseModel):
    status: str
    model: str
    model_loaded: bool
    version: Optional[str] = "2.0.0"
```

---

## 5. `dbt_project/packages.yml`

```yaml
# dbt_project/packages.yml
packages:
  - package: dbt-labs/dbt_utils
    version: [">=1.3.0", "<2.0.0"]
  
  - package: calogica/dbt_expectations
    version: [">=0.10.0", "<1.0.0"]
```

```bash
# Install dbt packages
cd dbt_project
dbt deps
```

---

## 6. dbt Intermediate Models (Complete SQL)

### `models/intermediate/int_customer_risk_profile.sql`

```sql
-- Computes risk z-score and risk band per billing_zip + card_network combination.
-- Used in mart_fraud_dashboard and mart_customer_360.

WITH base AS (
    SELECT
        billing_zip,
        card_network,
        COUNT(*)                              AS total_transactions,
        SUM(is_fraud)                         AS fraud_count,
        ROUND(SUM(is_fraud) / COUNT(*), 6)    AS fraud_rate,
        SUM(transaction_amt)                  AS total_amt,
        AVG(transaction_amt)                  AS avg_amt
    FROM {{ ref('stg_transactions') }}
    WHERE billing_zip IS NOT NULL
      AND card_network IS NOT NULL
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
        s.mean_fraud_rate,
        s.std_fraud_rate,
        SAFE_DIVIDE(b.fraud_rate - s.mean_fraud_rate, NULLIF(s.std_fraud_rate, 0)) AS fraud_z_score
    FROM base b
    CROSS JOIN stats s
)
SELECT
    billing_zip,
    card_network,
    total_transactions,
    fraud_count,
    fraud_rate,
    total_amt,
    avg_amt,
    ROUND(fraud_z_score, 4)                   AS risk_z_score,
    {{ risk_band('fraud_z_score') }}           AS risk_band   -- macro call
FROM scored
```

### `models/intermediate/int_campaign_response.sql`

```sql
-- Aggregates campaign response metrics by segment.
-- Computes response rates and age segmentation.

WITH base AS (
    SELECT
        contact_channel,
        contact_month,
        contact_day,
        job_category,
        marital_status,
        education_level,
        prev_campaign_outcome,
        CASE
            WHEN customer_age < 25  THEN 'Youth (< 25)'
            WHEN customer_age < 35  THEN 'Young Adult (25-34)'
            WHEN customer_age < 50  THEN 'Middle-Aged (35-49)'
            WHEN customer_age < 65  THEN 'Senior (50-64)'
            ELSE 'Retired (65+)'
        END                                          AS age_segment,
        subscribed,
        call_duration_seconds,
        num_contacts_this_campaign,
        euribor_3m_rate,
        consumer_price_idx
    FROM {{ ref('stg_campaigns') }}
),
aggregated AS (
    SELECT
        contact_channel,
        contact_month,
        contact_day,
        age_segment,
        job_category,
        marital_status,
        education_level,
        prev_campaign_outcome,
        COUNT(*)                                      AS total_contacts,
        SUM(subscribed)                               AS total_subscribed,
        ROUND(SUM(subscribed) / COUNT(*) * 100, 4)    AS response_rate_pct,
        ROUND(AVG(call_duration_seconds), 0)          AS avg_call_duration_s,
        ROUND(AVG(num_contacts_this_campaign), 2)     AS avg_contacts_per_campaign,
        ROUND(AVG(euribor_3m_rate), 4)               AS avg_euribor_rate,
        ROUND(AVG(consumer_price_idx), 4)             AS avg_cpi
    FROM base
    GROUP BY 1, 2, 3, 4, 5, 6, 7, 8
)
SELECT * FROM aggregated
```

### `models/intermediate/int_customer_360.sql`

```sql
-- Joins risk profiles with campaign data using billing_zip as customer proxy.
-- This creates the unified "Customer 360" view.

WITH risk AS (
    SELECT
        billing_zip,
        card_network,
        ROUND(AVG(risk_z_score), 4)    AS avg_risk_z_score,
        MAX(risk_band)                  AS max_risk_band,   -- 'Critical' > 'High' > 'Medium' > 'Low'
        SUM(fraud_count)               AS total_fraud_events,
        SUM(total_transactions)        AS total_transactions,
        SUM(total_amt)                 AS total_transaction_value
    FROM {{ ref('int_customer_risk_profile') }}
    GROUP BY 1, 2
),
campaign AS (
    SELECT
        age_segment,
        contact_channel,
        SUM(total_contacts)           AS campaign_contacts,
        MAX(response_rate_pct)        AS best_response_rate,
        MAX(contact_channel)          AS preferred_campaign_channel
    FROM {{ ref('int_campaign_response') }}
    GROUP BY 1, 2
)
SELECT
    r.billing_zip,
    r.card_network,
    r.avg_risk_z_score,
    r.max_risk_band,
    r.total_fraud_events,
    r.total_transactions,
    r.total_transaction_value,
    CASE
        WHEN r.max_risk_band IN ('High', 'Critical') THEN 'Suppress — High Risk'
        WHEN r.max_risk_band = 'Medium'              THEN 'Standard Review'
        ELSE 'Campaign Eligible'
    END                                               AS campaign_eligibility,
    'young_adult'                                     AS age_segment,      -- simulated join proxy
    c.preferred_campaign_channel
FROM risk r
LEFT JOIN campaign c
    ON c.age_segment = 'Young Adult (25-34)'   -- simplified join for demo purposes
```

---

## 7. `dbt_project/macros/risk_band.sql`

```sql
-- macros/risk_band.sql
-- Reusable macro that converts a z-score into a risk band label.
-- Used in int_customer_risk_profile and anywhere else risk classification is needed.
-- Call: {{ risk_band('your_z_score_column') }}

{% macro risk_band(z_score_col) %}
    CASE
        WHEN {{ z_score_col }} > 3  THEN 'Critical'
        WHEN {{ z_score_col }} > 2  THEN 'High'
        WHEN {{ z_score_col }} > 1  THEN 'Medium'
        ELSE 'Low'
    END
{% endmacro %}
```

---

## 8. `chat/chat_with_data.py` — PandasAI (Secured)

```python
# chat/chat_with_data.py
"""
BankLens 2.0 — Natural Language Data Interface
Uses PandasAI 2.4.0 with OpenAI backend (NOT litellm - see security notes)
"""
import pandasai as pai
from pandasai_openai import OpenAI as PaiOpenAI
from google.cloud import bigquery
from dotenv import load_dotenv
import os
import re

load_dotenv()

# ── Security: query sanitization ─────────────────────────────────────
INJECTION_KEYWORDS = ['ignore previous', 'system prompt', 'forget all', 'jailbreak']
MAX_QUERY_LENGTH = 500

def safe_chat(query: str, *dfs):
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("Query too long (max 500 chars)")
    for kw in INJECTION_KEYWORDS:
        if kw.lower() in query.lower():
            raise ValueError(f"Query contains disallowed keyword: '{kw}'")
    return pai.chat(query, *dfs)

# ── LLM setup ─────────────────────────────────────────────────────────
llm = PaiOpenAI(api_token=os.getenv("OPENAI_API_KEY"))
pai.config.set({
    "llm": llm,
    "enable_cache": False,
    "save_charts": True,
    "save_charts_path": "ml/model_artifacts/charts/"
})

# ── Load mart data from BigQuery ──────────────────────────────────────
client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
PROJECT = os.getenv("GCP_PROJECT_ID")
MARTS = f"{PROJECT}.banklens_marts"

print("Loading mart tables from BigQuery...")
fraud_df    = client.query(f"SELECT * FROM `{MARTS}.mart_fraud_dashboard`").to_dataframe()
campaign_df = client.query(f"SELECT * FROM `{MARTS}.mart_campaign_performance`").to_dataframe()
c360_df     = client.query(f"SELECT * FROM `{MARTS}.mart_customer_360`").to_dataframe()
print(f"Loaded: fraud={len(fraud_df):,} rows, campaign={len(campaign_df):,} rows")

# ── Wrap in pai.DataFrame ─────────────────────────────────────────────
fraud_pai    = pai.DataFrame(fraud_df, name="fraud_dashboard",
                              description="Daily transaction metrics with fraud labels")
campaign_pai = pai.DataFrame(campaign_df, name="campaign_performance",
                              description="Campaign response analytics")
c360_pai     = pai.DataFrame(c360_df, name="customer_360",
                              description="Unified customer risk and campaign profile")

# ── Demo queries ──────────────────────────────────────────────────────
if __name__ == "__main__":
    demo_queries = [
        "What is the overall fraud rate as a percentage?",
        "Which age segment has the highest campaign response rate?",
        "Show me a bar chart of fraud rate by card network",
        "How many high-risk customers were contacted via telephone?",
        "What is the average call duration for cellular vs telephone campaigns?",
    ]
    
    for query in demo_queries:
        print(f"\n{'─'*60}")
        print(f"Query: {query}")
        print("─"*60)
        result = safe_chat(query, fraud_pai, campaign_pai, c360_pai)
        print(f"Answer: {result}")
```

---

## 9. `.gitignore` (Complete)

```
# Python
__pycache__/
*.py[cod]
*.pyo
.venv/
venv/
env/
*.egg-info/
dist/
build/
.pytest_cache/

# Secrets & credentials
.env
*.json
*.pem
*.key
*.p12

# Data (raw files — too large for git)
data/raw/
*.csv
*.parquet

# ML models
*.pkl
*.joblib
ml/model_artifacts/

# dbt
dbt_project/profiles.yml
dbt_project/target/
dbt_project/logs/
dbt_project/dbt_packages/

# Notebooks
.ipynb_checkpoints/

# OS
.DS_Store
Thumbs.db

# Docker
.docker/
```

---

*Backend Structure Doc — BankLens 1.0 | June 2026*
