from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
ML_DIR = APP_DIR / "ml"

INTENT_MODEL_PATH = ML_DIR / "intentModel.pkl"
