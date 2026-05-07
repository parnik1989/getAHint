from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression 
import joblib
import os
from datetime import datetime
from app.core.paths import INTENT_MODEL_PATH, ML_DIR
from app.db.models import EventRecord
from app.db.schema import ensure_database_schema
from app.db.session import engine
from app.db.session import SessionLocal
from app.services.answer_generation_service import generate_event_answer
from app.services.category_service import classify_event_category, train_event_category_model
from app.services.personalization_service import personalize_results
from app.services.vector_service import backfill_event_embeddings, filter_and_rank_results, search_events_hybrid

EVENT_QUERY_INTENTS = {"content_query", "search", "information", "event_query"}
CONVERSATIONAL_RESPONSES = {
    "greeting": "Hello! Ask me about upcoming events in Hyderabad.",
    "help": "You can ask me things like 'upcoming AI workshops', 'music events this weekend', or 'startup events in Hyderabad'.",
    "feedback": "Thanks! Ask me anytime about upcoming events in Hyderabad.",
}


def format_event_answer(results, upcoming_only=False, fallback_to_past=False):
    return generate_event_answer("", results, upcoming_only=upcoming_only)


def classify_intent(message: str) -> str:
    rule_intent = _rule_based_intent(message)
    if rule_intent:
        return rule_intent

    if not INTENT_MODEL_PATH.exists():
        intent_train_model()

    try:
        pipeline = joblib.load(INTENT_MODEL_PATH)
        return pipeline.predict([message])[0]
    except Exception as e:
        print(f"Intent classification failed; treating as event query: {e}")
        return "content_query"


def build_chat_response(message: str, top_k: int = 5, user_id: str | None = None):
    message = message.strip()
    if not message:
        return {"answer": "Ask me about upcoming events in Hyderabad.", "results": [], "total_matches": 0, "intent": "empty"}

    intent = classify_intent(message)
    if intent in CONVERSATIONAL_RESPONSES:
        return {
            "answer": CONVERSATIONAL_RESPONSES[intent],
            "results": [],
            "total_matches": 0,
            "intent": intent,
        }

    if intent not in EVENT_QUERY_INTENTS:
        return {
            "answer": "I can help with upcoming events in Hyderabad. Try asking about concerts, workshops, conferences, or startup events.",
            "results": [],
            "total_matches": 0,
            "intent": intent,
        }

    model_response = testExistingModel(message, top_k=top_k, user_id=user_id)
    return {
        "answer": model_response.get("answer") or model_response.get("error", "I could not find an answer."),
        "results": model_response.get("results", []),
        "total_matches": model_response.get("total_matches", 0),
        "intent": intent,
        "query_category": model_response.get("query_category"),
    }


def _rule_based_intent(message: str) -> str | None:
    normalized = message.strip().lower()
    normalized = normalized.strip(" .,!?:;")
    if normalized in {"hi", "hello", "hey", "hii", "hola", "good morning", "good afternoon", "good evening"}:
        return "greeting"
    if normalized in {"thanks", "thank you", "bye", "goodbye", "see you"}:
        return "feedback"
    if normalized in {"help", "help me", "what can you do", "how can you help"}:
        return "help"
    return None

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
        ('vectorizer', TfidfVectorizer(ngram_range=(1, 2), min_df=1)),
        ('classifier', LogisticRegression(max_iter=1000, class_weight="balanced"))
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
    print("\n[1/3] Training intent classification model...")
    intent_train_model()
    
    # Train content/data model
    print("\n[2/3] Training event category classifier...")
    category_stats = train_event_category_model()
    categorize_stats = categorize_existing_events()

    print("\n[3/3] Training content embedding model...")
    training_stats = train_generic_model()
    
    print("\n" + "=" * 60)
    print("MODEL TRAINING COMPLETED SUCCESSFULLY")
    print("=" * 60)
    
    return {
        "status": "Model training completed",
        "timestamp": datetime.now().isoformat(),
        "training_stats": {
            **training_stats,
            **category_stats,
            **categorize_stats,
        }
    }


def categorize_existing_events():
    ensure_database_schema(engine)
    db = SessionLocal()
    try:
        records = db.query(EventRecord).all()
        updated = 0
        for record in records:
            category = classify_event_category(record.event_name, record.event_description, record.event_address)
            if record.category != category:
                record.category = category
                updated += 1
        db.commit()
        return {"categorized_records": len(records), "category_updates": updated}
    finally:
        db.close()

def train_generic_model():
    """
    Backfill per-event database embeddings for vector search.
    """
    print("\nBackfilling event embeddings in the database")
    ensure_database_schema(engine)
    db = SessionLocal()
    try:
        stats = backfill_event_embeddings(db)
        return {**stats, "source": "database_vectors", "training_completed": True}
    finally:
        db.close()

def testExistingModel(query: str, top_k: int = 5, user_id: str | None = None):
    """
    Find the most relevant trained events for a user query.
    """
    try:
        db = SessionLocal()
        try:
            results = search_events_hybrid(db, query, top_k=max(top_k * 4, 10))
            results = personalize_results(db, results, user_id)
            results, upcoming_only, fallback_to_past = filter_and_rank_results(results, query)
            results = results[:top_k]
            query_category = classify_event_category(query)
        finally:
            db.close()

        return {
            "query": query,
            "answer": format_event_answer(
                results,
                upcoming_only=upcoming_only,
                fallback_to_past=fallback_to_past,
            ),
            "results": results,
            "total_matches": len(results),
            "upcoming_only": upcoming_only,
            "fallback_to_past": fallback_to_past,
            "query_category": query_category if query_category != "general" else None,
        }

    except Exception as e:
        return {"error": str(e), "status": "Model not found or error in testing"}
