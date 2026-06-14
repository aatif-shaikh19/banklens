# BankLens — Phase-by-Phase Build Plan
**| Every step explained | All versions correct for June 2026**

---

## Phase 0 — Project Skeleton
**Duration: 2 hours | See Phase 0 Setup Chat Guide for Claude Code prompts**

Outputs: Directory structure, requirements.txt, .env.example, .gitignore, utility scripts, docs/, security hooks, first GitHub push.

Key teaching points:
- `__init__.py` makes folders importable as Python packages
- `.gitkeep` forces Git to track empty directories
- `WRITE_TRUNCATE` vs `WRITE_APPEND` — idempotency
- `--no-cache-dir` defends against poisoned pip cache (Shai-Hulud)

---

## Phase 1 — ETL: Load All 3 Datasets
**Duration: 3–4 hours**

### What You Build
Three Python scripts that move raw CSVs into BigQuery and Snowflake. These are your "data ingestion" layer — what every data engineering JD refers to when they say "build and maintain data pipelines."

### Key Concepts

**ETL vs ELT:**
- Old-school ETL: Transform data BEFORE loading (heavy Python preprocessing)
- Modern ELT: Load raw data first, transform inside the warehouse with SQL
- We do **ELT** — raw CSVs go straight to BigQuery, then dbt transforms them in-warehouse

**Idempotency:**
Running the same pipeline twice should produce the same result. We use `WRITE_TRUNCATE` in BigQuery (truncate then reload) instead of `WRITE_APPEND`. This way a second run produces exactly 590,540 rows — not 1,181,080.

**Chunked Loading:**
The IEEE-CIS file is 530MB. `pd.read_csv('file.csv')` would load all 530MB into RAM at once. With `chunksize=10_000`, we read 10,000 rows at a time, upload that chunk, then move to the next. The laptop only needs ~5MB of RAM per chunk instead of 530MB.

**pandas 3.x copy-on-write:**
Always use `.copy()` when slicing. `df[condition]['col'] = value` is a silent bug in pandas 3.x. Use `df.loc[condition, 'col'] = value` instead.

### Claude Code Prompt — Phase 1

```
We are building BankLens 2.0 Phase 1: ETL scripts.
Python 3.11, pandas 3.0.3, google-cloud-bigquery 3.27.0, snowflake-connector-python 4.0.0.
BigQuery sandbox is working. Snowflake trial is active.

Create the following 4 files with complete, production-ready content:

FILE 1: etl/load_transactions.py
Load IEEE-CIS fraud data to BigQuery.
- Files: data/raw/train_transaction.csv (530MB) + data/raw/train_identity.csv (65MB)
- Table: {GCP_PROJECT_ID}.banklens_raw.transactions
- Use chunked loading (chunksize=10_000) for memory safety
- LEFT JOIN identity on TransactionID (only 24% of transactions have identity rows)
- First chunk: WRITE_TRUNCATE. Subsequent chunks: WRITE_APPEND. (This makes it idempotent)
- Use pandas 3.x safe syntax: df.loc[condition, col] not df[condition][col]
- Log progress every 10 chunks
- Final verification: query COUNT(*) from BigQuery, assert it matches len(full_df)
- Wrap in run() function callable from run_all.py

FILE 2: etl/load_campaigns.py
Load UCI Bank Marketing to BigQuery.
- File: data/raw/bank-additional-full.csv (separator is semicolon, not comma!)
- Table: {GCP_PROJECT_ID}.banklens_raw.campaigns
- Rename columns with dots to underscores (SQL doesn't allow dots):
  emp.var.rate → emp_var_rate, cons.price.idx → cons_price_idx,
  cons.conf.idx → cons_conf_idx, nr.employed → nr_employed
- Validate: y column only contains 'yes'/'no' before loading
- Use WRITE_TRUNCATE
- Wrap in run() function

FILE 3: etl/load_fdic.py
Load FDIC regulatory data to Snowflake (NOT BigQuery — this goes to Snowflake).
- Source: FDIC public API at https://banks.data.fdic.gov/api/financials
- Fields: REPDTE,CERT,INSTNAME,ASSET,DEP,NETINC,INTINC,NONII,LNLSNET,NPERFV,TIER1RBC
- Paginate with limit=1000 until no more data
- Rename all columns to snake_case (see RENAME_MAP in backend structure doc)
- Add derived column npl_ratio_pct = (NPERFV / LNLSNET) * 100
- Add derived column rag_status: 'Red' if npl_ratio>5, 'Amber' if >2, else 'Green'
- Cache to data/raw/fdic_institutions.csv after first download
- Load to Snowflake using snowflake-connector-python 4.x + write_pandas
- Use snowflake.connector.pandas_tools.write_pandas for the upload
- Use snowflake-connector-python 4.0.0 connection syntax
- Truncate table before each load (idempotent)
- Wrap in run() function

FILE 4: etl/run_all.py
Master ETL runner that imports and calls run() from each script.
- Print ======= header before each step
- Time each step
- Print PASSED/FAILED summary at end
- Raise SystemExit if any step failed
- Usage: python etl/run_all.py

After creating all 4 files:
1. Run: wget "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip" -O data/raw/bank_marketing.zip
2. Run: cd data/raw && unzip -o bank_marketing.zip && cp bank-additional/bank-additional-full.csv bank-additional-full.csv && cd ../..
3. Run: python scripts/download_fdic.py
4. Run: python etl/run_all.py
5. Show the complete output
```

