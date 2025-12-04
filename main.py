import os
import telebot
from fastapi import FastAPI, Request
import requests
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

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

def get_weather_now(location_key: str):
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

def get_forecast_1day(location_key: str):
    url = f"http://dataservice.accuweather.com/forecasts/v1/daily/1day/{location_key}"
    params = {
        "apikey": ACCU_API_KEY,
        "language": "uk-ua",
        "metric": "true"
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None
    data = r.json()
    if "DailyForecasts" not in data:
        return None
    return data["DailyForecasts"][0]

def get_forecast_5days(location_key: str):
    url = f"http://dataservice.accuweather.com/forecasts/v1/daily/5day/{location_key}"
    params = {
        "apikey": ACCU_API_KEY,
        "language": "uk-ua",
        "metric": "true"
    }
    r = requests.get(url, params=params)
    if r.status_code != 200:
        return None
    data = r.json()
    if "DailyForecasts" not in data:
        return None
    return data["DailyForecasts"]

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "Привіт! Я бот погоди ☀️\n"
        "Напиши назву міста, і я покажу погоду.\n\n"
        "Наприклад: Київ"
    )


@bot.message_handler(func=lambda msg: True)
def ask_for_type(message):
    city = message.text.strip()

    waiting_msg = bot.send_animation(
        message.chat.id,
        animation="https://media.tenor.com/XFz9zaC46VcAAAAM/searching-digging.gif",
        caption="⏳ Зачекайте, шукаємо Ваше місто місто..."
    )

    location_key = get_location_key(city)

    if not location_key:
        bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=waiting_msg.message_id,
            text="❌ Не вдалося знайти місто. Спробуй іншу назву."
        )
        return

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Поточна погода", callback_data=f"now|{location_key}|{city}"),
        InlineKeyboardButton("Прогноз на 1 день", callback_data=f"1day|{location_key}|{city}")
    )
    kb.add(
        InlineKeyboardButton("Прогноз на 5 днів", callback_data=f"5day|{location_key}|{city}")
    )

    bot.edit_message_text(
        chat_id=message.chat.id,
        message_id=waiting_msg.message_id,
        text=f"Місто: *{city.capitalize ()}*\nОберіть тип прогнозу:",
        parse_mode="Markdown",
        reply_markup=kb
    )


@bot.callback_query_handler(func=lambda call: True)
def process_choice(call):
    chat_id = call.message.chat.id

    action, key, city = call.data.split("|")

    wait_msg = bot.send_animation(
        chat_id,
        animation="https://media.tenor.com/tHvaUzLZ2d8AAAAM/need-hug.gif",
        caption="⏳ Отримуємо дані..."
    )

 # ============  ПОТОЧНА ПОГОДА  ============
    if action == "now":
        w = get_weather_now(key)
        if not w:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=wait_msg.message_id,
                text="❌ Помилка отримання погоди."
            )
            return

        text = (
            f"🌍 *{city.capitalize()}*\n"
            f"📡 {w['WeatherText']}\n"
            f"🌡 Температура: {w['Temperature']['Metric']['Value']}°C\n"
            f"💨 Вітер: {w['Wind']['Speed']['Metric']['Value']} км/год\n"
            f"💧 Вологість: {w['RelativeHumidity']}%\n"
        )

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=wait_msg.message_id,
            text=text,
            parse_mode="Markdown"
        )

    # ============  ПРОГНОЗ НА 1 ДЕНЬ  ============
    elif action == "1day":
        f = get_forecast_1day(key)
        if not f:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=wait_msg.message_id,
                text="❌ Помилка запиту прогнозу."
            )
            return

        date = f["Date"].split("T")[0]
        min_t = f["Temperature"]["Minimum"]["Value"]
        max_t = f["Temperature"]["Maximum"]["Value"]
        phrase = f["Day"]["IconPhrase"]

        text = (
            f"📅 *Прогноз на 1 день — {city.capitalize()}*\n"
            f"Дата: {date}\n"
            f"🌡 {min_t}°C → {max_t}°C\n"
            f"☁️ {phrase}"
        )

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=wait_msg.message_id,
            text=text,
            parse_mode="Markdown"
        )

    # ============  ПРОГНОЗ НА 5 ДНІВ  ============
    elif action == "5day":
        forecast = get_forecast_5days(key)
        if not forecast:
            bot.edit_message_text(
                chat_id=chat_id,
                message_id=wait_msg.message_id,
                text="❌ Помилка запиту прогнозу."
            )
            return

        text = f"📅 *Прогноз на 5 днів — {city.capitalize()}*\n"
        for day in forecast:
            date = day["Date"].split("T")[0]
            min_t = day["Temperature"]["Minimum"]["Value"]
            max_t = day["Temperature"]["Maximum"]["Value"]
            phrase = day["Day"]["IconPhrase"]
            text += f"\n📆 {date}\n🌡 {min_t}°C → {max_t}°C\n☁️ {phrase}\n"

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=wait_msg.message_id,
            text=text,
            parse_mode="Markdown"
        )

    bot.answer_callback_query(call.id)


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
