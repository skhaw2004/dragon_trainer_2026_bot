from telegram import Update
from telegram.ext import ContextTypes
from db import get_participant_by_username, claim_participant, get_my_mortal
from handlers.relay import MENU_KEYBOARD

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    participant = get_participant_by_username(user.username or "")

    if participant is None:
        await update.message.reply_text(
            "Your username could not be found! Make sure your Telegram username matches what you put on the "
            "Google Form. \n\n"
            "Contact @liyouzh1, @fartingtoe or @xyun_z if you need any help!"
        )
        return

    claim_participant(participant["id"], user.id)
    mortal = get_my_mortal(participant["id"])
    if mortal:
        mortal_details = (
            f"Your dragon is: {mortal['real_name']}\n"
            f"🏠 Lair (room): {mortal['room']}\n"
            f"❤️ Loves: {mortal['likes']}\n"
            f"💔 Dislikes: {mortal['dislikes']}\n"
            f"🚫 Off-limits (never do this): {mortal['off_limits']}\n"
            f"🎯 Tier: {mortal['tier']}"
        )
    else:
        mortal_details = "Your dragon is: someone — something's off, tell the host"

    await update.message.reply_text(
        f"🐉 Welcome to Draco's Dragon and Trainer 2026, {participant['real_name']}!\n\n"
        "The Draco Dragon Training Academy doesn't hand out assignments lightly — but you've been chosen. "
        "Somewhere out there, a dragon has been placed in your care. Not to ride. Not to tame. "
        "To quietly protect (and maybe sometimes prank), without ever letting them know it's you.\n\n"
        f"{mortal_details}\n\n"
        "What they don't know yet — is who you are.\n\n"
        "But here's the twist every good saga needs: perched on some ledge in RC4 out of your sight, a mystery Trainer "
        "has been watching over you too, just as quietly. You won't find out who until the Great "
        "Reveal, so keep your eyes sharp.\n\n"
        "Pick who your next message flies to using the buttons below, or type /menu any time to bring "
        "them back up. Type /rules if you forget how the training works. \n\n" 
        "We, @liyouzh1, @fartingtoe, @xyun_z, will watch over all of you trainers throughout the training. "
        "Do contact us should you need assistance in taming your dragon. \n\n"
        "And remember — the best "
        "Trainers never reveal themselves before the feast. 🔥 \n\n"
        "IMPORTANT: PLEASE ASK YOUR DRAGON FOR CONSENT BEFORE ENTERING THEIR ROOM THANKS",
        reply_markup=MENU_KEYBOARD,
    )

async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🐉 Dragon & Trainer 2026 RULES:\n"
        "- You know who your dragon is — send them anonymous messages through this bot and plan when to give welfare/pranks.\n"
        "- You don't know who your trainer is — but you can reply to them anonymously too.\n"
        "- Type /menu to choose who your messages go to, /done to disconnect.\n"
        "- Don't reveal who you are before the big reveal!"
    )