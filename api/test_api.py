"""
api/test_api.py
FastAPI endpoint tests. Run: pytest api\test_api.py -v
"""
import pytest
from fastapi.testclient import TestClient

# Feature order matches training: V201 before V258
LEGIT_TRANSACTION = {
    "TransactionAmt": 50.00,
    "ProductCD": 0, "card4": 3, "card6": 0,
    "C1": 1.0, "C6": 1.0, "C13": 1.0,
    "D1": 30.0, "D15": 60.0,
    "V201": 0.1, "V258": 0.1,
}

HIGH_RISK_TRANSACTION = {
    "TransactionAmt": 9999.99,
    "ProductCD": 2, "card4": 0, "card6": 1,
    "C1": 50.0, "C6": 30.0, "C13": 45.0,
    "D1": -999.0, "D15": -999.0,
    "V201": 7.2, "V258": 8.5,
}


@pytest.fixture(scope="module")
def client():
    from api.main import app
    with TestClient(app, base_url="http://localhost") as c:
        yield c


def test_health_ok(client):
    r = client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["model_loaded"] is True
    assert data["auc_score"] == "0.9040"


def test_predict_returns_valid_structure(client):
    r = client.post("/predict", json=LEGIT_TRANSACTION)
    assert r.status_code == 200
    data = r.json()
    assert 0.0 <= data["fraud_probability"] <= 1.0
    assert data["risk_band"] in ["Low", "Medium", "High", "Critical"]
    assert len(data["recommendation"]) > 0


def test_legit_transaction_low_risk(client):
    r = client.post("/predict", json=LEGIT_TRANSACTION)
    prob = r.json()["fraud_probability"]
    assert prob < 0.50, f"Expected low probability, got {prob}"


def test_negative_amount_rejected(client):
    bad = {**LEGIT_TRANSACTION, "TransactionAmt": -100.0}
    assert client.post("/predict", json=bad).status_code == 422


def test_missing_field_rejected(client):
    assert client.post("/predict", json={"TransactionAmt": 100.0}).status_code == 422


def test_security_headers(client):
    r = client.get("/health")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"
    assert r.headers.get("Cache-Control") == "no-store"


def test_root_endpoint(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["model_auc"] == "0.9040"
