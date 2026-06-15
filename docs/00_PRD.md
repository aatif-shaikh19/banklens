# BankLens — Product Requirements Document
**v1.0 | June 2026 | Full Scope: ML + Power BI + Snowflake + AI Layer + Data Engineering**

---

## 1. Executive Summary

BankLens is a governed banking analytics platform that bridges two systems banks keep dangerously separate — **transaction fraud/risk data** and **campaign performance data**. Built to demonstrate readiness for Data Analyst, Data Analytics Engineer, and BI roles at HSBC, JP Morgan, Barclays, and Big4.

### The Core Problem
A customer flagged as high-risk by the fraud team still receives a premium credit card offer because the marketing team's CRM has zero visibility into risk signals. BankLens unifies both in one governed pipeline. Query 5 in `sql/analytics.sql` — an anti-join that surfaces these customers — IS the business justification for the entire project.

---

## 2. Final Scope

| Layer | Tool | Status |
|---|---|---|
| **Ingestion (ETL)** | Python scripts → BigQuery (primary) | ✅ Build |
| **Data Engineering** | dbt Core staging → intermediate → marts | ✅ Build |
| **Data Quality** | Great Expectations 1.x | ✅ Build |
| **Orchestration** | Apache Airflow 3.2.2 via Docker | ✅ Build |
| **ML Model** | XGBoost 3.2.0 + SHAP (trained on Colab) | ✅ Build |
| **Scoring API** | FastAPI 0.136.3 + Pydantic | ✅ Build |
| **Primary BI** | Power BI Desktop (4 pages, DAX, Copilot) | ✅ Build — REQUIRED |
| **Secondary BI** | Looker Studio (3 pages, campaign analytics) | ✅ Build |
| **Secondary Warehouse** | Snowflake (regulatory data + Cortex Analyst) | ✅ Build |
| **AI Layer** | Snowflake Cortex Analyst + PandasAI 2.4 | ✅ Build |
| **CI/CD** | GitHub Actions | ✅ Build |

---

## 3. ML Workflow (Colab-Integrated)

The IEEE-CIS dataset (530 MB) is trained on **Google Colab** (free T4 GPU) to avoid requiring that file on the local machine during the FastAPI serving phase.

```
Local Machine                    Google Colab
─────────────                    ────────────
data/raw/                        /content/drive/
  train_transaction.csv   ──►    train_transaction.csv
  train_identity.csv      ──►    train_identity.csv
                                       │
                                       ▼
                                XGBoost training
                                SHAP analysis
                                evaluate.py
                                       │
                                       ▼
                                fraud_model_xgb.pkl
                                shap_summary.png
                                       │
                          Download │
                                   ▼
Local Machine: ml/model_artifacts/fraud_model_xgb.pkl
FastAPI serves predictions from this model locally
```

---

## 4. Target Employer Alignment

| Skill | Tool | Employer |
|---|---|---|
| Advanced SQL (window fns, CTEs, anti-joins) | BigQuery SQL | JP Morgan, Barclays |
| Cloud data warehouse | BigQuery + Snowflake | HSBC, All |
| Data transformation + lineage | dbt Core 1.11 | Barclays, Deloitte, KPMG |
| Data quality governance | Great Expectations 1.x | All BFSI |
| ML in finance | XGBoost + SHAP + FastAPI | All BFSI |
| Primary BI with DAX + AI | Power BI Copilot | HSBC, KPMG, Deloitte |
| Campaign analytics dashboard | Looker Studio | HSBC specifically |
| Pipeline orchestration | Airflow 3.x | All |
| NL querying | Snowflake Cortex Analyst | Forward-thinking teams |
| Python data engineering | pandas 3.0, ETL scripts | Everyone |

---

## 5. Functional Requirements

### FR-1: ETL (3 scripts, idempotent, env-var credentials)
- `etl/load_transactions.py` → IEEE-CIS (590K rows) → BigQuery `banklens_raw.transactions`
- `etl/load_campaigns.py` → UCI Bank Marketing (45K rows) → BigQuery `banklens_raw.campaigns`
- `etl/load_fdic.py` → FDIC API → Snowflake `BANKLENS_DB.RAW.regulatory`
- All scripts use `WRITE_TRUNCATE` (idempotent), chunked loading for large files

