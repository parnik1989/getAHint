import re
from typing import Any

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from app.core.paths import CATEGORY_MODEL_PATH, ML_DIR

CATEGORY_KEYWORDS = {
    "music": {
        "acoustic",
        "band",
        "bhajan",
        "bollywood",
        "concert",
        "dj",
        "fusion",
        "jam",
        "jamming",
        "live",
        "mehfill",
        "music",
        "musical",
        "sufi",
    },
    "tech": {
        "ai",
        "big data",
        "conference",
        "cyber",
        "digital security",
        "grafana",
        "iot",
        "machine learning",
        "ml",
        "nemotron",
        "technology",
        "tech",
    },
    "startup": {
        "entrepreneur",
        "entrepreneurs",
        "founder",
        "founders",
        "growth",
        "networking",
        "startup",
        "startups",
        "vc",
    },
    "comedy": {
        "comedy",
        "improv",
        "laugh",
        "punchliners",
        "stand-up",
        "standup",
    },
    "workshop": {
        "camp",
        "class",
        "masterclass",
        "training",
        "workshop",
    },
    "business": {
        "business",
        "expo",
        "fair",
        "healthcare",
        "jewellery",
        "pharma",
        "summit",
        "trade",
    },
    "education": {
        "education",
        "masters",
        "philosophy",
        "public speaking",
        "toastmasters",
    },
    "family": {
        "children",
        "daughter",
        "kids",
        "mother",
        "puppet",
        "teens",
    },
    "sports": {
        "marathon",
        "run",
        "waterthon",
    },
}


def classify_event_category(*values: Any) -> str:
    text = " ".join(str(value or "") for value in values).lower()
    model_category = _model_category(text)
    if model_category:
        return model_category

    return _rule_category(text)


def train_event_category_model() -> dict:
    training_data = _category_training_data()
    x_train = [text for text, _ in training_data]
    y_train = [label for _, label in training_data]

    pipeline = Pipeline(
        [
            ("vectorizer", TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
            ("classifier", LogisticRegression(max_iter=1000, class_weight="balanced")),
        ]
    )
    pipeline.fit(x_train, y_train)
    ML_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(pipeline, CATEGORY_MODEL_PATH)
    return {"category_training_examples": len(training_data), "category_model_path": str(CATEGORY_MODEL_PATH)}


def _model_category(text: str) -> str | None:
    if not CATEGORY_MODEL_PATH.exists():
        return None

    try:
        pipeline = joblib.load(CATEGORY_MODEL_PATH)
        if hasattr(pipeline, "predict_proba"):
            probabilities = pipeline.predict_proba([text])[0]
            best_index = probabilities.argmax()
            if probabilities[best_index] < 0.42:
                return None
        return pipeline.predict([text])[0]
    except Exception as e:
        print(f"Category model failed; using rules: {e}")
        return None


def _rule_category(text: str) -> str:
    scores = {}
    for category, keywords in CATEGORY_KEYWORDS.items():
        score = 0
        for keyword in keywords:
            if " " in keyword:
                if keyword in text:
                    score += 2
            elif re.search(rf"\b{re.escape(keyword)}\b", text):
                score += 1
        if score:
            scores[category] = score

    if not scores:
        return "general"
    return sorted(scores.items(), key=lambda item: (-item[1], item[0]))[0][0]


def category_from_query(query: str) -> str | None:
    category = classify_event_category(query)
    return None if category == "general" else category


def _category_training_data() -> list[tuple[str, str]]:
    examples = []
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            examples.extend(
                [
                    (f"upcoming {keyword} events", category),
                    (f"find {keyword} in Hyderabad", category),
                    (f"{keyword} happening this month", category),
                ]
            )
    examples.extend(
        [
            ("AI product leadership conference", "tech"),
            ("machine learning and big data systems", "tech"),
            ("startup founder networking and VC connect", "startup"),
            ("stand-up comedy night and improv show", "comedy"),
            ("live band concert and bollywood music", "music"),
            ("business expo and trade fair", "business"),
            ("public speaking toastmasters meeting", "education"),
            ("kids puppet show and family activity", "family"),
            ("virtual marathon and conservation run", "sports"),
        ]
    )
    return examples
