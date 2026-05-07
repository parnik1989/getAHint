from fastapi import APIRouter, Depends, File, Header, HTTPException, status, UploadFile
from typing import List
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.eventSchema import EventInteractionCreate
from app.services.auth_service import get_user_id_for_token
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


def _embedding_update_after_ingestion(update_embeddings: bool):
    if not update_embeddings:
        return None
    return {
        "status": "Vector embedding updated during ingestion",
        "mode": "per_event_embedding",
    }

@router.get("/getAllEventData", response_model=List[Event], include_in_schema=False)
def get_all_events():
    return consolidateAllEventsFromDataStore()


@router.post("/events", status_code=201, include_in_schema=False)
def create_or_update_event(event: EventCreate, update_embeddings: bool = True, db: Session = Depends(get_db)):
    saved_event = upsert_event(db, event, update_embedding=update_embeddings)
    embedding_update = _embedding_update_after_ingestion(update_embeddings)
    return {"event": saved_event, "embedding_update": embedding_update}


@router.post("/events/bulk", include_in_schema=False)
def create_or_update_events(events: List[EventCreate], update_embeddings: bool = True, db: Session = Depends(get_db)):
    ingestion_result = upsert_events(db, events, update_embeddings=update_embeddings)
    embedding_update = _embedding_update_after_ingestion(update_embeddings)
    return {"ingestion": ingestion_result, "embedding_update": embedding_update}


@router.post("/ingestEvents")
def ingest_events(events: List[EventCreate], update_embeddings: bool = True, db: Session = Depends(get_db)):
    ingestion_result = upsert_events(db, events, update_embeddings=update_embeddings)
    embedding_update = _embedding_update_after_ingestion(update_embeddings)
    return {"ingestion": ingestion_result, "embedding_update": embedding_update}


@router.post("/syncWebEvents")
def sync_web_events(request: WebIngestionRequest, db: Session = Depends(get_db)):
    try:
        return ingest_web_events(db, request)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/uploadEventImage", status_code=201, include_in_schema=False)
async def upload_event_image(file: UploadFile = File(...), update_embeddings: bool = True, db: Session = Depends(get_db)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")
    content = await file.read()
    try:
        events = process_image_file(db, content, file.filename, update_embeddings=update_embeddings)
        embedding_update = _embedding_update_after_ingestion(update_embeddings and bool(events))
        return {"events": events, "embedding_update": embedding_update}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/events/interactions", status_code=201, include_in_schema=False)
def create_event_interaction(
    interaction: EventInteractionCreate,
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
):
    authenticated_user_id = get_user_id_for_token(db, authorization)
    if authenticated_user_id:
        interaction.user_id = authenticated_user_id
    return record_event_interaction(db, interaction)
