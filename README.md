# Dragon & Trainer 2026 🐉

A Telegram bot for running an anonymous Angel/Mortal game for a group of 70–80 people. Each "Trainer" (angel) is secretly assigned a "Dragon" (mortal) to look after anonymously, while a mystery Trainer of their own watches over them in return — until the big reveal. Built for Draco House at Residential College 4, NUS.

## How the game works

- Participants sign up via a **Microsoft Form**, giving their name, Telegram username, room, commitment level, welfare and surprise preferences, and two consent answers.
- The host exports those responses to CSV. **The bot reads that file directly and generates the pairings itself** — there is no list to type out by hand.
- Within each commitment level the bot shuffles everyone into a random cycle: A looks after B, B looks after C, and the last person closes the loop back to A. So everyone is exactly one person's Trainer and exactly one person's Dragon, and nobody is paired with themselves or paired mutually.
- Once live, each person messages the bot with `/start`. The bot recognises them by Telegram username and reveals their Dragon — name, room, preferences, and whether that Dragon consented to their room being entered.
- They can then message their Dragon anonymously, or reply anonymously to their own unknown Trainer. Text, photos, stickers, GIFs, voice notes, videos, audio and files are all relayed.
- `/report` flags an inappropriate message to the host, revealing the real sender's identity to admins only.

## Commitment levels

The form asks for **Low**, **Medium** or **High**, and participants are only ever matched within their own level. The bot accepts the form's full option text (`"High: Very good welfare, and big pranks"`) as well as a bare `high`.

**Each non-empty level needs at least 3 people.** A level of one would need someone to be their own Dragon; a level of two would make them each other's Dragon *and* Trainer, which the game forbids. Setup refuses to start rather than produce a broken game. Empty levels are fine.

## Tech stack

- **Python** 3.9+ (Render currently runs 3.14)
- **python-telegram-bot** — Bot API, commands, message handling, job scheduling
- **SQLite** (`sqlite3`, built-in) — participant, pairing and message data
- **python-dotenv** — loads secrets from `.env` locally
- **Flask** — health endpoint for Render
- **Render** — hosting, **paid instance with a persistent disk** (see Deployment)

## Project structure

```
d-t-Bot/
  bot.py                    # entrypoint: health server, handler registration, polling
  config.py                 # BOT_TOKEN and ADMIN_IDS from the environment
  signups.py                # reads and validates the form's CSV export
  db.py                     # SQLite schema and all queries
  matching.py               # random cycle generation, coverage checks, dropout splicing
  setup_game.py             # builds the game on first boot
  handlers/
    registration.py         # /start, /rules
    relay.py                # anonymous relay, /menu, /done, /whoami, /report
    admin.py                # /roster, /unmatched, /broadcast, /reassign, /export
    chunking.py             # splits messages over Telegram's 4096-character limit
    media.py                # relays every media type Telegram supports
  requirements.txt
```

## The signup export

Export the form's responses and **Save As → CSV UTF-8** (not plain CSV — participants' answers contain emoji). Save it as `signups.csv` beside the code.

Columns are located by a distinctive fragment of the question text, not the full header, so editing a question's wording will not break the import. Every problem is reported at once, with CSV row numbers — duplicate handles, unusable handles, blank required fields — rather than failing one row at a time.

**Never commit this file.** It holds real names, room numbers, Telegram handles and personal preferences. It is gitignored, along with `*.csv` and `*.xlsx` generally. In production it is supplied through Render's Secret Files.

## Setup (local development)

