from fastapi import FastAPI
from app.controllers import eventController, modelController, telegramController
from app.db.base import Base
from app.db.session import engine

app = FastAPI(title="getAHintService")

Base.metadata.create_all(bind=engine)

app.include_router(eventController.router, prefix="/eventService")
app.include_router(modelController.router, prefix="/modelService")
app.include_router(telegramController.router, prefix="/telegramService")


@app.get("/")
def root():
    return {
        "service": "getAHintService",
        "swagger_docs": "/docs",
        "openapi_schema": "/openapi.json",
        "telegram_status": "/telegramService/telegram/status",
    }
