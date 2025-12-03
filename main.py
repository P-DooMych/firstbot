import os
import telebot
from fastapi import FastAPI, Request
import requests
import json

from dotenv import load_dotenv
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-5-nano"

if not TOKEN:
    logger.error("TELEGRAM_BOT_TOKEN не задано в env")
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY не задано в env")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = FastAPI()

tone = "friendly"
TONE_SYSTEM_MESSAGES = {
    "friendly": "You are a friendly AI assistant. Always answer warmly and supportively.",
    "formal": "You are a very formal AI assistant. Answer strictly, politely and professionally.",
    "funny": "You are a humorous AI assistant. Answer in a funny way, add jokes.",
}

def extract_openai_text(response_json: dict) -> str:
    """
    Безпечний парсинг відповіді OpenAI Responses API за прикладом:
    - шукає в response_json["output"] перший об'єкт type == "message"
    - бере content[].text для content.type == "output_text"
    - fallback: response_json.get("output_text") або з'єднує всі тексти
    """
    try:
        outputs = response_json.get("output") or []
        if isinstance(outputs, list):
            for out in outputs:
                if out.get("type") == "message":
                    content_list = out.get("content") or []
                    if isinstance(content_list, list):
                        texts = []
                        for c in content_list:
                            if c.get("type") == "output_text":
                                text = c.get("text")
                                if text:
                                    texts.append(text)
                        if texts:
                            return "\n\n".join(texts)
                    maybe_text = out.get("text")
                    if maybe_text:
                        return maybe_text

        if "output_text" in response_json and isinstance(response_json["output_text"], str):
            return response_json["output_text"]

        if "text" in response_json and isinstance(response_json["text"], str):
            return response_json["text"]

        if "instructions" in response_json and isinstance(response_json["instructions"], str):
            return response_json["instructions"]

        collected = []
        for out in outputs:
            content_list = out.get("content") or []
            for c in content_list:
                t = c.get("text")
                if t:
                    collected.append(t)
        if collected:
            return "\n\n".join(collected)

    except Exception as e:
        logger.exception("Помилка при парсингу відповіді OpenAI: %s", e)

    try:
        return "⚠️ Не вдалося витягти текст відповіді. Діагностика:\n" + json.dumps(response_json, ensure_ascii=False, indent=2)[:2000]
    except Exception:
        return "⚠️ Не вдалося витягти текст відповіді і не вдалося серіалізувати JSON."

def ask_openai(user_text: str, tone_name: str = "friendly") -> str:
    if not OPENAI_API_KEY:
        return "⚠️ OpenAI API key not configured."

    system_msg = TONE_SYSTEM_MESSAGES.get(tone_name, TONE_SYSTEM_MESSAGES["friendly"])

    url = "https://api.openai.com/v1/responses"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": OPENAI_MODEL,
        "instructions": system_msg,
        "input": user_text
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
    except requests.exceptions.RequestException as e:
        logger.exception("Помилка мережі при виклику OpenAI: %s", e)
        return "⚠️ Помилка мережі при зв'язку з OpenAI."

    if resp.status_code != 200:
        logger.error("OpenAI returned non-200: %s %s", resp.status_code, resp.text)
        # Повертаємо користувачу коротку інформацію
        return f"⚠️ OpenAI API error: {resp.status_code}. {resp.text[:400]}"

    try:
        data = resp.json()
    except ValueError:
        logger.exception("Не вдалося розпарсити JSON від OpenAI")
        return "⚠️ Не вдалося розпарсити відповідь OpenAI."

    # Використовуємо нашу функцію парсингу
    text = extract_openai_text(data)
    return text

# ====== HANDLERS TELEGRAM ======

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(
        message,
        "Привіт! Я бот із настроєм. Використай /set_tone friendly|formal|funny щоб змінити тон."
    )

@bot.message_handler(commands=['set_tone'])
def set_tone_handler(message):
    global tone
    parts = message.text.split()
    if len(parts) != 2:
        bot.reply_to(message, "❗ Формат: /set_tone friendly|formal|funny")
        return
    new_tone = parts[1].strip().lower()
    if new_tone not in TONE_SYSTEM_MESSAGES:
        bot.reply_to(message, "❗ Невідомий тон. Доступні: friendly, formal, funny")
        return
    tone = new_tone
    bot.reply_to(message, f"✅ Тон змінено на: {tone}")

@bot.message_handler(func=lambda m: True)
def ai_chat(message):
    user_text = message.text or ""
    # Коротка індикація в логах
    logger.info("User %s asked: %s", message.from_user.id if message.from_user else "unknown", user_text[:200])
    answer = ask_openai(user_text, tone)
    bot.reply_to(message, answer)

# ====== WEBHOOK ======

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
