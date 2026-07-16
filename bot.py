from telegram.ext import Application, CommandHandler, MessageHandler, filters
from config import BOT_TOKEN
from handlers.registration import start, rules
from handlers.relay import relay, whoami, menu, done

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler((filters.TEXT & ~filters.COMMAND) | filters.PHOTO, relay))
    app.run_polling()

if __name__ == "__main__":
    main()