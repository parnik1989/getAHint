import json
import math
import re
from datetime import date, datetime
from functools import lru_cache
from typing import Any, Dict, List

import pandas as pd
from sentence_transformers import SentenceTransformer
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.models import EventRecord
from app.models.eventModel import Event

EMBEDDING_MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIMENSIONS = 384
MIN_SIMILARITY_SCORE = 0.25
RELATIVE_SCORE_RATIO = 0.72
GENERIC_QUERY_TERMS = {
    "a",
    "about",
    "any",
    "at",
    "event",
    "events",
    "festival",
    "festivals",
    "find",
    "for",
    "happening",
    "hyderabad",
    "in",
    "me",
    "near",
    "of",
    "on",
    "show",
    "the",
    "to",
    "upcoming",
}
SHORT_MEANINGFUL_TERMS = {"ai", "ml", "vr", "ar", "dj", "qs"}


@lru_cache(maxsize=2)
def _load_embedding_model(allow_download=False):
    try:
        return SentenceTransformer(EMBEDDING_MODEL_NAME, local_files_only=True)
    except Exception:
        if not allow_download:
            raise
        return SentenceTransformer(EMBEDDING_MODEL_NAME)


def _clean_value(value):
    if value is None or pd.isna(value):
        return ""
    return str(value).strip()


def _parse_event_date(date_value):
    if date_value is None or pd.isna(date_value):
        return None

    date_text = str(date_value).strip()
    for date_format in ("%Y-%m-%d", "%d-%m-%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y"):
        try:
            parsed_date = datetime.strptime(date_text, date_format).date()
            return parsed_date
        except ValueError:
            continue

    for date_format in ("%b %d", "%B %d"):
        try:
            parsed_date = datetime.strptime(date_text, date_format).date().replace(year=date.today().year)
            if parsed_date < date.today():
                parsed_date = parsed_date.replace(year=parsed_date.year + 1)
            return parsed_date
        except ValueError:
            continue
    return None


def _event_search_text(event: EventRecord | Event | Dict[str, Any]):
    if isinstance(event, dict):
        event_name = event.get("event_name")
        event_description = event.get("event_description")
        event_date = event.get("event_date")
        event_address = event.get("event_address")
        category = event.get("category")
    else:
        event_name = event.event_name
        event_description = event.event_description
        event_date = event.event_date
        event_address = event.event_address
        category = getattr(event, "category", None)

    return " | ".join(
        value
        for value in (
            _clean_value(event_name),
            _clean_value(event_description),
            _clean_value(event_date),
            _clean_value(event_address),
            _clean_value(category),
        )
        if value
    )


def _encode_text(text_value: str) -> List[float]:
    model = _load_embedding_model(allow_download=True)
    embedding = model.encode([text_value])[0]
    return [float(value) for value in embedding]


def _encode_texts(text_values: List[str]) -> List[List[float]]:
    model = _load_embedding_model(allow_download=True)
    embeddings = model.encode(text_values, show_progress_bar=True)
    return [[float(value) for value in embedding] for embedding in embeddings]


