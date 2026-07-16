def load_manual_pairings(pairs: list[tuple[str, str]], get_participant_id_by_name) -> dict[int, int]:
    """
    pairs: a list you write by hand, e.g.
        [("Alice", "Bob"), ("Bob", "Charlie"), ("Charlie", "Alice")]
    get_participant_id_by_name: looks up a participant's database id from their real_name
    """
    pairings = {}
    mortals_seen = set()

    for angel_name, mortal_name in pairs:
        angel_id = get_participant_id_by_name(angel_name)
        mortal_id = get_participant_id_by_name(mortal_name)

        if angel_id is None:
            raise ValueError(f"No participant named '{angel_name}'")
        if mortal_id is None:
            raise ValueError(f"No participant named '{mortal_name}'")
        if angel_id == mortal_id:
            raise ValueError(f"{angel_name} can't be their own mortal")
        if angel_id in pairings:
            raise ValueError(f"{angel_name} appears twice as an angel")
        if mortal_id in mortals_seen:
            raise ValueError(f"{mortal_name} appears twice as a mortal")

        pairings[angel_id] = mortal_id
        mortals_seen.add(mortal_id)

    return pairings


def validate_full_coverage(pairings: dict[int, int], all_participant_ids: list[int]):
    """Confirms every registered participant has exactly one angel duty
    and is exactly one person's mortal — catches typos/omissions in your manual list."""
    all_ids = set(all_participant_ids)
    missing_as_angel = all_ids - set(pairings.keys())
    missing_as_mortal = all_ids - set(pairings.values())
    if missing_as_angel:
        raise ValueError(f"No angel assigned for: {missing_as_angel}")
    if missing_as_mortal:
        raise ValueError(f"No mortal assigned for: {missing_as_mortal}")