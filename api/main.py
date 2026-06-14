"""
api/main.py
BankLens 2.0 — FastAPI Fraud Scoring API

Serves the trained XGBoost model via a secured REST endpoint.
Requires: ml/model_artifacts/fraud_model_xgb.pkl

Endpoints:
  POST /predict  — score a transaction, returns probability + risk_band + recommendation
  GET  /health   — liveness check, confirms model is loaded

Security:
  - Rate limiting: 60 requests/minute via slowapi
  - CORS: localhost:3000 and localhost:8501 only
  - TrustedHostMiddleware
  - Security headers: X-Content-Type-Options, X-Frame-Options, Cache-Control
  - All inputs validated with Pydantic Field constraints

FastAPI 0.136.3 — uses lifespan context manager (not deprecated @app.on_event)
Pydantic 2.10.6 — v2 syntax throughout

Usage:
  uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
  Then open: http://localhost:8000/docs
"""

# Implement in Phase 4
