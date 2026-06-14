# BankLens — Installation Guide
**| What to install on your laptop | June 2026**

---

## Storage Requirement

| Component | Space Needed |
|---|---|
| Python virtual environment (all packages) | 5–6 GB |
| Docker Desktop | 2.5 GB |
| Airflow Docker images (4 images pulled) | 4–5 GB |
| IEEE-CIS dataset (train files) | 600 MB |
| UCI + FDIC + OpenML fraud data | 35 MB |
| Trained XGBoost model (.pkl) | ~20 MB |
| Power BI Desktop | 500 MB |
| dbt artifacts + GE docs | 150 MB |

### **Minimum: 15 GB free | Recommended: 20 GB free**

Check your free space now:
```bash
# Linux/WSL
df -h ~

# Windows PowerShell
Get-PSDrive C | Select-Object Used, Free
```

---

## Part 1: Python 3.11

We use Python **3.11** specifically. snowflake-connector-python 4.x requires Python **3.10+**, and 3.11 is the sweet spot for all package compatibility in June 2026.

```bash
# Check if you have it
python3.11 --version
# If this prints Python 3.11.x — skip the install below

# Install on Ubuntu/WSL (if not already installed)
sudo add-apt-repository ppa:deadsnakes/ppa -y
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev python3.11-distutils -y
python3.11 --version   # confirm it worked
```

---

## Part 2: Git Configuration

```bash
git --version          # should already be installed
git config --global user.name "Aatif Shaikh"
git config --global user.email "aatif.shaikh2004@gmail.com"
```

---

## Part 3: Docker Desktop (for Airflow 3.x)

Airflow 3.2.2 runs inside Docker — easiest approach for a laptop.

- Download: **docker.com/products/docker-desktop**
- Install, open Docker Desktop
- Go to: **Settings → Resources → Memory → set to 6144 MB** (if 16GB RAM) or **4096 MB** (if 8GB RAM)
- On Windows: Docker requires WSL 2 — Docker Desktop will prompt you to set this up

```bash
# Verify after install
docker --version           # Docker 27.x or higher
docker compose version     # Compose v2.x — must be v2, not v1
```

---

## Part 4: Kaggle Dataset Download

For the IEEE-CIS dataset, **do this manually in the browser** — no CLI needed.

1. Sign in to **kaggle.com**
2. Go to: **kaggle.com/competitions/ieee-fraud-detection/data**
3. Accept the competition rules
4. Click **"Download All"** — this downloads `ieee-fraud-detection.zip` (~220MB)
5. Unzip it — you need `train_transaction.csv` (530MB) and `train_identity.csv` (65MB)

If you want the Kaggle CLI for other things:
1. Go to **kaggle.com → Profile → Settings → API**
2. Under **"Legacy API Credentials"** → click **"Create Legacy API Key"**
3. This downloads `kaggle.json` — the newer "Create New API Token" button is for `kagglehub`, a different library
```bash
mkdir -p ~/.kaggle
mv ~/Downloads/kaggle.json ~/.kaggle/
chmod 600 ~/.kaggle/kaggle.json
pip install kaggle    # CLI version
kaggle --version      # confirms it works
```

---

## Part 5: Cloud Accounts

### 5.1 GCP (BigQuery — Primary Warehouse)

1. **console.cloud.google.com** → sign in with Gmail
2. Project already created (`banklens-2` from earlier)
3. BigQuery Sandbox is active (10 GB free/month, no billing required)
4. Enable APIs: search for "BigQuery API" → Enable, "BigQuery Storage API" → Enable

**Service Account Setup (do once):**
```
IAM & Admin → Service Accounts → + Create Service Account
  Name: banklens-service
  Roles: BigQuery Data Editor + BigQuery Job User + BigQuery Read Session User
  Keys tab → Add Key → JSON → Download
Move key file: mkdir -p ~/.config/banklens && mv ~/Downloads/banklens-2-*.json ~/.config/banklens/service_account.json
chmod 600 ~/.config/banklens/service_account.json
```

### 5.2 Snowflake (Secondary Warehouse + Cortex Analyst)

1. **signup.snowflake.com** → Enterprise, AWS, US East (N. Virginia)
2. Verify email → log in
3. Note your **Account Identifier** from the URL or welcome email (format: `xy12345.us-east-1`)
4. **30-day clock starts now — complete Snowflake phases in Week 1**

**First-time SQL setup** (paste in Snowflake Worksheet):
```sql
-- Run as ACCOUNTADMIN
CREATE DATABASE IF NOT EXISTS BANKLENS_DB;
CREATE SCHEMA IF NOT EXISTS BANKLENS_DB.RAW;
CREATE SCHEMA IF NOT EXISTS BANKLENS_DB.MARTS;

CREATE ROLE IF NOT EXISTS BANKLENS_ROLE;
CREATE USER IF NOT EXISTS banklens_service
    PASSWORD = 'YourStrongPassword123!'
    DEFAULT_ROLE = BANKLENS_ROLE
    DEFAULT_WAREHOUSE = COMPUTE_WH;

GRANT USAGE ON DATABASE BANKLENS_DB TO ROLE BANKLENS_ROLE;
GRANT USAGE ON SCHEMA BANKLENS_DB.RAW TO ROLE BANKLENS_ROLE;
GRANT USAGE ON SCHEMA BANKLENS_DB.MARTS TO ROLE BANKLENS_ROLE;
GRANT CREATE TABLE ON SCHEMA BANKLENS_DB.RAW TO ROLE BANKLENS_ROLE;
GRANT CREATE TABLE ON SCHEMA BANKLENS_DB.MARTS TO ROLE BANKLENS_ROLE;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA BANKLENS_DB.RAW TO ROLE BANKLENS_ROLE;
GRANT ROLE BANKLENS_ROLE TO USER banklens_service;
GRANT ROLE BANKLENS_ROLE TO USER <your-snowflake-username>;

-- Auto-suspend warehouse to save trial credits
ALTER WAREHOUSE COMPUTE_WH SET AUTO_SUSPEND = 60;
```

