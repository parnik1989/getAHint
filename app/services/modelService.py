import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import json
import os

# Load the formatted JSON file.  
print("Loading puja schedule data..." + pd.__version__)


def trainEventModelService(club: str):
    train_model(club)
    # Add actual model training code here
    return {"status": "Model training initiated"}

def train_model(club: str):
    json_dir = "app/data/json"
    if not os.path.isdir(json_dir):
        print(f"JSON directory not found: {json_dir}")
        return

    dfs = []
    for fname in os.listdir(json_dir):
        if not fname.lower().endswith((".json", ".txt")):
            continue
        path = os.path.join(json_dir, fname)
        try:
            if fname.lower().endswith(".txt"):
                # Read each line as "event_name | event_date"
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                events = []
                for line in lines:
                    parts = line.strip().split("|")
                    if len(parts) == 2:
                        event_name = parts[0].strip()
                        event_date = parts[1].strip()
                        events.append({
                            "event_name": event_name,
                            "event_description": event_name,
                            "event_date": event_date
                        })
                df_part = pd.DataFrame(events)
            elif fname.lower().endswith(".json"):
                try:
                    df_part = pd.read_json(path)
                except ValueError:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    df_part = pd.DataFrame(data)
            else:
                continue

            if "event_description" not in df_part.columns:
                print(f"Skipping {fname}: no 'event_description' column")
                continue
            dfs.append(df_part)
            print(f"Loaded {len(df_part)} rows from {fname}")
        except Exception as e:
            print(f"Failed to load {path}: {e}")
            continue

    if not dfs:
        print("No data files loaded for training.")
        return

    df = pd.concat(dfs, ignore_index=True)
    print(f"Total events for training: {len(df)}")
    # Step 1: Vectorize event descriptions
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(df["event_description"].astype(str))

    # Step 2: Compute similarity matrix
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Step 3: Save model snapshot
    os.makedirs("app/ml", exist_ok=True)
    joblib.dump((vectorizer, cosine_sim, df), "app/ml/eventModel.pkl")

def testExistingModel(event_description: str):
    # Load the trained model
    vectorizer, cosine_sim, df = joblib.load("app/ml/eventModel.pkl")
    print("Model loaded successfully.")

    # Example test: Find similar events to a given event description
    test_event = event_description
    test_vec = vectorizer.transform([test_event])
    sim_scores = cosine_similarity(test_vec, vectorizer.transform(df["event_description"]))

    # Get top 5 similar events
    top_indices = sim_scores[0].argsort()[-5:][::-1]
    similar_events = df.iloc[top_indices]

    return {similar_events.to_dict(orient="records")[0]['event_name']+" at "+similar_events.to_dict(orient="records")[0]['event_date']}