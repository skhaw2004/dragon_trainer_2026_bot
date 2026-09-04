import asyncio

from telegram import Update
from telegram.error import Forbidden, RetryAfter, TelegramError
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from db import (
    get_pairings_for_review,
    get_all_claimed_participants,
    get_participant_by_name,
    get_all_pairings,
    save_pairings,
    mark_dropped,
    get_all_participants,
    get_unrecognized_attempts,
    get_all_participants,
)
from matching import remove_participant
from handlers.chunking import reply_chunks, send_chunks


# Telegram allows roughly 30 messages per second across different chats. Pace
# below that: a tight loop over 80 people trips flood control, and the previous
# bare `except: pass` discarded those failures without a trace.
SEND_INTERVAL = 0.05
SEND_ATTEMPTS = 3


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def _send_with_retry(bot, chat_id: int, text: str):
    """Send, honouring Telegram's own back-off request if flood control trips."""
    for attempt in range(SEND_ATTEMPTS):
        try:
            return await send_chunks(bot, chat_id, text)
        except RetryAfter as e:
            if attempt == SEND_ATTEMPTS - 1:
                raise
            await asyncio.sleep(e.retry_after + 1)


async def export_pairings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    rows = get_pairings_for_review()
    if not rows:
        await update.message.reply_text("No pairings loaded yet.")
        return

    lines, flagged = [], 0
    for r in rows:
        line = f"[{r['tier']}] {r['angel_name']} -> {r['mortal_name']}"
        if not r["mortal_gender_ok"]:
            # Gender is not recorded, so this cannot be enforced automatically.
            # Flag it so the host can check the trainer by hand.
            line += "  ⚠️ wants same-gender trainer"
            flagged += 1
        if r["mortal_notes"]:
            line += f"  📝 {r['mortal_notes']}"
        lines.append(line)

    if flagged:
        lines.append(f"\n⚠️ {flagged} dragon(s) asked for a same-gender trainer — "
                     f"check those pairings yourself.")
    await reply_chunks(update.message, "\n".join(lines))


async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    message_text = " ".join(context.args)
    if not message_text:
        await update.message.reply_text("Usage: /broadcast <message>")
        return

    participants = get_all_claimed_participants()
    if not participants:
        await update.message.reply_text(
            "Nobody has claimed their account yet, so there is no one to broadcast to. "
            "Participants become reachable only after they send /start."
        )
        return

    text = f"📢 Admin Broadcast: \n{message_text}"
    sent, blocked, failed = 0, [], []

    for p in participants:
        try:
            await _send_with_retry(context.bot, p["telegram_user_id"], text)
            sent += 1
        except Forbidden:
            # They blocked the bot or deleted the chat. Permanent; do not retry.
            blocked.append(p["real_name"])
        except (TelegramError, OSError) as e:
            failed.append(f"{p['real_name']} ({type(e).__name__})")
        await asyncio.sleep(SEND_INTERVAL)

    lines = [f"📢 Broadcast finished.", f"✅ Delivered: {sent}/{len(participants)} claimed"]
    if blocked:
        lines.append(f"\n🚫 Blocked the bot ({len(blocked)}): " + ", ".join(blocked))
    if failed:
        lines.append(f"\n⚠️ Failed ({len(failed)}): " + ", ".join(failed))

    # Unclaimed participants cannot be messaged at all — Telegram gives a bot no
    # way to reach someone who has never messaged it. Say so explicitly, or a
    # broadcast looks complete while silently missing people.
    unclaimed = [r["real_name"] for r in get_all_participants() if r["status"] != "claimed"]
    if unclaimed:
        lines.append(
            f"\n📭 Never reached, has not sent /start ({len(unclaimed)}): "
            + ", ".join(unclaimed)
        )
    await reply_chunks(update.message, "\n".join(lines))


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
    await reply_chunks(update.message, "\n".join(lines))

async def unmatched(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    attempts = get_unrecognized_attempts()
    if not attempts:
        await update.message.reply_text("No unrecognized attempts logged.")
        return
    lines = [
        f"@{a['telegram_username'] or '(no username)'} (id {a['telegram_user_id']}) at {a['attempted_at']}"
        for a in attempts
    ]
    await reply_chunks(update.message, "\n".join(lines))