import collections

from db import (
    init_db,
    clear_participants,
    normalize_tier,
    import_participants,
    get_participant_ids_by_tier,
    save_pairings,
    has_participants,
    reset_all_chat_modes,
    TIERS,
)
from matching import check_tier_sizes, generate_pairings, validate_full_coverage
from signups import SIGNUPS_PATH, load_signups


def setup():
    init_db()

    cleared = reset_all_chat_modes()
    if cleared:
        print(f"Cleared {cleared} stale chat connection(s) left over from the last run.")

    if has_participants():
        print("Participants already loaded, skipping setup.")
        return

    participants = load_signups()

    # Report what was actually read before validating it. Render's Shell can
    # only attach to a running instance, so when setup fails the bot crash-loops
    # and the shell is unavailable exactly when it would be most useful. The log
    # has to carry enough to diagnose a bad export on its own.
    counts = collections.Counter(normalize_tier(p["tier"]) for p in participants)
    print(f"Read {SIGNUPS_PATH} ({SIGNUPS_PATH.stat().st_size} bytes): "
          f"{len(participants)} participants, tiers "
          f"{ {t: counts.get(t, 0) for t in TIERS} }")

    # Check what can be checked before writing anything, so the usual failure
    # (a tier too small to match) never touches the database at all.
    check_tier_sizes(collections.Counter(normalize_tier(p["tier"]) for p in participants))

    # Importing participants and saving their pairings must succeed or fail
    # together. Participants are committed first, so without this a later
    # failure would leave people loaded with no pairings — and has_participants()
    # would then treat that half-built game as complete and skip setup forever,
    # leaving a bot that looks healthy and tells everyone their dragon is
    # missing.
    try:
        import_participants(participants)

        ids_by_tier = {tier: get_participant_ids_by_tier(tier) for tier in TIERS}
        pairings = generate_pairings(ids_by_tier)

        # generate_pairings cannot produce an invalid cycle, but check anyway so
        # the invariant stays enforced rather than assumed if that ever changes.
        for tier, tier_ids in ids_by_tier.items():
            tier_pairings = {a: m for a, m in pairings.items() if a in set(tier_ids)}
            validate_full_coverage(tier_pairings, tier_ids)

        save_pairings(pairings)
    except Exception:
        clear_participants()
        raise

    for tier in TIERS:
        count = len(ids_by_tier[tier])
        if count:
            print(f"  {tier}: {count} participants")
    print(f"Loaded {len(participants)} participants and {len(pairings)} pairings.")
    print("Pairings are not logged — use /export to see them.")


if __name__ == "__main__":
    setup()
