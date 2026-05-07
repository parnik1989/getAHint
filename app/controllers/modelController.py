from fastapi import APIRouter
from pydantic import BaseModel
from app.services.modelService import build_chat_response, trainEventModelService, testExistingModel

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    user_id: str | None = None


@router.get("/trainEventModel")
@router.get("/trainEventModel/{data_source}")
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

@router.get("/testModel/{query}")
def test_model(query: str):
    """
    Test the trained model with a similarity search query
    
    Parameters:
        query: Search query to find similar items
    
    Returns:
        User-facing answer text for the query
    """
    model_response = testExistingModel(query)
    if "answer" in model_response:
        return {"answer": model_response["answer"]}
    return {"answer": model_response.get("error", "I could not find an answer from the trained data.")}


@router.post("/chat")
def chat(request: ChatRequest):
    return build_chat_response(request.message, user_id=request.user_id)
