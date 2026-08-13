from __future__ import annotations

from .types import Player

Square = tuple[int, int]  # (col, row)

COLS, ROWS = 8, 12

# Player A sits south facing north (left hand = col 0); B mirrors at 180°.
BASE: dict[Player, Square] = {
    Player.A: (0, 0),
    Player.B: (7, 11),
}

# The rulebook gives no harbour dimensions; house choice documented in
# tests/test_board.py: 2x2 corner region, base on the corner square.
HARBOUR: dict[Player, set[Square]] = {
    Player.A: {(0, 0), (0, 1), (1, 0), (1, 1)},
    Player.B: {(7, 11), (7, 10), (6, 11), (6, 10)},
}

# The single entrance gap sits on the extreme left-hand column; every other
# harbour boundary edge is walled. Impassable to all but the Flying Boat.
_ENTRANCES: set[frozenset[Square]] = {
    frozenset({(0, 1), (0, 2)}),
    frozenset({(7, 10), (7, 9)}),
}

_WALLS: set[frozenset[Square]] = {
    frozenset({a, b})
    for player, squares in HARBOUR.items()
    for a in squares
    for b in [(a[0] + 1, a[1]), (a[0] - 1, a[1]), (a[0], a[1] + 1), (a[0], a[1] - 1)]
    if 0 <= b[0] < COLS and 0 <= b[1] < ROWS and b not in squares
} - _ENTRANCES


def in_bounds(sq: Square) -> bool:
    return 0 <= sq[0] < COLS and 0 <= sq[1] < ROWS


def adjacent(a: Square, b: Square) -> bool:
    return abs(a[0] - b[0]) + abs(a[1] - b[1]) == 1


def neighbours(sq: Square) -> list[Square]:
    col, row = sq
    return [
        n
        for n in [(col + 1, row), (col - 1, row), (col, row + 1), (col, row - 1)]
        if in_bounds(n)
    ]


def wall_blocks(a: Square, b: Square) -> bool:
    return frozenset({a, b}) in _WALLS
