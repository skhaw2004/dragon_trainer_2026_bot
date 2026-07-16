from db import init_db, import_participants, get_participant_by_name, get_participant_ids_by_tier, save_pairings, get_pairings_with_names
from matching import load_manual_pairings, validate_full_coverage

PARTICIPANTS = [
    {"name": "Stuart", "username": "liyouzh1", "tier": "easy"},
    {"name": "Bob", "username": "bob_tg", "tier": "easy"},
    {"name": "Charlie", "username": "charlie_tg", "tier": "easy"},
    {"name": "Dana", "username": "dana_tg", "tier": "easy"},
    #placeholder names
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

if __name__ == "__main__":
    init_db()
    import_participants(PARTICIPANTS)

    all_pairings = load_manual_pairings(PAIRINGS, get_participant_by_name)

    for tier in ("easy", "medium", "hard"):
        tier_ids = get_participant_ids_by_tier(tier)
        tier_pairings = {a: m for a, m in all_pairings.items() if a in tier_ids}
        validate_full_coverage(tier_pairings, tier_ids)

    save_pairings(all_pairings)
    for angel_name, mortal_name in get_pairings_with_names():
        print(f"Dragon:{angel_name} -> Trainer:{mortal_name}")
    print(f"Loaded {len(PARTICIPANTS)} participants and {len(all_pairings)} pairings.")