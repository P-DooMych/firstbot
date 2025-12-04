import os
import telebot
from fastapi import FastAPI, Request
import requests
from dotenv import load_dotenv
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Завантажує змінні середовища з .env файлу
load_dotenv()

# Отримує токени зі змінних середовища
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
ACCU_API_KEY = os.environ.get("ACCUWEATHER_API_KEY")

# Ініціалізація Telegram-бота
bot = telebot.TeleBot(TOKEN, threaded=False)

# Створення FastAPI сервера
app = FastAPI()


# ===================== ПОШУК МІСТА =====================
def get_location_key(city_name: str):
    languages = ["uk-UA", "en-US"] # Пробує дві мови: українську та англійську
    for lang in languages:
        url = "http://dataservice.accuweather.com/locations/v1/cities/search"
        params = {
            "apikey": ACCU_API_KEY,
            "q": city_name,
            "language": lang
        }
        r = requests.get(url, params=params).json()
        if r:
            return r[0]["Key"]
    return None


# ===================== ПОГОДА СТАНОМ НА ЗАРАЗ =====================
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


# ===================== ПОГОДА НА 1 ДЕНЬ =====================
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


# ===================== ПОГОДА НА 5 ДНІВ =====================
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


# ===================== КОМАНДИ БОТА =====================

# /start - початок розмови з ботом
@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(
        message,
        "Привіт! Я бот погоди ☀️\n"
        "Напиши назву міста, і я покажу погоду.\n\n"
        "Наприклад: Київ.\n\n"
        "Доступні команди:\n"
        "/start – почати\n"
        "/help – довідка\n"
        "/about – про бота"
    )

# /help - довідка по командaх
@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = (
        "📘 *Допомога*\n\n"
        "Доступні команди:\n"
        "/start – почати роботу з ботом\n"
        "/help – показати список команд\n"
        "/about – інформація про бота\n\n"
        "Можеш просто написати місто англійською або українською, і я покажу погоду ☀️"
    )
    bot.send_message(message.chat.id, help_text, parse_mode="Markdown")


# /about - інформація про бота
@bot.message_handler(commands=['about'])
def about_handler(message):
    about_text = (
        "ℹ️ *Про бота*\n\n"
        "Це open source бот, який показує погоду в будь-якому місті 🌍\n"
        "Працює на API AccuWeather та підтримує двомовний ввод міст.\n\n"
        "GitHub: https://github.com/P-DooMych/firstbot"
    )
    bot.send_message(message.chat.id, about_text, parse_mode="Markdown")


# ===================== ОБРОБКА ТЕКСТУ КОРИСТУВАЧА =====================
@bot.message_handler(func=lambda msg: True)
def ask_for_type(message):
    city = message.text.strip()

    # Анімація очікування
    waiting_msg = bot.send_animation(
        message.chat.id,
        animation="https://media.tenor.com/XFz9zaC46VcAAAAM/searching-digging.gif",
        caption="⏳ Зачекайте, шукаємо Ваше місто..."
    )

    location_key = get_location_key(city)

    # Якщо місто не знайдено
    if not location_key:
        bot.delete_message(message.chat.id, waiting_msg.message_id)
        bot.send_message(message.chat.id, "❌ Не вдалося знайти місто. Спробуйте іншу назву.")
        return

    # Кнопки з вибором прогнозу
    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("Поточна погода", callback_data=f"now|{location_key}|{city}"),
        InlineKeyboardButton("Прогноз на 1 день", callback_data=f"1day|{location_key}|{city}")
    )
    kb.add(
        InlineKeyboardButton("Прогноз на 5 днів", callback_data=f"5day|{location_key}|{city}")
    )

    bot.delete_message (message.chat.id, waiting_msg.message_id)
    bot.send_message (
        message.chat.id,
        f"Місто: *{city.capitalize ()}*\nОберіть тип прогнозу:",
        parse_mode="Markdown",
        reply_markup=kb
    )


