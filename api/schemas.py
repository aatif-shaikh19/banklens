"""
api/schemas.py
BankLens 2.0 — Pydantic Request/Response Schemas

TransactionInput:
  11 features matching the trained XGBoost model's feature set.
  All fields have Field constraints (ranges, descriptions, examples).

FraudPrediction:
  fraud_probability  — float 0–1
  risk_band          — Low / Medium / High / Critical
  recommendation     — human-readable action string
  model_version      — "xgboost-v2.0"

HealthResponse:
  status, model, model_loaded, version

Pydantic 2.10.6 — uses field_validator with @classmethod decorator.
"""

# Implement in Phase 4
