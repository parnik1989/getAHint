from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = APP_DIR / "data" / "json"
ML_DIR = APP_DIR / "ml"

EVENT_MODEL_PATH = ML_DIR / "eventModel.pkl"
INTENT_MODEL_PATH = ML_DIR / "intentModel.pkl"
TRAINING_METADATA_PATH = ML_DIR / "training_metadata.pkl"
