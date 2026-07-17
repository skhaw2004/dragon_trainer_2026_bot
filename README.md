# Dragon & Trainer 2026 🐉

A Telegram bot for running an anonymous Angel/Mortal game for a group of 40-50 people. Each "Trainer" (angel) is secretly assigned a "Dragon" (mortal) to look after anonymously, while a mystery Trainer of their own watches over them in return — until the big reveal. Built for Draco House at Residential College 4, NUS.

## How the game works

- Participants sign up via a Google Form, providing their name, tier (easy/medium/hard), Telegram username as well as their likes/dislikes and strict off-limits.
- The host manually decides pairings within each tier and loads everyone into the bot before launch.
- Once live, each person messages the bot with `/start`. The bot recognizes them by their Telegram username, tells them who their Dragon is (with room, likes, dislikes, and off-limits info), and lets them message their Dragon anonymously — or reply anonymously to their own unknown Trainer.
- A `/report` command lets anyone flag an inappropriate message to the host, revealing the real sender's identity only to admins.
- Admins can broadcast announcements with `/broadcast`, reassign dropouts mid-game without disrupting anyone else's pairing with `/reassign`, and export the full pairing list for a live reveal event with `/export`.

## Tech stack

- **Python** 3.9+
- **python-telegram-bot** — Telegram Bot API, commands, message handling, job scheduling
- **SQLite** (`sqlite3`, built-in) — participant/pairing/message data
- **python-dotenv** — loads secrets from `.env`
- **Flask** — minimal health-check endpoint for Render deployment
- **Render** — hosting, free tier

## Project structure

```
d-t-Bot/
  bot.py                  # entrypoint: health server, handler registration, polling
  config.py                # loads BOT_TOKEN and ADMIN_IDS from environment
  db.py                    # SQLite schema + all database queries
  matching.py               # manual pairing validation, dropout splicing
  setup_game.py              # participant/pairing data, auto-run on startup
  handlers/
    registration.py          # /start, /rules
    relay.py                  # anonymous message relay, /menu, /done, /whoami, /report
    admin.py                   # /roster, /unmatched, /broadcast, /reassign, /export
  requirements.txt
  .env.example
```

## Setup (local development)

1. Create a bot via [@BotFather](https://t.me/BotFather) on Telegram, get your token.
2. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill in your real values:
   ```
   BOT_TOKEN=your-bot-token
   ADMIN_IDS=your-telegram-user-id
   ```
4. Fill in `PARTICIPANTS` and `PAIRINGS` in `setup_game.py` with real (or test) data.
5. Run the bot:
   ```
   python bot.py
   ```

## Participant commands

| Command | Description |
|---|---|
| `/start` | Claims your identity and reveals your Dragon's details |
| `/rules` | Reminder of how the game works |
| `/menu` | Bring up the "Chat with your Mortal / Chat with your Angel" picker |
| `/done` | Disconnect from whoever you're currently messaging |
| `/whoami` | Check who you're currently connected to |
| `/report` | Flag the most recently received message to the host |

## Admin commands

*(only work for Telegram user IDs listed in `ADMIN_IDS`)*

| Command | Description |
|---|---|
| `/roster` | List all participants and their claim status |
| `/unmatched` | List anyone who tried `/start` but wasn't recognized |
| `/export` | Dump the full pairing list by name (for the live reveal) |
| `/broadcast <message>` | Send an announcement to every claimed participant |
| `/reassign <name>` | Remove a dropout, splicing their angel directly to their old mortal |

## Deployment

Deployed on Render's free tier as a Web Service. Since Render's free tier requires something answering HTTP to stay classified as alive, `bot.py` runs a minimal Flask server on a background thread alongside the bot's polling loop. An external pinger (UptimeRobot / cron-job.org) hits the deployed URL every ~10 minutes to prevent it from spinning down due to inactivity.

The database auto-initializes on startup (`setup()` in `setup_game.py`, called from `bot.py`) — it's safe to restart repeatedly, but **a fresh deploy on Render resets the disk entirely**, wiping any live registrations. Avoid pushing new deploys once real participants have started claiming their accounts, unless you're prepared to reload data from scratch.

## Known limitations

- Render's free tier disk is not persistent across deploys — see above.
- `/report` flags only the most recently received message, not a specific chosen one.
- Name lookups (`/reassign`, manual pairing) require an exact match to the stored `real_name`.
