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

3. Visit http://localhost:8000/docs for interactive Swagger API docs

Hosted Railway app

- Swagger UI: `https://<your-railway-domain>/docs`
- OpenAPI JSON: `https://<your-railway-domain>/openapi.json`
- Telegram status: `https://<your-railway-domain>/telegramService/telegram/status`

Telegram setup

Set these Railway variables:

```bash
TELEGRAM_BOT_TOKEN=<your bot token from BotFather>
PUBLIC_BASE_URL=https://<your-railway-domain>
```

After deployment, register the Telegram webhook once:

```bash
curl -X POST "https://<your-railway-domain>/telegramService/telegram/setWebhook"
```

Recommendations

- Endpoint: "GET /eventService/getAllEventData"
- Example:

```bash
curl "http://localhost:8000/eventService/getAllEventData"
```
