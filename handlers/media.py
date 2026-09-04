"""Relay the message types participants actually send.

The relay originally handled text and photos only, and the handler filter
matched nothing else — so a sticker, GIF or voice note was dropped with no
delivery, no error and no reply. Over two weeks with ~80 students that is a
certainty, and it reads as the bot being broken.
"""

# Captions are capped at 1024 characters, not 4096.
CAPTION_LIMIT = 1024

# Order matters: Telegram sets .document alongside .animation for GIFs, so the
# more specific kinds have to be tested first.
_KINDS = (
    ("photo",      lambda m: m.photo[-1].file_id if m.photo else None),
    ("sticker",    lambda m: m.sticker.file_id if m.sticker else None),
    ("animation",  lambda m: m.animation.file_id if m.animation else None),
    ("voice",      lambda m: m.voice.file_id if m.voice else None),
    ("video_note", lambda m: m.video_note.file_id if m.video_note else None),
    ("video",      lambda m: m.video.file_id if m.video else None),
    ("audio",      lambda m: m.audio.file_id if m.audio else None),
    ("document",   lambda m: m.document.file_id if m.document else None),
)

# Stickers and video notes carry no caption.
_CAPTIONABLE = {"photo", "animation", "voice", "video", "audio", "document"}

# The sender cannot see what metadata rides along with these, and a file called
# "stuart_holiday.jpg" ends the game for them. Warn rather than block.
_METADATA_LEAKS = {"document", "audio"}

_LABELS = {
    "photo": "Photo", "sticker": "Sticker", "animation": "GIF",
    "voice": "Voice message", "video_note": "Video note", "video": "Video",
    "audio": "Audio", "document": "File",
}


def find_media(message):
    """Return (kind, file_id) for whatever media the message holds."""
    for kind, get in _KINDS:
        file_id = get(message)
        if file_id:
            return kind, file_id
    return None, None


def leaks_metadata(kind: str) -> bool:
    return kind in _METADATA_LEAKS


def label_for(kind: str) -> str:
    return _LABELS.get(kind, kind)


async def send_media(bot, chat_id: int, kind: str, file_id: str, caption: str = None):
    """Resend media by file_id. Returns any caption text that did not fit."""
    overflow = None
    if kind not in _CAPTIONABLE:
        caption = None
    elif caption and len(caption) > CAPTION_LIMIT:
        # Send the media with just the attribution and the rest as its own
        # message, rather than letting Telegram reject the whole thing.
        head, overflow = caption[:CAPTION_LIMIT], caption[CAPTION_LIMIT:]
        caption = head

    senders = {
        "photo":      bot.send_photo,
        "sticker":    bot.send_sticker,
        "animation":  bot.send_animation,
        "voice":      bot.send_voice,
        "video_note": bot.send_video_note,
        "video":      bot.send_video,
        "audio":      bot.send_audio,
        "document":   bot.send_document,
    }
    send = senders[kind]
    if kind in _CAPTIONABLE:
        await send(chat_id, file_id, caption=caption)
    else:
        await send(chat_id, file_id)
    return overflow
