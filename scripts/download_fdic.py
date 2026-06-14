import requests
import pandas as pd
import os

OUTPUT = "data/raw/fdic_institutions.csv"
os.makedirs("data/raw", exist_ok=True)

LATEST_REPDTE = "20260331"

KEY_FIELDS = (
    "REPDTE,CERT,INSTNAME,ASSET,DEP,NETINC,INTINC,NONII,LNLSNET,NPERFV,TIER1RBC"
)

print(f"Fetching FDIC institutions for reporting date {LATEST_REPDTE}...")

all_data = []
offset = 0
limit = 1000

while True:
    params = {
        "filters": f"REPDTE:{LATEST_REPDTE}",
        "fields": KEY_FIELDS,
        "limit": limit,
        "offset": offset,
        "sort_by": "ASSET",
        "sort_order": "DESC",
        "output": "json",
    }

    r = requests.get(
        "https://banks.data.fdic.gov/api/financials",
        params=params,
        timeout=60,
    )

    r.raise_for_status()

    data = r.json().get("data", [])

    if not data:
        break

    all_data.extend([row["data"] for row in data])

    print(f"Fetched {len(all_data):,} records")

    if len(data) < limit:
        break

    offset += limit

df = pd.DataFrame(all_data)

df.to_csv(OUTPUT, index=False)

print(f"\n✅ Saved {len(df):,} institutions")
print(f"✅ File written to: {OUTPUT}")