### Verify Phase 1 Done
```bash
# In BigQuery Console:
SELECT COUNT(*) FROM `your-project.banklens_raw.transactions`;  -- expect ~590540
SELECT COUNT(*) FROM `your-project.banklens_raw.campaigns`;     -- expect 45211
SELECT AVG(isFraud)*100 FROM `your-project.banklens_raw.transactions`;  -- expect ~3.5

# In Snowflake Worksheet:
SELECT COUNT(*) FROM BANKLENS_DB.RAW.REGULATORY;    -- expect ~10000
SELECT COUNT(CASE WHEN rag_status='Red' THEN 1 END) AS red_banks FROM BANKLENS_DB.RAW.REGULATORY;
```

Screenshot these results — they go in your README.

---

## Phase 2 — dbt: 3-Layer Transformation
**Duration: 4–5 hours**

### What You Build
A dbt project with staging → intermediate → marts transformations on top of BigQuery raw tables.

### Key Concepts

**Why dbt Exists:**
Without dbt, you'd write a Python script that reads from BigQuery, transforms the data, and writes back. This is fragile — if it fails halfway, you have partial data. dbt runs SQL transformations INSIDE BigQuery, tracks dependencies between models (if B depends on A, A runs first), generates documentation with lineage graphs, and runs built-in tests. Data engineering teams at HSBC, Barclays, and Deloitte all use dbt.

**The `{{ ref() }}` Pattern:**
Instead of hardcoding table names like `SELECT * FROM banklens_raw.transactions`, you use `{{ ref('stg_transactions') }}`. dbt resolves this to the correct full table name in any environment (dev, staging, prod). This is why dbt projects are environment-agnostic.

**Materialization:**
- `view` = no storage cost, runs fresh every query (staging + intermediate use this)
- `table` = stores results as a real table (marts use this — Power BI needs fast table reads)

### Claude Code Prompt — Phase 2

