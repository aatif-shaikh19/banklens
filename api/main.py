"""
api/main.py
BankLens 2.0 Fraud Scoring API -- FastAPI 0.136.3
AUC-ROC: 0.9040 | Trained on 472,432 rows | XGBoost 3.2.0
"""
import os
import time
import logging
import numpy as np
import joblib
from contextlib import asynccontextmanager
from dotenv import load_dotenv

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from api.schemas import TransactionInput, FraudPrediction, HealthResponse

load_dotenv()
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)

MODEL_PATH = os.getenv(
    "MODEL_PATH",
    os.path.join("ml", "model_artifacts", "fraud_model_xgb.pkl")
)

# Feature order MUST match notebook training (Cell 6) exactly
# V201 at index 9, V258 at index 10 -- do not reorder
FEATURE_ORDER = [
    "TransactionAmt", "ProductCD", "card4", "card6",
    "C1", "C6", "C13", "D1", "D15", "V201", "V258"
]

limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not os.path.exists(MODEL_PATH):
        raise RuntimeError(
            f"Model not found at {MODEL_PATH}\n"
            "Download fraud_model_xgb.pkl from Colab and place in ml/model_artifacts/"
        )
    logger.info(f"Loading model from {MODEL_PATH} ...")
    app.state.model = joblib.load(MODEL_PATH)
    logger.info("Model loaded -- AUC 0.9040 | 500 trees | 11 features")
    yield
    del app.state.model
    logger.info("Model unloaded on shutdown")


app = FastAPI(
    title="BankLens 2.0 -- Fraud Scoring API",
    description=(
        "XGBoost fraud probability scorer. "
        "AUC-ROC: 0.9040. Trained on IEEE-CIS dataset (472K rows). "
        "Part of BankLens 2.0 banking analytics platform by Aatif Shaikh."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["localhost", "127.0.0.1", "*.onrender.com"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"]         = "DENY"
    response.headers["X-XSS-Protection"]        = "1; mode=block"
    response.headers["Cache-Control"]           = "no-store"
    response.headers["Referrer-Policy"]         = "no-referrer"
    return response


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start    = time.time()
    response = await call_next(request)
    ms       = round((time.time() - start) * 1000, 1)
    logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({ms}ms)")
    return response


@app.post("/predict", response_model=FraudPrediction)
@limiter.limit("60/minute")
async def predict_fraud(request: Request, txn: TransactionInput):
    """
    Score a transaction for fraud probability.

    Feature order (CRITICAL -- must match training):
    TransactionAmt, ProductCD, card4, card6, C1, C6, C13, D1, D15, V201, V258

    Returns probability (0-1), risk_band, and recommended action.
    """
    try:
        # Build feature array in EXACT training order
        # V201 at index 9, V258 at index 10 -- verified against notebook Cell 6
        features = np.array([[
            txn.TransactionAmt,
            txn.ProductCD,
            txn.card4,
            txn.card6,
            txn.C1,
            txn.C6,
            txn.C13,
            txn.D1,
            txn.D15,
            txn.V201,   # index 9 -- matches FEATURES[9] in training
            txn.V258,   # index 10 -- matches FEATURES[10] in training
        ]])
        prob = float(request.app.state.model.predict_proba(features)[0][1])
    except Exception as exc:
        logger.error(f"Prediction error: {exc}")
        raise HTTPException(status_code=500, detail="Scoring error -- check server logs")

    if prob > 0.80:
        band = "Critical"
        rec  = "Block transaction immediately -- contact customer"
    elif prob > 0.50:
        band = "High"
        rec  = "Request step-up authentication (OTP / biometric)"
    elif prob > 0.20:
        band = "Medium"
        rec  = "Flag for manual review within 24 hours"
    else:
        band = "Low"
        rec  = "Approve"

    logger.info(f"amt={txn.TransactionAmt} card={txn.card4} -> prob={prob:.4f} [{band}]")

    return FraudPrediction(
        fraud_probability=round(prob, 4),
        risk_band=band,
        recommendation=rec,
    )


@app.get("/health", response_model=HealthResponse)
async def health(request: Request):
    loaded = hasattr(request.app.state, "model")
    return HealthResponse(
        status="healthy" if loaded else "degraded",
        model_loaded=loaded,
        model_version="xgboost-3.2.0-v1-auc0.9040",
    )


@app.get("/")
async def root():
    return {
        "project": "BankLens 2.0",
        "author": "Aatif Shaikh",
        "model_auc": "0.9040",
        "docs": "/docs",
        "health": "/health",
        "predict": "POST /predict",
    }
