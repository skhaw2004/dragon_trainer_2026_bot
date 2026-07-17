import threading
import os
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.registration import start, rules
from handlers.relay import relay, whoami, menu, done, report
from handlers.admin import export_pairings, broadcast, reassign, roster, unmatched
from setup_game import setup

health_app = Flask(__name__)

@health_app.route("/")
def health():
    return "ok"

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    health_app.run(host="0.0.0.0", port=port)

def main():
    setup()
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(CommandHandler("report", report))
    app.add_handler(CommandHandler("export", export_pairings))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("reassign", reassign))
    app.add_handler(CommandHandler("roster", roster))
    app.add_handler(CommandHandler("unmatched", unmatched))
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO, relay))
    app.run_polling()

if __name__ == "__main__":
    main()