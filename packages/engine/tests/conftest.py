"""Shared helpers: deterministic legal placements for both modes."""
import pytest

from dover_engine.board import BASE, COLS
from dover_engine.state import FULL_ROSTER, SHORT_ROSTER, new_game
from dover_engine.types import Player, PieceType


def roster_list(roster: dict[PieceType, int]) -> list[PieceType]:
    return [t for t, n in roster.items() for _ in range(n)]


def side_squares(player: Player, back_rows: int) -> list:
    """All squares of the player's back N rows except the base, nearest row
    first, plus the first square of the following (odd-piece) row."""
    rows = range(back_rows) if player is Player.A else range(11, 11 - back_rows, -1)
    squares = [
        (col, row) for row in rows for col in range(COLS) if (col, row) != BASE[player]
    ]
    odd_row = back_rows if player is Player.A else 11 - back_rows
    squares.append((0 if player is Player.A else 7, odd_row))
    return squares


def make_placements(mode: str, player: Player) -> list[tuple[PieceType, tuple]]:
    roster = FULL_ROSTER if mode == "full" else SHORT_ROSTER
    back_rows = 5 if mode == "full" else 3
    return list(zip(roster_list(roster), side_squares(player, back_rows)))


@pytest.fixture
def full_game():
    return new_game(
        "full",
        make_placements("full", Player.A),
        make_placements("full", Player.B),
        first_to_move=Player.A,
    )


@pytest.fixture
def short_game():
    return new_game(
        "capture_base",
        make_placements("capture_base", Player.A),
        make_placements("capture_base", Player.B),
        first_to_move=Player.A,
    )