```
BankLens 2.0 Phase 2: dbt transformation pipeline.
dbt-core 1.11.4, dbt-bigquery 1.11.1.

Step 1: Initialize dbt project
Run shell: dbt init banklens_dbt --skip-profile-setup
Move into dbt_project/: mv banklens_dbt/* dbt_project/ && rm -rf banklens_dbt

Step 2: Create dbt_project/dbt_project.yml with:
name: 'banklens'
version: '2.0.0'
profile: 'banklens'
model-paths: ["models"]
test-paths: ["tests"]
macro-paths: ["macros"]
models:
  banklens:
    staging:
      +materialized: view
      +schema: staging
    intermediate:
      +materialized: view
      +schema: intermediate
    marts:
      +materialized: table
      +schema: marts

Step 3: Create dbt_project/profiles.yml.example with BigQuery service-account auth
(This is the example template — actual profiles.yml goes in dbt_project/ and is gitignored)

Step 4: Create dbt_project/packages.yml (already exists — leave it)

Step 5: Create models/staging/sources.yml declaring both raw tables

Step 6: Create all SQL models (copy from doc 07_BACKEND_STRUCTURE.md):
- models/staging/stg_transactions.sql
- models/staging/stg_campaigns.sql
- models/staging/stg_regulatory.sql (reads from Snowflake via dbt-snowflake)
- models/intermediate/int_customer_risk_profile.sql
- models/intermediate/int_campaign_response.sql
- models/intermediate/int_customer_360.sql
- models/marts/mart_fraud_dashboard.sql
- models/marts/mart_campaign_performance.sql
- models/marts/mart_customer_360.sql
- models/marts/mart_regulatory_summary.sql
- macros/risk_band.sql

Step 7: Create .yml files for each model with column docs and tests:
Each staging model needs: not_null and unique tests on primary keys
Each mart needs: not_null tests on key metrics

Step 8: Create dbt_project/profiles.yml (actual file — gitignored) from the example

Step 9: Run in sequence:
  dbt deps
  dbt debug --profiles-dir .
  dbt run --profiles-dir . --select staging
  dbt test --profiles-dir . --select staging
  dbt run --profiles-dir .
  dbt test --profiles-dir .
  dbt docs generate --profiles-dir .

Show me the output of each dbt command.
```

### Verify Phase 2 Done
- `dbt run` shows X models, 0 errors
- `dbt test` shows X tests, 0 failures
- `dbt docs generate` creates `target/` folder
- BigQuery shows `banklens_marts` dataset with all 4 mart tables
- **Screenshot the dbt lineage graph** from `dbt docs serve` → localhost:8080 → click "Lineage Graph" bottom right

---

## Phase 3 — Great Expectations + Airflow 3.2.2
**Duration: 2–3 hours**

### Great Expectations 1.x (New API)
GE 1.x is completely different from 0.18.x. The old Batch Request / DataContext API is gone. We use the new Fluent Data Sources API.

### Airflow 3.2.2 (Breaking Changes from 2.x)
Key changes you must know:
- Import: `from airflow.sdk import DAG` (not `from airflow import DAG`)
- `schedule_interval` parameter **removed** → use `schedule='0 6 * * 1'`
- `start_date` must be set directly on DAG, not in `default_args`
- The Docker Compose file for Airflow 3.x is different from 2.x

### Claude Code Prompt — Phase 3

```
BankLens 2.0 Phase 3: Data quality + Orchestration.
great-expectations 1.15.2 (v1 Fluent API), apache-airflow 3.2.2.

Part A — Great Expectations:

Create great_expectations/checkpoints/transactions_checkpoint.py using GE 1.x API:
- context = gx.get_context(mode="file", project_root_dir="great_expectations")
- Add Pandas data source reading from data/sample/sample_transactions.csv
- Add expectations: column_exists, not_null (transaction_id, transaction_amt),
  unique (transaction_id), between for amt (0.01-50000), between for isFraud (0,1),
  mean_between for isFraud (0.01-0.06), values_in_set for risk_band
- Run checkpoint, raise RuntimeError if any fail
- Wrap in run() function

Create great_expectations/checkpoints/campaigns_checkpoint.py similarly for campaigns.

Part B — Airflow 3.2.2:

Download Airflow 3.2.2 Docker Compose:
Run shell: curl -LfO 'https://airflow.apache.org/docs/apache-airflow/3.2.2/docker-compose.yaml'

Create airflow/dags/banklens_pipeline.py using AIRFLOW 3.x SYNTAX:
- Import: from airflow.sdk import DAG  (Airflow 3.x import)
- Use: schedule='0 6 * * 1'  (NOT schedule_interval — removed in 3.x)
- Set start_date directly on DAG (not in default_args)
- Tasks: fetch_transactions, fetch_campaigns, fetch_fdic (parallel),
  then dbt_run, dbt_test, ge_validate, refresh_powerbi_stub
- Email on failure using default_args email list
- All fetchers import from etl.load_* modules

Create .env.airflow with: AIRFLOW_UID=1000

Part C — Run Airflow:
mkdir -p airflow/logs airflow/plugins airflow/config
Run: docker compose --env-file .env.airflow up airflow-init
Run: docker compose --env-file .env.airflow up -d
Wait 60 seconds, then: docker compose ps

Open http://localhost:8080 (login: airflow / airflow)
Screenshot the DAG list showing banklens_weekly_pipeline.
```

