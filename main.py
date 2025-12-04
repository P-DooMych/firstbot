import os
import telebot
from fastapi import FastAPI, Request
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCU_API_KEY = os.environ.get("ACCUWEATHER_API_KEY")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = FastAPI()

def get_location_key(city_name: str):
    url = "http://dataservice.accuweather.com/locations/v1/cities/search"
    params = {
        "apikey": ACCU_API_KEY,
        "q": city_name,
        "language": "uk-ua"
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None
    data = r.json()
    if not data:
        return None
    return data[0]["Key"]

def get_weather(location_key: str):
    url = f"http://dataservice.accuweather.com/currentconditions/v1/{location_key}"
    params = {
        "apikey": ACCU_API_KEY,
        "details": "true",
        "language": "uk-ua"
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None
    data = r.json()
    if not data:
        return None
    return data[0]

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "Привіт! Я бот погоди ☀️\n"
        "Напиши назву міста, і я скажу тобі поточну погоду.\n\n"
        "Наприклад: Київ"
    )

@bot.message_handler(func=lambda msg: True)
def weather_handler(message):
    city = message.text.strip()
    location_key = get_location_key(city)
    if not location_key:
        bot.reply_to(message, "❌ Не вдалося знайти місто. Спробуй іншу назву.")
        return
    weather = get_weather(location_key)
    if not weather:
        bot.reply_to(message, "❌ Не вдалося отримати погоду 😢")
        return
    text = (
        f"🌍 *{city.capitalize()}*\n"
        f"📡 {weather['WeatherText']}\n"
        f"🌡 Температура: {weather['Temperature']['Metric']['Value']}°C\n"
        f"💨 Вітер: {weather['Wind']['Speed']['Metric']['Value']} км/год\n"
        f"💧 Вологість: {weather['RelativeHumidity']}%\n"
    )
    bot.reply_to(message, text, parse_mode="Markdown")

@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return {"ok": True}

@app.get("/")
def home():
    return {"status": "OK", "bot": "weather-bot"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000))
    )
