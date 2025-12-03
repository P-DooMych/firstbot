import os
import telebot

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start_handler(message):
    bot.reply_to(message, "Hello!!")

if __name__ == "__main__":
    bot.infinity_polling(skip_pending=True)