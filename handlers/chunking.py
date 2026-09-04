"""Send messages that may exceed Telegram's per-message limit.

Telegram rejects messages over 4096 characters with a BadRequest. Nothing here
registers an error handler, so an oversized send produces no reply at all — the
command looks like it silently did nothing, which is indistinguishable from the
bot being down. Several messages grow without bound: the admin listings grow
with headcount, and the relay and the /start reveal both embed text written by
participants.
"""

# Telegram measures length in UTF-16 code units, so an emoji outside the basic
# plane counts as two. Leave headroom for the part-number prefix as well.
TELEGRAM_LIMIT = 4096
SAFE_LIMIT = 3900


def telegram_len(text: str) -> int:
    return len(text.encode("utf-16-le")) // 2


def _truncate_to_units(text: str, units: int) -> str:
    """Longest prefix of text that fits in `units` UTF-16 code units.

    Slicing by character count is wrong here: an emoji is one character but two
    units, so a character-based cut can produce a piece twice the intended size.
    Python slices code points, so this can never split a surrogate pair.
    """
    if telegram_len(text) <= units:
        return text
    lo, hi = 0, len(text)
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if telegram_len(text[:mid]) <= units:
            lo = mid
        else:
            hi = mid - 1
    return text[:lo]


def split_for_telegram(text: str, limit: int = SAFE_LIMIT) -> list[str]:
    """Split text into sendable pieces, preferring line boundaries.

    A single line longer than the limit is hard-split rather than dropped —
    someone will eventually paste a wall of text with no newlines in it.
    """
    if not text:
        return []
    if telegram_len(text) <= limit:
        return [text]

    chunks, current = [], ""
    for line in text.split("\n"):
        while telegram_len(line) > limit:          # one very long line
            if current:
                chunks.append(current)
                current = ""
            head = _truncate_to_units(line, limit)
            chunks.append(head)
            line = line[len(head):]
        candidate = f"{current}\n{line}" if current else line
        if telegram_len(candidate) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return [c for c in chunks if c]


def _numbered(chunks: list[str], numbered: bool) -> list[str]:
    if not numbered or len(chunks) <= 1:
        return chunks
    total = len(chunks)
    return [f"({i}/{total})\n{c}" for i, c in enumerate(chunks, 1)]


async def reply_chunks(message, text: str, numbered: bool = True, **kwargs):
    """Reply to a message, splitting if needed. kwargs go to the first part."""
    chunks = _numbered(split_for_telegram(text), numbered)
    for i, chunk in enumerate(chunks):
        await message.reply_text(chunk, **(kwargs if i == 0 else {}))
    return len(chunks)


async def send_chunks(bot, chat_id: int, text: str, numbered: bool = False, **kwargs):
    """Send to a chat id, splitting if needed. kwargs go to the first part."""
    chunks = _numbered(split_for_telegram(text), numbered)
    for i, chunk in enumerate(chunks):
        await bot.send_message(chat_id, chunk, **(kwargs if i == 0 else {}))
    return len(chunks)
