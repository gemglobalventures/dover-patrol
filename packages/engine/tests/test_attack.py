"""Attacks and declines.

Rulebook: an attack is declared at the same time as the move that creates
the back-to-back contact — "Attack!" or "No Attack!" — and the move passes
either way. The winner remains on the square it attacked from. A standing
piece may also attack an adjacent enemy in lieu of moving, unless that pair
was previously declined; declined pairs clear when either piece moves.
In the short game ("Capturing the Base") attacking is compulsory.
"""
import pytest

from conftest import custom_state

from dover_engine.actions import Attack, Decline, Move
from dover_engine.combat import Fate
from dover_engine.engine import IllegalAction, apply_action
from dover_engine.events import Combat, Declined
from dover_engine.types import Player, PieceType

T = PieceType
A, B = Player.A, Player.B


def duel(attacker_type, defender_type, **kwargs):
    return custom_state(
        [("a0", attacker_type, A, (3, 3)), ("b0", defender_type, B, (3, 4))],
        **kwargs,
    )


def test_move_into_contact_with_attack_resolves_combat():
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 2)), ("b0", T.DESTROYER, B, (3, 4))]
    )
    new, events = apply_action(state, Move("a0", (3, 3), attack=(3, 4)))
    # Winner stays on the square it attacked from; loser is removed.
    assert new.pieces["a0"].square == (3, 3)
    assert new.pieces["b0"].square is None
    assert new.to_move is B
    combat = next(e for e in events if isinstance(e, Combat))
    assert (combat.attacker_fate, combat.defender_fate) == (Fate.HOLDS, Fate.SUNK)


def test_attack_reveals_both_pieces_to_both_players():
    state = custom_state(
        [("a0", T.FLYING_BOAT, A, (3, 2)), ("b0", T.FLAGSHIP, B, (3, 4))]
    )
    new, _ = apply_action(state, Move("a0", (3, 3), attack=(3, 4)))
    assert new.knowledge[A]["b0"] is T.FLAGSHIP  # the scouted value
    assert new.knowledge[B]["a0"] is T.FLYING_BOAT


def test_move_with_no_attack_declines_new_contacts():
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 2)), ("b0", T.DESTROYER, B, (3, 4))]
    )
    new, _ = apply_action(state, Move("a0", (3, 3)))
    assert frozenset({"a0", "b0"}) in new.declined


def test_declined_pair_cannot_launch_standing_attack():
    state = duel(
        T.BATTLESHIP,
        T.DESTROYER,
        declined=frozenset({frozenset({"a0", "b0"})}),
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Attack("a0", (3, 4)))


def test_standing_attack_on_undeclined_pair():
    state = duel(T.BATTLESHIP, T.DESTROYER)
    new, events = apply_action(state, Attack("a0", (3, 4)))
    assert new.pieces["b0"].square is None
    assert new.pieces["a0"].square == (3, 3)
    assert any(isinstance(e, Combat) for e in events)


def test_equal_values_sink_both():
    state = duel(T.DESTROYER, T.DESTROYER)
    new, _ = apply_action(state, Attack("a0", (3, 4)))
    assert new.pieces["a0"].square is None
    assert new.pieces["b0"].square is None


def test_standing_attack_requires_adjacency():
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 3)), ("b0", T.DESTROYER, B, (3, 5))]
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Attack("a0", (3, 5)))


def test_cannot_attack_own_piece():
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 3)), ("a1", T.DESTROYER, A, (3, 4))]
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Attack("a0", (3, 4)))


@pytest.mark.parametrize("ptype", [T.MINE_LAYER, T.MINE])
def test_mine_layer_and_mine_cannot_attack(ptype):
    state = duel(ptype, T.PATROL_VESSEL)
    with pytest.raises(IllegalAction):
        apply_action(state, Attack("a0", (3, 4)))


def test_move_attack_must_target_new_contact():
    # The declared target must be a piece the move actually came back-to-back with.
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 2)), ("b0", T.DESTROYER, B, (5, 5))]
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (3, 3), attack=(5, 5)))


def test_no_effect_pair_may_reattack_later():
    # A Flying Boat probe leaves both in place and the pair undeclined.
    state = duel(T.FLYING_BOAT, T.FLAGSHIP)
    new, _ = apply_action(state, Attack("a0", (3, 4)))
    assert frozenset({"a0", "b0"}) not in new.declined
    # B takes a turn elsewhere, then A may probe again.
    state2 = custom_state(
        [
            ("a0", T.FLYING_BOAT, A, (3, 3)),
            ("b0", T.FLAGSHIP, B, (3, 4)),
            ("b1", T.PATROL_VESSEL, B, (6, 6)),
        ],
        to_move=B,
    )
    state3, _ = apply_action(state2, Move("b1", (6, 7)))
    _, events = apply_action(state3, Attack("a0", (3, 4)))
    assert any(isinstance(e, Combat) for e in events)


def test_explicit_decline_action_records_pair_and_passes_turn():
    state = duel(T.BATTLESHIP, T.DESTROYER)
    new, events = apply_action(state, Decline("a0", (3, 4)))
    assert frozenset({"a0", "b0"}) in new.declined
    assert new.to_move is B
    assert Declined("a0", "b0") in events


def test_short_game_attack_is_compulsory_on_contact():
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 2)), ("b0", T.DESTROYER, B, (3, 4))],
        mode="capture_base",
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", (3, 3)))
    new, _ = apply_action(state, Move("a0", (3, 3), attack=(3, 4)))
    assert new.pieces["b0"].square is None


def test_short_game_forbids_decline_action():
    state = duel(T.BATTLESHIP, T.DESTROYER, mode="capture_base")
    with pytest.raises(IllegalAction):
        apply_action(state, Decline("a0", (3, 4)))


def test_short_game_move_without_contact_is_fine():
    state = custom_state(
        [("a0", T.BATTLESHIP, A, (3, 2)), ("b0", T.DESTROYER, B, (3, 6))],
        mode="capture_base",
    )
    new, _ = apply_action(state, Move("a0", (3, 3)))
    assert new.pieces["a0"].square == (3, 3)


def test_sunk_pieces_drop_out_of_declined_tracking():
    state = custom_state(
        [
            ("a0", T.BATTLESHIP, A, (3, 3)),
            ("b0", T.DESTROYER, B, (3, 4)),
            ("b1", T.PATROL_VESSEL, B, (2, 3)),
        ],
        declined=frozenset({frozenset({"a0", "b1"})}),
    )
    # a0 sinks b0 by standing attack; the a0/b1 declined pair must survive
    # (neither of them moved), while pairs containing sunk pieces clear.
    new, _ = apply_action(state, Attack("a0", (3, 4)))
    assert frozenset({"a0", "b1"}) in new.declined

    state2 = custom_state(
        [("a0", T.DESTROYER, A, (3, 3)), ("b0", T.DESTROYER, B, (3, 4))],
        declined=frozenset({frozenset({"a0", "b0"})}),
    )
    # Equal-value duel elsewhere is impossible while declined; but if b0 is
    # sunk by someone else the pair clears. Simulate via a second attacker.
    state2 = custom_state(
        [
            ("a0", T.DESTROYER, A, (3, 3)),
            ("a1", T.BATTLESHIP, A, (4, 4)),
            ("b0", T.DESTROYER, B, (3, 4)),
        ],
        declined=frozenset({frozenset({"a0", "b0"})}),
    )
    new2, _ = apply_action(state2, Attack("a1", (3, 4)))
    assert new2.declined == frozenset()
