from fastapi import FastAPI
from app.controllers import eventController, modelController, telegramController

app = FastAPI(title="getAHintService")

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
