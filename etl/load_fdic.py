"""
etl/load_fdic.py
Loads FDIC regulatory data (already downloaded) into Snowflake.
Source: data/raw/fdic_institutions.csv (from scripts/download_fdic.py)
Target: Snowflake BANKLENS_DB.RAW.REGULATORY
Strategy: DROP TABLE + recreate (idempotent)

Uses snowflake-connector-python + write_pandas for bulk upload.
"""
import os
import logging
import pandas as pd
from snowflake.connector.pandas_tools import write_pandas
from dotenv import load_dotenv
from etl.utils import get_snowflake_conn, log_success

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(message)s")
logger = logging.getLogger(__name__)

CSV_PATH = os.path.join("data", "raw", "fdic_institutions.csv")
TABLE    = "REGULATORY"

RENAME_MAP = {
    "REPDTE":   "REPORT_DATE",
    "CERT":     "CERT_NUMBER",
    "INSTNAME": "INSTITUTION_NAME",
    "ASSET":    "TOTAL_ASSETS_K",
    "DEP":      "TOTAL_DEPOSITS_K",
    "NETINC":   "NET_INCOME_K",
    "INTINC":   "INTEREST_INCOME_K",
    "NONII":    "NONINTEREST_INCOME_K",
    "LNLSNET":  "NET_LOANS_K",
    "NPERFV":   "NONCURRENT_LOANS_K",
    "TIER1RBC": "TIER1_CAPITAL_RATIO",
}


def run() -> None:
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(
            f"File not found: {CSV_PATH}\n"
            "Run: python scripts\\download_fdic.py"
        )

    logger.info("Reading FDIC data from cache...")
    df = pd.read_csv(CSV_PATH, low_memory=False)
    logger.info(f"Raw shape: {df.shape}")

    # Keep only the columns we need and rename to snake_case for SQL
    available = {k: v for k, v in RENAME_MAP.items() if k in df.columns}
    df = df[list(available.keys())].rename(columns=available).copy()

    # Add derived regulatory metrics (used in Power BI Regulatory page)
    net_loans = pd.to_numeric(df["NET_LOANS_K"], errors="coerce")
    noncurr   = pd.to_numeric(df["NONCURRENT_LOANS_K"], errors="coerce")
    df.loc[:, "NPL_RATIO_PCT"] = (noncurr / net_loans.replace(0, float("nan"))) * 100
    df.loc[:, "RAG_STATUS"] = df["NPL_RATIO_PCT"].apply(
        lambda x: "Red" if x > 5 else ("Amber" if x > 2 else "Green")
        if pd.notna(x) else "Unknown"
    )

    logger.info(f"Final shape: {df.shape}")
    logger.info(f"RAG distribution:\n{df['RAG_STATUS'].value_counts().to_string()}")

    # Connect to Snowflake and load
    conn = get_snowflake_conn()
    cur  = conn.cursor()

    # write_pandas uses its own internal cursor that doesn't inherit the
    # warehouse from connection params — must set it explicitly on the session
    warehouse = os.getenv("SNOWFLAKE_WAREHOUSE")
    cur.execute(f"USE WAREHOUSE {warehouse}")
    logger.info(f"Activated warehouse: {warehouse}")

    # Idempotent: drop and recreate the table each run
    cur.execute(f"DROP TABLE IF EXISTS {TABLE}")
    logger.info(f"Dropped existing {TABLE} table (if any)")

    success, nchunks, nrows, _ = write_pandas(
        conn, df, TABLE,
        auto_create_table=True,    # creates table from DataFrame schema
        overwrite=True,
    )
    conn.close()

    if not success:
        raise RuntimeError("Snowflake write_pandas failed")
    log_success(f"Snowflake.BANKLENS_DB.RAW.{TABLE}", nrows)


if __name__ == "__main__":
    run()
