"""
etl/load_campaigns.py
Load UCI Bank Marketing dataset into BigQuery.

Source file:
  data/raw/bank-additional-full.csv — 45K rows, semicolon-separated

Target: {GCP_PROJECT_ID}.banklens_raw.campaigns

Key behaviour:
  - Read CSV with sep=';'
  - Rename columns with dots to underscores (SQL doesn't allow dots):
      emp.var.rate → emp_var_rate
      cons.price.idx → cons_price_idx
      cons.conf.idx → cons_conf_idx
      nr.employed → nr_employed
  - Validate: y column must contain only 'yes'/'no'
  - Use WRITE_TRUNCATE (idempotent)
  - Log row count on success

Usage: python etl/load_campaigns.py
       or imported and called via etl/run_all.py → run()
"""


def run():
    """Entry point for run_all.py orchestrator. Implement in Phase 1."""
    raise NotImplementedError("Phase 1: implement load_campaigns.run()")


if __name__ == "__main__":
    run()
