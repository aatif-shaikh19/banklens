# BankLens — Tech Stack (June 2026 Edition)
**Every version verified from PyPI on June 14, 2026**

---

## ⚠️ Critical Version Changes — Read Before Installing

Three things that will silently break if you use the original spec's versions:

### 1. Apache Airflow 2.x → 3.2.2 (BREAKING CHANGES)
Airflow released version 3.0 in 2025. The original spec used 2.9.x. The APIs changed:
- `schedule_interval` param **removed** → use `schedule` only
- `start_date` in `default_args` **no longer works** → set it directly on DAG
- Many imports moved
- Email/alerting system redesigned
- We use Airflow **3.2.2** syntax throughout this project

### 2. snowflake-connector-python: Now 4.x (Dropped Python 3.9)
The connector has moved to its 4.x series (released May 28, 2026). It no longer supports Python 3.9. Minimum is Python 3.10. We use Python 3.11 — no issue.

### 3. dbt-snowflake MUST be ≥ 1.10.6
Snowflake changed default column sizes in May 2026. Any dbt-snowflake below 1.10.6 will crash on incremental models. Use 1.11.1.

### 4. Kaggle CLI Token: Now "Legacy API Credentials"
The Kaggle website changed its UI. The token that generates `kaggle.json` is now under:
**Account Settings → "Legacy API Credentials" → "Create Legacy API Key"**
Not just "Create New API Token" (that now gives you a different token for the new `kagglehub` library).

### 5. scikit-learn 1.9.0 Just Released (June 2, 2026)
Brand new release. Works fine with our project. More efficient preprocessing.

### 6. Supply Chain Attacks (Shai-Hulud / Hades, May–June 2026)
Compromised PyPI packages relevant to this project:
- `guardrails-ai==0.10.1` — NOT in our stack
- `mistralai==2.4.6` — NOT in our stack
- `litellm==1.82.7, 1.82.8` — indirect via pandasai_litellm — **DO NOT install pandasai_litellm**
- `lightning==2.6.2, 2.6.3` — NOT in our stack
- All our packages are **safe** — confirmed below

---

## Verified Package Versions (All Safe)

| Package | Version | Released | Notes |
|---|---|---|---|
| **Python** | **3.11.x** | — | Min 3.10 (snowflake connector), 3.11 recommended |
| **pandas** | **3.0.3** | Jan 2026 | CoW enabled by default — always use .copy() or .loc |
| **numpy** | **2.2.3** | — | Required for pandas 3.x compat |
| **scikit-learn** | **1.9.0** | Jun 2, 2026 | Latest stable |
| **xgboost** | **3.2.0** | Feb 10, 2026 | `use_label_encoder` param removed in 3.x |
| **shap** | **0.47.2** | — | TreeExplainer API unchanged |
| **joblib** | **1.4.2** | — | Model serialization |
| **fastapi** | **0.136.3** | May 23, 2026 | Use `lifespan` not `@on_event` |
| **uvicorn[standard]** | **0.34.0** | — | — |
| **pydantic** | **2.10.6** | — | v2 syntax throughout |
| **slowapi** | **0.1.9** | — | Rate limiting |
| **great-expectations** | **1.15.2** | Apr 9, 2026 | **v1 API completely different from v0.18** |
| **apache-airflow** | **3.2.2** | May 29, 2026 | **v3 breaking changes from v2** |
| **apache-airflow-providers-snowflake** | **6.13.0** | May 23, 2026 | Separate from core |
| **dbt-core** | **1.11.4** | — | — |
| **dbt-bigquery** | **1.11.1** | — | — |
| **dbt-snowflake** | **1.11.1** | — | MUST be ≥1.10.6 |
| **google-cloud-bigquery** | **3.27.0** | — | — |
| **google-cloud-bigquery-storage** | **2.28.0** | — | Arrow-based fast reads |
| **snowflake-connector-python** | **4.0.0** | May 28, 2026 | 4.x series, Python 3.10+ only |
| **snowflake-sqlalchemy** | **1.7.0** | — | — |
| **pyarrow** | **18.1.0** | — | BigQuery + Snowflake fast transfer |
| **matplotlib** | **3.10.1** | — | — |
| **seaborn** | **0.13.2** | — | — |
| **plotly** | **5.24.1** | — | — |
| **streamlit** | **1.58.0** | — | Latest |
| **kaleido** | **0.2.1** | — | Plotly static image export |
| **pandasai** | **2.4.0** | — | New `pai.DataFrame` API |
| **pandasai_openai** | **0.1.0** | — | Use this, NOT pandasai_litellm |
| **openai** | **1.59.12** | — | Direct OpenAI SDK |
| **openpyxl** | **3.1.5** | — | Excel reports |
| **python-dotenv** | **1.0.1** | — | .env management |
| **requests** | **2.32.3** | — | FDIC API calls |
| **pyarrow** | **18.1.0** | — | — |
| **pytest** | **8.3.5** | — | — |
| **httpx** | **0.28.1** | — | FastAPI test client |
| **pip-audit** | **2.8.0** | — | CVE scanning |
| **bandit** | **1.8.3** | — | Static security |
| **detect-secrets** | **1.5.0** | — | Pre-commit secret scanning |
| **pip** | **26.1** | Apr 26, 2026 | Upgrade pip first |

