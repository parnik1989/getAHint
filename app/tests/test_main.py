from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_all_event_data():
    r = client.get("/eventService/getAllEventData")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) > 0
    assert all("id" in event for event in events)
    assert all("event_id" not in event for event in events)
    assert all(event["event_date"].count("-") == 2 for event in events)
