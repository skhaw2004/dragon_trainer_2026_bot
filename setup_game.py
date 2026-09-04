from db import (
    init_db,
    import_participants,
    get_participant_ids_by_tier,
    save_pairings,
    has_participants,
    reset_all_chat_modes,
    TIERS,
)
from matching import generate_pairings, validate_full_coverage
from signups import load_signups


def setup():
    init_db()

    cleared = reset_all_chat_modes()
    if cleared:
        print(f"Cleared {cleared} stale chat connection(s) left over from the last run.")

    if has_participants():
        print("Participants already loaded, skipping setup.")
        return

    participants = load_signups()
    import_participants(participants)

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
    print(f"Loaded {len(participants)} participants and {len(pairings)} pairings.")
    print("Pairings are not logged — use /export to see them.")


if __name__ == "__main__":
    setup()