def _vector_literal(embedding: List[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in embedding) + "]"


def _is_postgres(db: Session) -> bool:
    return db.bind is not None and db.bind.dialect.name == "postgresql"


def _cosine_similarity(left: List[float], right: List[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


def _row_to_result(row, similarity_score: float) -> Dict[str, Any]:
    parsed_date = _parse_event_date(row.event_date)
    event_date = parsed_date.isoformat() if parsed_date else _clean_value(row.event_date)
    return {
        "id": int(row.id) if row.id is not None else None,
        "event_name": _clean_value(row.event_name),
        "event_description": _clean_value(row.event_description),
        "event_date": event_date,
        "event_address": _clean_value(row.event_address),
        "category": _clean_value(getattr(row, "category", None)) or None,
        "similarity_score": round(float(similarity_score), 4),
    }


def store_event_embedding(db: Session, event_id: int) -> None:
    record = db.query(EventRecord).filter(EventRecord.id == event_id).one()
    embedding = _encode_text(_event_search_text(record))

    if _is_postgres(db):
        db.execute(
            text("UPDATE events SET event_embedding = CAST(:embedding AS vector) WHERE id = :event_id"),
            {"embedding": _vector_literal(embedding), "event_id": event_id},
        )
    else:
        record.embedding_json = json.dumps(embedding)

    db.commit()


def backfill_event_embeddings(db: Session) -> Dict[str, int]:
    records = db.query(EventRecord).order_by(EventRecord.id.asc()).all()
    if not records:
        return {"embedded_records": 0, "embedding_model": EMBEDDING_MODEL_NAME}

    embeddings = _encode_texts([_event_search_text(record) for record in records])
    for record, embedding in zip(records, embeddings):
        if _is_postgres(db):
            db.execute(
                text("UPDATE events SET event_embedding = CAST(:embedding AS vector) WHERE id = :event_id"),
                {"embedding": _vector_literal(embedding), "event_id": record.id},
            )
        else:
            record.embedding_json = json.dumps(embedding)
    db.commit()
    return {"embedded_records": len(records), "embedding_model": EMBEDDING_MODEL_NAME}


def search_events_by_embedding(db: Session, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    query_embedding = _encode_text(query)

    if _is_postgres(db):
        rows = db.execute(
            text(
                """
                SELECT
                    id,
                    event_name,
                    event_description,
                    event_date,
                    event_address,
                    category,
                    1 - (event_embedding <=> CAST(:embedding AS vector)) AS similarity_score
                FROM events
                WHERE event_embedding IS NOT NULL
                ORDER BY event_embedding <=> CAST(:embedding AS vector)
                LIMIT :limit
                """
            ),
            {"embedding": _vector_literal(query_embedding), "limit": top_k},
        ).mappings()
        return [
            {
                "id": row["id"],
                "event_name": row["event_name"],
                "event_description": row["event_description"],
                "event_date": row["event_date"],
                "event_address": row["event_address"],
                "category": row["category"],
                "similarity_score": round(float(row["similarity_score"]), 4),
            }
            for row in rows
        ]

    scored_results = []
    records = db.query(EventRecord).filter(EventRecord.embedding_json.isnot(None)).all()
    for record in records:
        embedding = json.loads(record.embedding_json)
        scored_results.append(_row_to_result(record, _cosine_similarity(query_embedding, embedding)))

    scored_results.sort(key=lambda result: result["similarity_score"], reverse=True)
    return scored_results[:top_k]


def search_events_hybrid(db: Session, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Search live database rows first, then blend in vector matches when embeddings are available.
    This keeps event answers current even when the periodic ingestion has not run model backfill.
    """
    candidate_limit = max(top_k * 4, 20)
    lexical_results = search_events_by_text(db, query, top_k=candidate_limit)
    merged_results = {result["id"]: result for result in lexical_results if result.get("id") is not None}

    if _has_stored_embeddings(db):
        try:
            for result in search_events_by_embedding(db, query, top_k=candidate_limit):
                event_id = result.get("id")
                if event_id in merged_results:
                    existing = merged_results[event_id]
                    existing["similarity_score"] = round(
                        max(existing["similarity_score"], result["similarity_score"]),
                        4,
                    )
                elif event_id is not None:
                    merged_results[event_id] = result
        except Exception as e:
            print(f"Embedding search skipped; using database text search only: {e}")

    results = list(merged_results.values())
    results.sort(key=lambda result: result["similarity_score"], reverse=True)
    return results[:candidate_limit]


def search_events_by_text(db: Session, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    query_terms = _meaningful_terms(query)
    wants_upcoming = _is_upcoming_query(query)
    today = date.today()
    records = db.query(EventRecord).order_by(EventRecord.event_date.asc(), EventRecord.id.asc()).all()
    scored_results = []

    for record in records:
        parsed_date = _parse_event_date(record.event_date)
        if parsed_date and parsed_date < today:
            continue

        score = _lexical_score(record, query_terms, wants_upcoming)
        if score <= 0 and query_terms:
            continue

        result = _row_to_result(record, score)
        if parsed_date:
            days_until_event = max((parsed_date - today).days, 0)
            result["_sort_days_until_event"] = days_until_event
        else:
            result["_sort_days_until_event"] = 99999
        scored_results.append(result)

    scored_results.sort(
        key=lambda result: (
            -result["similarity_score"],
            result["_sort_days_until_event"],
            result["event_name"].lower(),
        )
    )
    for result in scored_results:
        result.pop("_sort_days_until_event", None)
    return scored_results[:top_k]


def _lexical_score(record: EventRecord, query_terms: set[str], wants_upcoming: bool) -> float:
    if not query_terms:
        return 0.35 if wants_upcoming else 0.0

    name_terms = _meaningful_terms(record.event_name)
    description_terms = _meaningful_terms(record.event_description)
    address_terms = _meaningful_terms(record.event_address)
    category_terms = _meaningful_terms(getattr(record, "category", None) or "")
    overlap_score = (
        0.45 * len(query_terms & name_terms)
        + 0.3 * len(query_terms & description_terms)
        + 0.15 * len(query_terms & address_terms)
        + 0.25 * len(query_terms & category_terms)
    )
    coverage = len(query_terms & (name_terms | description_terms | address_terms | category_terms)) / max(len(query_terms), 1)
    score = min(0.95, overlap_score + (0.25 * coverage))
    if wants_upcoming and score > 0:
        score = min(0.98, score + 0.05)
    return round(score, 4)


def _has_stored_embeddings(db: Session) -> bool:
    if _is_postgres(db):
        row = db.execute(text("SELECT EXISTS (SELECT 1 FROM events WHERE event_embedding IS NOT NULL)")).scalar()
        return bool(row)
    return db.query(EventRecord.id).filter(EventRecord.embedding_json.isnot(None)).first() is not None


def filter_and_rank_results(results: List[Dict[str, Any]], query: str) -> tuple[List[Dict[str, Any]], bool, bool]:
    results = _filter_relevant_results(results, query)
    today = date.today()
    wants_upcoming = _is_upcoming_query(query)
    upcoming_results = []
    for result in results:
        parsed_date = _parse_event_date(result.get("event_date"))
        if parsed_date and parsed_date >= today:
            upcoming_results.append(result)

    results = sorted(
        upcoming_results,
        key=lambda result: (_parse_event_date(result.get("event_date")), -result["similarity_score"]),
    )

    return results, bool(wants_upcoming), False


def _filter_relevant_results(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    if not results:
        return []

    best_score = max(result["similarity_score"] for result in results)
    threshold = max(MIN_SIMILARITY_SCORE, best_score * RELATIVE_SCORE_RATIO)
    score_filtered = [result for result in results if result["similarity_score"] >= threshold]

    query_terms = _meaningful_terms(query)
    if len(query_terms) < 2:
        return score_filtered

    required_overlap = min(2, len(query_terms))
    return [
        result
        for result in score_filtered
        if len(query_terms & _meaningful_terms(_event_search_text(result))) >= required_overlap
    ]


def _meaningful_terms(text_value: str) -> set[str]:
    terms = set()
    for term in re.findall(r"[a-z0-9]+", text_value.lower()):
        if term in GENERIC_QUERY_TERMS:
            continue
        if len(term) > 2 or term in SHORT_MEANINGFUL_TERMS:
            terms.add(term)
            if len(term) > 3 and term.endswith("s") and not term.endswith("ss"):
                terms.add(term[:-1])
    return terms


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
