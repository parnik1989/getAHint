from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression 
import joblib
import os
from datetime import datetime
from app.core.paths import INTENT_MODEL_PATH, ML_DIR
from app.db.schema import ensure_database_schema
from app.db.session import engine
from app.db.session import SessionLocal
from app.services.vector_service import backfill_event_embeddings, filter_and_rank_results, search_events_hybrid


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

def testExistingModel(query: str, top_k: int = 5):
    """
    Find the most relevant trained events for a user query.
    """
    try:
        db = SessionLocal()
        try:
            results = search_events_hybrid(db, query, top_k=max(top_k * 4, 10))
            results, upcoming_only, fallback_to_past = filter_and_rank_results(results, query)
            results = results[:top_k]
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
        }

    except Exception as e:
        return {"error": str(e), "status": "Model not found or error in testing"}
