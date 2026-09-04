import threading
import os
import time
from flask import Flask
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.registration import start, rules
from handlers.relay import relay, whoami, menu, done, report
from handlers.admin import export_pairings, broadcast, reassign, roster, unmatched
from setup_game import setup

health_app = Flask(__name__)

# The Flask thread and the Telegram polling loop are independent, so a plain
# "ok" would keep reporting healthy long after polling had died. Reporting the
# real state means a failed poll fails Render's health check, which restarts
# the service instead of leaving it silently deaf.
tg_app = None
STARTUP_GRACE_SECONDS = 90
_started_at = time.monotonic()


def bot_is_polling() -> bool:
    return tg_app is not None and tg_app.updater is not None and tg_app.updater.running


@health_app.route("/")
def health():
    if bot_is_polling():
        return "ok"
    if time.monotonic() - _started_at < STARTUP_GRACE_SECONDS:
        return "starting", 200          # still booting; don't fail the deploy
    return "bot not polling", 503

def run_health_server():
    port = int(os.environ.get("PORT", 8080))
    health_app.run(host="0.0.0.0", port=port)

def main():
    global tg_app
    setup()
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    tg_app = app
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
    # Everything that is not a command reaches the relay, so an unsupported
    # message gets an explanation instead of being silently dropped.
    app.add_handler(MessageHandler(
        ~filters.COMMAND & ~filters.StatusUpdate.ALL, relay))
    app.run_polling()

if __name__ == "__main__":
    main()