from datetime import datetime
from enum import Enum

from pydantic import BaseModel
from sqlalchemy import Column, DateTime, Integer, String

from app.db.base import Base


class EventType(Enum):
    CONFERENCE = "conference"
    MEETUP = "meetup"
    WORKSHOP = "workshop"
    WEBINAR = "webinar"
    HACKATHON = "hackathon"
    SOCIAL = "social"


class Event(BaseModel):
    id: int
    event_name: str
    event_description: str
    event_date: str
    event_address: str


class EventDB(Base):
    """
    SQLAlchemy ORM model for the events table.

    This mirrors app.db.models.EventRecord and is provided as a named export
    from app.models for code that imports EventDB from this module.  Both
    classes map to the same 'events' table — use whichever import path is
    more convenient; they are interchangeable at the ORM level.
    """

    __tablename__ = "events"
    # Avoid re-declaring the table when EventRecord (app.db.models) is also
    # imported in the same process — SQLAlchemy raises if two mapped classes
    # share a table without extend_existing.
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, index=True)
    event_name = Column(String(255), nullable=False)
    event_description = Column(String, nullable=False)
    event_date = Column(String(50), nullable=False, index=True)
    event_address = Column(String(500), nullable=False)
    event_category = Column(String(255), nullable=True)
    event_type = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)