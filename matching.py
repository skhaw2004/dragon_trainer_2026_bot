def load_manual_pairings(pairs: list[tuple[str, str]], get_participant_by_name) -> dict[int, int]:
    """pairs: e.g. [("Alice", "Bob"), ("Bob", "Charlie")]"""
    pairings = {}
    mortals_seen = set()

    for angel_name, mortal_name in pairs:
        angel = get_participant_by_name(angel_name)
        mortal = get_participant_by_name(mortal_name)

        if angel is None:
            raise ValueError(f"No participant named '{angel_name}'")
        if mortal is None:
            raise ValueError(f"No participant named '{mortal_name}'")
        if angel["id"] == mortal["id"]:
            raise ValueError(f"{angel_name} can't be their own mortal")
        if angel["tier"] != mortal["tier"]:
            raise ValueError(
                f"{angel_name} ({angel['tier']}) and {mortal_name} ({mortal['tier']}) are in different tiers"
            )
        if angel["id"] in pairings:
            raise ValueError(f"{angel_name} appears twice as an angel")
        if mortal["id"] in mortals_seen:
            raise ValueError(f"{mortal_name} appears twice as a mortal")

        pairings[angel["id"]] = mortal["id"]
        mortals_seen.add(mortal["id"])

    return pairings


def validate_full_coverage(pairings: dict[int, int], all_participant_ids: list[int]):
    """Call once per tier — confirms everyone in that tier has exactly
    one angel duty and is exactly one person's mortal."""
    all_ids = set(all_participant_ids)
    missing_as_angel = all_ids - set(pairings.keys())
    missing_as_mortal = all_ids - set(pairings.values())
    if missing_as_angel:
        raise ValueError(f"No angel assigned for: {missing_as_angel}")
    if missing_as_mortal:
        raise ValueError(f"No mortal assigned for: {missing_as_mortal}")


def remove_participant(dropped_id: int, pairings: dict[int, int]) -> dict[int, int]:
    """Splices a dropout out, reconnecting their angel directly to their mortal."""
    angel_of_dropped = next(a for a, m in pairings.items() if m == dropped_id)
    mortal_of_dropped = pairings[dropped_id]
    pairings[angel_of_dropped] = mortal_of_dropped
    del pairings[dropped_id]
    return pairings