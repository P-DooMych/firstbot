import os
import telebot
from fastapi import FastAPI, Request
import requests
import json

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
OPENAI_MODEL = "gpt-5-nano"

bot = telebot.TeleBot(TOKEN, threaded=False)
app = FastAPI()

tone = "friendly"  # Тон за замовчуванням

TONE_SYSTEM_MESSAGES = {
    "friendly": "You are a friendly AI assistant. Always answer warmly and supportively.",
    "formal": "You are a very formal AI assistant. Answer strictly, politely and professionally.",
    "funny": "You are a humorous AI assistant. Answer in a funny way, add jokes.",
}
def ask_openai(user_text, tone):
    url = "https://api.openai.com/v1/responses"

    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "instructions": TONE_SYSTEM_MESSAGES[tone],
        "input": user_text
    }

    response = requests.post(url, headers=headers, json=payload)
    data = response.json()

    try:
        return data["output_text"]
    except:
        return "Error: " + json.dumps(data)

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to (message,
                  "Привіт! Я бот із настроєм 😄\n\n"
                  "Доступні тони:\n"
                  "• friendly — дружній\n"
                  "• formal — формальний\n"
                  "• funny — кумедний\n\n"
                  "Змінити тон: /set_tone [тон]")

@bot.message_handler(commands=['set_tone'])
def set_tone_handler(message):
    global tone

    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❗ Формат: /set_tone friendly|formal|funny")
        return

    new_tone = parts[1].lower()

    if new_tone not in TONE_SYSTEM_MESSAGES:
        bot.reply_to(message, "❗ Невідомий тон. Доступні: friendly, formal, funny")
        return

    tone = new_tone
    bot.reply_to(message, f"✅ Тон змінено на: {tone}")

@bot.message_handler(func=lambda msg: True)
def ai_chat(message):
    answer = ask_openai(message.text, tone)
    bot.reply_to(message, answer)

@app.post("/webhook")
async def process_webhook(request: Request):
    json_data = await request.json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return {"ok": True}

@app.get("/")
def home():
    return {"status": "ok"}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))
