"""
scripts/create_samples.py
Creates 1000-row sample CSVs from raw datasets.
Windows-compatible — uses os.path not Unix paths.
Usage: python scripts\create_samples.py
"""
import pandas as pd
import os

RAW    = os.path.join("data", "raw")
SAMPLE = os.path.join("data", "sample")
os.makedirs(SAMPLE, exist_ok=True)

def make_sample(filename, sep=",", n=1000):
    src = os.path.join(RAW, filename)
    if not os.path.exists(src):
        print(f"  Skipping {filename} — not in data/raw/ yet")
        return
    df = pd.read_csv(src, sep=sep, nrows=n)
    out = os.path.join(SAMPLE, f"sample_{filename}")
    df.to_csv(out, index=False)
    print(f"  Created {out} ({len(df)} rows x {df.shape[1]} cols)")

print("Creating samples from data/raw/...")
make_sample("train_transaction.csv")
make_sample("train_identity.csv")
make_sample("bank-additional-full.csv", sep=";")
make_sample("fdic_institutions.csv")
print("Done. Use data/sample/ for fast dev testing.")
