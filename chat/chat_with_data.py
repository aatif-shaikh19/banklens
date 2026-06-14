# chat/chat_with_data.py
"""
BankLens 2.0 — Natural Language Data Interface
Uses OpenAI directly instead of PandasAI (removed — conflicts with pandas 3.x).
This approach is more transparent and easier to explain in interviews.
"""

import openai
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv
import os

load_dotenv()

client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def nl_query(question: str, df: pd.DataFrame, table_name: str) -> str:
    """
    Ask a natural language question about a DataFrame.
    Uses GPT-4o-mini to generate a pandas expression, then evaluates it.
    """
    schema = df.dtypes.to_string()
    sample = df.head(5).to_string()
    col_list = list(df.columns)

    prompt = f"""You are a Python data analyst. 
You have a pandas DataFrame called `df` with these columns: {col_list}

Schema:
{schema}

Sample rows:
{sample}

Question: {question}

Reply with ONLY a single Python expression using `df` that answers the question.
No explanation. No markdown. Just the expression.
Examples of valid replies:
  df['fraud_rate_pct'].mean()
  df[df['risk_band']=='High']['total_transactions'].sum()
  df.groupby('contact_channel')['response_rate_pct'].mean().idxmax()
"""
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=0,
    )
    code = response.choices[0].message.content.strip()

    try:
        result = eval(code, {"df": df, "pd": pd})
        return f"Q: {question}\nCode: {code}\nAnswer: {result}"
    except Exception as e:
        return f"Q: {question}\nCode: {code}\nError: {e}"


def load_marts() -> dict:
    """Load all mart tables from BigQuery into DataFrames."""
    bq = bigquery.Client(project=os.getenv("GCP_PROJECT_ID"))
    p = os.getenv("GCP_PROJECT_ID")
    m = os.getenv("GCP_DATASET_MARTS", "banklens_marts")

    print("Loading mart tables from BigQuery...")
    tables = {
        "fraud": f"`{p}.{m}.mart_fraud_dashboard`",
        "campaign": f"`{p}.{m}.mart_campaign_performance`",
        "customer360": f"`{p}.{m}.mart_customer_360`",
    }
    return {
        name: bq.query(f"SELECT * FROM {q}").to_dataframe()
        for name, q in tables.items()
    }


if __name__ == "__main__":
    dfs = load_marts()
    print(f"Loaded: {', '.join(f'{k}={len(v):,}rows' for k, v in dfs.items())}\n")

    # Demo queries — screenshot these for portfolio
    demo_questions = [
        ("fraud", "What is the overall fraud rate as a percentage?"),
        ("campaign", "Which contact channel has the highest response rate?"),
        ("campaign", "What is the average response rate by age segment?"),
        ("customer360", "How many customers are classified as high risk?"),
        ("fraud", "Which card network has the most fraud transactions?"),
    ]

    for table_key, question in demo_questions:
        print("-" * 60)
        print(nl_query(question, dfs[table_key], table_key))
    print("\nDone. Screenshot this output for your AI Layer portfolio section.")
