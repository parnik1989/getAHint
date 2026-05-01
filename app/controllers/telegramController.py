from fastapi import APIRouter, HTTPException, Request
import os
import requests
from app.services.modelService import testExistingModel
import joblib

router = APIRouter()
TELEGRAM_WEBHOOK_PATH = "/telegramService/telegram/webhook"
#classifier = pipeline("zero-shot-classification", model="distilbert-base-uncased")


def get_telegram_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def get_telegram_api_url() -> str:
    return f"https://api.telegram.org/bot{get_telegram_token()}"


def get_public_base_url() -> str:
    base_url = (
        os.getenv("PUBLIC_BASE_URL", "")
        or os.getenv("RAILWAY_PUBLIC_DOMAIN", "")
        or os.getenv("RAILWAY_STATIC_URL", "")
    ).strip()
    if base_url and not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"
    return base_url.rstrip("/")


def get_webhook_url() -> str:
    base_url = get_public_base_url()
    return f"{base_url}{TELEGRAM_WEBHOOK_PATH}" if base_url else ""


def set_telegram_webhook() -> dict:
    token = get_telegram_token()
    webhook_url = get_webhook_url()

    if not token:
        raise HTTPException(status_code=500, detail="TELEGRAM_BOT_TOKEN is not configured")
    if not webhook_url:
        raise HTTPException(status_code=500, detail="PUBLIC_BASE_URL is not configured")

    response = requests.post(
        f"{get_telegram_api_url()}/setWebhook",
        json={"url": webhook_url},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()

# Example: your existing event formatter
def get_event_response(user_text: str) -> str:
    model_response = testExistingModel(user_text)
    if "answer" in model_response:
        return model_response["answer"]
    return model_response.get("error", "I could not find an event answer from the trained data.")

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"]["text"]
    print(chat_id, user_text)
    pipeline = joblib.load("app/ml/intentModel.pkl")
    intent = pipeline.predict([user_text])[0]  
    # Step 2: Respond based on intent
    if intent == "greeting":
        response_text = "Hello 👋! I am here to help you with the upcoming events in Hyderabad."
    elif intent == "help":
        response_text = "You can ask me about puja, festivals, or workshops happening in Hyderabad."
    elif intent in ("content_query", "search", "information", "event_query"):
        response_text = get_event_response(user_text)
    elif intent == "feedback":
        response_text = "Thanks! Ask me anytime about upcoming events in Hyderabad."
    else:
        response_text = "Sorry, I didn’t understand. Try asking about event or festivals."
    print(response_text)
    # Send reply back to Telegram
    token = get_telegram_token()
    if token:
        requests.post(
            f"{get_telegram_api_url()}/sendMessage",
            json={"chat_id": chat_id, "text": response_text},
            timeout=10,
        )
    return {"status": "ok","message": response_text}


@router.get("/telegram/status")
def telegram_status():
    return {
        "telegram_token_configured": bool(get_telegram_token()),
        "public_base_url_configured": bool(get_public_base_url()),
        "webhook_url": get_webhook_url(),
        "set_webhook_endpoint": "/telegramService/telegram/setWebhook",
    }


@router.post("/telegram/setWebhook")
def configure_telegram_webhook():
    return set_telegram_webhook()
