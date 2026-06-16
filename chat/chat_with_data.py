"""
chat/chat_with_data.py
BankLens 2.0 -- Natural Language Data Interface
Uses Groq (llama-3.3-70b-versatile) instead of OpenAI.
Free tier: 14,400 requests/day -- more than enough.
Groq is faster than OpenAI for this use case (~200ms per query).

How it works:
1. Load all 3 mart tables from BigQuery into pandas DataFrames
2. User asks a question in plain English
3. Llama-3.3-70b receives schema + sample rows as context
4. Model returns a pandas expression as a string
5. We eval() it safely against the real DataFrame

Usage: python chat/chat_with_data.py
"""
import os
import warnings
import numpy as np
import pandas as pd
from groq import Groq
from google.cloud import bigquery
from dotenv import load_dotenv

warnings.filterwarnings("ignore")
load_dotenv()

# -- Groq client ----------------------------------------------------------
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = "llama-3.3-70b-versatile"

# -- BigQuery client --------------------------------------------------------
bq      = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
PROJECT = os.getenv("GCP_PROJECT_ID")
# dbt's default generate_schema_name macro appends the custom +schema suffix
# to the base dataset, so mart models actually land in "<base>_marts"
# (e.g. banklens_marts_marts), not the base dataset itself.
MARTS   = os.getenv("GCP_DATASET_MARTS", "banklens_marts") + "_marts"


def load_mart(table_name: str) -> pd.DataFrame:
    """Load a mart table from BigQuery into a pandas DataFrame."""
    df = bq.query(
        f"SELECT * FROM `{PROJECT}.{MARTS}.{table_name}`"
    ).to_dataframe()
    print(f"  Loaded {table_name}: {len(df):,} rows x {df.shape[1]} cols")
    return df


def build_context(df: pd.DataFrame, table_name: str) -> str:
    """Build schema + sample context for the LLM."""
    return f"""
DataFrame name: df
Table: {table_name}
Columns: {list(df.columns)}
Schema:
{df.dtypes.to_string()}

Sample rows (first 3):
{df.head(3).to_string(max_cols=8)}
"""


def ask_groq(question: str, df: pd.DataFrame, table_name: str) -> str:
    """Send question to Groq, get back a pandas expression string."""
    context = build_context(df, table_name)

    prompt = f"""You are a Python data analyst working with a pandas DataFrame called `df`.

{context}

Question: {question}

Rules:
- Reply with ONE Python expression using `df` only
- No explanations, no markdown, no code blocks -- just the raw expression
- Use only pandas operations
- For aggregations return a scalar or small Series
- For filtering return at most 20 rows

Examples of valid replies:
  df['fraud_rate_pct'].mean()
  df.groupby('card_network')['fraud_count'].sum().sort_values(ascending=False)
  df[df['risk_band'] == 'Critical'][['billing_zip','total_fraud_events']].head(10)
"""

    response = groq_client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=200,
        temperature=0,
    )
    return response.choices[0].message.content.strip()


def safe_eval(expression: str, df: pd.DataFrame):
    """Evaluate pandas expression in sandboxed scope."""
    expression = expression.replace("```python", "").replace("```", "").strip()
    return eval(
        expression,
        {"__builtins__": {}, "pd": pd, "np": np},
        {"df": df}
    )


def query(question: str, df: pd.DataFrame, table_name: str) -> object:
    """Full pipeline: question -> Groq expression -> eval -> result."""
    print(f"\n{'-'*60}")
    print(f"Q: {question}")

    expression = ask_groq(question, df, table_name)
    print(f"Code: {expression}")

    try:
        result = safe_eval(expression, df)
        print(f"Answer: {result}")
        return result
    except Exception as exc:
        msg = f"Eval error: {exc} | Expression: {expression}"
        print(f"ERROR: {msg}")
        return msg


def run_demo():
    """5 demo queries across all 3 mart tables. Screenshot this output."""
    print("BankLens 2.0 -- Natural Language Data Interface (Groq)")
    print(f"Model: {MODEL}")
    print("=" * 60)
    print("Loading mart tables from BigQuery...")

    dfs = {
        "mart_fraud_dashboard":      load_mart("mart_fraud_dashboard"),
        "mart_campaign_performance": load_mart("mart_campaign_performance"),
        "mart_customer_360":         load_mart("mart_customer_360"),
    }
    print("\nAll tables loaded")

    demo_queries = [
        ("mart_fraud_dashboard",
         "What is the overall fraud rate percentage across all transactions?"),

        ("mart_fraud_dashboard",
         "Which card network has the highest total fraud count?"),

        ("mart_campaign_performance",
         "Which age segment has the highest campaign response rate?"),

        ("mart_campaign_performance",
         "What is the response rate difference between cellular and telephone?"),

        ("mart_customer_360",
         "How many customers are suppressed due to high fraud risk?"),
    ]

    print(f"\nRunning {len(demo_queries)} natural language queries...\n")
    for table_key, question in demo_queries:
        query(question, dfs[table_key], table_key)

    print(f"\n{'='*60}")
    print("Demo complete. Screenshot the output for your portfolio.")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_demo()
