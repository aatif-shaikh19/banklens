"""
etl/load_fdic.py
Load FDIC bank statistics into Snowflake (NOT BigQuery).

Source: FDIC public API — https://banks.data.fdic.gov/api/financials
Fields: REPDTE, CERT, INSTNAME, ASSET, DEP, NETINC, INTINC, NONII,
        LNLSNET, NPERFV, TIER1RBC

Target: BANKLENS_DB.RAW.REGULATORY

Key behaviour:
  - Paginate API with limit=1000 until no more results
  - Cache response to data/raw/fdic_institutions.csv after first download
  - Rename all columns to snake_case
  - Derive: npl_ratio_pct = (NPERFV / LNLSNET) * 100
  - Derive: rag_status — 'Red' if npl_ratio > 5, 'Amber' if > 2, else 'Green'
  - Truncate Snowflake table before each load (idempotent)
  - Use snowflake.connector.pandas_tools.write_pandas for upload
  - snowflake-connector-python 4.0.0 syntax

Usage: python etl/load_fdic.py
       or imported and called via etl/run_all.py → run()
"""


def run():
    """Entry point for run_all.py orchestrator. Implement in Phase 1."""
    raise NotImplementedError("Phase 1: implement load_fdic.run()")


if __name__ == "__main__":
    run()
