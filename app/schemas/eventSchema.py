from pydantic import BaseModel
from datetime import date

from app.models.eventModel import EventType


class EventCreate(BaseModel):
    event_name: str
    event_description: str
    event_date: str
    event_address: str
    source_name: str | None = None
    source_type: str | None = None


class Event(BaseModel):
    id: int
    event_name: str
    event_description: str
    event_date: date
    event_address: str
