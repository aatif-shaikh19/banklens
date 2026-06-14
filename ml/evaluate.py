"""
ml/evaluate.py
BankLens 2.0 — Model Evaluation

Computes and prints evaluation metrics for the trained XGBoost model:
  - AUC-ROC score (target: >= 0.85)
  - Classification report (precision, recall, F1)
  - Confusion matrix

Requires: ml/model_artifacts/fraud_model_xgb.pkl (from Phase 4 Colab training)
"""


def evaluate(model_path: str = 'ml/model_artifacts/fraud_model_xgb.pkl',
             data_path: str = 'data/raw/train_transaction.csv') -> dict:
    """Load model and compute evaluation metrics. Implement in Phase 4."""
    raise NotImplementedError("Phase 4: implement after model is trained in Colab")


if __name__ == "__main__":
    metrics = evaluate()
    print(metrics)
