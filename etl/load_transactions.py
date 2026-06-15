"""
etl/load_transactions.py
Loads IEEE-CIS Fraud Detection data into BigQuery banklens_raw.transactions.
Source: data/raw/train_transaction.csv (530MB, 590K rows)
        data/raw/train_identity.csv   (65MB,  144K rows)
Target: banklens_raw.transactions (one wide table, LEFT JOINed)
Strategy: chunked loading (10K rows/chunk) for memory safety
          First chunk: WRITE_TRUNCATE | Subsequent chunks: WRITE_APPEND
          Combined effect = idempotent full reload
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

PROJECT    = os.getenv("GCP_PROJECT_ID")
DATASET    = os.getenv("GCP_DATASET_RAW", "banklens_raw")
TABLE      = "transactions"
TXN_FILE   = os.path.join("data", "raw", "train_transaction.csv")
ID_FILE    = os.path.join("data", "raw", "train_identity.csv")
CHUNK_SIZE = 10_000


def run() -> None:
    # Validate files exist before starting
    for path in [TXN_FILE, ID_FILE]:
        if not os.path.exists(path):
            raise FileNotFoundError(
                f"File not found: {path}\n"
                "Download IEEE-CIS from kaggle.com/competitions/ieee-fraud-detection/data\n"
                "and place train_transaction.csv and train_identity.csv in data/raw/"
            )

    # Load identity data fully — 65MB fits comfortably in RAM
    logger.info("Loading identity data (65MB, one-time)...")
    identity_df = pd.read_csv(ID_FILE)
    logger.info(f"Identity rows: {len(identity_df):,} | Cols: {identity_df.shape[1]}")

    client = get_bq_client()
    ensure_bq_dataset(client, PROJECT, DATASET)
    destination = f"{PROJECT}.{DATASET}.{TABLE}"

    total_rows = 0
    first_chunk = True

    logger.info(f"Loading transactions in {CHUNK_SIZE:,}-row chunks...")
    logger.info("This takes 3-5 minutes for 590K rows — grab a coffee")

    for chunk_num, txn_chunk in enumerate(
        pd.read_csv(TXN_FILE, chunksize=CHUNK_SIZE)
    ):
        # LEFT JOIN: every transaction kept, identity columns NULL if no match
        merged = txn_chunk.merge(identity_df, on="TransactionID", how="left")

        # First chunk wipes the table (WRITE_TRUNCATE), rest append
        # Combined effect across all chunks = full idempotent reload
        write_mode = "WRITE_TRUNCATE" if first_chunk else "WRITE_APPEND"
        job_config = bigquery.LoadJobConfig(
            write_disposition=write_mode,
            autodetect=True,
        )

        job = client.load_table_from_dataframe(
            merged, destination, job_config=job_config
        )
        job.result()

        total_rows += len(merged)
        first_chunk = False

        # Log progress every 10 chunks (every 100K rows)
        if chunk_num % 10 == 0:
            logger.info(
                f"Chunk {chunk_num:>3} | {total_rows:>7,} rows uploaded so far..."
            )

    # Final verification
    bq_count = bq_row_count(client, PROJECT, DATASET, TABLE)
    logger.info(f"Local rows processed : {total_rows:,}")
    logger.info(f"BigQuery row count   : {bq_count:,}")
    assert bq_count == total_rows, \
        f"Row count mismatch! Local: {total_rows}, BigQuery: {bq_count}"
    log_success(destination, bq_count)

    # Spot check fraud rate (should be ~3.5%)
    rate_result = client.query(
        f"SELECT ROUND(AVG(isFraud) * 100, 2) AS fraud_rate "
        f"FROM `{destination}`"
    ).result()
    fraud_rate = list(rate_result)[0].fraud_rate
    logger.info(f"Fraud rate: {fraud_rate}% (expected ~3.5%)")


if __name__ == "__main__":
    run()
