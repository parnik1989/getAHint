from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_read_items():
    r = client.get("/api/v1/items")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
