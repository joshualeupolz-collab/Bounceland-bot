import os
import json
import logging
import threading
import asyncio
from datetime import datetime, timedelta
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes
from flask import Flask

# -----------------------------
# Konfiguration
# -----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID", "0"))
OWNER_ID = int(os.environ.get("OWNER_ID", "0"))

POLL_FILE = "poll_weeks.json"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# -----------------------------
# Hilfsfunktionen
# -----------------------------
def load_polls():
    if not os.path.exists(POLL_FILE):
        return {"users": {}}
    with open(POLL_FILE, "r") as f:
        return json.load(f)

def save_polls(data):
    with open(POLL_FILE, "w") as f:
        json.dump(data, f)

def get_weeks():
    start = datetime(2025, 11, 1)
    end = datetime(2026, 4, 30)
    weeks = []
    current = start
    while current <= end:
        iso = current.isocalendar()
        week_id = f"{iso[0]}-W{iso[1]:02d}"
        weeks.append((week_id, current.strftime("%d.%m.%Y")))
        current += timedelta(days=7 - current.weekday())
    return weeks

ARRIVAL_OPTIONS = ["Van", "Car", "Tent", "Hammock", "In someone else's", "Other"]
WEEK_OPTIONS = ["Ganze Woche", "Halbe Woche", "Nicht da"]

def build_arrival_keyboard(polls, user):
    selected = polls.get("users", {}).get(user, {}).get("arrival")
    buttons = []
    for opt in ARRIVAL_OPTIONS:
        label = f"✅ {opt}" if selected == opt else opt
        buttons.append([InlineKeyboardButton(label, callback_data=f"arrival|{opt}")])
    return InlineKeyboardMarkup(buttons)

def build_week_keyboard(polls, user, week_id):
    selected = polls.get("users", {}).get(user, {}).get("weeks", {}).get(week_id)
    buttons = []
    for opt in WEEK_OPTIONS:
        label = opt
        if selected == opt:
            label = f"✅ {opt}" if opt == "Ganze Woche" else f"🟡 {opt}" if opt == "Halbe Woche" else f"❌ {opt}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"week|{week_id}|{opt}")])
    return InlineKeyboardMarkup(buttons)

def calc_week_summary(polls):
    summary = {}
    weeks = get_weeks()
    for week_id, _ in weeks:
        total = 0
        for user_data in polls.get("users", {}).values():
            choice = user_data.get("weeks", {}).get(week_id)
            if choice == "Ganze Woche":
                total += 1
            elif choice == "Halbe Woche":
                total += 0.5
        summary[week_id] = total
    return summary

def get_color_icon(count):
    if count < 35:
        return "🟢"
    elif count <= 50:
        return "🟠"
    else:
        return "🔴"

def build_overview_text(polls):
    summary = calc_week_summary(polls)
    text = "📊 *Wochen-Übersicht*\n\n"
    for week_id, count in summary.items():
        color = get_color_icon(count)
        bars = int(count // 5) * "█"
        remainder = count % 5
        if remainder >= 2.5:
            bars += "▌"
        text += f"{color} {week_id}: {bars} ({count})\n"
    return text

# -----------------------------
# Button Handler
# -----------------------------
async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user.first_name
    data = load_polls()

    data_parts = query.data.split("|")
    if data_parts[0] == "arrival":
        choice = data_parts[1]
        if user not in data["users"]:
            data["users"][user] = {"arrival": choice, "weeks": {}}
        else:
            data["users"][user]["arrival"] = choice
    elif data_parts[0] == "week":
        week_id = data_parts[1]
        choice = data_parts[2]
        if user not in data["users"]:
            data["users"][user] = {"arrival": None, "weeks": {week_id: choice}}
        else:
            if "weeks" not in data["users"][user]:
                data["users"][user]["weeks"] = {}
            data["users"][user]["weeks"][week_id] = choice

    save_polls(data)

    if data_parts[0] == "arrival":
        await query.edit_message_text(
            "Wie bist du vor Ort?",
            reply_markup=build_arrival_keyboard(data, user)
        )
    elif data_parts[0] == "week":
        week_id = data_parts[1]
        await query.edit_message_text(
            f"Wochen-Auswahl für {week_id}:",
            reply_markup=build_week_keyboard(data, user, week_id)
        )
    await query.answer("✅ Updated!")

# -----------------------------
# Commands
# -----------------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Zuerst bitte angeben, wie du vor Ort bist:",
        reply_markup=build_arrival_keyboard(load_polls(), update.effective_user.first_name)
    )

async def cmd_week(update: Update, context: ContextTypes.DEFAULT_TYPE):
    weeks = get_weeks()
    first_week_id, _ = weeks[0]
    await update.message.reply_text(
        f"Wähle deine Anwesenheit für {first_week_id}:",
        reply_markup=build_week_keyboard(load_polls(), update.effective_user.first_name, first_week_id)
    )

async def cmd_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = load_polls()
    text = build_overview_text(data)
    await update.message.reply_text(text, parse_mode="Markdown")

# -----------------------------
# Flask für Keep-Alive
# -----------------------------
app_flask = Flask("keepalive")

@app_flask.route("/")
def home():
    return "Bot is alive"

@app_flask.route("/ping")
def ping():
    return "alive", 200

def start_webserver():
    app_flask.run(host="0.0.0.0", port=5000)

# -----------------------------
# Hauptfunktion
# -----------------------------
def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("❌ BOT_TOKEN oder CHAT_ID fehlt!")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("week", cmd_week))
    app.add_handler(CommandHandler("overview", cmd_overview))

    t = threading.Thread(target=start_webserver, daemon=True)
    t.start()

    async def start_bot():
        await app.initialize()
        await app.start()
        await app.updater.start_polling()
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            print("Stopping bot...")
        finally:
            await app.stop()
            await app.shutdown()

    asyncio.run(start_bot())

# -----------------------------
# Start
# -----------------------------
if __name__ == "__main__":
    main()
