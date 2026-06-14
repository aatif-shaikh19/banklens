"""
scripts/verify_setup.py
Run this to verify every package in the BankLens 2.0 stack is installed correctly.
Usage: python scripts/verify_setup.py
"""
import sys
import importlib.metadata

# Windows terminals default to CP1252 which can't render emoji — force UTF-8
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

def _meta_version(pkg: str):
    return importlib.metadata.version(pkg)

BOLD  = "\033[1m"
GREEN = "\033[92m"
RED   = "\033[91m"
RESET = "\033[0m"

def check(label: str, fn):
    try:
        result = fn()
        print(f"  {GREEN}✅  {label}: {result}{RESET}")
        return True
    except Exception as e:
        print(f"  {RED}❌  {label}: {e}{RESET}")
        return False

print(f"\n{BOLD}BankLens 2.0 — Environment Verification{RESET}")
print("=" * 50)

print(f"\n{BOLD}Python{RESET}")
check("Python version", lambda: sys.version.split()[0])

print(f"\n{BOLD}Core Data Science{RESET}")
check("pandas",        lambda: __import__("pandas").__version__)
check("numpy",         lambda: __import__("numpy").__version__)
check("scikit-learn",  lambda: __import__("sklearn").__version__)
check("xgboost",       lambda: __import__("xgboost").__version__)
check("shap",          lambda: __import__("shap").__version__)
check("scipy",         lambda: __import__("scipy").__version__)

print(f"\n{BOLD}API Layer{RESET}")
check("fastapi",       lambda: __import__("fastapi").__version__)
check("uvicorn",       lambda: __import__("uvicorn").__version__)
check("pydantic",      lambda: __import__("pydantic").__version__)
check("slowapi",       lambda: _meta_version("slowapi"))

print(f"\n{BOLD}Cloud Connectors{RESET}")
check("google-cloud-bigquery",  lambda: __import__("google.cloud.bigquery", fromlist=["bigquery"]).__version__)
check("snowflake-connector",    lambda: __import__("snowflake.connector", fromlist=["connector"]).__version__)

print(f"\n{BOLD}Data Quality{RESET}")
check("great-expectations",     lambda: __import__("great_expectations").__version__)

print(f"\n{BOLD}Visualization{RESET}")
check("plotly",    lambda: __import__("plotly").__version__)
check("streamlit", lambda: __import__("streamlit").__version__)
check("matplotlib", lambda: __import__("matplotlib").__version__)
check("seaborn",   lambda: __import__("seaborn").__version__)

print(f"\n{BOLD}AI / NL Layer{RESET}")
# pandasai removed from requirements.txt — conflicts with pandas 3.x
# Using openai directly instead (see chat/chat_with_data.py)
check("openai",    lambda: __import__("openai").__version__)

print(f"\n{BOLD}Dev Tools{RESET}")
check("pytest",         lambda: __import__("pytest").__version__)
check("python-dotenv",  lambda: _meta_version("python-dotenv"))
check("pip-audit",      lambda: __import__("pip_audit").__version__)

print("\n" + "=" * 50)
print(f"{BOLD}If you see any ❌, run: pip install --no-cache-dir -r requirements.txt{RESET}\n")