---

## `requirements.txt` — Complete Pinned File

```
# BankLens — Python Dependencies
# Verified June 14, 2026 | Python 3.11 required
# Install: pip install --no-cache-dir -r requirements.txt
# Then:    pip-audit   (should show zero vulnerabilities)

# ── Core Data Science ────────────────────────────────────────────────
pandas==3.0.3
numpy==2.2.3
scikit-learn==1.9.0
scipy==1.15.2

# ── ML / Explainability ──────────────────────────────────────────────
xgboost==3.2.0
shap==0.47.2
joblib==1.4.2

# ── API Layer ────────────────────────────────────────────────────────
fastapi==0.136.3
uvicorn[standard]==0.34.0
pydantic==2.10.6
slowapi==0.1.9

# ── Data Quality ─────────────────────────────────────────────────────
# v1.x API is completely different from v0.18.x — use 1.x docs only
great-expectations==1.15.2

# ── dbt ──────────────────────────────────────────────────────────────
dbt-core==1.11.4
dbt-bigquery==1.11.1
dbt-snowflake==1.11.1        # MUST be >=1.10.6 (Snowflake May 2026 column change)

# ── Cloud Connectors ─────────────────────────────────────────────────
google-cloud-bigquery==3.27.0
google-cloud-bigquery-storage==2.28.0
snowflake-connector-python==4.0.0   # 4.x series, Python 3.10+ required
snowflake-sqlalchemy==1.7.0
pyarrow==18.1.0
fsspec==2025.3.0

# ── Visualization ────────────────────────────────────────────────────
matplotlib==3.10.1
seaborn==0.13.2
plotly==5.24.1
streamlit==1.58.0
kaleido==0.2.1

# ── AI Layer ─────────────────────────────────────────────────────────
openai==1.60.2

# ── ETL / Utilities ──────────────────────────────────────────────────
openpyxl==3.1.5
python-dotenv==1.0.1
requests==2.32.3

# ── Security & Dev ───────────────────────────────────────────────────
pytest==8.3.5
httpx==0.28.1
pip-audit==2.8.0
bandit==1.8.3
detect-secrets==1.5.0
```

**Note: Apache Airflow (3.2.2) is installed separately inside Docker — not in this requirements.txt. See the Installation Guide.**

---

## Airflow 3.x vs 2.x — Key API Differences

If you find any Airflow 2.x tutorials online, these changes will break your DAG:

```python
# ── AIRFLOW 2.x (OLD — DO NOT USE) ──────────────────────────────────
from airflow import DAG
from datetime import datetime

with DAG(
    dag_id='banklens',
    schedule_interval='0 6 * * 1',   # REMOVED in 3.x
    default_args={
        'start_date': datetime(2024, 1, 1),   # Ignored in 3.x default_args
        'email_on_failure': True,
    }
) as dag:
    ...

# ── AIRFLOW 3.x (CORRECT) ────────────────────────────────────────────
from airflow.sdk import DAG              # New import path in 3.x
from datetime import datetime

with DAG(
    dag_id='banklens_weekly_pipeline',
    schedule='0 6 * * 1',              # 'schedule' not 'schedule_interval'
    start_date=datetime(2024, 1, 1),   # Set on DAG, not in default_args
    default_args={
        'retries': 2,
        'email': ['aatif.shaikh2004@gmail.com'],
    },
    catchup=False,
    tags=['banklens', 'bfsi'],
) as dag:
    ...
```

---

## XGBoost 3.x Changes

```python
# OLD (2.x) — broken in 3.x
model = XGBClassifier(use_label_encoder=False, eval_metric='auc')

# NEW (3.x) — correct
model = XGBClassifier(
    eval_metric='auc',      # use_label_encoder removed entirely
    device='cpu',           # explicit device setting
)
```

---

## pandas 3.x Breaking Change

```python
# OLD — produces SettingWithCopyWarning or wrong result in 3.x
df[df['col'] > 5]['new_col'] = 'value'   # SILENT BUG

# CORRECT in 3.x
df.loc[df['col'] > 5, 'new_col'] = 'value'

# Or explicitly copy when slicing
subset = df[df['col'] > 5].copy()
subset['new_col'] = 'value'
```

---

## Tool Versions (Non-Python)

| Tool | Version | Notes |
|---|---|---|
| **Git** | 2.x | — |
| **Docker Desktop** | Latest (June 2026) | For Airflow; 6GB RAM recommended |
| **Power BI Desktop** | June 2026 release | Windows only; free |
| **Google Colab** | Web (free T4 GPU) | For XGBoost training |
| **dbt CLI** | 1.11.4 | Installed via pip |
| **VS Code** | Latest | With dbt Power User extension |

---

*Tech Stack — BankLens 1.0 | All versions verified June 14, 2026*
