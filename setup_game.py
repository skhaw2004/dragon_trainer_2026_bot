from db import (
    init_db,
    import_participants,
    get_participant_ids_by_tier,
    save_pairings,
    get_pairings_with_names,
    has_participants,
    reset_all_chat_modes,
    TIERS,
)
from matching import generate_pairings, validate_full_coverage

# One dict per signup, straight from the form. "tier" accepts the form's full
# option text ("High: Very good welfare, and big pranks") or a bare tier name.
# room_consent  -> Q6, may your trainer enter your room
# opposite_gender_ok -> Q7, collected for manual review; not auto-enforced
# notes         -> Q8, free text for the host when arranging pairings
PARTICIPANTS = [
    {"name": "Stuart", "username": "liyouzh1", "tier": "Low: Only welfare, no pranks",
     "room": "16-04", "room_consent": "Yes", "opposite_gender_ok": "Yes",
     "welfare_prefs": "boba, cats, K-pop; no coffee",
     "surprise_prefs": "no horror-themed surprises",
     "notes": ""},

    {"name": "Bob", "username": "bob_tg", "tier": "Low: Only welfare, no pranks",
     "room": "16-10", "room_consent": "Yes", "opposite_gender_ok": "No",
     "welfare_prefs": "pizza, dogs; no spicy food",
     "surprise_prefs": "can shift furniture, no wet surprises",
     "notes": ""},

    {"name": "Charlie", "username": "charlie_tg", "tier": "Low: Only welfare, no pranks",
     "room": "17-09", "room_consent": "No", "opposite_gender_ok": "Yes",
     "welfare_prefs": "bubble tea, board games; allergic to shellfish",
     "surprise_prefs": "please do not open cabinets",
     "notes": ""},

    {"name": "Dana", "username": "dana_tg", "tier": "Low: Only welfare, no pranks",
     "room": "15-03", "room_consent": "Yes", "opposite_gender_ok": "Yes",
     "welfare_prefs": "matcha, plants; no durian",
     "surprise_prefs": "nothing after 10pm",
     "notes": ""},
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

    ids_by_tier = {tier: get_participant_ids_by_tier(tier) for tier in TIERS}
    pairings = generate_pairings(ids_by_tier)

    # generate_pairings cannot produce an invalid cycle, but check anyway so the
    # invariant stays enforced rather than assumed if that ever changes.
    for tier, tier_ids in ids_by_tier.items():
        tier_pairings = {a: m for a, m in pairings.items() if a in set(tier_ids)}
        validate_full_coverage(tier_pairings, tier_ids)

    save_pairings(pairings)

    for tier in TIERS:
        count = len(ids_by_tier[tier])
        if count:
            print(f"  {tier}: {count} participants")
    for angel_name, mortal_name in get_pairings_with_names():
        print(f"{angel_name} -> {mortal_name}")
    print(f"Loaded {len(PARTICIPANTS)} participants and {len(pairings)} pairings.")


if __name__ == "__main__":
    setup()
