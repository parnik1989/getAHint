from collections import Counter
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from app.db.models import EventInteraction, EventRecord
from app.schemas.eventSchema import EventInteractionCreate
from app.services.user_profile_service import explicit_category_preferences

INTERACTION_WEIGHTS = {
    "click": 1.0,
    "view": 0.5,
    "save": 2.0,
}


def record_event_interaction(db: Session, interaction: EventInteractionCreate) -> dict:
    record = EventInteraction(
        user_id=interaction.user_id,
        event_id=interaction.event_id,
        interaction_type=interaction.interaction_type,
        query=interaction.query,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return {"id": record.id, "status": "recorded"}


def user_category_preferences(db: Session, user_id: str | None) -> dict[str, float]:
    if not user_id:
        return {}

    scores = Counter()

    account_id = _account_id_from_public_user_id(user_id)
    for category, weight in explicit_category_preferences(db, account_id).items():
        scores[category] += weight

    rows = (
        db.query(EventInteraction.interaction_type, EventRecord.category)
        .join(EventRecord, EventRecord.id == EventInteraction.event_id)
        .filter(EventInteraction.user_id == user_id, EventRecord.category.isnot(None))
        .all()
    )
    for interaction_type, category in rows:
        scores[category] += INTERACTION_WEIGHTS.get(interaction_type, 1.0)
    return dict(scores)


def personalize_results(db: Session, results: List[Dict[str, Any]], user_id: str | None) -> List[Dict[str, Any]]:
    preferences = user_category_preferences(db, user_id)
    if not preferences:
        return results

    max_preference = max(preferences.values())
    personalized = []
    for result in results:
        category = result.get("category")
        boost = 0.0
        if category in preferences and max_preference > 0:
            boost = min(0.15, 0.15 * (preferences[category] / max_preference))
        adjusted = {**result, "personalization_boost": round(boost, 4)}
        adjusted["similarity_score"] = round(float(adjusted.get("similarity_score", 0)) + boost, 4)
        personalized.append(adjusted)

    personalized.sort(key=lambda result: result["similarity_score"], reverse=True)
    return personalized


def has_user_preferences(db: Session, user_id: str | None) -> bool:
    return bool(user_category_preferences(db, user_id))


def _account_id_from_public_user_id(user_id: str | None) -> int | None:
    if not user_id or not user_id.startswith("user-"):
        return None
    try:
        return int(user_id.split("-", 1)[1])
    except ValueError:
        return None
