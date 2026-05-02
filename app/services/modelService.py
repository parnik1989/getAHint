import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression 
import joblib
import os
from sentence_transformers import SentenceTransformer
from datetime import date, datetime
from app.core.paths import EVENT_MODEL_PATH, INTENT_MODEL_PATH, ML_DIR, TRAINING_METADATA_PATH
from app.services.event_service import consolidateAllEventsFromDataStore

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"


def _model_to_dict(model_instance):
    if hasattr(model_instance, "model_dump"):
        return model_instance.model_dump()
    return model_instance.dict()


def _load_embedding_model(allow_download=False):
    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    except Exception:
        if not allow_download:
            raise
        return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _parse_event_date(date_value):
    if date_value is None or pd.isna(date_value):
        return None

    date_text = str(date_value).strip()
    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%b %d"):
        try:
            parsed_date = datetime.strptime(date_text, date_format).date()
            if date_format == "%b %d":
                parsed_date = parsed_date.replace(year=2025)
            return parsed_date
        except ValueError:
            continue
    return None


def _clean_value(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _build_event_search_text(row):
    text_fields = [
        "event_name",
        "event_description",
        "event_date",
        "event_address",
        "event_category",
        "event_type",
    ]
    return " | ".join(_clean_value(row.get(field)) for field in text_fields if _clean_value(row.get(field)))


def _prepare_event_dataframe():
    events = consolidateAllEventsFromDataStore()
    records = []

    for event in events:
        record = _model_to_dict(event)
        parsed_date = _parse_event_date(record.get("event_date"))
        record["event_date"] = parsed_date.isoformat() if parsed_date else _clean_value(record.get("event_date"))
        record["search_text"] = _build_event_search_text(record)
        records.append(record)

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df = df[df["search_text"].astype(str).str.len() > 0].copy()
    df["event_date_dt"] = pd.to_datetime(df["event_date"], errors="coerce")
    return df


def _is_upcoming_query(query):
    query_text = query.lower()
    upcoming_terms = (
        "upcoming",
        "coming",
        "future",
        "next",
        "soon",
        "this week",
        "this month",
        "today",
        "tomorrow",
    )
    return any(term in query_text for term in upcoming_terms)


def _row_to_event_result(row):
    return {
        "id": int(row["id"]) if pd.notna(row.get("id")) else None,
        "event_name": _clean_value(row.get("event_name")),
        "event_description": _clean_value(row.get("event_description")),
        "event_date": _clean_value(row.get("event_date")),
        "event_address": _clean_value(row.get("event_address")),
        "similarity_score": round(float(row.get("similarity_score", 0)), 4),
    }


def format_event_answer(results, upcoming_only=False, fallback_to_past=False):
    if not results:
        return "I could not find matching events in the trained data."

    prefix = "I found these matching events:"
    if upcoming_only:
        prefix = "I found these matching upcoming events:"
    if fallback_to_past:
        prefix = "I could not find upcoming events in the trained data. Closest trained matches are:"

    lines = [prefix]
    for event in results:
        lines.append(
            f"- {event['event_name']} on {event['event_date']} at {event['event_address']}. "
            f"{event['event_description']}"
        )
    return "\n".join(lines)

def intent_train_model():
    """Train generic intent classification model"""
    # Universal training data that works for any content type
    training_data = [
        # Greetings
        ("hi", "greeting"),
        ("hello", "greeting"),
        ("hey", "greeting"),
        ("greetings", "greeting"),
        ("good morning", "greeting"),
        ("good afternoon", "greeting"),
        
        # Help requests
        ("help me", "help"),
        ("what can you do", "help"),
        ("can you assist me", "help"),
        ("i need help", "help"),
        ("assist me", "help"),
        ("tell me how to use this", "help"),
        
        # Search/Query requests
        ("show me items", "search"),
        ("find me something", "search"),
        ("search for", "search"),
        ("look for", "search"),
        ("find similar", "search"),
        ("show me related", "search"),
        ("what is available", "search"),
        ("list all", "search"),
        
        # Information requests
        ("tell me about", "information"),
        ("what is", "information"),
        ("describe", "information"),
        ("explain", "information"),
        ("i want to know", "information"),
        ("give me details", "information"),
        
        # Specific/Generic queries (generic enough for any content)
        ("show me items", "content_query"),
        ("what do you have", "content_query"),
        ("upcoming items", "content_query"),
        ("schedule", "content_query"),
        ("when is", "content_query"),
        ("where is", "content_query"),
        ("what are", "content_query"),
        ("can you find", "content_query"),
        ("search results", "content_query"),
        ("similar items", "content_query"),
        
        # Time-based queries
        ("this month", "content_query"),
        ("this week", "content_query"),
        ("coming soon", "content_query"),
        ("future items", "content_query"),
        ("when is next", "content_query"),
        
        # Feedback
        ("thanks", "feedback"),
        ("thank you", "feedback"),
        ("goodbye", "feedback"),
        ("bye", "feedback"),
        ("see you later", "feedback"),
        ("appreciate it", "feedback"),
    ]

    X_train = [text for text, label in training_data]
    y_train = [label for text, label in training_data]

    pipeline = Pipeline([
        ('vectorizer', CountVectorizer()),
        ('classifier', LogisticRegression())
    ])
    pipeline.fit(X_train, y_train)

    # Save model
    os.makedirs(ML_DIR, exist_ok=True)
    joblib.dump(pipeline, INTENT_MODEL_PATH)
    print("Intent model training completed.")
    return pipeline

def trainEventModelService(data_source: str = None):
    """
    Train the intent classifier and event retrieval model from database records.
    
    Args:
        data_source: Deprecated; kept for backward-compatible routes.
    
    Returns:
        Training status and statistics
    """
    print("=" * 60)
    print("STARTING GENERIC MODEL TRAINING")
    print("=" * 60)
    
    # Train intent model first
    print("\n[1/2] Training intent classification model...")
    intent_train_model()
    
    # Train content/data model
    print("\n[2/2] Training content embedding model...")
    training_stats = train_generic_model()
    
    print("\n" + "=" * 60)
    print("MODEL TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 60)
    
    return {
        "status": "Model training completed",
        "timestamp": datetime.now().isoformat(),
        "training_stats": training_stats
    }

def train_generic_model():
    """
    Train the event retrieval model on normalized event records from the database.
    """
    print("\nPreparing normalized event data from the database")
    combined_df = _prepare_event_dataframe()
    total_records = len(combined_df)
    print(f"Total records to train on: {total_records}")

    if total_records == 0:
        return {"total_records": 0, "error": "No event records to train"}

    combined_texts = combined_df["search_text"].astype(str).tolist()

    print(f"\nTraining semantic embedding model on {total_records} records...")
    print("Generating embeddings (this may take a moment)...")

    model = _load_embedding_model(allow_download=True)
    embeddings = model.encode(combined_texts, show_progress_bar=True)

    print("Saving trained model...")
    os.makedirs(ML_DIR, exist_ok=True)
    joblib.dump((EMBEDDING_MODEL_NAME, embeddings, combined_df), EVENT_MODEL_PATH)

    metadata = {
        "training_date": datetime.now().isoformat(),
        "total_records": total_records,
        "source": "database",
        "columns": list(combined_df.columns),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "total_embeddings": len(embeddings),
    }
    joblib.dump(metadata, TRAINING_METADATA_PATH)

    print("\n✓ Model saved successfully!")

    return {
        "source": "database",
        "total_records": total_records,
        "embeddings_generated": len(embeddings),
        "columns": list(combined_df.columns),
        "training_completed": True
    }

def testExistingModel(query: str, top_k: int = 5):
    """
    Find the most relevant trained events for a user query.
    """
    try:
        model_ref, embeddings, df = joblib.load(EVENT_MODEL_PATH)
        model = _load_embedding_model(allow_download=True) if isinstance(model_ref, str) else model_ref
        print("Model loaded successfully.")

        query_vec = model.encode([query])
        sim_scores = cosine_similarity(query_vec, embeddings)
        ranked_df = df.copy()
        ranked_df["similarity_score"] = sim_scores[0]
        ranked_df = ranked_df.sort_values("similarity_score", ascending=False)

        today = pd.Timestamp(date.today())
        wants_upcoming = _is_upcoming_query(query)
        fallback_to_past = False

        if wants_upcoming and "event_date_dt" in ranked_df.columns:
            upcoming_df = ranked_df[ranked_df["event_date_dt"].notna() & (ranked_df["event_date_dt"] >= today)]
            if not upcoming_df.empty:
                ranked_df = upcoming_df.sort_values(["event_date_dt", "similarity_score"], ascending=[True, False])
            else:
                fallback_to_past = True

        top_matches = ranked_df.head(top_k)
        results = [_row_to_event_result(row) for _, row in top_matches.iterrows()]

        return {
            "query": query,
            "answer": format_event_answer(
                results,
                upcoming_only=not fallback_to_past and bool(wants_upcoming),
                fallback_to_past=fallback_to_past,
            ),
            "results": results,
            "total_matches": len(results),
            "upcoming_only": not fallback_to_past and bool(wants_upcoming),
            "fallback_to_past": fallback_to_past,
        }

    except Exception as e:
        return {"error": str(e), "status": "Model not found or error in testing"}