---

## Phase 4 — Google Colab: Train XGBoost + SHAP, Then FastAPI Local
**Duration: 3–4 hours**

### Why Colab for Training?
The IEEE-CIS dataset is 530MB. Training XGBoost on 590K rows with 394 features takes ~15 minutes on a laptop CPU. On Colab's free T4 GPU it takes ~3 minutes. More importantly, you don't need to keep the 530MB file on your laptop after training — just the 20MB `.pkl` model file.

### Google Colab Notebook Setup

Create a new notebook at **colab.research.google.com**. Change runtime:
**Runtime → Change runtime type → T4 GPU → Save**

**Paste this as the first cell:**
```python
# Cell 1: Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Verify your files are there
import os
files = os.listdir('/content/drive/MyDrive/BankLens/')
print(files)
# Should show: train_transaction.csv, train_identity.csv
```

### Claude Code Prompt — Phase 4 (Colab Notebook)

```
Create a Google Colab notebook file: notebooks/banklens_fraud_model_colab.ipynb

This notebook trains the BankLens 2.0 XGBoost fraud model.
It will be run on Google Colab with T4 GPU (free tier).
Use xgboost 3.2.0 syntax (use_label_encoder removed, device='cpu').
Use scikit-learn 1.9.0 (latest June 2026).
Use pandas 3.0.3 (use .loc for all assignments, not chained indexing).

The notebook should have these cells in order:

Cell 1 — Mount Drive and verify files:
from google.colab import drive
drive.mount('/content/drive')
# List files in /content/drive/MyDrive/BankLens/

Cell 2 — Install packages:
!pip install xgboost==3.2.0 shap==0.47.2 scikit-learn==1.9.0 pandas==3.0.3 numpy==2.2.3

Cell 3 — Load data with chunked reading:
Load train_transaction.csv from Drive in chunks, join with train_identity.csv.
Use chunksize=10_000 for memory safety. Print shape and fraud rate.

Cell 4 — Feature engineering:
Select FEATURES = ['TransactionAmt', 'ProductCD', 'card4', 'card6',
                   'C1', 'C6', 'C13', 'D1', 'D15', 'V258', 'V201']
Encode categoricals with LabelEncoder (ProductCD, card4, card6)
Fill NaN with -999 (XGBoost handles this well)
train_test_split with stratify=y, test_size=0.2, random_state=42

Cell 5 — Train XGBoost 3.2.0:
Calculate scale_pos_weight = non_fraud_count / fraud_count
XGBClassifier with n_estimators=500, max_depth=6, learning_rate=0.05,
scale_pos_weight=ratio, subsample=0.8, colsample_bytree=0.8,
eval_metric='auc', early_stopping_rounds=50, device='cpu', n_jobs=-1
fit with eval_set=[(X_test, y_test)], verbose=100

Cell 6 — Evaluate:
roc_auc_score, classification_report
Print final AUC prominently with print(f"FINAL AUC-ROC: {auc:.4f}")
Assert auc >= 0.85 (will warn if below)

Cell 7 — SHAP analysis:
shap.TreeExplainer(model) on X_test[:500]
Generate summary_plot (bar type), save to /content/shap_summary.png
Show the plot in the notebook

Cell 8 — Save model:
import joblib
joblib.dump(model, '/content/drive/MyDrive/BankLens/fraud_model_xgb.pkl')
print("Model saved to Drive. Download it and put in ml/model_artifacts/")

Cell 9 — Download files to local:
from google.colab import files
files.download('/content/shap_summary.png')
files.download('/content/drive/MyDrive/BankLens/fraud_model_xgb.pkl')
print("Downloaded! Put these in ml/model_artifacts/")
```

