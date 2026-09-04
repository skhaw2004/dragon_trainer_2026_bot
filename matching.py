# `X | None` annotations are evaluated at runtime on Python 3.9 (the local
# venv) but not on 3.10+; deferring annotations keeps both working.
from __future__ import annotations

import os
import random


MIN_TIER_SIZE = 3


def check_tier_sizes(counts: dict) -> None:
    """Reject tiers too small to form a cycle, before any work is done."""
    for tier, n in sorted(counts.items()):
        if 0 < n < MIN_TIER_SIZE:
            raise ValueError(
                f"tier {tier!r} has only {n} participant(s); at least "
                f"{MIN_TIER_SIZE} are needed. One person would have to be their "
                f"own dragon, and two would have to be each other's dragon and "
                f"trainer."
            )


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
        check_tier_sizes({tier: len(ids)})
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


def swap_participants(pairings: dict, a_id: int, b_id: int) -> dict:
    """Swap two people's positions in their cycle.

    Used to repair a pairing by hand — chiefly when someone asked for a
    same-gender trainer and drew one of the opposite gender, which the bot
    cannot detect for itself because no gender is recorded.

    Rebuilding the whole cycle from an ordered list, rather than re-pointing
    individual edges, keeps the result a valid cycle by construction — including
    when the two are already adjacent, which is the case edge-by-edge surgery
    tends to get wrong.
    """
    if a_id == b_id:
        raise ValueError("those are the same person")
    if a_id not in pairings or b_id not in pairings:
        raise ValueError("both people must already be in the pairings")

    cycle, cur = [a_id], pairings[a_id]
    while cur != a_id:
        cycle.append(cur)
        cur = pairings[cur]
    if b_id not in cycle:
        raise ValueError(
            "they are not in the same cycle, so swapping them would mix "
            "commitment levels"
        )

    i, j = cycle.index(a_id), cycle.index(b_id)
    cycle[i], cycle[j] = cycle[j], cycle[i]

    updated = dict(pairings)
    for angel, mortal in zip(cycle, cycle[1:] + cycle[:1]):
        updated[angel] = mortal
    return updated


def remove_participant(dropped_id: int, pairings: dict[int, int]) -> dict[int, int]:
    """Splices a dropout out, reconnecting their angel directly to their mortal."""
    angel_of_dropped = next(a for a, m in pairings.items() if m == dropped_id)
    mortal_of_dropped = pairings[dropped_id]
    pairings[angel_of_dropped] = mortal_of_dropped
    del pairings[dropped_id]
    return pairings