import os
import telebot
from fastapi import FastAPI, Request

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = telebot.TeleBot(TOKEN, threaded=False)
app = FastAPI()

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(message, "Hello!!")

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