### 5.3 OpenAI (for PandasAI)
- **platform.openai.com** → Add billing ($5 minimum → will cost <$0.10 for this project)
- API Keys → Create new secret key → save in `.env` as `OPENAI_API_KEY`
- **Optional**: skip if not doing the PandasAI layer. Snowflake Cortex Analyst is free.

### 5.4 Google Colab (for XGBoost training)
- No install needed — browser-based at **colab.research.google.com**
- Uses your Gmail account (same as GCP)
- Free T4 GPU — change runtime: Runtime → Change runtime type → T4 GPU
- Upload IEEE-CIS files to Google Drive first (see Datasets Guide)

### 5.5 Power BI Desktop
- Download: **microsoft.com/en-us/power-bi/desktop** or via Microsoft Store
- **Windows only** — ~500MB
- For Copilot AI features: sign up for **Microsoft Fabric free trial** at **app.fabric.microsoft.com** (60 days free)
- No account needed for just the Desktop version

---

## Part 6: Python Environment Setup

```bash
# Navigate to your cloned repo
cd banklens-2.0

# Create environment with Python 3.11 specifically
python3.11 -m venv .venv

# Activate
source .venv/bin/activate        # Linux/Mac/WSL
# .venv\Scripts\activate         # Windows PowerShell

# Verify you're in the right Python
python --version    # Must show Python 3.11.x
which python        # Must point to .venv

# Upgrade pip to latest (26.1 as of June 2026)
pip install --upgrade pip

# Install all packages — no cache for supply chain safety
pip install --no-cache-dir -r requirements.txt
# This takes 5–10 minutes

# Audit for known CVEs
pip install pip-audit
pip-audit
# Expected: "No known vulnerabilities found"
```

---

## Part 7: Environment File

```bash
cp .env.example .env
# Edit with your actual values:
nano .env   # or: code .env
```

Fill these in `.env`:
```bash
# GCP
GCP_PROJECT_ID=banklens-2-XXXXXX              # from GCP Console top bar
GCP_DATASET_RAW=banklens_raw
GCP_DATASET_MARTS=banklens_marts
GOOGLE_APPLICATION_CREDENTIALS=/home/aatif/.config/banklens/service_account.json

# Snowflake
SNOWFLAKE_ACCOUNT=xy12345.us-east-1           # from welcome email
SNOWFLAKE_USER=banklens_service
SNOWFLAKE_PASSWORD=YourStrongPassword123!
SNOWFLAKE_DATABASE=BANKLENS_DB
SNOWFLAKE_SCHEMA=RAW
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# OpenAI (optional — for PandasAI)
OPENAI_API_KEY=sk-...

# Airflow email alerts
SMTP_EMAIL=aatif.shaikh2004@gmail.com
SMTP_PASSWORD=your-16-char-gmail-app-password

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
MODEL_PATH=ml/model_artifacts/fraud_model_xgb.pkl
```

---

## Complete Checklist Before Phase 1

```
TOOLS
[ ] python3.11 --version → shows 3.11.x
[ ] git config shows your name and email
[ ] Docker Desktop is running (docker ps works)
[ ] .venv is active (python --version shows 3.11)
[ ] pip-audit shows no vulnerabilities

DATASETS
[ ] data/raw/train_transaction.csv exists (530 MB)
[ ] data/raw/train_identity.csv exists (65 MB)
[ ] data/raw/bank-additional-full.csv exists (5 MB — downloaded by Claude Code Prompt 1)
[ ] python scripts/download_fdic.py succeeded

CLOUD
[ ] GCP BigQuery sandbox accessible (test: BigQuery Console → Run a query)
[ ] Service account JSON at ~/.config/banklens/service_account.json
[ ] .env filled in with GCP_PROJECT_ID and GOOGLE_APPLICATION_CREDENTIALS
[ ] Snowflake account created, SQL setup run, banklens_service user exists
[ ] Snowflake .env vars filled in (SNOWFLAKE_ACCOUNT, USER, PASSWORD...)

SECURITY
[ ] .env does NOT appear in git status
[ ] git check-ignore -v .env → shows .gitignore is hiding it
[ ] *.json in .gitignore (protects service account)
[ ] pre-commit hook installed and tested

GOOGLE DRIVE (for Colab ML training)
[ ] train_transaction.csv uploaded to Drive → BankLens/ folder
[ ] train_identity.csv uploaded to Drive → BankLens/ folder
```

---

*Installation Guide — BankLens 1.0 | June 2026*
