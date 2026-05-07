from fastapi.testclient import TestClient
from app.db.models import EventRecord
from app.db.session import SessionLocal
from app.main import app
from app.schemas.eventSchema import EventCreate
from app.services.vector_service import filter_and_rank_results, search_events_hybrid
from app.services.web_ingestion_service import _event_from_serper_result, _extract_events_from_html
from app.services.event_service import upsert_event

client = TestClient(app)


def _delete_test_event():
    db = SessionLocal()
    try:
        db.query(EventRecord).filter(
            EventRecord.event_name.in_(
                (
                    "Test Event",
                    "Test Future Science Workshop",
                    "Test Past AI Workshop",
                )
            )
        ).delete()
        db.commit()
    finally:
        db.close()


def test_get_all_event_data():
    _delete_test_event()
    created = client.post(
        "/eventService/events?update_embeddings=false",
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
    assert created.json()["embedding_update"] is None

    r = client.get("/eventService/getAllEventData")
    assert r.status_code == 200
    events = r.json()
    assert isinstance(events, list)
    assert len(events) > 0
    assert all("id" in event for event in events)
    assert all("event_id" not in event for event in events)
    assert all(event["event_date"].count("-") == 2 for event in events)
    _delete_test_event()


def test_ingestion_assigns_event_category():
    _delete_test_event()
    created = client.post(
        "/eventService/events?update_embeddings=false",
        json={
            "event_name": "Test Future Science Workshop",
            "event_description": "AI workshop for product builders.",
            "event_date": "2999-06-01",
            "event_address": "Hyderabad",
            "source_name": "test",
            "source_type": "api",
        },
    )

    assert created.status_code == 201
    assert created.json()["event"]["category"] in {"tech", "workshop"}
    _delete_test_event()


def test_records_event_interaction():
    _delete_test_event()
    created = client.post(
        "/eventService/events?update_embeddings=false",
        json={
            "event_name": "Test Future Science Workshop",
            "event_description": "AI workshop for product builders.",
            "event_date": "2999-06-01",
            "event_address": "Hyderabad",
            "source_name": "test",
            "source_type": "api",
        },
    )
    event_id = created.json()["event"]["id"]

    response = client.post(
        "/eventService/events/interactions",
        json={
            "user_id": "test-user",
            "event_id": event_id,
            "interaction_type": "click",
            "query": "ai workshops",
        },
    )

    assert response.status_code == 201
    assert response.json()["status"] == "recorded"
    _delete_test_event()


def test_chat_response_marks_personalized_after_interaction():
    _delete_test_event()
    created = client.post(
        "/eventService/events?update_embeddings=false",
        json={
            "event_name": "Test Future Science Workshop",
            "event_description": "AI workshop for product builders.",
            "event_date": "2999-06-01",
            "event_address": "Hyderabad",
            "source_name": "test",
            "source_type": "api",
        },
    )
    event_id = created.json()["event"]["id"]
    client.post(
        "/eventService/events/interactions",
        json={
            "user_id": "personalized-user",
            "event_id": event_id,
            "interaction_type": "save",
            "query": "ai workshops",
        },
    )

    response = client.post(
        "/modelService/chat",
        json={"message": "upcoming workshops", "user_id": "personalized-user"},
    )

    assert response.status_code == 200
    assert response.json()["personalized"] is True
    _delete_test_event()


def test_chat_greeting_does_not_return_events():
    response = client.post("/modelService/chat", json={"message": "hi"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["intent"] == "greeting"
    assert payload["results"] == []
    assert "upcoming events" in payload["answer"].lower()


def test_specific_query_filters_unrelated_vector_neighbors():
    results = [
        {
            "id": 1,
            "event_name": "Bonalu Festival",
            "event_description": "Telangana temple celebration",
            "event_date": "2026-07-01",
            "event_address": "Hyderabad",
            "similarity_score": 0.72,
        },
        {
            "id": 2,
            "event_name": "Hard Rock Cafe Night",
            "event_description": "Live music",
            "event_date": "2026-07-02",
            "event_address": "Hyderabad",
            "similarity_score": 0.34,
        },
    ]

    filtered, _, _ = filter_and_rank_results(results, "bonalu festival")

    assert [event["event_name"] for event in filtered] == ["Bonalu Festival"]


def test_short_ai_and_plural_terms_match_event_text():
    _delete_test_event()
    db = SessionLocal()
    try:
        saved = upsert_event(
            db,
            EventCreate(
                event_name="Test Future Science Workshop",
                event_description="AI workshop for product builders.",
                event_date="2999-06-01",
                event_address="Hyderabad",
                source_name="test",
                source_type="api",
            ),
            update_embedding=False,
        )
        db.query(EventRecord).filter(EventRecord.id == saved.id).update({"embedding_json": None})
        db.commit()

        results = search_events_hybrid(db, "upcoming AI workshops in Hyderabad", top_k=5)
    finally:
        db.close()
        _delete_test_event()

    assert "Test Future Science Workshop" in {result["event_name"] for result in results}


def test_natural_cultural_query_keeps_topic_terms():
    _delete_test_event()
    db = SessionLocal()
    try:
        saved = upsert_event(
            db,
            EventCreate(
                event_name="Test Regional Culture Night",
                event_description="Indian regional sounds and cultural rhythms.",
                event_date="2999-06-02",
                event_address="Hyderabad",
                source_name="test",
                source_type="api",
            ),
            update_embedding=False,
        )
        db.query(EventRecord).filter(EventRecord.id == saved.id).update({"embedding_json": None})
        db.commit()

        results = search_events_hybrid(
            db,
            "can you suggest any upcoming cultural events in coming days ?",
            top_k=5,
        )
    finally:
        db.close()
        db = SessionLocal()
        try:
            db.query(EventRecord).filter(EventRecord.event_name == "Test Regional Culture Night").delete()
            db.commit()
        finally:
            db.close()

    assert "Test Regional Culture Night" in {result["event_name"] for result in results}


def test_extracts_schema_org_event_json_ld():
    html = """
    <html>
      <head>
        <script type="application/ld+json">
        {
          "@context": "https://schema.org",
          "@type": "Event",
          "name": "Hyderabad Science Evening",
          "startDate": "2026-08-12T18:00:00+05:30",
          "description": "Talks and demos for science enthusiasts.",
          "location": {
            "@type": "Place",
            "name": "Science Center",
            "address": {
              "@type": "PostalAddress",
              "addressLocality": "Hyderabad"
            }
          }
        }
        </script>
      </head>
    </html>
    """

    events = _extract_events_from_html(html, "https://example.com/events/science")

    assert len(events) == 1
    assert events[0].event_name == "Hyderabad Science Evening"
    assert events[0].event_date == "2026-08-12"
    assert events[0].event_address == "Science Center, Hyderabad"


def test_parses_serper_result_into_event_shape():
    result = {
        "title": "Bonalu Festival Hyderabad - Events",
        "link": "https://example.com/bonalu",
        "snippet": "Bonalu Festival with folk dances and temple processions on July 15, 2026 at Ujjaini Mahankali Temple, Hyderabad.",
        "date": "2 days ago",
    }

    event = _event_from_serper_result(result, "upcoming cultural events Hyderabad", "Hyderabad")

    assert event is not None
    assert event.event_name == "Bonalu Festival Hyderabad"
    assert event.event_date == "2026-07-15"
    assert event.event_address == "Ujjaini Mahankali Temple, Hyderabad"
    assert event.source_type == "web_serper"


def test_hybrid_search_uses_latest_database_rows_without_embeddings():
    _delete_test_event()
    db = SessionLocal()
    try:
        saved = upsert_event(
            db,
            EventCreate(
                event_name="Test Future Science Workshop",
                event_description="Hands-on science demos for students.",
                event_date="2999-06-01",
                event_address="Hyderabad",
                source_name="test",
                source_type="api",
            ),
            update_embedding=False,
        )
        db.query(EventRecord).filter(EventRecord.id == saved.id).update({"embedding_json": None})
        db.commit()

        results = search_events_hybrid(db, "upcoming science workshop in Hyderabad", top_k=5)
    finally:
        db.close()
        _delete_test_event()

    assert results
    assert "Test Future Science Workshop" in {result["event_name"] for result in results}


def test_chat_ranking_excludes_past_events():
    _delete_test_event()
    db = SessionLocal()
    try:
        upsert_event(
            db,
            EventCreate(
                event_name="Test Past AI Workshop",
                event_description="AI workshop with an already passed date.",
                event_date="2020-01-01",
                event_address="Hyderabad",
                source_name="test",
                source_type="api",
            ),
            update_embedding=False,
        )
        upsert_event(
            db,
            EventCreate(
                event_name="Test Future Science Workshop",
                event_description="AI workshop with an upcoming date.",
                event_date="2999-06-01",
                event_address="Hyderabad",
                source_name="test",
                source_type="api",
            ),
            update_embedding=False,
        )
        results = search_events_hybrid(db, "AI workshop Hyderabad", top_k=10)
        filtered, _, fallback_to_past = filter_and_rank_results(results, "AI workshop Hyderabad")
    finally:
        db.close()
        _delete_test_event()

    event_names = {result["event_name"] for result in filtered}
    assert "Test Future Science Workshop" in event_names
    assert "Test Past AI Workshop" not in event_names
    assert fallback_to_past is False
