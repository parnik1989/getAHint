from fastapi import APIRouter,File,HTTPException,status,UploadFile
from typing import List
from app.services.event_service import consolidateAllEventsFromDataStore, process_image_file
from app.models.eventModel import Event

router = APIRouter()

@router.get("/getAllEventData", response_model=List[Event])
def get_all_events():
    return consolidateAllEventsFromDataStore()

@router.post("/uploadEventImage", response_model=List[Event], status_code=201)
async def upload_event_image(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No filename provided")
    content = await file.read()
    try:
        events = process_image_file(content, file.filename)
        return events
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))