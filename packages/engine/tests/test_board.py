"""Board geometry: 8 cols x 12 rows, orthogonal adjacency, harbour walls.

Harbour geometry (the rulebook gives no dimensions; documented house choice):
each harbour is the 2x2 region in its player's left-hand corner, base on the
corner square, wall on every other boundary with the single entrance gap on
the extreme left-hand column ("the left-hand side of the board should be
carefully watched, for once the enemy gets on the extreme edge and can move
down into the Harbour...").

Player A sits south (rows 0..4 setup, faces north, left hand = col 0).
Player B sits north (faces south, left hand = col 7).
"""
import pytest

from dover_engine.board import (
    BASE,
    COLS,
    ROWS,
    HARBOUR,
    adjacent,
    in_bounds,
    neighbours,
    wall_blocks,
)
from dover_engine.types import Player


def test_dimensions():
    assert (COLS, ROWS) == (8, 12)
    assert in_bounds((0, 0)) and in_bounds((7, 11))
    assert not in_bounds((8, 0)) and not in_bounds((0, 12)) and not in_bounds((-1, 3))


def test_orthogonal_adjacency():
    assert adjacent((3, 3), (3, 4))
    assert adjacent((3, 3), (2, 3))
    assert not adjacent((3, 3), (4, 4))  # no diagonals anywhere in the game
    assert not adjacent((3, 3), (3, 5))
    assert not adjacent((3, 3), (3, 3))


def test_neighbours_clipped_to_board():
    assert set(neighbours((0, 0))) == {(1, 0), (0, 1)}
    assert set(neighbours((3, 3))) == {(2, 3), (4, 3), (3, 2), (3, 4)}


def test_bases_and_harbours():
    assert BASE[Player.A] == (0, 0)
    assert BASE[Player.B] == (7, 11)
    assert HARBOUR[Player.A] == {(0, 0), (0, 1), (1, 0), (1, 1)}
    assert HARBOUR[Player.B] == {(7, 11), (7, 10), (6, 11), (6, 10)}


def test_harbour_a_walls():
    # Entrance: extreme left column stays open.
    assert not wall_blocks((0, 1), (0, 2))
    # Every other boundary crossing is walled.
    assert wall_blocks((1, 1), (1, 2))
    assert wall_blocks((1, 0), (2, 0))
    assert wall_blocks((1, 1), (2, 1))


def test_harbour_b_walls_mirrored():
    assert not wall_blocks((7, 10), (7, 9))
    assert wall_blocks((6, 10), (6, 9))
    assert wall_blocks((6, 11), (5, 11))
    assert wall_blocks((6, 10), (5, 10))


def test_walls_symmetric():
    assert wall_blocks((1, 2), (1, 1))
    assert not wall_blocks((0, 2), (0, 1))


def test_open_sea_has_no_walls():
    assert not wall_blocks((3, 3), (3, 4))
    assert not wall_blocks((0, 0), (0, 1))  # inside the harbour itself
    assert not wall_blocks((0, 0), (1, 0))
