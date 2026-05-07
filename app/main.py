from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.controllers import eventController, modelController, telegramController
from app.db.schema import ensure_database_schema
from app.db.session import engine
from app.models.database import Base
from app.services.scheduler_service import start_daily_web_sync_scheduler, stop_daily_web_sync_scheduler
from app.tasks.scheduler import start_scheduler, stop_scheduler


# Ensure all ORM-declared tables exist (including any added by EventDB)
Base.metadata.create_all(bind=engine)
ensure_database_schema(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start the asyncio-based daily web-sync scheduler
    start_daily_web_sync_scheduler()
    # Start the APScheduler-based periodic event-fetch scheduler
    start_scheduler()
    yield
    # Shutdown both schedulers on application exit
    stop_scheduler()
    await stop_daily_web_sync_scheduler()


app = FastAPI(title="getAHintService", lifespan=lifespan)

app.include_router(eventController.router, prefix="/eventService")
app.include_router(modelController.router, prefix="/modelService")
app.include_router(telegramController.router, prefix="/telegramService")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/")
def root():
    return {
        "service": "getAHintService",
        "swagger_docs": "/docs",
        "openapi_schema": "/openapi.json",
        "telegram_status": "/telegramService/telegram/status",
        "chat": "/chat",
    }


@app.get("/chat")
def chat_page():
    return FileResponse("app/static/chat.html")
