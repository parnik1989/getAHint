from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from typing import List
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.services.event_service import (
    consolidateAllEventsFromDataStore,
    process_image_file,
    upsert_event,
    upsert_events,
)
from app.models.eventModel import Event
from app.schemas.eventSchema import EventCreate

router = APIRouter()

@router.get("/getAllEventData", response_model=List[Event])
def get_all_events():
    return consolidateAllEventsFromDataStore()


@router.post("/events", response_model=Event, status_code=201)
def create_or_update_event(event: EventCreate, db: Session = Depends(get_db)):
    return upsert_event(db, event)


@router.post("/events/bulk")
def create_or_update_events(events: List[EventCreate], db: Session = Depends(get_db)):
    return upsert_events(db, events)


@router.post("/ingestEvents")
def ingest_events(events: List[EventCreate], db: Session = Depends(get_db)):
    return upsert_events(db, events)


@router.post("/uploadEventImage", response_model=List[Event], status_code=201)
async def upload_event_image(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")
    content = await file.read()
    try:
        events = process_image_file(db, content, file.filename)
        return events
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))
