import asyncio
import logging
import threading
from flask import Flask
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

# -----------------------------------------------------
# Konfiguration
# -----------------------------------------------------
BOT_TOKEN = "8462904785:AAEpAT43bmCj1uWpYxmFdyaaWm4tul9f-5Y"
CHAT_ID = "-1002317320028"

# -----------------------------------------------------
# Flask Webserver für Render
# -----------------------------------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Bot is alive and running!"


# -----------------------------------------------------
# Telegram Bot Logik
# -----------------------------------------------------
user_responses = {}

OPTIONS = ["Option A", "Option B", "Option C"]

def get_keyboard():
    keyboard = [
        [InlineKeyboardButton(opt, callback_data=opt)] for opt in OPTIONS
    ]
    return InlineKeyboardMarkup(keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hey 👋 Wähle bitte eine Option:", reply_markup=get_keyboard())


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    choice = query.data
    user_responses[user_id] = choice

    await query.answer(f"✅ Deine Wahl: {choice}")
    await query.edit_message_text(text=f"Du hast **{choice}** gewählt.", parse_mode="Markdown")


async def postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=CHAT_ID, text="📊 Neue Umfrage:", reply_markup=get_keyboard())


# -----------------------------------------------------
# Telegram Bot Runner (läuft im Hintergrund)
# -----------------------------------------------------
async def run_bot():
    logging.info("🤖 Telegram-Bot wird gestartet...")

    app_builder = ApplicationBuilder().token(BOT_TOKEN).build()
    app_builder.add_handler(CommandHandler("start", start))
    app_builder.add_handler(CommandHandler("postnow", postnow))
    app_builder.add_handler(CallbackQueryHandler(button_click))

    await app_builder.initialize()
    await app_builder.start()
    await app_builder.updater.start_polling()
    await app_builder.updater.idle()


def start_bot_thread():
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(run_bot())


# -----------------------------------------------------
# Hauptstartpunkt für Render
# -----------------------------------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Bot im Hintergrund-Thread starten
    threading.Thread(target=start_bot_thread, daemon=True).start()

    # Flask im Vordergrund laufen lassen (Render erwartet einen offenen Port)
    app.run(host="0.0.0.0", port=10000)
