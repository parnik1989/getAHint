from pydantic import BaseModel
from datetime import date

from app.models.eventModel import EventType

class Event(BaseModel):
    id: int
    event_name: str
    event_description: str
    event_date: date
    event_address: str
    class Config:
        orm_mode = True