1. Create a bot via [@BotFather](https://t.me/BotFather) and get your token.
2. Create a virtual environment and install dependencies:
   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and fill it in:
   ```
   BOT_TOKEN=your-bot-token
   ADMIN_IDS=your-telegram-user-id
   ```
4. Put the CSV export at `signups.csv`.
5. Run the bot:
   ```
   python bot.py
   ```

**Only one instance may run at a time.** Telegram terminates one poller with a 409 Conflict if two share a token, so never run locally while the deployed bot is up. Use a separate test bot and token if you need both.

## Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `BOT_TOKEN` | yes | from BotFather |
| `ADMIN_IDS` | yes | comma-separated Telegram user IDs. Controls admin commands **and** who receives `/report`. If unset, nobody is an admin and every admin command silently does nothing. |
| `DB_DIR` | production | directory for `game.db`. Must point at the mounted disk on Render, or data is wiped on every deploy. |
| `SIGNUPS_FILE` | no | path to the CSV export. Defaults to `signups.csv` beside the code. |
| `MATCH_SEED` | no | reproduces a specific draw. Unset means genuinely random. |
| `IDLE_SECONDS` | no | how long a chat connection survives inactivity. Defaults to 900 (15 minutes). |
| `PORT` | set by Render | health server port. |

## Participant commands

| Command | Description |
|---|---|
| `/start` | Claims your identity and reveals your Dragon's details |
| `/rules` | Reminder of how the game works |
| `/menu` | Choose whether to message your Dragon or your Trainer |
| `/done` | Disconnect from whoever you're messaging |
| `/whoami` | Check who you're currently connected to |
| `/report` | Flag the most recently received message to the host |

## Admin commands

*(only work for Telegram user IDs listed in `ADMIN_IDS`; everyone else gets silence)*

| Command | Description |
|---|---|
| `/roster` | All participants and their claim status |
| `/unmatched` | Anyone who tried `/start` but wasn't recognised |
| `/export` | Full pairing list, flagged ⚠️ where a Dragon asked for a same-gender Trainer and 📝 with their signup notes |
| `/broadcast <message>` | Announce to every claimed participant, paced to stay under Telegram's rate limit. Reports who blocked the bot, who failed, and who has never sent `/start` and so cannot be reached at all. |
| `/reassign <name>` | Remove a dropout, splicing their Trainer directly to their old Dragon |
| `/swap <name> \| <name>` | Exchange two people's places in the cycle, to repair a pairing by hand |

## What the bot cannot enforce

The form asks whether someone is comfortable with a Trainer of the opposite gender, but **it does not collect anyone's gender**, so this cannot be honoured automatically. `/export` flags those rows instead — read it after generating pairings and check those matches by hand.

Free-text signup notes ("please don't pair me with X") are shown next to the pairing they concern, for the same reason.

When a flagged pairing is wrong, `/swap` exchanges two people's places in the cycle to repair it. It refuses to swap across commitment levels, and rebuilds the whole cycle rather than re-pointing individual edges, so the result is always a valid cycle.

## Deployment

Deployed on Render as a paid Web Service with a **1 GB persistent disk mounted at `/var/data`**, and `DB_DIR=/var/data` set in the environment.

**The disk is not optional.** Render's free tier has an ephemeral filesystem, so any deploy, restart or maintenance event wipes `game.db` — un-claiming every participant. Recovery would mean asking all 80 people to `/start` again, which `/broadcast` cannot tell them about, because it can only reach people who have already claimed.

The CSV export is uploaded through **Environment → Secret Files** as `signups.csv`, which lands at the app root where the code looks for it. It is never committed.

`bot.py` runs a Flask health endpoint on a background thread alongside polling. It reports the **real** state of the Telegram poller rather than always returning `ok`, so a dead poller returns 503, fails Render's health check, and gets restarted instead of sitting there silently deaf. There is a 90-second startup grace period so deploys don't fail while booting.

Attaching a disk disables zero-downtime deploys, which is what you want here: two instances polling the same token would fight over `getUpdates`.

### Reloading the game

The database is built once. `setup()` skips everything if participants already exist, so **restarts and redeploys are safe** — pairings, claims and message history all survive, and only in-progress chat connections are reset.

That same guard means editing the export does **not** update a running game. To rebuild from scratch:

```bash
rm /var/data/game.db      # Render Shell
```
then redeploy. Everyone is re-matched, so only do this before the game starts.

Setup is all-or-nothing: if anything fails partway, participants are rolled back so the next boot retries cleanly rather than leaving a half-built game that looks complete.

## Known limitations

- **No way to add a late participant.** Anyone not in the export when the game is built cannot take part without rebuilding, which re-matches everyone. Someone whose handle is wrong can fix it by changing their own Telegram username to match the form.
- Opposite-gender preferences are flagged, not enforced — see above.
- `/report` flags only the most recently received message, not a chosen one.
- `/reassign` requires an exact match on the stored name.
- Files and audio keep their original filename and tags, which can identify the sender. They still send, but the sender is warned.
- Voice notes are relayed as-is, and a voice is recognisable.
