from db import init_db, import_participants, get_participant_by_name, get_participant_ids_by_tier, save_pairings
from matching import load_manual_pairings, validate_full_coverage

PARTICIPANTS = [
    {"name": "Alice", "username": "alice_tg", "tier": "easy"},
    {"name": "Bob", "username": "bob_the_builder", "tier": "easy"},
    # ... all 40-50, copied by hand from the form responses
]

PAIRINGS = [
    ("Alice", "Bob"),
    ("Bob", "Charlie"),
    # ...
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
    print(f"Loaded {len(PARTICIPANTS)} participants and {len(all_pairings)} pairings.")