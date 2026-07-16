import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "game.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    # can access column by name using: row["real_name"]
    return conn

def init_db():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS participants (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        real_name TEXT NOT NULL,
        join_code TEXT UNIQUE NOT NULL,
        telegram_user_id INTEGER,
        telegram_username TEXT,
        status TEXT NOT NULL DEFAULT 'invited',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("DATABASE INITIALIZED AT", DB_PATH)