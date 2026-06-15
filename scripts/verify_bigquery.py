"""
scripts/verify_bigquery.py
Verifies BigQuery raw tables loaded correctly after Phase 1 ETL.
Usage: python scripts\verify_bigquery.py
"""
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()
client = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
p = os.getenv("GCP_PROJECT_ID")

queries = {
    "Campaign row count":
        f"SELECT COUNT(*) AS cnt FROM `{p}.banklens_raw.campaigns`",
    "Transaction row count":
        f"SELECT COUNT(*) AS cnt FROM `{p}.banklens_raw.transactions`",
    "Fraud rate %":
        f"SELECT ROUND(AVG(isFraud)*100, 2) AS fraud_rate FROM `{p}.banklens_raw.transactions`",
    "Top product codes":
        f"SELECT ProductCD, COUNT(*) AS cnt FROM `{p}.banklens_raw.transactions` GROUP BY ProductCD ORDER BY cnt DESC LIMIT 5",
    "Campaign subscription":
        f"SELECT y, COUNT(*) AS cnt FROM `{p}.banklens_raw.campaigns` GROUP BY y",
}

for name, sql in queries.items():
    result = list(client.query(sql).result())
    print(f"\n{name}:")
    for row in result:
        print(" ", dict(row))
