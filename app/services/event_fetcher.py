"""
Periodic event fetching service.

Replace EVENTS_API_URL with your actual event source.  The fetch/save
helpers are intentionally thin so they can be swapped for web-scraping,
a different REST API, or any other ingestion strategy without touching
the scheduler or the database layer.
"""
import logging
import os
from datetime import datetime

import requests
from sqlalchemy.orm import Session

from app.db.models import EventRecord
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — override via environment variables
# ---------------------------------------------------------------------------

# Primary REST endpoint to pull events from.  Set EVENTS_API_URL in your
# Railway service variables to point at a real source.
EVENTS_API_URL = os.getenv("EVENTS_API_URL", "https://api.example.com/events")

REQUEST_TIMEOUT_SECONDS = int(os.getenv("EVENTS_API_TIMEOUT", "10"))


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------


def fetch_events_from_source() -> list[dict]:
    """
    Fetch raw event records from the configured external source.

    Returns a list of dicts with at minimum the keys:
        event_name, event_description, event_date, event_address

    Returns an empty list on any error so callers can proceed safely.
    """
    try:
        response = requests.get(EVENTS_API_URL, timeout=REQUEST_TIMEOUT_SECONDS)
        response.raise_for_status()
        data = response.json()
        # Support both a bare list and {"events": [...]} envelope
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            return data.get("events") or data.get("data") or []
        return []
    except Exception as exc:
        logger.error("Failed to fetch events from %s: %s", EVENTS_API_URL, exc)
        return []


# ---------------------------------------------------------------------------
# Persist
# ---------------------------------------------------------------------------


def save_events_to_db(events_data: list[dict]) -> None:
    """
    Upsert a list of event dicts into the PostgreSQL events table.

    An event is matched by (event_name, event_date); if a match is found the
    description and address are refreshed, otherwise a new row is inserted.
    """
    db: Session = SessionLocal()
    try:
        saved = 0
        for event_data in events_data:
            name = event_data.get("event_name", "").strip()
            event_date = event_data.get("event_date", "").strip()
            if not name or not event_date:
                continue

            existing = (
                db.query(EventRecord)
                .filter(
                    EventRecord.event_name == name,
                    EventRecord.event_date == event_date,
                )
                .first()
            )

            if existing:
                existing.event_description = event_data.get("event_description", existing.event_description)
                existing.event_address = event_data.get("event_address", existing.event_address)
                existing.updated_at = datetime.utcnow()
            else:
                db.add(
                    EventRecord(
                        event_name=name,
                        event_description=event_data.get("event_description", ""),
                        event_date=event_date,
                        event_address=event_data.get("event_address", ""),
                        source_name=event_data.get("source_name"),
                        source_type=event_data.get("source_type", "api"),
                    )
                )
            saved += 1

        db.commit()
        logger.info("Saved/updated %d events in the database", saved)
    except Exception as exc:
        db.rollback()
        logger.error("Failed to save events to database: %s", exc)
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------


def periodic_event_update() -> None:
    """
    Fetch events from the external source and persist them to the database.

    Intended to be called by the background scheduler (app/tasks/scheduler.py)
    on a regular interval.
    """
    logger.info("Starting periodic event update…")
    events = fetch_events_from_source()
    if events:
        save_events_to_db(events)
        logger.info("Periodic event update completed — %d events processed", len(events))
    else:
        logger.info("Periodic event update completed — no events returned from source")
