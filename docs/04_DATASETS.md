# BankLens — Datasets Guide
**| Manual download approach | No CLI required for IEEE-CIS**

---

## Dataset Overview

| # | Dataset | Rows | Source | How to Get | Used For |
|---|---|---|---|---|---|
| **A** | IEEE-CIS Fraud Detection | 590,540 | Kaggle (2019) | Manual browser download | ML model, fraud dashboard, risk bands |
| **B** | UCI Bank Marketing | 45,211 | UCI ML Repo | `wget` — no login | Campaign analytics, Looker Studio |
| **C** | FDIC Statistics | ~10,000 institutions | FDIC API | Python script | Regulatory compliance Power BI page |
| **D** | Bank Account Fraud NeurIPS 2022 | 1,000,000 | Kaggle | Manual browser download (optional) | Supplemental EDA, realistic features |

---

## Dataset A — IEEE-CIS Fraud Detection (PRIMARY)

### Important: Download This to Your Laptop First

You need to download the files manually from the browser and place them in `data/raw/`. Then you'll upload them to Google Colab for ML training.

### Step-by-Step Download

1. Go to **kaggle.com** and sign in
2. Navigate to: **kaggle.com/competitions/ieee-fraud-detection/data**
3. Accept the competition rules if prompted (one-time click)
4. Click **"Download All"** button — this downloads `ieee-fraud-detection.zip` (~220MB compressed)
5. Unzip it. You'll get these files:
   - `train_transaction.csv` — **530MB** — this is your primary file
   - `train_identity.csv` — **65MB** — device/identity info
   - `test_transaction.csv` — ignore (no labels)
   - `test_identity.csv` — ignore

6. Move to your project:
```bash
# Linux/WSL — adjust path to where you unzipped
mv ~/Downloads/train_transaction.csv banklens-2.0/data/raw/
mv ~/Downloads/train_identity.csv banklens-2.0/data/raw/
```

### Key Columns

```
TransactionID      — unique row identifier, join key with train_identity.csv
TransactionDT      — seconds since reference timestamp (Nov 30, 2017 00:00:00)
TransactionAmt     — USD amount (note: can be fractional)
ProductCD          — product category: W, C, R, H, S
card4              — Visa / Mastercard / Amex / Discover
card6              — credit / debit
addr1              — billing zip code (numeric)
addr2              — billing country code (numeric)
P_emaildomain      — purchaser email domain (gmail.com, yahoo.com, etc.)
R_emaildomain      — recipient email domain
C1–C14            — count features (e.g. C1 = # of recipients for this card)
D1–D15            — time-delta features (D1 = days since last transaction)
M1–M9             — match features (name/address match flags)
V1–V339           — 339 Vesta-engineered behavioral features (anonymized)
isFraud            — TARGET: 0 = legitimate, 1 = fraud
```

### Dataset Stats (Know These for Interviews)
- Fraud transactions: 20,663 (3.5%)
- Legit transactions: 569,877 (96.5%)
- Imbalance ratio: **27.6:1** → must use `scale_pos_weight` in XGBoost
- Time span: November 2017 – July 2019
- Source: Vesta Corporation (real e-commerce data, anonymized)

---

## Dataset A → Google Colab Upload

After downloading to your laptop, for ML training:

1. Go to **drive.google.com**
2. Create a folder: **BankLens**
3. Upload `train_transaction.csv` and `train_identity.csv` into it
4. In Colab, mount Drive and access them (see Phase 4 build prompt)

The Colab notebook we'll build in Phase 4 reads from Drive, trains XGBoost, saves the model, and you download the `.pkl` file back to your laptop.

---

## Dataset B — UCI Bank Marketing

### Download (no login required)

```bash
# From your banklens-2.0 directory:
wget "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip" \
     -O data/raw/bank_marketing.zip

cd data/raw
unzip -o bank_marketing.zip

# The file we want (largest, most features):
cp "bank-additional/bank-additional-full.csv" bank-additional-full.csv
cd ../..

# Verify
wc -l data/raw/bank-additional-full.csv
# Should print: 45212 (45211 rows + 1 header)
```

### Key Columns

