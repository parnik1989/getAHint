from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.controllers import authController, eventController, modelController
from app.db.schema import ensure_database_schema
from app.db.session import engine
from app.services.scheduler_service import start_daily_web_sync_scheduler, stop_daily_web_sync_scheduler


ensure_database_schema(engine)


@asynccontextmanager
async def lifespan(app: FastAPI):
    start_daily_web_sync_scheduler()
    yield
    await stop_daily_web_sync_scheduler()


app = FastAPI(title="getAHintService", lifespan=lifespan)

app.include_router(authController.router, prefix="/auth")
app.include_router(eventController.router, prefix="/eventService")
app.include_router(modelController.router, prefix="/modelService")
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse("app/static/chat.html")


@app.get("/chat", include_in_schema=False)
def chat_page():
    return FileResponse("app/static/chat.html")
