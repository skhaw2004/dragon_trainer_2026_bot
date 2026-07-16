from telegram import Update
from telegram.ext import ContextTypes
from db import get_participant_by_username, claim_participant, get_my_mortal
from handlers.relay import MENU_KEYBOARD

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    participant = get_participant_by_username(user.username or "")

    if participant is None:
        await update.message.reply_text(
            "Your username could not be found. Make sure your Telegram username matches what you put on the "
            "Google sign-up form."
        )
        return

    claim_participant(participant["id"], user.id)
    mortal = get_my_mortal(participant["id"])
    mortal_name = mortal["real_name"] if mortal else "someone — something's off, tell the host"

    await update.message.reply_text(
        f"Welcome to Dragon & Trainer 2026, {participant['real_name']}!\n\n"
        f"Your trainer is: {mortal_name}. Send them anonymous kindness any time through this bot.\n"
        "You'll also get anonymous messages from your own secret trainer — you can reply to them too.\n\n"
        "Pick who to talk to below, or type /menu any time to bring this up again.",
        reply_markup=MENU_KEYBOARD,
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Dragon & Trainer 2026 RULES:\n"
        "- You know who your dragon is — send them anonymous kindness through this bot.\n"
        "- You don't know who your trainer is — but you can reply to them anonymously too.\n"
        "- Type /menu to choose who your messages go to, /done to disconnect.\n"
        "- Don't reveal who you are before the big reveal!"
    )