```
# Customer demographics
age            — integer (18–95 range in this dataset)
job            — admin., blue-collar, entrepreneur, housemaid, management,
                  retired, self-employed, services, student, technician,
                  unemployed, unknown
marital        — married, single, divorced, unknown
education      — basic.4y, basic.6y, basic.9y, high.school, illiterate,
                  professional.course, university.degree, unknown
default        — has credit in default? yes/no/unknown
housing        — has housing loan? yes/no/unknown
loan           — has personal loan? yes/no/unknown

# Campaign info (this campaign)
contact        — cellular or telephone ← KEY feature
month          — jan-dec
day_of_week    — mon-fri
duration       — call duration in seconds (⚠️ do NOT use as model feature — see below)
campaign       — # of contacts during this campaign
pdays          — days since last contact from PREVIOUS campaign (999 = never)
previous       — # of contacts before this campaign
poutcome       — previous outcome: failure / nonexistent / success

# Macroeconomic context
emp.var.rate   — employment variation rate (quarterly indicator)
cons.price.idx — consumer price index (monthly)
cons.conf.idx  — consumer confidence index (monthly)
euribor3m      — Euribor 3-month rate (daily)
nr.employed    — quarterly number of bank employees

# TARGET
y              — subscribed to term deposit? yes/no → encode as 1/0
```

**⚠️ Important: `duration` should NEVER be used as a feature in a production model.** You don't know call duration before the call happens. Use it for analysis (longer calls → higher conversion) but exclude it from any ML model you build on this dataset.

---

## Dataset C — FDIC Statistics (via API)

### Download via Script

```bash
# From your banklens-2.0 directory with .venv active:
python scripts/download_fdic.py
# Creates: data/raw/fdic_institutions.csv
# Takes: ~2–3 minutes (paginates 10,000+ institutions)
```

### Key Columns for Regulatory Dashboard

```
REPDTE      — report date (YYYYMMDD format, e.g. 20250331 = Q1 2025)
CERT        — institution certificate number (unique ID)
INSTNAME    — institution name (e.g. "JPMorgan Chase Bank")
ASSET       — total assets in $thousands
DEP         — total deposits in $thousands
NETINC      — net income in $thousands
INTINC      — total interest income in $thousands
NONII       — total noninterest income in $thousands
LNLSNET     — net loans and leases in $thousands
NPERFV      — noncurrent loans/leases in $thousands (used for NPL ratio)
TIER1RBC    — Tier 1 risk-based capital ratio (%) ← regulatory adequacy metric
```

### Derived Metrics for Power BI

```
NPL Ratio (%) = NPERFV / LNLSNET × 100
RAG Status    = Red if NPL > 5%, Amber if NPL > 2%, Green otherwise
ROA (%)       = NETINC / ASSET × 100
CAR           = TIER1RBC (already a ratio)
```

---

## Dataset D — Bank Account Fraud NeurIPS 2022 (Optional but Recommended)

### Why Include This?
The IEEE-CIS features (V1–V339) are heavily anonymized PCA components. The BAF dataset has **interpretable features** like `velocity_6h`, `credit_risk_score`, `foreign_request` — much better for explaining fraud concepts in interviews.

### Download
1. Go to: **kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022**
2. Click **Download** → download the zip
3. Unzip → use only `Base.csv` (~400MB, 1M rows)
4. Move to `data/raw/baf_base.csv`

**Use in EDA notebook only** — not for the main ML pipeline.

---

## Storage Requirements Summary

```
data/raw/
├── train_transaction.csv      530 MB  ← IEEE-CIS, primary ML dataset
├── train_identity.csv          65 MB  ← IEEE-CIS identity info
├── bank-additional-full.csv     5 MB  ← UCI campaign dataset
├── fdic_institutions.csv        5 MB  ← Regulatory data
├── creditcard_fraud.csv        25 MB  ← Downloaded automatically in ETL script
└── baf_base.csv               400 MB  ← Optional NeurIPS 2022 dataset

Total data/raw/: ~630 MB minimum, ~1.03 GB with optional BAF dataset
```

---

## Kaggle Account Setup (June 2026 Updated Instructions)

The Kaggle UI has changed. The token that generates `kaggle.json` is now under a section called "Legacy API Credentials":

1. Go to **kaggle.com → click your profile photo → Settings**
2. Scroll to **"API"** section
3. Under **"Legacy API Credentials"**, click **"Create Legacy API Key"**
4. This downloads `kaggle.json`
5. Store it: `mkdir -p ~/.kaggle && mv ~/Downloads/kaggle.json ~/.kaggle/ && chmod 600 ~/.kaggle/kaggle.json`

**Note:** The main "Create New API Token" button at the top of the API section generates a token for the new `kagglehub` Python library, not the classic `kaggle` CLI. For our project (which uses the classic `kaggle` CLI), you need "Legacy API Key" specifically.

For the IEEE-CIS competition dataset, you can also just download it directly from the browser (described in Dataset A above) — no CLI needed at all.

---

*Datasets Guide — BankLens 1.0 | June 2026*
