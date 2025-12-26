import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import joblib
import json
import os

# Load the formatted JSON file
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
        if not fname.lower().endswith(".json"):
            continue
        path = os.path.join(json_dir, fname)
        try:
            # try pandas reader first, fallback to json.load
            try:
                df_part = pd.read_json(path)
            except ValueError:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                df_part = pd.DataFrame(data)
            if "event_description" not in df_part.columns:
                print(f"Skipping {fname}: no 'event_description' column")
                continue
            dfs.append(df_part)
            print(f"Loaded {len(df_part)} rows from {fname}")
        except Exception as e:
            print(f"Failed to load {path}: {e}")
            continue

    if not dfs:
        print("No valid JSON files with event_description found.")
        return

    df = pd.concat(dfs, ignore_index=True)
    df = df.dropna(subset=["event_description"])
    print(f"Total events for training: {len(df)}")
    # Step 1: Vectorize event descriptions
    vectorizer = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(df["event_description"])

    # Step 2: Compute similarity matrix
    cosine_sim = cosine_similarity(tfidf_matrix, tfidf_matrix)

    # Step 3: Save model snapshot
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

    print("Top similar events to '{}':".format(test_event))
    print(similar_events[["event_name", "event_description", "event_date"]])

    return {"status": "Model tested successfully", "similar_events": similar_events.to_dict(orient="records")}