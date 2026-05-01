import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression 
import joblib
import json
import os
from sentence_transformers import SentenceTransformer
from datetime import date, datetime
from app.services.event_service import consolidateAllEventsFromDataStore

EVENT_MODEL_PATH = "app/ml/eventModel.pkl"
INTENT_MODEL_PATH = "app/ml/intentModel.pkl"
TRAINING_METADATA_PATH = "app/ml/training_metadata.pkl"
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

def discover_text_columns(df):
    """Automatically discover text columns suitable for semantic search"""
    text_candidates = []
    for col in df.columns:
        print(f"  Checking column: {col} (dtype: {df[col].dtype})")
        if df[col].dtype == 'str' or df[col].dtype == 'int64' or df[col].dtype == 'object' :
            # Check if column contains meaningful text
            # Calculate average text length across multiple rows
            text_lengths = df[col].astype(str).str.len()
            avg_length = text_lengths.mean()
            non_empty_count = (text_lengths > 0).sum()
            
            # Accept if average text is substantial OR mostly non-empty
            #if avg_length >= 5 or (non_empty_count / len(df) > 0.7 if len(df) > 0 else False):
            text_candidates.append(col)
    return text_candidates

def discover_data_files(data_dir):
    """Automatically discover all data files in the directory"""
    discovered_files = []
    if not os.path.isdir(data_dir):
        print(f"Data directory not found: {data_dir}")
        return discovered_files
    
    for fname in os.listdir(data_dir):
        if fname.lower().endswith((".json", ".txt", ".csv")):
            path = os.path.join(data_dir, fname)
            if os.path.isfile(path):
                discovered_files.append((fname, path))
    
    return discovered_files

def load_data_file(file_path, file_name):
    """Intelligently load data from various file formats"""
    try:
        if file_name.lower().endswith(".json"):
            try:
                df = pd.read_json(file_path)
            except ValueError:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                df = pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame([data])
        
        elif file_name.lower().endswith(".csv"):
            df = pd.read_csv(file_path)
        
        elif file_name.lower().endswith(".txt"):
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            data_rows = []
            
            # Check if it's pipe-delimited format (simple flat format)
            if "|" in content:
                lines = content.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line or line.startswith("#") or "==" in line:
                        continue
                    parts = [p.strip() for p in line.split("|")]
                    data_rows.append({"text": " ".join(parts)})
            else:
                # Parse structured format with key-value pairs (Date:, Location:, Description:, etc)
                lines = content.split("\n")
                current_record = {}
                
                for line in lines:
                    line = line.rstrip()
                    
                    # Skip headers and empty section markers
                    if "==" in line or (line.upper() == line and len(line) > 2):
                        if current_record and "text" in current_record:
                            data_rows.append(current_record)
                            current_record = {}
                        continue
                    
                    # Check for key-value pairs (Date:, Location:, Description:, etc)
                    if ":" in line and len(line.split(":")) == 2:
                        key, value = line.split(":", 1)
                        key = key.strip().lower().replace(" ", "_")
                        value = value.strip()
                        
                        if key == "description" or len(value) > 10:
                            current_record[key] = value
                    
                    # If line is just text (no colon, not empty)
                    elif line.strip() and ":" not in line:
                        # First substantial line becomes title/name
                        if "name" not in current_record and len(line.strip()) > 3:
                            current_record["name"] = line.strip()
                
                # Add final record
                if current_record:
                    data_rows.append(current_record)
                
                # Create unified "text" column from all fields for embeddings
                for row in data_rows:
                    text_parts = []
                    for key in ["name", "description", "location", "date", "duration"]:
                        if key in row:
                            text_parts.append(str(row[key]))
                    row["text"] = " | ".join(text_parts)
            
            df = pd.DataFrame(data_rows) if data_rows else pd.DataFrame()
        
        else:
            return None
        
        if df.empty:
            return None
        
        return df
    
    except Exception as e:
        print(f"Error loading {file_name}: {e}")
        return None

def select_best_text_column(df):
    """Select the most suitable text column for embeddings"""
    text_candidates = discover_text_columns(df)
    print(f"  Found text candidates: {text_candidates}")
    if not text_candidates:
        return None
    
    # Prioritize columns with longer average text
    best_col = max(text_candidates, 
                   key=lambda col: df[col].astype(str).str.len().mean())
    return best_col

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
    os.makedirs("app/ml", exist_ok=True)
    joblib.dump(pipeline, INTENT_MODEL_PATH)
    print("Intent model training completed.")
    return pipeline

def trainEventModelService(data_source: str = None):
    """
    Generic model training that automatically discovers and trains on all available data
    
    Args:
        data_source: Optional specific data source/club name (for backward compatibility)
    
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
    Train the event retrieval model on normalized event records.
    """
    data_dir = "app/data/json"
    discovered_files = discover_data_files(data_dir)

    print(f"\nPreparing normalized event data from: {data_dir}")
    combined_df = _prepare_event_dataframe()
    total_records = len(combined_df)
    print(f"Total records to train on: {total_records}")

    if total_records == 0:
        return {"files_loaded": 0, "total_records": 0, "error": "No event records to train"}

    combined_texts = combined_df["search_text"].astype(str).tolist()

    print(f"\nTraining semantic embedding model on {total_records} records...")
    print("Generating embeddings (this may take a moment)...")

    model = _load_embedding_model(allow_download=True)
    embeddings = model.encode(combined_texts, show_progress_bar=True)

    print("Saving trained model...")
    os.makedirs("app/ml", exist_ok=True)
    joblib.dump((EMBEDDING_MODEL_NAME, embeddings, combined_df), EVENT_MODEL_PATH)

    metadata = {
        "training_date": datetime.now().isoformat(),
        "total_records": total_records,
        "total_files": len(discovered_files),
        "files": [file_name for file_name, _ in discovered_files],
        "columns": list(combined_df.columns),
        "embedding_model": EMBEDDING_MODEL_NAME,
        "total_embeddings": len(embeddings),
    }
    joblib.dump(metadata, TRAINING_METADATA_PATH)

    print("\n✓ Model saved successfully!")

    return {
        "files_loaded": len(discovered_files),
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
