"""Flag lifecycle: capture from the base, the move-off/run-aground
obligation, transfers on the immediately-following move, drops, and the
Mine-Sweeper-only recovery after a mine kill."""
import pytest

from conftest import custom_state

from dover_engine.actions import Attack, Move, RunAground, TransferFlag
from dover_engine.engine import IllegalAction, apply_action
from dover_engine.events import (
    FlagCaptured,
    FlagDropped,
    FlagPickedUp,
    FlagTransferred,
    GameOver,
    RanAground,
)
from dover_engine.state import FlagLoc
from dover_engine.types import Player, PieceType

T = PieceType
A, B = Player.A, Player.B
B_BASE = (7, 11)
A_BASE = (0, 0)


def test_capture_flag_from_base():
    state = custom_state([("a0", T.DESTROYER, A, (7, 10))])
    new, events = apply_action(state, Move("a0", B_BASE))
    assert FlagCaptured(B, "a0") in events
    assert new.pieces["a0"].carrying == frozenset({B})
    assert new.flags[B] == FlagLoc(carrier="a0")


def test_cannot_enter_enemy_base_without_flag_there():
    state = custom_state(
        [("a0", T.DESTROYER, A, (7, 10))],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", B_BASE))


def test_capturer_must_move_off_base_next_turn():
    state = custom_state(
        [("a0", T.DESTROYER, A, (7, 10)), ("a1", T.PATROL_VESSEL, A, (3, 3)),
         ("b0", T.PATROL_VESSEL, B, (0, 6))],
    )
    state, _ = apply_action(state, Move("a0", B_BASE))
    state, _ = apply_action(state, Move("b0", (0, 5)))
    # A may not move another piece while the capturer sits on the base.
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a1", (3, 4)))
    new, _ = apply_action(state, Move("a0", (7, 10)))
    assert new.pieces["a0"].square == (7, 10)
    assert new.pieces["a0"].carrying == frozenset({B})


def test_run_aground_rejected_while_an_exit_exists():
    state = custom_state(
        [
            ("a0", T.DESTROYER, A, B_BASE, frozenset({B})),
            ("b1", T.PATROL_VESSEL, B, (6, 11)),
        ],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    # (7,10) is still free, so the capturer can and must sail off.
    with pytest.raises(IllegalAction):
        apply_action(state, RunAground("a0"))
    new, _ = apply_action(state, Move("a0", (7, 10)))
    assert new.pieces["a0"].square == (7, 10)


def test_run_aground_when_truly_stuck():
    # Capturer on the base with both harbour neighbours occupied.
    state = custom_state(
        [
            ("a0", T.DESTROYER, A, B_BASE, frozenset({B})),
            ("a1", T.PATROL_VESSEL, A, (3, 3)),
            ("b1", T.PATROL_VESSEL, B, (6, 11)),
            ("b2", T.PATROL_VESSEL, B, (7, 10)),
        ],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    # Moving another piece is still barred; the only legal resolution is aground.
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a1", (3, 4)))
    new, events = apply_action(state, RunAground("a0"))
    assert new.pieces["a0"].square is None
    assert new.flags[B] == FlagLoc(square=B_BASE)
    assert RanAground("a0") in events
    assert new.to_move is B


def test_transfer_on_the_immediately_following_move():
    state = custom_state(
        [
            ("a0", T.PATROL_VESSEL, A, (3, 3), frozenset({B})),
            ("a1", T.BATTLESHIP, A, (3, 5)),
            ("b0", T.PATROL_VESSEL, B, (0, 6)),
        ],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    state, _ = apply_action(state, Move("a0", (3, 4)))  # now adjacent to a1
    state, _ = apply_action(state, Move("b0", (0, 5)))
    new, events = apply_action(state, TransferFlag("a0", "a1"))
    assert new.pieces["a1"].carrying == frozenset({B})
    assert new.pieces["a0"].carrying == frozenset()
    assert new.flags[B] == FlagLoc(carrier="a1")
    assert FlagTransferred(B, "a0", "a1") in events
    assert new.to_move is B


def test_transfer_window_expires_if_not_used():
    state = custom_state(
        [
            ("a0", T.PATROL_VESSEL, A, (3, 3), frozenset({B})),
            ("a1", T.BATTLESHIP, A, (3, 5)),
            ("a2", T.PATROL_VESSEL, A, (6, 6)),
            ("b0", T.PATROL_VESSEL, B, (0, 6)),
        ],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    state, _ = apply_action(state, Move("a0", (3, 4)))
    state, _ = apply_action(state, Move("b0", (0, 5)))
    state, _ = apply_action(state, Move("a2", (6, 7)))  # A does something else
    state, _ = apply_action(state, Move("b0", (0, 6)))
    with pytest.raises(IllegalAction):
        apply_action(state, TransferFlag("a0", "a1"))


def test_carrier_cannot_attack_other_carrier():
    state = custom_state(
        [
            ("a0", T.BATTLESHIP, A, (3, 3), frozenset({B})),
            ("b0", T.DESTROYER, B, (3, 4), frozenset({A})),
        ],
        flags={A: FlagLoc(carrier="b0"), B: FlagLoc(carrier="a0")},
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Attack("a0", (3, 4)))


def test_equal_value_duel_with_carrier_drops_flag():
    state = custom_state(
        [
            ("a0", T.DESTROYER, A, (3, 3)),
            ("b0", T.DESTROYER, B, (3, 4), frozenset({A})),
        ],
        flags={A: FlagLoc(carrier="b0"), B: FlagLoc(square=B_BASE)},
    )
    new, events = apply_action(state, Attack("a0", (3, 4)))
    assert new.flags[A] == FlagLoc(square=(3, 4))
    assert FlagDropped(A, (3, 4), False) in events


def test_successful_attack_on_carrier_takes_the_flag():
    state = custom_state(
        [
            ("a0", T.BATTLESHIP, A, (3, 3)),
            ("b0", T.DESTROYER, B, (3, 4), frozenset({A})),
        ],
        flags={A: FlagLoc(carrier="b0"), B: FlagLoc(square=B_BASE)},
    )
    new, _ = apply_action(state, Attack("a0", (3, 4)))
    assert new.pieces["a0"].carrying == frozenset({A})
    assert new.flags[A] == FlagLoc(carrier="a0")


def test_mine_kill_drops_sweeper_only_flag():
    state = custom_state(
        [
            ("a0", T.DESTROYER, A, (3, 3), frozenset({B})),
            ("b0", T.MINE, B, (3, 5)),
        ],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    new, events = apply_action(state, Move("a0", (3, 4)))
    assert new.pieces["a0"].square is None
    assert new.flags[B] == FlagLoc(square=(3, 4), sweeper_only=True)
    assert FlagDropped(B, (3, 4), True) in events


def test_only_sweeper_recovers_mine_dropped_flag():
    flags = {
        A: FlagLoc(square=A_BASE),
        B: FlagLoc(square=(3, 4), sweeper_only=True),
    }
    state = custom_state(
        [("a1", T.BATTLESHIP, A, (2, 4)), ("b0", T.MINE, B, (3, 5))], flags=flags
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a1", (3, 4)))

    state = custom_state(
        [("a1", T.MINE_SWEEPER, A, (2, 4)), ("b0", T.MINE, B, (3, 5))], flags=flags
    )
    new, events = apply_action(state, Move("a1", (3, 4)))
    assert new.pieces["a1"].carrying == frozenset({B})
    assert FlagPickedUp(B, "a1") in events


def test_deposit_enemy_flag_wins_when_own_flag_home():
    state = custom_state(
        [("a0", T.DESTROYER, A, (0, 1), frozenset({B}))],
        flags={A: FlagLoc(square=A_BASE), B: FlagLoc(carrier="a0")},
    )
    new, events = apply_action(state, Move("a0", A_BASE))
    assert new.winner is A
    assert GameOver(A) in events


def test_cannot_deposit_enemy_flag_while_own_flag_is_away():
    state = custom_state(
        [
            ("a0", T.DESTROYER, A, (0, 1), frozenset({B})),
            ("b0", T.PATROL_VESSEL, B, (5, 8), frozenset({A})),
        ],
        flags={A: FlagLoc(carrier="b0"), B: FlagLoc(carrier="a0")},
    )
    with pytest.raises(IllegalAction):
        apply_action(state, Move("a0", A_BASE))


def test_carrying_both_flags_home_wins():
    state = custom_state(
        [("a0", T.DESTROYER, A, (0, 1), frozenset({A, B}))],
        flags={A: FlagLoc(carrier="a0"), B: FlagLoc(carrier="a0")},
    )
    new, _ = apply_action(state, Move("a0", A_BASE))
    assert new.winner is A


def test_short_game_base_occupation_wins():
    state = custom_state(
        [("a0", T.DESTROYER, A, (7, 10))], mode="capture_base"
    )
    new, events = apply_action(state, Move("a0", B_BASE))
    assert new.winner is A
    assert GameOver(A) in events


def test_immobilised_opponent_loses_when_your_flag_is_home():
    # B's only piece is a mine; mines may never move.
    state = custom_state(
        [("a0", T.DESTROYER, A, (3, 3)), ("b0", T.MINE, B, (7, 7))]
    )
    new, events = apply_action(state, Move("a0", (3, 4)))
    assert new.winner is A
    assert GameOver(A) in events


def test_immobilised_opponent_draws_when_your_flag_is_away():
    # A sinks B's last mobile piece (the carrier of A's flag). The flag passes
    # to the attacker — so it is NOT on A's base — and B has only a mine left:
    # hemming in without your own flag at home is only a draw.
    state = custom_state(
        [
            ("a0", T.BATTLESHIP, A, (5, 3)),
            ("b0", T.MINE, B, (7, 7)),
            ("b1", T.PATROL_VESSEL, B, (5, 4), frozenset({A})),
        ],
        flags={A: FlagLoc(carrier="b1"), B: FlagLoc(square=B_BASE)},
    )
    new, _ = apply_action(state, Attack("a0", (5, 4)))
    assert new.winner == "draw"
