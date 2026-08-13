"""Movement: one orthogonal square onto an empty space; harbour walls block
all but the Flying Boat; mines never move; passive mine / mine-layer
adjacency kills resolve on movement."""
import pytest

from conftest import custom_state

from dover_engine.actions import Move
from dover_engine.engine import IllegalAction, apply_action
from dover_engine.events import Moved, PassiveKill, WallCrossed
from dover_engine.types import Player, PieceType

T = PieceType
A, B = Player.A, Player.B


def test_simple_move_flips_turn():
    state = custom_state([("a0", T.DESTROYER, A, (3, 3))])
    new, events = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square == (3, 4)
    assert new.to_move is B
    assert Moved("a0", (3, 3), (3, 4)) in events


@pytest.mark.parametrize("to", [(4, 4), (3, 5), (3, 3), (3, 2 - 4)])
def test_rejects_bad_geometry(to):
    state = custom_state([("a0", T.DESTROYER, A, (3, 3))])
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", to))


def test_rejects_moving_out_of_turn():
    state = custom_state([("b0", T.DESTROYER, B, (3, 3))], to_move=A)
    with pytest.raises(IllegalAction):
        apply_action(state, Move("b0", (3, 4)))


def test_rejects_moving_a_mine():
    state = custom_state([("a0", T.MINE, A, (3, 3))])
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (3, 4)))


def test_rejects_occupied_destination():
    state = custom_state(
        [("a0", T.DESTROYER, A, (3, 3)), ("b0", T.DESTROYER, B, (3, 4))]
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (3, 4)))


def test_wall_blocks_ordinary_ship():
    state = custom_state([("a0", T.DESTROYER, A, (1, 2))])
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (1, 1)))  # walled harbour boundary


def test_harbour_entrance_is_open():
    state = custom_state([("a0", T.DESTROYER, A, (0, 2))])
    new, _ = apply_action(state, Move("a0", (0, 1)))
    assert new.pieces["a0"].square == (0, 1)


def test_flying_boat_crosses_wall_with_declaration():
    state = custom_state([("a0", T.FLYING_BOAT, A, (1, 2))])
    new, events = apply_action(state, Move("a0", (1, 1)))
    assert new.pieces["a0"].square == (1, 1)
    assert WallCrossed("a0") in events
    # The declaration reveals the Flying Boat to the opponent.
    assert new.knowledge[B]["a0"] is T.FLYING_BOAT


def test_flying_boat_jumps_over_mine():
    state = custom_state(
        [("a0", T.FLYING_BOAT, A, (3, 3)), ("b0", T.MINE, B, (3, 4))]
    )
    new, _ = apply_action(state, Move("a0", (3, 5)))
    assert new.pieces["a0"].square == (3, 5)
    assert new.pieces["b0"].square == (3, 4)  # the mine stays
    # A two-square hop is publicly a Flying Boat move.
    assert new.knowledge[B]["a0"] is T.FLYING_BOAT


def test_flying_boat_cannot_jump_without_a_mine():
    state = custom_state([("a0", T.FLYING_BOAT, A, (3, 3))])
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (3, 5)))


def test_flying_boat_cannot_jump_onto_occupied_square():
    state = custom_state(
        [
            ("a0", T.FLYING_BOAT, A, (3, 3)),
            ("b0", T.MINE, B, (3, 4)),
            ("b1", T.PATROL_VESSEL, B, (3, 5)),
        ]
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (3, 5)))


def test_moving_next_to_enemy_mine_blows_up():
    state = custom_state(
        [("a0", T.FLAGSHIP, A, (3, 3)), ("b0", T.MINE, B, (3, 5))]
    )
    new, events = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square is None  # blown up
    assert new.pieces["b0"].square == (3, 5)  # mine remains
    assert PassiveKill("a0", "b0") in events
    # "the Mine being shown"
    assert new.knowledge[A]["b0"] is T.MINE


def test_submarine_is_not_exempt_from_mines():
    state = custom_state(
        [("a0", T.SUBMARINE, A, (3, 3)), ("b0", T.MINE, B, (3, 5))]
    )
    new, _ = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square is None


@pytest.mark.parametrize("ptype", [T.MINE_SWEEPER, T.MINE_LAYER, T.FLYING_BOAT])
def test_mine_exempt_pieces_survive_adjacency(ptype):
    state = custom_state(
        [("a0", ptype, A, (3, 3)), ("b0", T.MINE, B, (3, 5))]
    )
    new, _ = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square == (3, 4)


def test_own_mine_is_harmless():
    state = custom_state(
        [("a0", T.FLAGSHIP, A, (3, 3)), ("a1", T.MINE, A, (3, 5))]
    )
    new, _ = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square == (3, 4)


def test_moving_next_to_enemy_mine_layer_blows_up():
    state = custom_state(
        [("a0", T.FLAGSHIP, A, (3, 3)), ("b0", T.MINE_LAYER, B, (3, 5))]
    )
    new, events = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square is None
    assert PassiveKill("a0", "b0") in events
    assert new.knowledge[A]["b0"] is T.MINE_LAYER


@pytest.mark.parametrize(
    "ptype",
    [T.MINE_SWEEPER, T.SUBMARINE, T.FLYING_BOAT, T.MINE_LAYER, T.DESTROYER],
)
def test_mine_layer_exempt_pieces_survive_adjacency(ptype):
    state = custom_state(
        [("a0", ptype, A, (3, 3)), ("b0", T.MINE_LAYER, B, (3, 5))]
    )
    new, _ = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square == (3, 4)


def test_moving_clears_declined_pairs():
    state = custom_state(
        [("a0", T.DESTROYER, A, (3, 3)), ("b0", T.DESTROYER, B, (3, 4))],
        declined=frozenset({frozenset({"a0", "b0"})}),
    )
    new, _ = apply_action(state, Move("a0", (2, 3)))
    assert new.declined == frozenset()


def test_ordinary_ship_cannot_enter_own_base():
    state = custom_state([("a0", T.DESTROYER, A, (0, 1))])
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (0, 0)))
