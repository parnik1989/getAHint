import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression 
import joblib
import json
import os
from sentence_transformers import SentenceTransformer
from datetime import datetime

# Load the formatted JSON file.  
print("Loading data..." + pd.__version__)

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
    joblib.dump(pipeline, "app/ml/intentModel.pkl")
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
    Generic model training that works with any data structure
    Automatically discovers, loads, and trains on all available data
    """
    data_dir = "app/data/json"
    
    print(f"\nDiscovering data files in: {data_dir}")
    discovered_files = discover_data_files(data_dir)
    
    if not discovered_files:
        print(f"No data files found in {data_dir}")
        return {"files_loaded": 0, "total_records": 0, "error": "No data files found"}
    
    print(f"Found {len(discovered_files)} data file(s):")
    for fname, _ in discovered_files:
        print(f"  - {fname}")
    
    # Load all data files
    all_data = []
    file_stats = []
    
    for fname, fpath in discovered_files:
        print(f"\nLoading: {fname}...")
        df = load_data_file(fpath, fname)
        
        if df is None or df.empty:
            print(f"  ⚠ Skipped: No valid data")
            continue
        
        # Find best text column
        text_col = select_best_text_column(df)
        if text_col is None:
            print(f"  ⚠ Skipped: No suitable text column found")
            continue
        
        # Store data with metadata
        all_data.append({
            "source": fname,
            "dataframe": df,
            "text_column": text_col,
            "records": len(df)
        })
        
        file_stats.append({
            "file": fname,
            "records": len(df),
            "columns": list(df.columns),
            "text_column": text_col
        })
        
        print(f"  ✓ Loaded: {len(df)} records (using column: '{text_col}')")
    
    if not all_data:
        print("\nNo usable data found in any files")
        return {"files_loaded": 0, "total_records": 0, "error": "No usable data found"}
    
    # Combine all data
    print(f"\nCombining data from {len(all_data)} source(s)...")
    combined_texts = []
    combined_df = pd.DataFrame()
    
    for data_item in all_data:
        df = data_item["dataframe"]
        text_col = data_item["text_column"]
        
        # Add text to combined list
        combined_texts.extend(df[text_col].astype(str).tolist())
        
        # Add dataframe to combined
        combined_df = pd.concat([combined_df, df], ignore_index=True)
    
    total_records = len(combined_df)
    print(f"Total records to train on: {total_records}")
    
    if total_records == 0:
        return {"files_loaded": len(all_data), "total_records": 0, "error": "No records to train"}
    
    # Train semantic embedding model
    print(f"\nTraining semantic embedding model on {total_records} records...")
    print("Generating embeddings (this may take a moment)...")
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(combined_texts, show_progress_bar=True)
    
    # Compute similarity matrix
    print("Computing similarity matrix...")
    cosine_sim = cosine_similarity(embeddings)
    
    # Save complete model
    print("Saving trained model...")
    os.makedirs("app/ml", exist_ok=True)
    joblib.dump((model, embeddings, combined_df), "app/ml/eventModel.pkl")
    
    # Also save training metadata
    metadata = {
        "training_date": datetime.now().isoformat(),
        "total_records": total_records,
        "total_files": len(all_data),
        "file_stats": file_stats,
        "embedding_model": "all-MiniLM-L6-v2",
        "total_embeddings": len(embeddings)
    }
    joblib.dump(metadata, "app/ml/training_metadata.pkl")
    
    print("\n✓ Model saved successfully!")
    
    return {
        "files_loaded": len(all_data),
        "total_records": total_records,
        "embeddings_generated": len(embeddings),
        "file_stats": file_stats,
        "training_completed": True
    }

def testExistingModel(query: str):
    """
    Generic test function that finds similar items from trained model
    Works with any data type (events, products, content, etc.)
    """
    try:
        model, embeddings, df = joblib.load("app/ml/eventModel.pkl")
        print("Model loaded successfully.")
        
        # Encode query
        query_vec = model.encode([query])
        sim_scores = cosine_similarity(query_vec, embeddings)
        
        # Get top 5 similar items
        top_indices = sim_scores[0].argsort()[-5:][::-1]
        similar_items = df.iloc[top_indices]
        
        # Build results (generic - work with any columns)
        results = []
        for idx, row in similar_items.iterrows():
            result_str = f"Match {idx + 1}: "
            # Try to build a meaningful description from available columns
            for col in df.columns:
                if col in ['event_name', 'name', 'title']:
                    result_str += f"{row[col]}"
                    break
            if len(result_str) == len(f"Match {idx + 1}: "):
                result_str += str(row.iloc[0])
            
            results.append(result_str)
        
        return {"results": results, "total_matches": len(results)}
    
    except Exception as e:
        return {"error": str(e), "status": "Model not found or error in testing"}