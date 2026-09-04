import os
import sqlite3
from pathlib import Path

# On Render the database must live on the mounted persistent disk, otherwise it
# is wiped on every deploy/restart. DB_DIR points at that mount in production;
# locally it is unset and the database stays next to the code as before.
DB_DIR = Path(os.environ.get("DB_DIR") or Path(__file__).parent)
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "game.db"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        real_name TEXT NOT NULL,
        telegram_username TEXT UNIQUE NOT NULL,
        telegram_user_id INTEGER,
        tier TEXT NOT NULL CHECK(tier IN ('easy', 'medium', 'hard')),
        status TEXT NOT NULL DEFAULT 'invited',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        room TEXT,
        likes TEXT,
        dislikes TEXT,
        off_limits TEXT,
        chat_mode TEXT NOT NULL DEFAULT 'none' CHECK(chat_mode IN('none', 'mortal', 'angel'))
    );

    CREATE TABLE IF NOT EXISTS pairings (
        angel_id INTEGER NOT NULL,
        mortal_id INTEGER NOT NULL,
        FOREIGN KEY (angel_id) REFERENCES participants(id),
        FOREIGN KEY (mortal_id) REFERENCES participants(id)
    );

    CREATE TABLE IF NOT EXISTS message_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_id INTEGER NOT NULL,
        to_id INTEGER NOT NULL,
        content_type TEXT NOT NULL,
        content TEXT NOT NULL,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        reported BOOLEAN DEFAULT 0,
        FOREIGN KEY (from_id) REFERENCES participants(id),
        FOREIGN KEY (to_id) REFERENCES participants(id)
    );
                       
    CREATE TABLE IF NOT EXISTS unrecognized_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_user_id INTEGER,
        telegram_username TEXT,
        attempted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE VIEW IF NOT EXISTS pairings_readable AS
    SELECT a.real_name AS angel_name, m.real_name AS mortal_name
    FROM pairings p
    JOIN participants a ON p.angel_id = a.id
    JOIN participants m ON p.mortal_id = m.id;
    """)
    conn.commit()
    conn.close()


def import_participants(participants: list[dict]):
    conn = get_connection()
    for p in participants:
        conn.execute(
            """INSERT INTO participants
               (real_name, telegram_username, tier, room, likes, dislikes, off_limits)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                p["name"].strip(),
                p["username"].strip().lstrip("@").lower(),
                p["tier"].strip().lower(),
                p.get("room", "").strip(),
                p.get("likes", "").strip(),
                p.get("dislikes", "").strip(),
                p.get("off_limits", "").strip(),
            ),
        )
    conn.commit()
    conn.close()


def get_participant_by_name(name: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, tier FROM participants WHERE real_name = ?", (name,)
    ).fetchone()
    conn.close()
    return row


def get_participant_by_username(username: str):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, real_name, tier, status FROM participants WHERE telegram_username = ?",
        (username.strip().lstrip("@").lower(),),
    ).fetchone()
    conn.close()
    return row


def get_participant_ids_by_tier(tier: str) -> list[int]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id FROM participants WHERE tier = ?", (tier.lower(),)
    ).fetchall()
    conn.close()
    return [row["id"] for row in rows]


def save_pairings(pairings: dict[int, int]):
    conn = get_connection()
    conn.execute("DELETE FROM pairings")
    conn.executemany(
        "INSERT INTO pairings (angel_id, mortal_id) VALUES (?, ?)",
        list(pairings.items()),
    )
    conn.commit()
    conn.close()


def get_pairings_with_names():
    conn = get_connection()
    rows = conn.execute("""
        SELECT a.real_name AS angel_name, m.real_name AS mortal_name
        FROM pairings p
        JOIN participants a ON p.angel_id = a.id
        JOIN participants m ON p.mortal_id = m.id
    """).fetchall()
    conn.close()
    return [(row["angel_name"], row["mortal_name"]) for row in rows]


def claim_participant(participant_id: int, telegram_user_id: int):
    conn = get_connection()
    conn.execute(
        "UPDATE participants SET telegram_user_id = ?, status = 'claimed' WHERE id = ?",
        (telegram_user_id, participant_id),
    )
    conn.commit()
    conn.close()

