# BankLens — Security Architecture Document
**June 2026 Edition | Hardened against Shai-Hulud, Hades, and supply chain threats**

---

## 1. Threat Model

BankLens handles real financial data (IEEE-CIS contains real fraud patterns, FDIC is real regulatory data). Even as a portfolio project, treating it with production-grade security demonstrates maturity to hiring managers at HSBC, Barclays, and JP Morgan.

### Assets to Protect
| Asset | Sensitivity | Location |
|---|---|---|
| GCP Service Account JSON key | **CRITICAL** | Local disk only, never in git |
| Snowflake credentials | **CRITICAL** | `.env` file only, never in git |
| OpenAI API key | **HIGH** | `.env` file only |
| BigQuery data (590K transactions) | **HIGH** | GCP project (not public) |
| Trained XGBoost model (.pkl) | **MEDIUM** | Local, gitignored |
| Dashboard screenshots | **LOW** | Public (README) |

### Threat Actors (June 2026)
1. **TeamPCP / Shai-Hulud worm**: Steals cloud credentials from CI/CD pipelines and developer environments. Active and evolving.
2. **Dependency confusion attacks**: Malicious packages with names similar to private packages uploaded to PyPI.
3. **Secret scanning bots**: Automatically scan GitHub for committed API keys.
4. **Prompt injection via LLM queries**: Malicious data in BigQuery tables could attempt to manipulate PandasAI or Cortex Analyst.

---

## 2. Credential Security

### Rule 1: Never put secrets in code. Period.

```bash
# .gitignore — these MUST be present
.env
*.json          # catches service account JSON
*.pkl           # catches trained models (could be adversarially modified)
data/raw/       # real data stays local
*.pem
*.key
```

### .env Template (`.env.example` — safe to commit)
```bash
# GCP
GCP_PROJECT_ID=your-gcp-project-id
GCP_DATASET_RAW=banklens_raw
GCP_DATASET_MARTS=banklens_marts
GOOGLE_APPLICATION_CREDENTIALS=path/to/service_account.json

# Snowflake
SNOWFLAKE_ACCOUNT=your-account.region
SNOWFLAKE_USER=your_user
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_DATABASE=BANKLENS_DB
SNOWFLAKE_SCHEMA=RAW
SNOWFLAKE_WAREHOUSE=COMPUTE_WH

# OpenAI (for PandasAI)
OPENAI_API_KEY=sk-...

# Email (for Airflow alerts)
SMTP_EMAIL=aatif.shaikh2004@gmail.com
SMTP_PASSWORD=your-app-password

# FastAPI
API_HOST=0.0.0.0
API_PORT=8000
API_SECRET_KEY=generate-a-random-32-char-string-here

# Limits
MAX_REQUESTS_PER_MINUTE=60
```

### Secret Generation (Do This)
```bash
# Generate a cryptographically random API_SECRET_KEY
python3 -c "import secrets; print(secrets.token_hex(32))"

# Add to .env immediately, never commit
```

---

## 3. GCP Security Hardening

### Service Account — Principle of Least Privilege
When creating your service account in GCP, grant ONLY these roles:

```
Roles to grant:
✅ BigQuery Data Editor         (banklens_raw + banklens_marts datasets only)
✅ BigQuery Job User            (run queries)
✅ BigQuery Read Session User   (for fast reads via Storage API)

Roles to NEVER grant to the service account:
❌ Project Owner
❌ Editor  
❌ BigQuery Admin
❌ Storage Admin
```

**How to restrict to specific datasets (not the whole project):**
```bash
# BigQuery dataset-level IAM — in Cloud Console:
# BigQuery → banklens_raw dataset → Share → Add Principal
# Principal: your-sa@your-project.iam.gserviceaccount.com
# Role: BigQuery Data Editor (dataset-scoped)
# Repeat for banklens_marts
```

### Service Account JSON Key Security
```bash
# Store service account JSON outside the repo
mkdir -p ~/.config/banklens/
mv downloaded-key.json ~/.config/banklens/service_account.json
chmod 600 ~/.config/banklens/service_account.json

# In .env:
GOOGLE_APPLICATION_CREDENTIALS=/home/aatif/.config/banklens/service_account.json
# (use absolute path)
```

