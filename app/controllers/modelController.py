from fastapi import APIRouter
from app.services.modelService import trainEventModelService, testExistingModel

router = APIRouter()

@router.get("/trainEventModel")
@router.get("/trainEventModel/{data_source}")
def train_event_model(data_source: str = None):
    """
    Generic model training endpoint
    
    - Automatically discovers all data files in app/data/json/
    - Supports any data type (events, products, content, etc.)
    - Works with JSON, CSV, and TXT files
    - Trains semantic embedding model and intent classifier
    
    Optional Parameters:
        data_source: Specific data source/club name (for backward compatibility, not required)
    
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
        Top 5 similar items based on semantic similarity
    """
    return testExistingModel(query)