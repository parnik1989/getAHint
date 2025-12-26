# getAHintService - FastAPI starter

Quick start

1. Create a virtualenv and activate it

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Run the app

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

3. Visit http://localhost:8000/docs for interactive API docs

Recommendations

- Endpoint: `GET /api/v1/recommendations?movie_id=<id>&n=<count>`
- Example:

```bash
curl "http://localhost:8000/api/v1/recommendations?movie_id=3&n=5"
```