### BigQuery Dataset Access Controls
```sql
-- Run in BigQuery after creating datasets
-- Restrict public access — ensure "Make Public" is OFF for both datasets
-- In Console: BigQuery → Dataset → Sharing → Dataset Permissions
-- Remove: allUsers, allAuthenticatedUsers
-- Keep: Only your service account + your personal GCP account
```

---

## 4. Snowflake Security

### Create Dedicated User and Role (Not Account Admin)
```sql
-- In Snowflake Worksheet — run as ACCOUNTADMIN

-- 1. Create a dedicated role
CREATE ROLE BANKLENS_ROLE;

-- 2. Create a dedicated user (NOT your admin user)
CREATE USER banklens_service
    PASSWORD = 'use-a-strong-password-here'
    DEFAULT_ROLE = BANKLENS_ROLE
    DEFAULT_WAREHOUSE = COMPUTE_WH
    DEFAULT_NAMESPACE = BANKLENS_DB.RAW;

-- 3. Grant minimal privileges
GRANT USAGE ON DATABASE BANKLENS_DB TO ROLE BANKLENS_ROLE;
GRANT USAGE ON SCHEMA BANKLENS_DB.RAW TO ROLE BANKLENS_ROLE;
GRANT CREATE TABLE ON SCHEMA BANKLENS_DB.RAW TO ROLE BANKLENS_ROLE;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA BANKLENS_DB.RAW 
    TO ROLE BANKLENS_ROLE;
GRANT ROLE BANKLENS_ROLE TO USER banklens_service;

-- 4. Grant role to yourself for dbt access
GRANT ROLE BANKLENS_ROLE TO USER <your-snowflake-username>;
```

---

## 5. FastAPI Security Layer

### Complete Secured `api/main.py`
```python
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from pydantic import BaseModel, Field, field_validator
from contextlib import asynccontextmanager
import joblib
import numpy as np
import logging
import time
import os

# ── Logging ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s'
)
logger = logging.getLogger(__name__)

# ── Rate Limiting ────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

# ── Model Lifecycle ──────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Load model at startup, clean up at shutdown."""
    model_path = os.getenv("MODEL_PATH", "ml/model_artifacts/fraud_model_xgb.pkl")
    if not os.path.exists(model_path):
        raise RuntimeError(f"Model not found at {model_path}")
    app.state.model = joblib.load(model_path)
    logger.info("Fraud scoring model loaded successfully")
    yield
    del app.state.model
    logger.info("Model unloaded")

# ── App Setup ────────────────────────────────────────────────────────
app = FastAPI(
    title="BankLens 2.0 — Fraud Scoring API",
    version="2.0.0",
    description="XGBoost-based transaction fraud probability scorer",
    docs_url="/docs",         # Swagger UI
    redoc_url="/redoc",       # ReDoc UI
    lifespan=lifespan
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Middleware ───────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # Streamlit
    allow_credentials=False,
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type", "Authorization"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.onrender.com"]
)

# ── Security Headers Middleware ───────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000"
    response.headers["Cache-Control"] = "no-store"
    return response

# ── Request Logging Middleware ────────────────────────────────────────
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = round((time.time() - start) * 1000, 2)
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration}ms)")
    return response

# ── Input Schemas ─────────────────────────────────────────────────────
class TransactionInput(BaseModel):
    TransactionAmt: float = Field(..., gt=0, le=50000, description="Transaction amount in USD")
    ProductCD:      int   = Field(..., ge=0, le=4, description="Product code (encoded 0-4)")
    card4:          int   = Field(..., ge=0, le=3, description="Card network (encoded)")
    card6:          int   = Field(..., ge=0, le=1, description="Card type (encoded)")
    C1:             float = Field(..., ge=0, description="Count feature 1")
    C6:             float = Field(..., ge=0, description="Count feature 6")
    C13:            float = Field(..., ge=0, description="Count feature 13")
    D1:             float = Field(..., ge=-1, description="Days since last transaction")
    D15:            float = Field(..., ge=-1, description="Days feature 15")
    V258:           float = Field(..., description="Vesta feature 258")
    V201:           float = Field(..., description="Vesta feature 201")

    @field_validator('TransactionAmt')
    @classmethod
    def amount_must_be_positive(cls, v):
        if v <= 0:
            raise ValueError("Transaction amount must be positive")
        return round(v, 2)

class FraudPrediction(BaseModel):
    fraud_probability: float
    risk_band:         str
    recommendation:    str
    model_version:     str = "xgboost-v2.0"

# ── Endpoints ──────────────────────────────────────────────────────────
@app.post("/predict", response_model=FraudPrediction)
@limiter.limit("60/minute")
async def predict_fraud(request: Request, txn: TransactionInput):
    """Score a transaction for fraud probability. Rate limit: 60 requests/minute."""
    try:
        features = np.array([[
            txn.TransactionAmt, txn.ProductCD, txn.card4, txn.card6,
            txn.C1, txn.C6, txn.C13, txn.D1, txn.D15, txn.V258, txn.V201
        ]])
        prob = float(request.app.state.model.predict_proba(features)[0][1])
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail="Scoring error")

    if prob > 0.8:
        band, rec = "Critical", "Block transaction immediately"
    elif prob > 0.5:
        band, rec = "High", "Request step-up authentication"
    elif prob > 0.2:
        band, rec = "Medium", "Flag for manual review"
    else:
        band, rec = "Low", "Approve"

    logger.info(f"Scored: amt={txn.TransactionAmt} → prob={prob:.4f} band={band}")
    return FraudPrediction(fraud_probability=round(prob, 4), risk_band=band, recommendation=rec)

@app.get("/health")
async def health(request: Request):
    model_loaded = hasattr(request.app.state, 'model')
    return {
        "status": "healthy" if model_loaded else "degraded",
        "model": "XGBoost v2.0",
        "model_loaded": model_loaded
    }
```

