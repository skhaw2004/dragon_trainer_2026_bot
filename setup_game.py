from db import init_db, import_participants, get_participant_by_name, get_participant_ids_by_tier, save_pairings, get_pairings_with_names, has_participants, reset_all_chat_modes
from matching import load_manual_pairings, validate_full_coverage

PARTICIPANTS = [
    {"name": "Stuart", "username": "liyouzh1", "tier": "easy",
     "room": "16-04", "likes": "boba, cats, K-pop",
     "dislikes": "coffee, horror movies", "off_limits": "no nut allergy gifts"},

    {"name": "Bob", "username": "bob_tg", "tier": "easy",
     "room": "16-10", "likes": "video games, pizza, dogs",
     "dislikes": "spicy food, early mornings", "off_limits": "no alcohol-related gifts"},

    {"name": "Charlie", "username": "charlie_tg", "tier": "easy",
     "room": "17-09", "likes": "anime, bubble tea, board games",
     "dislikes": "seafood, loud parties", "off_limits": "no shellfish (allergy)"},

    {"name": "Dana", "username": "dana_tg", "tier": "easy",
     "room": "15-03", "likes": "reading, plants, matcha",
     "dislikes": "clowns, crowded places", "off_limits": "no surprise visits after 10pm"},
]

PAIRINGS = [
    ("Stuart", "Bob"),
    ("Bob", "Charlie"),
    ("Charlie", "Dana"),
    ("Dana", "Stuart"),
    #placeholder pairings

    #easy

    #medium

    #hard
]

def setup():
    init_db()

    cleared = reset_all_chat_modes()
    if cleared:
        print(f"Cleared {cleared} stale chat connection(s) left over from the last run.")

    if has_participants():
        print("Participants already loaded, skipping setup.")
        return

    import_participants(PARTICIPANTS)
    all_pairings = load_manual_pairings(PAIRINGS, get_participant_by_name)

    for tier in ("easy", "medium", "hard"):
        tier_ids = get_participant_ids_by_tier(tier)
        tier_pairings = {a: m for a, m in all_pairings.items() if a in tier_ids}
        validate_full_coverage(tier_pairings, tier_ids)

    save_pairings(all_pairings)
    for angel_name, mortal_name in get_pairings_with_names():
        print(f"{angel_name} -> {mortal_name}")
    print(f"Loaded {len(PARTICIPANTS)} participants and {len(all_pairings)} pairings.")

if __name__ == "__main__":
    setup()