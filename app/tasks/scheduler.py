"""
APScheduler-based background task scheduler.

Runs periodic_event_update every 6 hours (configurable via the
EVENTS_FETCH_INTERVAL_HOURS environment variable) to keep the database
populated with the latest events from the configured external source.
"""
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler

from app.services.event_fetcher import periodic_event_update

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Singleton scheduler instance
# ---------------------------------------------------------------------------

scheduler = BackgroundScheduler()

_FETCH_INTERVAL_HOURS = int(os.getenv("EVENTS_FETCH_INTERVAL_HOURS", "6"))


# ---------------------------------------------------------------------------
# Lifecycle helpers (called from app/main.py lifespan)
# ---------------------------------------------------------------------------


def start_scheduler() -> None:
    """Register periodic jobs and start the APScheduler background scheduler."""
    scheduler.add_job(
        periodic_event_update,
        trigger="interval",
        hours=_FETCH_INTERVAL_HOURS,
        id="event_update",
        name="Periodic Event Update",
        replace_existing=True,
    )

    if not scheduler.running:
        scheduler.start()
        logger.info(
            "APScheduler started — event update every %d hour(s)",
            _FETCH_INTERVAL_HOURS,
        )


def stop_scheduler() -> None:
    """Gracefully shut down the APScheduler background scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped")
