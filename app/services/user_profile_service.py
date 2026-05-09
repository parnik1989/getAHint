from sqlalchemy.orm import Session

from app.db.models import UserPreference, UserProfile
from app.schemas.authSchema import UserProfileUpdate

SUPPORTED_CATEGORIES = {
    "business",
    "comedy",
    "cultural",
    "education",
    "family",
    "general",
    "music",
    "sports",
    "startup",
    "tech",
    "workshop",
}


def get_profile(db: Session, user_id: int) -> dict:
    profile = _ensure_profile(db, user_id)
    return _profile_to_dict(db, profile)


def update_profile(db: Session, user_id: int, request: UserProfileUpdate) -> dict:
    profile = _ensure_profile(db, user_id)
    profile.display_name = _clean_text(request.display_name, max_length=100)
    profile.city = _clean_text(request.city, max_length=100) or "Hyderabad"

    categories = [
        category.strip().lower()
        for category in request.preferred_categories
        if category.strip().lower() in SUPPORTED_CATEGORIES
    ]
    db.query(UserPreference).filter(UserPreference.user_id == user_id).delete()
    for category in sorted(set(categories)):
        db.add(UserPreference(user_id=user_id, category=category, weight=3))

    db.commit()
    db.refresh(profile)
    return _profile_to_dict(db, profile)


def explicit_category_preferences(db: Session, user_id: int | None) -> dict[str, float]:
    if user_id is None:
        return {}

    rows = db.query(UserPreference.category, UserPreference.weight).filter(UserPreference.user_id == user_id).all()
    return {category: float(weight) for category, weight in rows}


def _ensure_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).one_or_none()
    if profile:
        return profile

    profile = UserProfile(user_id=user_id, city="Hyderabad")
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _profile_to_dict(db: Session, profile: UserProfile) -> dict:
    preferences = (
        db.query(UserPreference.category)
        .filter(UserPreference.user_id == profile.user_id)
        .order_by(UserPreference.category.asc())
        .all()
    )
    return {
        "user_id": f"user-{profile.user_id}",
        "display_name": profile.display_name,
        "city": profile.city or "Hyderabad",
        "preferred_categories": [row.category for row in preferences],
        "supported_categories": sorted(SUPPORTED_CATEGORIES),
    }


def _clean_text(value: str | None, max_length: int) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:max_length] if value else None
