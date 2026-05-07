from fastapi import APIRouter, Depends, File, HTTPException, status, UploadFile
from typing import List
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.eventSchema import EventInteractionCreate
from app.services.event_service import (
    consolidateAllEventsFromDataStore,
    process_image_file,
    upsert_event,
    upsert_events,
)
from app.models.eventModel import Event
from app.schemas.eventSchema import EventCreate, WebIngestionRequest
from app.services.personalization_service import record_event_interaction
from app.services.web_ingestion_service import ingest_web_events

router = APIRouter()


def _train_model_after_ingestion(train_model: bool):
    if not train_model:
        return None
    return {
        "status": "Vector embedding updated during ingestion",
        "mode": "per_event_embedding",
    }

@router.get("/getAllEventData", response_model=List[Event], include_in_schema=False)
def get_all_events():
    return consolidateAllEventsFromDataStore()


@router.post("/events", status_code=201, include_in_schema=False)
def create_or_update_event(event: EventCreate, train_model: bool = True, db: Session = Depends(get_db)):
    saved_event = upsert_event(db, event, update_embedding=train_model)
    training_result = _train_model_after_ingestion(train_model)
    return {"event": saved_event, "model_training": training_result}


@router.post("/events/bulk", include_in_schema=False)
def create_or_update_events(events: List[EventCreate], train_model: bool = True, db: Session = Depends(get_db)):
    ingestion_result = upsert_events(db, events, update_embeddings=train_model)
    training_result = _train_model_after_ingestion(train_model)
    return {"ingestion": ingestion_result, "model_training": training_result}


@router.post("/ingestEvents")
def ingest_events(events: List[EventCreate], train_model: bool = True, db: Session = Depends(get_db)):
    ingestion_result = upsert_events(db, events, update_embeddings=train_model)
    training_result = _train_model_after_ingestion(train_model)
    return {"ingestion": ingestion_result, "model_training": training_result}


@router.post("/syncWebEvents")
def sync_web_events(request: WebIngestionRequest, db: Session = Depends(get_db)):
    try:
        return ingest_web_events(db, request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/uploadEventImage", status_code=201, include_in_schema=False)
async def upload_event_image(file: UploadFile = File(...), train_model: bool = True, db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")
    content = await file.read()
    try:
        events = process_image_file(db, content, file.filename, update_embeddings=train_model)
        training_result = _train_model_after_ingestion(train_model and bool(events))
        return {"events": events, "model_training": training_result}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/events/interactions", status_code=201, include_in_schema=False)
def create_event_interaction(interaction: EventInteractionCreate, db: Session = Depends(get_db)):
    return record_event_interaction(db, interaction)
