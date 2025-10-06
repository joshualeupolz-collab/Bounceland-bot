import os
import logging
import threading
import nest_asyncio
from flask import Flask
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = int(os.environ.get("CHAT_ID"))

app = Flask(__name__)

@app.route("/")
def home():
    return "✅ Test Bot is alive!"

async def postnow(update: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Test Nachricht: /postnow funktioniert!")

async def run_bot():
    logging.info("🤖 Test Bot wird gestartet...")
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("postnow", postnow))
    await application.initialize()
    await application.start()
    await application.run_polling()

def start_bot_thread():
    nest_asyncio.apply()
    import asyncio
    asyncio.run(run_bot())

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    threading.Thread(target=start_bot_thread, daemon=True).start()
    app.run(host="0.0.0.0", port=10000)
