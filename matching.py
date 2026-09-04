# `X | None` annotations are evaluated at runtime on Python 3.9 (the local
# venv) but not on 3.10+; deferring annotations keeps both working.
from __future__ import annotations

import os
import random


def generate_pairings(ids_by_tier: dict[str, list[int]],
                      rng: random.Random | None = None) -> dict[int, int]:
    """Assign everyone a dragon by shuffling each tier into a random cycle.

    Shuffling a tier and chaining it A->B->C->...->A gives, by construction,
    exactly the properties the game needs: everyone is one person's trainer and
    one person's dragon, nobody is their own, and in a cycle of three or more
    nobody's dragon is also their trainer. Tiers never mix because each is
    shuffled separately.

    Set MATCH_SEED to reproduce a particular draw; otherwise it is random.
    """
    if rng is None:
        seed = os.environ.get("MATCH_SEED")
        rng = random.Random(seed) if seed else random.Random()

    pairings: dict[int, int] = {}
    for tier, ids in sorted(ids_by_tier.items()):
        if not ids:
            continue
        if len(ids) < 3:
            raise ValueError(
                f"tier {tier!r} has only {len(ids)} participant(s); at least 3 are "
                f"needed. One person would have to be their own dragon, and two "
                f"would have to be each other's dragon and trainer."
            )
        order = list(ids)
        rng.shuffle(order)
        for angel, mortal in zip(order, order[1:] + order[:1]):
            pairings[angel] = mortal
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