**After running the notebook:**
1. Download `fraud_model_xgb.pkl` → move to `ml/model_artifacts/fraud_model_xgb.pkl`
2. Download `shap_summary.png` → move to `ml/model_artifacts/shap_summary.png`
3. Screenshot the final AUC output — goes in your README

### Claude Code Prompt — FastAPI (Local)

```
BankLens 2.0: Create the FastAPI fraud scoring API.
FastAPI 0.136.3, Pydantic 2.10.6, slowapi 0.1.9.

Create api/main.py with:
- lifespan context manager (NOT @app.on_event — removed in FastAPI 0.115+)
  loads ml/model_artifacts/fraud_model_xgb.pkl at startup
  raises RuntimeError if model file not found
- CORSMiddleware: allow localhost:3000 and localhost:8501
- TrustedHostMiddleware: localhost and 127.0.0.1
- Security headers middleware: X-Content-Type-Options, X-Frame-Options, Cache-Control
- Request logging middleware: log method, path, status code, duration
- Rate limiting with slowapi: 60 requests/minute on /predict
- /predict POST endpoint with full Pydantic validation (all 11 features)
  Returns fraud_probability, risk_band, recommendation, model_version
  Thresholds: >0.8=Critical/Block, >0.5=High/Step-up-auth, >0.2=Medium/Flag, else Low/Approve
- /health GET endpoint returning status, model loaded bool, version

Create api/schemas.py with:
- TransactionInput model with Field validators (ranges, descriptions, example values)
- FraudPrediction output model
- HealthResponse model

Create api/test_api.py with pytest tests using httpx:
- Test /health returns 200 and model_loaded=True
- Test /predict with valid input returns expected risk_band
- Test /predict with invalid input (negative amount) returns 422

After creating files, run:
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
(Note: only works if ml/model_artifacts/fraud_model_xgb.pkl exists from Colab)

Show me the startup logs.
```

---

## Phase 5 — Power BI Dashboard (Required)
**Duration: 4–5 hours | Windows only**

### Connect to BigQuery
1. Open Power BI Desktop
2. **Home → Get Data → Google BigQuery**
3. Sign in with the same Gmail as your GCP account
4. Select project `banklens-2` → dataset `banklens_marts`
5. Import: `mart_fraud_dashboard`, `mart_campaign_performance`, `mart_customer_360`, `mart_regulatory_summary`
6. Click **Load**

### Model Relationships
- `mart_fraud_dashboard[txn_date]` → `mart_regulatory_summary[report_date]` (many-to-one)
- `mart_fraud_dashboard[risk_band]` → `mart_customer_360[max_risk_band]` (many-to-many)

### DAX Measures (Create These First)
```dax
Total Transactions = SUM(mart_fraud_dashboard[total_transactions])

Fraud Rate % = DIVIDE(
    SUM(mart_fraud_dashboard[fraud_count]),
    SUM(mart_fraud_dashboard[total_transactions]), 0) * 100

Total Volume = SUM(mart_fraud_dashboard[total_volume])

Campaign Response Rate = DIVIDE(
    SUM(mart_campaign_performance[total_subscribed]),
    SUM(mart_campaign_performance[total_contacts]), 0) * 100

YoY Volume Change % =
VAR cy = SUM(mart_fraud_dashboard[total_volume])
VAR py = CALCULATE(SUM(mart_fraud_dashboard[total_volume]),
         DATEADD(mart_fraud_dashboard[txn_date], -1, YEAR))
RETURN DIVIDE(cy - py, py, 0) * 100

MoM Fraud Rate Change =
VAR cm = [Fraud Rate %]
VAR pm = CALCULATE([Fraud Rate %],
         DATEADD(mart_fraud_dashboard[txn_date], -1, MONTH))
RETURN cm - pm

Risk Band Color = SWITCH(SELECTEDVALUE(mart_fraud_dashboard[risk_band]),
    "Critical", "#E24B4A", "High", "#EF9F27",
    "Medium", "#378ADD", "Low", "#1D9E75", "#888780")

High Risk Flag = IF([Fraud Rate %] > 5, "⚠️ Above Threshold", "✓ Within Limit")
```

