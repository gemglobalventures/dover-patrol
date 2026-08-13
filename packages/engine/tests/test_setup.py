"""Setup validation.

Full game: 40 pieces per side fill the nearest five rows (39 non-base
squares — the Flag dispossesses one piece of its space) with the odd piece
on the sixth row. Short game ("Capturing the Base"): 24 pieces on the three
back rows, base unoccupied, odd piece on the fourth row, no flags.
"""
import pytest

from conftest import make_placements

from dover_engine.board import BASE
from dover_engine.state import FULL_ROSTER, SHORT_ROSTER, SetupError, new_game
from dover_engine.types import Player, PieceType


def test_rosters_sum_correctly():
    assert sum(FULL_ROSTER.values()) == 40
    assert sum(SHORT_ROSTER.values()) == 24


def test_full_game_initial_state(full_game):
    state = full_game
    assert state.mode == "full"
    assert state.to_move is Player.A
    assert len(state.pieces) == 80
    assert all(p.square is not None for p in state.pieces.values())
    # Flags start on their own bases, not carried.
    for player in Player:
        loc = state.flags[player]
        assert loc.carrier is None and loc.square == BASE[player]
    # Nobody knows anything about enemy pieces yet.
    assert state.knowledge == {Player.A: {}, Player.B: {}}
    assert state.winner is None


def test_short_game_has_no_flags(short_game):
    assert short_game.mode == "capture_base"
    assert len(short_game.pieces) == 48
    assert short_game.flags == {}


def test_piece_at_lookup(full_game):
    piece = full_game.piece_at((3, 2))
    assert piece is not None and piece.owner is Player.A
    assert full_game.piece_at((3, 6)) is None


def test_rejects_piece_on_base():
    placements = make_placements("full", Player.A)
    # Move the odd piece onto the base square.
    bad = [(t, BASE[Player.A] if sq == (0, 5) else sq) for t, sq in placements]
    with pytest.raises(SetupError):
        new_game("full", bad, make_placements("full", Player.B), first_to_move=Player.A)


def test_rejects_wrong_roster():
    placements = make_placements("full", Player.A)
    t, sq = placements[0]
    assert t is PieceType.FLAGSHIP
    bad = [(PieceType.PATROL_VESSEL, sq)] + placements[1:]
    with pytest.raises(SetupError):
        new_game("full", bad, make_placements("full", Player.B), first_to_move=Player.A)


def test_rejects_duplicate_square():
    placements = make_placements("full", Player.A)
    bad = placements[:-1] + [(placements[-1][0], placements[0][1])]
    with pytest.raises(SetupError):
        new_game("full", bad, make_placements("full", Player.B), first_to_move=Player.A)


def test_rejects_piece_outside_setup_zone():
    placements = make_placements("full", Player.A)
    # Odd piece two rows too deep.
    bad = placements[:-1] + [(placements[-1][0], (0, 7))]
    with pytest.raises(SetupError):
        new_game("full", bad, make_placements("full", Player.B), first_to_move=Player.A)


def test_rejects_two_pieces_on_odd_row():
    placements = make_placements("full", Player.A)
    # Move one row-4 piece to row 5 alongside the odd piece.
    bad = [(t, (sq[0], 5) if sq == (4, 4) else sq) for t, sq in placements]
    with pytest.raises(SetupError):
        new_game("full", bad, make_placements("full", Player.B), first_to_move=Player.A)


def test_short_game_zone_is_three_rows():
    placements = make_placements("capture_base", Player.B)
    assert all(sq[1] >= 8 for _, sq in placements)
    bad = placements[:-1] + [(placements[-1][0], (0, 7))]
    with pytest.raises(SetupError):
        new_game(
            "capture_base",
            make_placements("capture_base", Player.A),
            bad,
            first_to_move=Player.A,
        )


def test_public_validate_placements():
    from dover_engine.state import validate_placements

    good = make_placements("full", Player.A)
    validate_placements("full", Player.A, good)  # should not raise
    with pytest.raises(SetupError):
        validate_placements("full", Player.A, good[:-1])
