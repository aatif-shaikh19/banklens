# BankLens 2.0 — Dataset Download Instructions

All raw data files go in data/raw/ (this folder is gitignored — never committed).

## Dataset A — IEEE-CIS Fraud Detection (PRIMARY, ~600MB)
Source: https://www.kaggle.com/competitions/ieee-fraud-detection/data

```bash
# Requires: Kaggle CLI + kaggle.json configured
kaggle competitions download -c ieee-fraud-detection -p data/raw/
cd data/raw/
unzip ieee-fraud-detection.zip
# Result: train_transaction.csv (~530MB), train_identity.csv (~65MB)
```

## Dataset B — UCI Bank Marketing (~5MB)
Source: https://archive.ics.uci.edu/dataset/222/bank+marketing

```bash
wget "https://archive.ics.uci.edu/static/public/222/bank+marketing.zip" -O data/raw/bank_marketing.zip
cd data/raw/
unzip bank_marketing.zip
# Use: bank-additional/bank-additional-full.csv (45K rows, semicolon-separated)
cp bank-additional/bank-additional-full.csv bank-additional-full.csv
```

## Dataset C — FDIC Statistics (via API, ~5MB)

```bash
python scripts/download_fdic.py
# Creates: data/raw/fdic_institutions.csv
```

## Dataset D — Bank Account Fraud NeurIPS 2022 (~400MB, optional)
Source: https://www.kaggle.com/datasets/sgpjesus/bank-account-fraud-dataset-neurips-2022

```bash
kaggle datasets download -d sgpjesus/bank-account-fraud-dataset-neurips-2022 -p data/raw/baf/
cd data/raw/baf/
unzip bank-account-fraud-dataset-neurips-2022.zip
# Use: Base.csv (1M rows, most realistic features)
```

After downloading, create samples for fast development:
```bash
python scripts/create_samples.py
```