def get_my_mortal(participant_id: int):
    conn = get_connection()
    row = conn.execute("""
        SELECT p2.id, p2.real_name, p2.telegram_user_id, p2.tier, p2.room, p2.likes, p2.dislikes, p2.off_limits
        FROM pairings p JOIN participants p2 ON p.mortal_id = p2.id
        WHERE p.angel_id = ?
    """, (participant_id,)).fetchone()
    conn.close()
    return row


def get_my_angel(participant_id: int):
    conn = get_connection()
    row = conn.execute("""
        SELECT p2.id, p2.real_name, p2.telegram_user_id
        FROM pairings p JOIN participants p2 ON p.angel_id = p2.id
        WHERE p.mortal_id = ?
    """, (participant_id,)).fetchone()
    conn.close()
    return row


def get_participant_by_telegram_id(telegram_user_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, real_name, chat_mode, telegram_user_id FROM participants WHERE telegram_user_id = ?",
        (telegram_user_id,),
    ).fetchone()
    conn.close()
    return row


def set_chat_mode(participant_id: int, mode: str):
    conn = get_connection()
    conn.execute("UPDATE participants SET chat_mode = ? WHERE id = ?", (mode, participant_id))
    conn.commit()
    conn.close()


def reset_all_chat_modes() -> int:
    """Clear connections left dangling by a restart.

    chat_mode is stored in the database, but the idle-disconnect timers are
    in-memory APScheduler jobs that die with the process. Without this, anyone
    connected when the bot restarts stays connected indefinitely, and their next
    message — possibly hours later — silently goes to their dragon or trainer.
    """
    conn = get_connection()
    cur = conn.execute("UPDATE participants SET chat_mode = 'none' WHERE chat_mode != 'none'")
    cleared = cur.rowcount
    conn.commit()
    conn.close()
    return cleared


def log_message(from_id: int, to_id: int, content_type: str, content: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO message_log (from_id, to_id, content_type, content) VALUES (?, ?, ?, ?)",
        (from_id, to_id, content_type, content),
    )
    conn.commit()
    conn.close()

def get_last_received_message(participant_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM message_log WHERE to_id = ? ORDER BY sent_at DESC LIMIT 1",
        (participant_id,),
    ).fetchone()
    conn.close()
    return row


def mark_message_reported(message_id: int):
    conn = get_connection()
    conn.execute("UPDATE message_log SET reported = 1 WHERE id = ?", (message_id,))
    conn.commit()
    conn.close()


def get_participant_by_id(participant_id: int):
    conn = get_connection()
    row = conn.execute(
        "SELECT id, real_name, telegram_username, telegram_user_id FROM participants WHERE id = ?",
        (participant_id,),
    ).fetchone()
    conn.close()
    return row

def get_all_claimed_participants():
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, real_name, telegram_user_id FROM participants WHERE status = 'claimed'"
    ).fetchall()
    conn.close()
    return rows


def get_all_pairings() -> dict[int, int]:
    conn = get_connection()
    rows = conn.execute("SELECT angel_id, mortal_id FROM pairings").fetchall()
    conn.close()
    return {row["angel_id"]: row["mortal_id"] for row in rows}

def get_all_participants():
    conn = get_connection()
    rows = conn.execute("SELECT real_name, tier, status FROM participants ORDER BY real_name").fetchall()
    conn.close()
    return rows

def mark_dropped(participant_id: int):
    conn = get_connection()
    conn.execute("UPDATE participants SET status = 'dropped' WHERE id = ?", (participant_id,))
    conn.commit()
    conn.close()

def has_participants() -> bool:
    conn = get_connection()
    row = conn.execute("SELECT COUNT(*) as cnt FROM participants").fetchone()
    conn.close()
    return row["cnt"] > 0

def log_unrecognized_attempt(telegram_user_id: int, telegram_username: str):
    conn = get_connection()
    conn.execute(
        "INSERT INTO unrecognized_attempts (telegram_user_id, telegram_username) VALUES (?, ?)",
        (telegram_user_id, telegram_username or ""),
    )
    conn.commit()
    conn.close()

def get_unrecognized_attempts():
    conn = get_connection()
    rows = conn.execute(
        "SELECT telegram_user_id, telegram_username, attempted_at FROM unrecognized_attempts ORDER BY attempted_at DESC"
    ).fetchall()
    conn.close()
    return rows

if __name__ == "__main__":
    init_db()
    print("Database initialized at", DB_PATH)