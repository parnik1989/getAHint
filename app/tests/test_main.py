from fastapi.testclient import TestClient
from app.db.models import EventRecord
from app.db.session import SessionLocal
from app.main import app

client = TestClient(app)


def _delete_test_event():
    db = SessionLocal()
    try:
        db.query(EventRecord).filter(EventRecord.event_name == "Test Event").delete()
        db.commit()
    finally:
        db.close()


def test_get_all_event_data():
    _delete_test_event()
    created = client.post(
        "/eventService/events",
        json={
            "event_name": "Test Event",
            "event_description": "Temporary event for API read verification.",
            "event_date": "2026-06-01",
            "event_address": "Hyderabad",
            "source_name": "test",
            "source_type": "api",
        },
    )
    assert created.status_code == 201

    r = client.get("/eventService/getAllEventData")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) > 0
    assert all("id" in event for event in events)
    assert all("event_id" not in event for event in events)
    assert all(event["event_date"].count("-") == 2 for event in events)
    _delete_test_event()
