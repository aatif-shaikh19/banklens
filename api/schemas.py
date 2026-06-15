"""
api/schemas.py
Pydantic request/response schemas for BankLens 2.0 fraud scoring API.
Feature order matches notebook training order exactly:
TransactionAmt, ProductCD, card4, card6, C1, C6, C13, D1, D15, V201, V258
"""
from pydantic import BaseModel, Field
from typing import Optional


class TransactionInput(BaseModel):
    TransactionAmt: float = Field(
        ..., gt=0, le=50000,
        description="Transaction amount in USD",
        examples=[500.00]
    )
    ProductCD: int = Field(
        ..., ge=0, le=4,
        description="Encoded product code: C=0, H=1, R=2, S=3, W=4",
        examples=[0]
    )
    card4: int = Field(
        ..., ge=0, le=3,
        description="Encoded card network: amex=0, discover=1, mastercard=2, visa=3",
        examples=[3]
    )
    card6: int = Field(
        ..., ge=0, le=1,
        description="Encoded card type: credit=0, debit=1",
        examples=[0]
    )
    C1:  float = Field(..., ge=0, description="Recipient count for this card", examples=[3.0])
    C6:  float = Field(..., ge=0, description="Address count feature", examples=[1.0])
    C13: float = Field(..., ge=0, description="Count feature 13 -- top fraud predictor", examples=[2.0])
    D1:  float = Field(..., description="Days since last transaction (-999 if first)", examples=[5.0])
    D15: float = Field(..., description="Days feature 15", examples=[10.0])
    V201: float = Field(..., description="Vesta risk feature 201", examples=[0.3])
    V258: float = Field(..., description="Vesta risk feature 258", examples=[0.5])

    model_config = {
        "json_schema_extra": {
            "example": {
                "TransactionAmt": 500.00,
                "ProductCD": 0,
                "card4": 3,
                "card6": 0,
                "C1": 3.0, "C6": 1.0, "C13": 2.0,
                "D1": 5.0, "D15": 10.0,
                "V201": 0.3, "V258": 0.5
            }
        }
    }


class FraudPrediction(BaseModel):
    fraud_probability: float = Field(..., description="Fraud probability 0-1")
    risk_band: str = Field(..., description="Low / Medium / High / Critical")
    recommendation: str = Field(..., description="Recommended action")
    model_version: str = Field(default="xgboost-3.2.0-v1-auc0.9040")


class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    auc_score: str = "0.9040"
    model_version: Optional[str] = None
    api_version: str = "2.0.0"
