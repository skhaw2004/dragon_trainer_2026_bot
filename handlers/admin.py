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
    get_participant_by_id,
    get_unrecognized_attempts,
    get_all_participants,
    get_participant_by_id,
)
from matching import remove_participant, swap_participants
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

async def swap(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exchange two people's places in the cycle, to repair a pairing by hand.

    The opposite-gender preference cannot be enforced automatically — no gender
    is recorded — so /export flags who asked and this fixes the ones that are
    actually wrong.
    """
    if not is_admin(update.effective_user.id):
        return

    raw = " ".join(context.args)
    if "|" not in raw:
        await update.message.reply_text(
            "Usage: /swap <name> | <name>\n\n"
            "Names must match /roster exactly, separated by a vertical bar — "
            "names contain spaces, so the bar is what tells them apart.\n"
            "Example: /swap Tan Cher Hean | Zhang Xinyun"
        )
        return

    name_a, name_b = (part.strip() for part in raw.split("|", 1))
    people = {}
    for name in (name_a, name_b):
        person = get_participant_by_name(name)
        if person is None:
            await update.message.reply_text(
                f"No participant named '{name}'. Names must match /roster exactly."
            )
            return
        people[name] = person

    pairings = get_all_pairings()
    try:
        updated = swap_participants(pairings, people[name_a]["id"], people[name_b]["id"])
    except ValueError as e:
        await update.message.reply_text(f"Can't swap those: {e}.")
        return

    # Report the change from each affected person's point of view, before and
    # after, so the result can be checked rather than taken on trust.
    changed = [a for a in updated if updated[a] != pairings[a]]
    lines = ["✅ Swapped. Trainer -> dragon changes:"]
    for angel_id in changed:
        angel = get_participant_by_id(angel_id)
        was = get_participant_by_id(pairings[angel_id])
        now = get_participant_by_id(updated[angel_id])
        lines.append(f"  {angel['real_name']}: {was['real_name']} -> {now['real_name']}")

    save_pairings(updated)

    claimed = [get_participant_by_id(a)["real_name"] for a in changed
               if get_participant_by_id(a)["telegram_user_id"] is not None]
    if claimed:
        lines.append(
            f"\n⚠️ Already claimed, so they have seen their old dragon and must "
            f"be told: " + ", ".join(claimed)
        )
    lines.append("\nRun /export to check the result.")
    await reply_chunks(update.message, "\n".join(lines))
