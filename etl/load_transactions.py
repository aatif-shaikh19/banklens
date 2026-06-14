"""
etl/load_transactions.py
Load IEEE-CIS Fraud Detection dataset into BigQuery.

Source files:
  data/raw/train_transaction.csv  — 590K rows, 393 columns
  data/raw/train_identity.csv     — 144K rows, 41 columns (24% of transactions)

Target: {GCP_PROJECT_ID}.banklens_raw.transactions

Key behaviour:
  - LEFT JOIN identity on TransactionID before loading
  - Chunked reading (chunksize=10_000) for memory safety on 530MB file
  - First chunk: WRITE_TRUNCATE (idempotent). Subsequent chunks: WRITE_APPEND.
  - Fill NA: -999 for numerics, 'unknown' for strings
  - Deduplicate on TransactionID
  - Log progress every 10 chunks
  - Verify final row count matches source after load

Usage: python etl/load_transactions.py
       or imported and called via etl/run_all.py → run()
"""


def run():
    """Entry point for run_all.py orchestrator. Implement in Phase 1."""
    raise NotImplementedError("Phase 1: implement load_transactions.run()")


if __name__ == "__main__":
    run()
