"""
tests/test_etl.py
BankLens 2.0 — ETL Unit Tests

Tests for the ETL layer (etl/load_transactions.py, load_campaigns.py, load_fdic.py).
Uses sample data from data/sample/ to avoid requiring full 530MB raw files.

Test coverage (implement in Phase 1):
  - test_transactions_schema: verify column names and types after load
  - test_campaigns_column_rename: verify dot→underscore renaming
  - test_fdic_derived_columns: verify npl_ratio_pct and rag_status logic
  - test_idempotency: running load twice produces same row count

Usage: pytest tests/test_etl.py -v
"""

# Implement in Phase 1
