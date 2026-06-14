"""
etl/utils.py
Shared utility functions for BankLens 2.0.
Handles BigQuery and Snowflake connections using environment variables.
"""
import os
import logging
from google.cloud import bigquery
import snowflake.connector
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


def get_bq_client() -> bigquery.Client:
    """Return an authenticated BigQuery client using GOOGLE_APPLICATION_CREDENTIALS."""
    project = os.getenv("GCP_PROJECT_ID")
    if not project:
        raise ValueError("GCP_PROJECT_ID not set. Did you source your .env?")
    return bigquery.Client(project=project)


def get_snowflake_conn():
    """Return an authenticated Snowflake connection using env vars."""
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


def bq_row_count(client: bigquery.Client, project: str, dataset: str, table: str) -> int:
    """Return row count for a BigQuery table."""
    result = client.query(
        f"SELECT COUNT(*) as cnt FROM `{project}.{dataset}.{table}`"
    ).result()
    return list(result)[0].cnt


def log_load_success(table: str, rows: int):
    logger.info(f"✅  Loaded {rows:,} rows → {table}")
