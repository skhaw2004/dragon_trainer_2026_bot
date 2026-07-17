from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from db import (
    get_pairings_with_names,
    get_all_claimed_participants,
    get_participant_by_name,
    get_all_pairings,
    save_pairings,
    mark_dropped,
)
from matching import remove_participant


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def export_pairings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    pairs = get_pairings_with_names()
    if not pairs:
        await update.message.reply_text("No pairings loaded yet.")
        return
    text = "\n".join(f"{angel} -> {mortal}" for angel, mortal in pairs)
    await update.message.reply_text(text)


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    participants = get_all_claimed_participants()
    sent = 0
    for p in participants:
        try:
            await context.bot.send_message(p["telegram_user_id"], f"📢 Admin Broadcast: \n{message_text}")
            sent += 1
        except Exception:
            pass  # e.g. they've blocked the bot
    await update.message.reply_text(f"Broadcast sent to {sent}/{len(participants)} participants.")


async def reassign(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /reassign <name>")
        return

    name = " ".join(context.args)
    participant = get_participant_by_name(name)
    if participant is None:
        await update.message.reply_text(f"No participant named '{name}'")
        return

    pairings = get_all_pairings()
    if participant["id"] not in pairings:
        await update.message.reply_text(f"{name} isn't currently in the pairings (already removed?).")
        return

    updated = remove_participant(participant["id"], pairings)
    save_pairings(updated)
    mark_dropped(participant["id"])

    await update.message.reply_text(
        f"{name} has been removed. Their angel is now connected directly to their old mortal."
    )

async def roster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    participants = get_all_participants()
    if not participants:
        await update.message.reply_text("No participants loaded yet.")
        return
    lines = [f"{p['real_name']} ({p['tier']}) — {p['status']}" for p in participants]
    await update.message.reply_text("\n".join(lines))