---

## 6. dbt Security

### `profiles.yml` — Never Commit This File

```yaml
# dbt_project/profiles.yml
# This file contains credentials. NEVER commit. Add to .gitignore.

banklens:
  target: dev
  outputs:
    dev:
      type: bigquery
      method: service-account
      project: "{{ env_var('GCP_PROJECT_ID') }}"
      dataset: "{{ env_var('GCP_DATASET_MARTS') }}"
      keyfile: "{{ env_var('GOOGLE_APPLICATION_CREDENTIALS') }}"
      location: US
      threads: 4
      timeout_seconds: 300

    snowflake:
      type: snowflake
      account: "{{ env_var('SNOWFLAKE_ACCOUNT') }}"
      user: "{{ env_var('SNOWFLAKE_USER') }}"
      password: "{{ env_var('SNOWFLAKE_PASSWORD') }}"
      database: BANKLENS_DB
      schema: MARTS
      warehouse: COMPUTE_WH
      threads: 4
```

### `.gitignore` additions for dbt
```
dbt_project/profiles.yml
dbt_project/logs/
dbt_project/target/
```

---

## 7. GitHub Actions Security (Post-Shai-Hulud)

```yaml
# .github/workflows/dbt_ci.yml — Hardened version

name: BankLens dbt CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

# CRITICAL: Restrict default token permissions
permissions:
  contents: read
  pull-requests: write

jobs:
  dbt-test:
    runs-on: ubuntu-latest
    timeout-minutes: 15  # Kill runaway jobs

    steps:
      # Pin to full SHA — not floating tag (Shai-Hulud exploited floating tags)
      - uses: actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683  # v4.2.2

      - name: Set up Python 3.11
        uses: actions/setup-python@0b93645e9fea7318ecaed2b359559ac225c90a2  # v5.3.0
        with:
          python-version: '3.11'

      - name: Install dependencies (no cache — supply chain safety)
        run: |
          pip install --no-cache-dir dbt-core==1.11.4 dbt-bigquery==1.11.1 \
            great-expectations==1.15.2 pip-audit==2.8.0

      # CRITICAL: Audit installed packages before using them
      - name: Audit dependencies for known vulnerabilities
        run: pip-audit --strict

      - name: Configure GCP credentials
        env:
          GCP_CREDENTIALS: ${{ secrets.GCP_SERVICE_ACCOUNT_JSON }}
        run: |
          echo "$GCP_CREDENTIALS" > /tmp/gcp_creds.json
          echo "GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_creds.json" >> $GITHUB_ENV

      - name: Run dbt compile
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCP_DATASET_MARTS: banklens_marts
        run: cd dbt_project && dbt compile --profiles-dir .

      - name: Run dbt test
        env:
          GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
          GCP_DATASET_MARTS: banklens_marts
        run: cd dbt_project && dbt test --profiles-dir .

      # Clean up credentials after use
      - name: Cleanup credentials
        if: always()
        run: rm -f /tmp/gcp_creds.json
```

