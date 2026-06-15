"""
etl/utils.py
Shared connection helpers for BankLens 2.0 ETL layer.
All credentials read from .env via python-dotenv.
"""
import os
import logging
from google.cloud import bigquery
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_bq_client() -> bigquery.Client:
    """Return authenticated BigQuery client. Reads GCP_PROJECT_ID from .env."""
    project = os.getenv("GCP_PROJECT_ID")
    if not project:
        raise ValueError("GCP_PROJECT_ID not set. Did you fill in .env?")
    return bigquery.Client(project=project)


def ensure_bq_dataset(client: bigquery.Client, project: str,
                       dataset_id: str, location: str = "US") -> None:
    """Create BigQuery dataset if it does not already exist."""
    full_id = f"{project}.{dataset_id}"
    try:
        client.get_dataset(full_id)
        logger.info(f"Dataset already exists: {full_id}")
    except Exception:
        ds = bigquery.Dataset(full_id)
        ds.location = location
        client.create_dataset(ds, timeout=30)
        logger.info(f"Created dataset: {full_id}")


def get_snowflake_conn():
    """Return authenticated Snowflake connection. All params from .env."""
    required = [
        "SNOWFLAKE_ACCOUNT", "SNOWFLAKE_USER", "SNOWFLAKE_PASSWORD",
        "SNOWFLAKE_DATABASE", "SNOWFLAKE_SCHEMA", "SNOWFLAKE_WAREHOUSE"
    ]
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


def bq_row_count(client: bigquery.Client, project: str,
                  dataset: str, table: str) -> int:
    """Return the current row count for a BigQuery table."""
    result = client.query(
        f"SELECT COUNT(*) AS cnt FROM `{project}.{dataset}.{table}`"
    ).result()
    return list(result)[0].cnt


def log_success(destination: str, rows: int) -> None:
    logger.info(f"✅  {rows:,} rows loaded → {destination}")
