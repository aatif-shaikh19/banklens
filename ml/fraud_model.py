"""
ml/fraud_model.py
BankLens 2.0 — XGBoost Fraud Detection Model

Trained on Google Colab (free T4 GPU) using IEEE-CIS dataset.
Model artifact saved to ml/model_artifacts/fraud_model_xgb.pkl.

Key config:
  - XGBoost 3.2.0 (use_label_encoder removed, device='cpu' explicit)
  - n_estimators=500, max_depth=6, learning_rate=0.05
  - scale_pos_weight handles 97:3 class imbalance
  - AUC-ROC target: >= 0.85
  - Features: TransactionAmt, ProductCD, card4, card6,
              C1, C6, C13, D1, D15, V258, V201

See notebooks/banklens_fraud_model_colab.ipynb for the full Colab training notebook.
"""


FEATURES = [
    'TransactionAmt', 'ProductCD', 'card4', 'card6',
    'C1', 'C6', 'C13', 'D1', 'D15', 'V258', 'V201'
]
CATEGORICAL = ['ProductCD', 'card4', 'card6']
TARGET = 'isFraud'
MODEL_PATH = 'ml/model_artifacts/fraud_model_xgb.pkl'


def train(data_path: str = 'data/raw/train_transaction.csv',
          model_output: str = MODEL_PATH) -> float:
    """Train XGBoost model. Returns AUC-ROC. Implement in Phase 4."""
    raise NotImplementedError("Phase 4: run training in Colab, download .pkl")


if __name__ == "__main__":
    auc = train()
    print(f"Final AUC-ROC: {auc:.4f}")
