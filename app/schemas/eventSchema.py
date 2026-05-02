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


class WebIngestionRequest(BaseModel):
    queries: list[str] | None = None
    source_urls: list[str] | None = None
    city: str = "Hyderabad"
    max_search_results: int = 10
    include_search_result_snippets: bool = True
    train_model: bool = True


class Event(BaseModel):
    id: int
    event_name: str
    event_description: str
    event_date: date
    event_address: str