### 4 Pages
- **Page 1 — Executive Overview**: KPI cards (4), monthly volume line chart, product bar, risk donut, Copilot shortcut
- **Page 2 — Risk Intelligence**: Fraud matrix (card_network × risk_band), scatter volume vs fraud, top zips bar, rolling fraud line, slicers
- **Page 3 — Customer 360**: Campaign eligibility table, response rate stacked bar with risk overlay, high-risk subscribers KPI (Query 5 result)
- **Page 4 — Regulatory Compliance**: Capital adequacy KPIs, NPL ratio trend, institution table with RAG status

**Screenshot each page at 1440×900.** These are your primary portfolio artifacts.

---

## Phase 6 — Looker Studio (3 Pages)
**Duration: 2 hours**

1. Go to **lookerstudio.google.com**
2. Create → Report → Connect to Data → BigQuery
3. Select: `banklens-2` → `banklens_marts` → `mart_campaign_performance`
4. Build 3 pages (campaign overview, customer response, performance tiers)
5. Publish → get shareable link → add to README

---

## Phase 7 — Snowflake Cortex Analyst + PandasAI
**Duration: 2–3 hours**

### Cortex Analyst
```sql
-- Upload semantic_model.yaml to Snowflake stage
CREATE STAGE IF NOT EXISTS BANKLENS_DB.RAW.banklens_stage;
-- Then in Snowflake UI: Database → RAW → Stages → Upload semantic_model.yaml
```

Test these NL queries in Cortex Analyst UI (Snowflake console → left nav → Cortex Analyst):
- "What is the average NPL ratio for Red-status institutions?"
- "Show me institutions with Tier 1 capital ratio below 10%"
- "Which state has the most institutions with negative net income?"

Screenshot the responses — they demonstrate AI-native SQL querying.

### PandasAI
```bash
# With .venv active:
python chat/chat_with_data.py
# Screenshot the output — shows NL questions getting answered from BigQuery data
```

---

## Phase 8 — README + CI + Screenshots
**Duration: 2 hours**

### Claude Code Prompt — Phase 8
```
BankLens 2.0 Phase 8: README and CI.

1. Update .github/workflows/dbt_ci.yml:
   - Pin ALL GitHub Actions to SHA hashes (not floating tags)
   - Use dbt-core 1.11.4 and dbt-bigquery 1.11.1
   - Add pip-audit --strict step before dbt runs
   - Add permissions: contents: read  (minimal permissions — Shai-Hulud defense)

2. Create a comprehensive README.md in the repo root with:
   - Project title and tagline
   - Problem statement (the campaign/risk gap)
   - Architecture diagram (ASCII or description)
   - Tech stack table
   - Sections: Datasets, ETL, dbt Transformation, ML Model, Dashboards, AI Layer, CI/CD
   - Placeholders for screenshots (we'll fill in after screenshots are taken)
   - Key results placeholders: AUC score, high-risk customers found, best campaign channel
   - dbt lineage graph placeholder
   - SHAP summary plot placeholder
   - Power BI screenshot placeholder
   - Looker Studio public link placeholder
   - Setup instructions (git clone, pip install, dbt run, uvicorn)

3. Run: git add . && git status
   Show me what files are staged.
   Then: git commit -m "Phase 8: README, CI, complete project"
   Then: git push origin main
```

---

*Build Phases — BankLens 1.0 | June 2026 | All versions correct*