### FR-2: dbt Transformations (3 layers)
- staging/ → intermediate/ → marts/ pattern
- `dbt run && dbt test` must pass 0 failures
- `dbt docs generate` must produce browsable lineage graph

### FR-3: Great Expectations (data quality gates)
- GE 1.x (new Fluent API — not the 0.18.x API from old docs)
- transactions checkpoint: uniqueness, null checks, fraud rate 1–6%, risk band values
- campaigns checkpoint: subscribed in [0,1], channel in valid set
- Failure must halt pipeline

### FR-4: Airflow 3.2.2 DAG
- Schedule: every Monday 06:00 UTC
- Task order: fetch → dbt_run → dbt_test → ge_validate → refresh_powerbi
- Retries: 2, delay: 5 min, email on failure
- **Note: Airflow 3.x uses new syntax — no `schedule_interval`, different imports**

### FR-5: ML (trained on Colab, served locally)
- XGBoost 3.2.0, scale_pos_weight for 97:3 imbalance
- AUC-ROC ≥ 0.85 on test set
- SHAP summary plot saved as PNG
- FastAPI `/predict` returns probability + risk_band + recommendation

### FR-6: Power BI (non-negotiable)
- 4 pages: Executive Overview, Risk Intelligence, Customer 360, Regulatory Compliance
- All 8 DAX measures implemented
- Power BI Copilot AI summaries (requires 60-day Fabric trial)
- Connected to BigQuery mart tables

### FR-7: Looker Studio
- 3 pages connected to `mart_campaign_performance`
- Shareable public link in README

### FR-8: Snowflake + AI Layer
- FDIC regulatory data in Snowflake
- Cortex Analyst semantic model (`semantic_model.yaml`) answering 3+ NL queries
- PandasAI 2.4 with OpenAI backend (NOT litellm)

### FR-9: CI/CD
- GitHub Actions runs `dbt compile && dbt test` on every push to `main`
- Green CI badge on README

---

## 6. Success Criteria

**Project is done when:**
- [ ] `dbt run && dbt test` — 0 failures
- [ ] FastAPI `/predict` works at localhost:8000/docs
- [ ] Power BI file opens and loads data from BigQuery
- [ ] Looker Studio public link is live
- [ ] Airflow DAG shows green manual trigger
- [ ] Cortex Analyst answers 3 NL queries (screenshot)
- [ ] README has: architecture diagram, all dashboard screenshots, dbt lineage, SHAP plot, AUC score
- [ ] GitHub Actions CI is green
- [ ] AUC ≥ 0.85 printed in Colab training output

---

## 7. Timeline (4–6 focused days)

| Phase | Focus | Days |
|---|---|---|
| 0 | Environment, accounts, structure | Day 1 Morning |
| 1 | ETL → BigQuery + Snowflake | Day 1 Afternoon |
| 2 | dbt (staging → intermediate → marts) | Day 2 |
| 3 | GE quality gates + Airflow 3.x DAG | Day 2 Afternoon |
| 4 | Colab: train XGBoost + SHAP + FastAPI local | Day 3 |
| 5 | Power BI (4 pages, DAX, Copilot) | Day 4 |
| 6 | Looker Studio (3 pages) | Day 5 Morning |
| 7 | Snowflake Cortex Analyst + PandasAI | Day 5 Afternoon |
| 8 | README + CI + Screenshots + Push | Day 6 |

---

## 8. Non-Goals for v1

- Apache Airflow DAG (documented in docs/ — future scope for production scale-out; replaced in v1 by GitHub Actions scheduled workflow)
- Real-time streaming ingestion (batch ETL only in v1)
- Multi-tenant auth on FastAPI (single-user local serving only)

---

*PRD v1.0 — BankLens 1.0 | June 2026 | Full scope restored*
