import os
import logging
import threading
import nest_asyncio
from flask import Flask
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# -----------------------------
# Telegram Token & Chat-ID
# -----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))  # Private Chat oder Gruppe

# -----------------------------
# Flask Webserver für Render
# -----------------------------
app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Test Bot is alive!"

# -----------------------------
# Telegram Handler
# -----------------------------
async def postnow(update: ContextTypes.DEFAULT_TYPE):
    # sendet Nachricht an den Chat, in dem der Befehl abgesetzt wurde
    await update.message.reply_text("📊 Test Nachricht: /postnow funktioniert!")

# -----------------------------
# Telegram Bot Runner
# -----------------------------
async def run_bot():
    logging.info("🤖 Test Bot wird gestartet...")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("postnow", postnow))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    await application.updater.idle()


def start_bot_thread():
    nest_asyncio.apply()
    import asyncio
    asyncio.run(run_bot())

# -----------------------------
# Hauptstartpunkt für Render
# -----------------------------
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    # Bot im Hintergrund starten
    threading.Thread(target=start_bot_thread, daemon=True).start()

    # Flask im Vordergrund laufen lassen (Render benötigt offenen Port)
    app.run(host="0.0.0.0", port=10000)
