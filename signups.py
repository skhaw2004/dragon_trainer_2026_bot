"""Read participants straight from the signup form's CSV export.

Transcribing ~80 people x 9 fields by hand was the largest remaining source of
human error, and the costliest typo — a wrong Telegram handle — locks that
person out of the bot entirely. So the export is read directly instead.

The file is never committed: it holds real names, room numbers, handles and
personal preferences, and the repo is public. Locally it sits next to the code;
on Render it is uploaded through Secret Files, which land in the same place.
"""
import csv
import os
import re
from pathlib import Path

SIGNUPS_PATH = Path(os.environ.get("SIGNUPS_FILE") or
                    Path(__file__).parent / "signups.csv")

# Columns are found by a distinctive fragment rather than the full header.
# The real headers contain embedded newlines and non-breaking spaces, and any
# edit to a form question would change them; a fragment survives both.
COLUMNS = {
    "name":               "provide your name",
    "username":           "telegram handle",
    "room":               "room number",
    "tier":               "commitment level",
    "room_consent":       "enter your room",
    "opposite_gender_ok": "opposite gender",
    "notes":              "take note of when arranging",
    "surprise_prefs":     "preferences for surprises",
    "welfare_prefs":      "likes and dislikes for welfare",
}

REQUIRED = ("name", "username", "room", "tier", "room_consent", "opposite_gender_ok")
USERNAME_RE = re.compile(r"[a-z0-9_]{5,32}")


def _resolve_columns(headers: list[str], path: Path) -> dict[str, str]:
    resolved, problems = {}, []
    for field, fragment in COLUMNS.items():
        hits = [h for h in headers if fragment in h.lower()]
        if not hits:
            problems.append(f"no column matching {fragment!r} (for {field})")
        elif len(hits) > 1:
            problems.append(f"{len(hits)} columns match {fragment!r} (for {field})")
        else:
            resolved[field] = hits[0]
    if problems:
        raise ValueError(
            f"{path} does not look like the signup form export:\n  "
            + "\n  ".join(problems)
        )
    return resolved


def load_signups(path: Path = None) -> list[dict]:
    """Parse the export into participant dicts, reporting every problem at once.

    Failing on the first bad row would mean fixing 80 rows one deploy at a time,
    so all problems are collected and raised together with their row numbers.
    """
    path = path or SIGNUPS_PATH
    if not path.exists():
        raise FileNotFoundError(
            f"No signup export at {path}. Save the form's responses as CSV there "
            f"(locally), or upload it through Render's Secret Files as "
            f"'{path.name}' (in production)."
        )

    with open(path, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    if not rows:
        raise ValueError(f"{path} has no responses in it.")

    cols = _resolve_columns(list(rows[0].keys()), path)
    participants, problems, seen = [], [], {}

    for n, row in enumerate(rows, start=2):        # row 1 is the header
        vals = {f: (row.get(c) or "").strip() for f, c in cols.items()}
        if not any(vals[f] for f in REQUIRED):
            continue                               # trailing blank line

        for field in REQUIRED:
            if not vals[field]:
                problems.append(f"row {n}: {field} is blank")

        handle = vals["username"].lstrip("@").lower()
        if handle:
            if not USERNAME_RE.fullmatch(handle):
                problems.append(
                    f"row {n}: {vals['username']!r} is not a usable Telegram "
                    f"username (letters, digits and underscores, 5-32 chars)"
                )
            if handle in seen:
                problems.append(
                    f"row {n}: telegram handle @{handle} also used on row {seen[handle]}"
                )
            else:
                seen[handle] = n

        vals["username"] = handle
        participants.append(vals)

    if problems:
        raise ValueError(
            f"{len(problems)} problem(s) in {path} — fix the form responses and "
            f"re-export:\n  " + "\n  ".join(problems)
        )
    return participants
