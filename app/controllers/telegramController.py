from fastapi import APIRouter, Request
import requests
from app.services.modelService import testExistingModel

router = APIRouter()
TOKEN = "7295025416:AAHgAG-8YmbS9NdVl9apG3VPocIGYurjLPo"
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"

# Example: your existing event formatter
def get_event_response(user_text: str) -> str:
    # Replace with your ML/JSON logic
    return testExistingModel(user_text);

@router.post("/telegram/webhook")
async def telegram_webhook(request: Request):
    data = await request.json()
    chat_id = data["message"]["chat"]["id"]
    user_text = data["message"]["text"]
    print(chat_id, user_text)
    # Call your backend logic
    response_text = get_event_response(user_text)
    print(list({'Maha Sasthi puja at 28-09-2025'})[0] )
    # Send reply back to Telegram
    requests.post(
        f"{TELEGRAM_API_URL}/sendMessage",
        json={"chat_id": chat_id, "text": response_text.pop()} 
    )
    return {"status": "ok"}