from fastapi import APIRouter
from pydantic import BaseModel
from app.services.modelService import build_chat_response, trainEventModelService

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


@router.get("/trainEventModel")
@router.get("/trainEventModel/{data_source}", include_in_schema=False)
def train_event_model(data_source: str = None):
    """
    Model training endpoint.

    - Reads event records from the database
    - Backfills event vector embeddings for search
    - Trains the lightweight intent classifier
    
    Optional Parameters:
        data_source: Deprecated; kept for backward compatibility.
    
    Returns:
        Training status and comprehensive statistics
    """
    return trainEventModelService(data_source)

@router.post("/chat", include_in_schema=False)
def chat(request: ChatRequest):
    return build_chat_response(request.message, user_id=request.user_id)
