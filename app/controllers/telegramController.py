from fastapi import APIRouter, Request
import os
import requests
from app.services.modelService import testExistingModel
import joblib

router = APIRouter()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TOKEN}"
#classifier = pipeline("zero-shot-classification", model="distilbert-base-uncased")

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
    if TOKEN:
        requests.post(
            f"{TELEGRAM_API_URL}/sendMessage",
            json={"chat_id": chat_id, "text": response_text} 
        )
    return {"status": "ok","message": response_text}
