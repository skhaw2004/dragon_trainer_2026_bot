from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from handlers.chunking import reply_chunks, send_chunks
from handlers.media import find_media, label_for, leaks_metadata, send_media
from db import get_participant_by_telegram_id, get_my_mortal, get_my_angel, log_message, set_chat_mode, get_last_received_message, mark_message_reported, get_participant_by_id

MORTAL_BUTTON = "🐉 Chat with your Dragon"
ANGEL_BUTTON = "🏋️ Chat with your Trainer"
IDLE_SECONDS = 120

MENU_KEYBOARD = ReplyKeyboardMarkup([[MORTAL_BUTTON, ANGEL_BUTTON]], resize_keyboard=True)


def idle_job_name(telegram_user_id: int) -> str:
    return f"idle_{telegram_user_id}"


def reset_idle_timer(context, telegram_user_id: int, participant_id: int):
    for job in context.job_queue.get_jobs_by_name(idle_job_name(telegram_user_id)):
        job.schedule_removal()
    context.job_queue.run_once(
        disconnect_due_to_idle, when=IDLE_SECONDS,
        chat_id=telegram_user_id, data=participant_id, name=idle_job_name(telegram_user_id),
    )


async def disconnect_due_to_idle(context: ContextTypes.DEFAULT_TYPE):
    set_chat_mode(context.job.data, "none")
    await context.bot.send_message(
        context.job.chat_id,
        f"You've been inactive for {IDLE_SECONDS // 60} minute(s) and have been disconnected. Type /menu to reconnect.",
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Who do you want to talk to?", reply_markup=MENU_KEYBOARD)


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = get_participant_by_telegram_id(update.effective_user.id)
    if sender is None:
        return
    set_chat_mode(sender["id"], "none")
    for job in context.job_queue.get_jobs_by_name(idle_job_name(update.effective_user.id)):
        job.schedule_removal()
    await update.message.reply_text("You've disconnected. Type /menu to reconnect.")


async def relay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = get_participant_by_telegram_id(update.effective_user.id)
    if sender is None:
        await update.message.reply_text("I don't recognize you — message /start first.")
        return

    text = update.message.text

    if text == MORTAL_BUTTON:
        set_chat_mode(sender["id"], "mortal")
        reset_idle_timer(context, update.effective_user.id, sender["id"])
        await update.message.reply_text(
            "You've been connected with your dragon 🐉. Anything you type here will be sent "
            "anonymously to them.\nTo exit, type /done"
        )
        return

    if text == ANGEL_BUTTON:
        set_chat_mode(sender["id"], "angel")
        reset_idle_timer(context, update.effective_user.id, sender["id"])
        await update.message.reply_text(
            "You've been connected with your trainer 🏋️. Anything you type here will be sent "
            "anonymously to them.\nTo exit, type /done"
        )
        return

    if sender["chat_mode"] == "none":
        await update.message.reply_text("You're not connected to anyone right now. Type /menu to choose.")
        return

    if sender["chat_mode"] == "angel":
        recipient = get_my_angel(sender["id"])
        recipient_label = "your trainer"    
        sender_label = "your dragon"      
    else:
        recipient = get_my_mortal(sender["id"])
        recipient_label = "your dragon"
        sender_label = "your trainer"

    if recipient is None or recipient["telegram_user_id"] is None:
        await update.message.reply_text(f"{recipient_label.capitalize()} hasn't joined the bot yet. Try again later.")
        return

    reset_idle_timer(context, update.effective_user.id, sender["id"])

    if update.message.text:
        await send_chunks(context.bot, recipient["telegram_user_id"],
                          f"💌 Message from {sender_label}:\n\n{update.message.text}")
        log_message(sender["id"], recipient["id"], "text", update.message.text)
        return

    kind, file_id = find_media(update.message)
    if kind is None:
        # Locations, contacts, polls and the like have no anonymous equivalent.
        # Say so — silence is indistinguishable from the bot being broken.
        await update.message.reply_text(
            "I can only pass on text, photos, stickers, GIFs, voice notes, "
            "videos, audio and files. That one didn't go through — try "
            "sending it another way."
        )
        return

    # The sender's own caption used to be discarded entirely.
    header = f"💌 {label_for(kind)} from {sender_label}"
    caption = f"{header}:\n\n{update.message.caption}" if update.message.caption else header

    overflow = await send_media(context.bot, recipient["telegram_user_id"],
                                kind, file_id, caption)
    if overflow:
        await send_chunks(context.bot, recipient["telegram_user_id"], overflow)
    log_message(sender["id"], recipient["id"], kind, file_id)

    if leaks_metadata(kind):
        await update.message.reply_text(
            f"⚠️ Sent — but {label_for(kind).lower()}s carry their file name and "
            f"details, which your recipient can see. Rename before sending if "
            f"it gives you away."
        )


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = get_participant_by_telegram_id(update.effective_user.id)
    if sender is None:
        await update.message.reply_text("I don't recognize you — message /start first.")
        return
    if sender["chat_mode"] == "none":
        await update.message.reply_text("You're not connected to anyone right now. Type /menu to choose.")
    else:
        await update.message.reply_text(f"You're currently connected to: your {sender['chat_mode']}.")

async def report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    sender = get_participant_by_telegram_id(update.effective_user.id)
    if sender is None:
        await update.message.reply_text("I don't recognize you — message /start first.")
        return

    msg = get_last_received_message(sender["id"])
    if msg is None:
        await update.message.reply_text("You haven't received any messages yet to report.")
        return

    mark_message_reported(msg["id"])
    reported_sender = get_participant_by_id(msg["from_id"])
    header = (
        f"🚩 Report from {sender['real_name']} (@{sender['telegram_username']}):\n"
        f"Message was from {reported_sender['real_name']} (@{reported_sender['telegram_username']}), "
        f"sent at {msg['sent_at']}"
    )

    for admin_id in ADMIN_IDS:
        await context.bot.send_message(admin_id, header)
        if msg["content_type"] == "text":
            await send_chunks(context.bot, admin_id, msg["content"])
        else:
            await send_media(context.bot, admin_id, msg["content_type"], msg["content"])

    await update.message.reply_text("Thanks, I've flagged this to the host.")