---

## 8. PandasAI / LLM Security

### Prompt Injection Protection
When a user's natural language query interacts with financial data, a malicious value in the data could attempt to hijack the LLM prompt.

```python
# chat/chat_with_data.py — Secured version
import pandasai as pai
from pandasai_openai import OpenAI as PaiOpenAI
import re

ALLOWED_QUERY_PATTERN = re.compile(r'^[a-zA-Z0-9\s\?\.,\-\_\%\(\)]+$')
MAX_QUERY_LENGTH = 500

def safe_chat(query: str, *dfs):
    """Sanitize query before sending to PandasAI."""
    # Length guard
    if len(query) > MAX_QUERY_LENGTH:
        raise ValueError("Query too long")
    
    # Block obvious injection attempts
    INJECTION_KEYWORDS = ['ignore previous', 'system prompt', 'forget all', 
                          'jailbreak', 'DAN', 'SYSTEM:']
    for kw in INJECTION_KEYWORDS:
        if kw.lower() in query.lower():
            raise ValueError("Query contains disallowed terms")
    
    return pai.chat(query, *dfs)

# Usage:
llm = PaiOpenAI(api_token=os.getenv("OPENAI_API_KEY"))
pai.config.set({"llm": llm, "enable_cache": False})  # disable cache for security

result = safe_chat("What is the overall fraud rate?", fraud_df)
```

---

## 9. Data Security Summary Checklist

Before pushing to GitHub, verify:

```
CREDENTIALS
[ ] .env is in .gitignore — verified with: git check-ignore -v .env
[ ] No API keys in any .py, .yaml, .yml, .sql file
[ ] Service account JSON is NOT in the repo directory
[ ] profiles.yml is in .gitignore
[ ] git log --all --full-history -- .env shows no prior commits of .env

DATA
[ ] data/raw/ is in .gitignore
[ ] No sample data contains real PII
[ ] BigQuery datasets are NOT public

PACKAGES
[ ] pip-audit runs clean (no known CVEs)
[ ] All packages in requirements.txt have exact pinned versions
[ ] No use of mistralai, guardrails-ai, litellm, lightning (compromised packages)
[ ] pandasai uses pandasai_openai, NOT pandasai_litellm

GITHUB ACTIONS
[ ] All Action steps use SHA-pinned versions, not floating tags
[ ] permissions: contents: read is set (minimal permissions)
[ ] Secrets are stored in GitHub Secrets, not in yaml files

API
[ ] Rate limiting is enabled (60/minute via slowapi)
[ ] CORS allows only localhost origins
[ ] Security headers middleware is active
[ ] /predict endpoint validates all input ranges with Pydantic Field validators
[ ] Model loaded via lifespan context manager, not global variable

SNOWFLAKE
[ ] banklens_service user exists with BANKLENS_ROLE only
[ ] ACCOUNTADMIN credentials not in .env
[ ] Warehouse auto-suspend is set to 1 minute (saves trial credits)
```

---

## 10. Secret Scanning — Pre-Push Hook

Install this git hook to prevent accidental secret commits:

```bash
# Install detect-secrets
pip install detect-secrets==1.5.0

# Scan existing codebase first
detect-secrets scan > .secrets.baseline

# Create pre-commit hook
cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
detect-secrets-hook --baseline .secrets.baseline
if [ $? -ne 0 ]; then
    echo "❌ Secret detected! Commit blocked. Remove secrets before committing."
    exit 1
fi
EOF
chmod +x .git/hooks/pre-commit
```

---

*Security Document — BankLens 1.0 | June 2026*  
*Hardened against: TeamPCP/Shai-Hulud (CVE-2026-45321), Hades Campaign, LiteLLM compromise*
