"""
etl/load_campaigns.py
Loads UCI Bank Marketing dataset into BigQuery banklens_raw.campaigns.
Source: data/raw/bank-additional-full.csv (semicolon-separated, 41,188 rows, 20 features)
Target: banklens_raw.campaigns in BigQuery
Strategy: WRITE_TRUNCATE (idempotent — safe to run multiple times)
"""
import os
import logging
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv
from etl.utils import get_bq_client, ensure_bq_dataset, bq_row_count, log_success

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

PROJECT  = os.getenv("GCP_PROJECT_ID")
DATASET  = os.getenv("GCP_DATASET_RAW", "banklens_raw")
TABLE    = "campaigns"
CSV_PATH = os.path.join("data", "raw", "bank-additional-full.csv")


def run() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"File not found: {CSV_PATH}\n"
            "Run the UCI download step first — see data/download_instructions.md"
        )

    logger.info("Reading UCI Bank Marketing CSV (semicolon-separated)...")
    df = pd.read_csv(CSV_PATH, sep=";")
    logger.info(f"Shape: {df.shape} | Columns: {list(df.columns)}")

    # Validate before loading — fail fast if data is corrupt
    assert set(df["y"].unique()).issubset({"yes", "no"}), \
        "Unexpected values in target column 'y'"
    assert df["age"].between(0, 120).all(), "Age values out of valid range"
    subscription_rate = (df["y"] == "yes").mean() * 100
    logger.info(f"Subscription rate: {subscription_rate:.1f}% (expected ~11%)")

    # Rename columns with dots — BigQuery and SQL do not allow dots in column names
    df = df.rename(columns={
        "emp.var.rate":   "emp_var_rate",
        "cons.price.idx": "cons_price_idx",
        "cons.conf.idx":  "cons_conf_idx",
        "nr.employed":    "nr_employed",
    })

    # Connect and ensure the dataset exists before loading
    client = get_bq_client()
    ensure_bq_dataset(client, PROJECT, DATASET)

    destination = f"{PROJECT}.{DATASET}.{TABLE}"
    job_config  = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE",
        autodetect=True,
    )
    logger.info(f"Loading to {destination}...")
    job = client.load_table_from_dataframe(df, destination, job_config=job_config)
    job.result()   # blocks until job finishes

    # Verify the count matches what we uploaded
    count = bq_row_count(client, PROJECT, DATASET, TABLE)
    assert count == len(df), f"Row mismatch: uploaded {len(df)}, BigQuery has {count}"
    log_success(destination, count)


if __name__ == "__main__":
    run()
