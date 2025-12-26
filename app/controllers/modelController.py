from fastapi import APIRouter
from app.services.modelService import trainEventModelService,testExistingModel

router = APIRouter()

@router.get("/trainEventModel/{club}")
def train_event_model(club: str):
    return trainEventModelService(club)

@router.get("/testModel/{event_description}")
def test_model(event_description: str):
    return testExistingModel(event_description)
       