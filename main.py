import os
import json
import logging
import asyncio
import threading
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CallbackQueryHandler, CommandHandler, ContextTypes
from flask import Flask

# -----------------------------
# Konfiguration
# -----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))
THREAD_ID = int(os.environ.get("THREAD_ID", "0"))
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

POLL_FILE = "polls.json"
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def load_polls():
    if not os.path.exists(POLL_FILE):
        return {}
    with open(POLL_FILE, "r") as f:
        return json.load(f)

def save_polls(polls):
    with open(POLL_FILE, "w") as f:
        json.dump(polls, f)

def format_poll_text(poll):
    text = "🍽 *Weekly Meal Participation*\n\n"
    for day, users in poll.items():
        user_list = "\n".join([f"- {u}" for u in users]) if users else "–"
        text += f"*{day}*: {user_list}\n\n"
    return text

def build_keyboard():
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(day, callback_data=day)] for day in DAYS]
    )

# -----------------------------
# Button Handling
# -----------------------------
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user.first_name
    day = query.data
    data = load_polls()
    polls = data.get("polls", {})

    if day not in polls:
        polls[day] = []

    if user in polls[day]:
        polls[day].remove(user)
    else:
        polls[day].append(user)

    data["polls"] = polls
    save_polls(data)
    await query.answer("✅ Updated!")

    text = format_poll_text(polls)
    try:
        await query.edit_message_text(text=text, reply_markup=build_keyboard(), parse_mode="Markdown")
    except:
        pass

# -----------------------------
# Wochen-Umfrage posten
# -----------------------------
async def post_weekly_poll(app):
    polls = {day: [] for day in DAYS}
    save_polls({"polls": polls})
    text = format_poll_text(polls)
    kwargs = {
        "chat_id": CHAT_ID,
        "text": text,
        "reply_markup": build_keyboard(),
        "parse_mode": "Markdown"
    }
    if THREAD_ID:
        kwargs["message_thread_id"] = THREAD_ID

    await app.bot.send_message(**kwargs)
    logging.info("✅ Neue Wochenumfrage gepostet.")

# -----------------------------
# Manueller Befehl /postnow
# -----------------------------
async def cmd_postnow(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if OWNER_ID and user_id != OWNER_ID:
        await update.message.reply_text("⛔️ Only the owner can use this command.")
        return
    await post_weekly_poll(context.application)
    await update.message.reply_text("✅ Neue Wochenumfrage gepostet!")

# -----------------------------
# Mini-Webserver (für Keep-Alive)
# -----------------------------
app_flask = Flask("keepalive")

@app_flask.route("/")
def home():
    return "Bot is alive ✅"

@app_flask.route("/ping")
def ping():
    return "pong", 200

def start_simple_webserver():
    app_flask.run(host="0.0.0.0", port=5000)

# -----------------------------
# Hauptfunktion
# -----------------------------
async def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ ERROR: BOT_TOKEN oder CHAT_ID fehlen (in Secrets setzen)!")
        return

    application = Application.builder().token(BOT_TOKEN).build()
    application.add_handler(CallbackQueryHandler(handle_button))
    application.add_handler(CommandHandler("postnow", cmd_postnow))

    # Flask Webserver starten
    t = threading.Thread(target=start_simple_webserver, daemon=True)
    t.start()

    # Scheduler für automatische Posts
    scheduler = AsyncIOScheduler(timezone="Europe/Berlin")
    scheduler.add_job(post_weekly_poll, trigger="cron", day_of_week="sat", hour=18, minute=0, args=[application])
    scheduler.start()

    logging.info("✅ Bot & Scheduler laufen (Samstag 18:00 Europe/Berlin)")
    await application.initialize()
    await application.start()
    await application.run_polling()

if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()  # erlaubt paralleles Flask + Telegram

    loop = asyncio.get_event_loop()

    def run_bot():
        loop.run_until_complete(main())

    # Flask separat starten
    threading.Thread(target=start_simple_webserver, daemon=True).start()

    # Telegram-Bot starten
    try:
        run_bot()
    except (KeyboardInterrupt, SystemExit):
        logging.info("🛑 Bot stopped manually.")
