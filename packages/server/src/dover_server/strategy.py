from __future__ import annotations

import random
from collections import Counter

from dover_engine.board import BASE, COLS, HARBOUR
from dover_engine.state import FULL_ROSTER, SHORT_ROSTER
from dover_engine.types import Player, PieceType

from .rooms import Placements

T = PieceType

# The rulebook's Hints on Play, distilled:
#  - keep a Submarine, Destroyer and Mine Sweeper guarded in the Harbour;
#    a Mine there also protects the Flag;
#  - the high-value ships should not be risked early: back row;
#  - screen the fleet with the cheap, expendable vessels;
#  - watch the left-hand side (the harbour entrance column).
GARRISON = [T.MINE_SWEEPER, T.SUBMARINE, T.MINE, T.DESTROYER]
SCREEN = [
    T.MOTOR_TORPEDO_BOAT,
    T.PATROL_VESSEL,
    T.AUXILIARY_CRUISER,
    T.LIGHT_CRUISER,
    T.BATTLE_CRUISER,
    T.DESTROYER,
]
BACK = [
    T.FLAGSHIP,
    T.VICE_FLAGSHIP,
    T.BATTLE_SQUADRON,
    T.BATTLESHIP,
    T.MINE,
    T.MINE_LAYER,
    T.SUBMARINE,
    T.MINE_SWEEPER,
    T.FLYING_BOAT,
]
SCOUT = [T.MOTOR_TORPEDO_BOAT, T.PATROL_VESSEL, T.AUXILIARY_CRUISER]


def strategic_placements(mode: str, player: Player, rng: random.Random) -> Placements:
    """A sensible, varied arrangement following the rulebook's own advice."""
    roster = FULL_ROSTER if mode == "full" else SHORT_ROSTER
    pool = Counter({t: n for t, n in roster.items() if n})
    back_rows = 5 if mode == "full" else 3
    rows = (
        list(range(back_rows))
        if player is Player.A
        else list(range(11, 11 - back_rows, -1))
    )  # deepest first
    odd_row = back_rows if player is Player.A else 11 - back_rows
    base = BASE[player]

    def take(prefs: list[T]) -> T:
        for t in prefs:
            if pool[t] > 0:
                pool[t] -= 1
                return t
        remaining = [t for t, n in pool.items() for _ in range(n)]
        t = rng.choice(remaining)
        pool[t] -= 1
        return t

    def shuffled(prefs: list[T], keep_first: int) -> list[T]:
        """Vary the tail of a preference list so layouts differ."""
        head, tail = list(prefs[:keep_first]), list(prefs[keep_first:])
        rng.shuffle(tail)
        return head + tail

    placements: dict[tuple[int, int], T] = {}

    # Harbour garrison guarding the base (and the flag, in the full game).
    harbour_sqs = [sq for sq in sorted(HARBOUR[player]) if sq != base]
    for sq in harbour_sqs:
        placements[sq] = take(shuffled(GARRISON, 0))

    # A cheap scout on the row beyond, somewhere near the middle.
    placements[(rng.choice(range(2, 6)), odd_row)] = take(SCOUT)

    # Back row: the heavy ships and the pieces worth protecting.
    back_row_sqs = [
        (c, rows[0]) for c in range(COLS) if (c, rows[0]) != base and (c, rows[0]) not in placements
    ]
    rng.shuffle(back_row_sqs)
    for sq in back_row_sqs:
        placements[sq] = take(shuffled(BACK, 4))

    # Front row: an expendable screen.
    front = rows[-1]
    front_sqs = [(c, front) for c in range(COLS) if (c, front) != base and (c, front) not in placements]
    rng.shuffle(front_sqs)
    for sq in front_sqs:
        placements[sq] = take(shuffled(SCREEN, 0))

    # Everything else fills the middle rows at random.
    middle_sqs = [
        (c, r)
        for r in rows[1:-1]
        for c in range(COLS)
        if (c, r) != base and (c, r) not in placements
    ]
    rng.shuffle(middle_sqs)
    for sq in middle_sqs:
        placements[sq] = take([])

    return [(t, sq) for sq, t in placements.items()]