# ===================== ОБРОБКА НАТИСКАНЬ КНОПОК =====================
@bot.callback_query_handler(func=lambda call: True)
def process_choice(call):
    chat_id = call.message.chat.id

    action, key, city = call.data.split("|")

    # Анімація очікування
    wait_msg = bot.send_animation(
        chat_id,
        animation="https://media.tenor.com/tHvaUzLZ2d8AAAAM/need-hug.gif",
        caption="⏳ Отримуємо дані..."
    )

 # ============  ПОТОЧНА ПОГОДА  ============
    if action == "now":
        w = get_weather_now(key)
        bot.delete_message(chat_id, wait_msg.message_id)

        if not w:
            bot.send_message (chat_id, "❌ Помилка отримання погоди.")
            return

        text = (
            f"🌍 *{city.capitalize()}*\n"
            f"📡 {w['WeatherText']}\n"
            f"🌡 Температура: {w['Temperature']['Metric']['Value']}°C\n"
            f"💨 Вітер: {w['Wind']['Speed']['Metric']['Value']} км/год\n"
            f"💧 Вологість: {w['RelativeHumidity']}%\n"
        )

        bot.send_message(chat_id, text, parse_mode="Markdown")

    # ============  ПРОГНОЗ НА 1 ДЕНЬ  ============
    elif action == "1day":
        f = get_forecast_1day(key)
        bot.delete_message(chat_id, wait_msg.message_id)

        if not f:
            bot.send_message(chat_id, "❌ Помилка запиту прогнозу.")
            return

        date = f["Date"].split("T")[0]
        min_t = f["Temperature"]["Minimum"]["Value"]
        max_t = f["Temperature"]["Maximum"]["Value"]
        phrase = f["Day"]["IconPhrase"]

        text = (
            f"📅 *Прогноз на 1 день — {city.capitalize ()}*\n"
            f"Дата: {date}\n"
            f"🌡 {min_t}°C → {max_t}°C\n"
            f"☁️ {phrase}"
        )
        bot.send_message(chat_id, text, parse_mode="Markdown")

    # ============  ПРОГНОЗ НА 5 ДНІВ  ============
    elif action == "5day":
        forecast = get_forecast_5days(key)
        bot.delete_message (chat_id, wait_msg.message_id)

        if not forecast:
            bot.send_message (chat_id, "❌ Помилка запиту прогнозу.")
            return

        text = f"📅 *Прогноз на 5 днів — {city.capitalize ()}*\n"
        for day in forecast:
            date = day["Date"].split ("T")[0]
            min_t = day["Temperature"]["Minimum"]["Value"]
            max_t = day["Temperature"]["Maximum"]["Value"]
            phrase = day["Day"]["IconPhrase"]
            text += f"\n📆 {date}\n🌡 {min_t}°C → {max_t}°C\n☁️ {phrase}\n"

        bot.send_message (chat_id, text, parse_mode="Markdown")

    bot.answer_callback_query(call.id)


# ===================== ВЕБХУК ДЛЯ RENDER =====================
@app.post("/webhook")
async def webhook(request: Request):
    json_data = await request.json()
    update = telebot.types.Update.de_json(json_data)
    bot.process_new_updates([update])
    return {"ok": True}

@app.get("/")
def home():
    return {"status": "OK", "bot": "weather-bot"}


# ===================== ЗАПУСК =====================
if __name__ == '__main__':
    port = os.environ.get("PORT")

    # для запуску на Render
    if port:
        import uvicorn

        RENDER_URL = os.environ.get("RENDER_EXTERNAL_URL")
        bot.set_webhook(url=RENDER_URL, drop_pending_updates=True)

        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=int(port)
        )

    # для локального запуску
    else:
        try:
            bot.delete_webhook()
        except:
            pass
        bot.infinity_polling(skip_pending=True)