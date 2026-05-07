import asyncio
import os
from datetime import datetime, time, timedelta, timezone

from app.db.session import SessionLocal
from app.schemas.eventSchema import WebIngestionRequest
from app.services.web_ingestion_service import ingest_web_events

_daily_web_sync_task: asyncio.Task | None = None


def start_daily_web_sync_scheduler():
    global _daily_web_sync_task

    if not _env_bool("ENABLE_DAILY_WEB_SYNC", default=False):
        print("Daily web event sync scheduler is disabled.")
        return

    if _daily_web_sync_task and not _daily_web_sync_task.done():
        return

    _daily_web_sync_task = asyncio.create_task(_daily_web_sync_loop())
    print("Daily web event sync scheduler started.")


async def stop_daily_web_sync_scheduler():
    global _daily_web_sync_task

    if not _daily_web_sync_task:
        return

    _daily_web_sync_task.cancel()
    try:
        await _daily_web_sync_task
    except asyncio.CancelledError:
        pass
    finally:
        _daily_web_sync_task = None
        print("Daily web event sync scheduler stopped.")


async def _daily_web_sync_loop():
    if _env_bool("WEB_SYNC_RUN_ON_STARTUP", default=False):
        await _run_web_sync_in_thread()

    while True:
        delay_seconds = _seconds_until_next_run()
        print(f"Next web event sync in {round(delay_seconds)} seconds.")
        await asyncio.sleep(delay_seconds)
        await _run_web_sync_in_thread()


async def _run_web_sync_in_thread():
    await asyncio.to_thread(_run_web_sync)


def _run_web_sync():
    request = _web_sync_request_from_env()
    db = SessionLocal()
    try:
        result = ingest_web_events(db, request)
        print(f"Daily web event sync completed: {result}")
    except Exception as e:
        print(f"Daily web event sync failed: {e}")
    finally:
        db.close()


def _web_sync_request_from_env() -> WebIngestionRequest:
    return WebIngestionRequest(
        queries=_split_env_list("WEB_SYNC_QUERIES"),
        source_urls=_split_env_list("WEB_SYNC_SOURCE_URLS"),
        city=os.getenv("WEB_SYNC_CITY", "Hyderabad"),
        max_search_results=_env_int("WEB_SYNC_MAX_SEARCH_RESULTS", default=10),
        exclude_past_events=_env_bool("WEB_SYNC_EXCLUDE_PAST_EVENTS", default=True),
        update_embeddings=_env_bool("WEB_SYNC_UPDATE_EMBEDDINGS", default=True),
    )


def _seconds_until_next_run() -> float:
    interval_minutes = _env_int("WEB_SYNC_INTERVAL_MINUTES", default=0)
    if interval_minutes > 0:
        return interval_minutes * 60

    now = datetime.now(timezone.utc)
    run_time = _parse_run_time(os.getenv("WEB_SYNC_RUN_AT_UTC", "02:00"))
    next_run = datetime.combine(now.date(), run_time, tzinfo=timezone.utc)
    if next_run <= now:
        next_run += timedelta(days=1)
    return (next_run - now).total_seconds()


def _parse_run_time(value: str) -> time:
    try:
        hour_text, minute_text = value.strip().split(":", 1)
        return time(hour=int(hour_text), minute=int(minute_text))
    except (ValueError, TypeError):
        return time(hour=2, minute=0)


def _split_env_list(name: str) -> list[str] | None:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return None
    return [item.strip() for item in raw_value.split("|") if item.strip()]


def _env_bool(name: str, default: bool) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except ValueError:
        return default
