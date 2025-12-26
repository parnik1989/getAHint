from pydantic import BaseModel
from enum import Enum


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