"""Random self-play smoke tests: every action offered by legal_actions must
apply cleanly, and core invariants must hold at every ply."""
import random

import pytest

from conftest import make_placements

from dover_engine.engine import apply_action, legal_actions
from dover_engine.state import new_game
from dover_engine.types import Player


def _assert_invariants(state):
    live = [p for p in state.pieces.values() if p.square is not None]
    squares = [p.square for p in live]
    assert len(squares) == len(set(squares)), "two pieces on one square"

    for flag_owner, loc in state.flags.items():
        assert (loc.carrier is None) != (loc.square is None), "flag in limbo"
        if loc.carrier is not None:
            carrier = state.pieces[loc.carrier]
            assert carrier.square is not None, "flag carried by a sunk piece"
            assert flag_owner in carrier.carrying

    for piece in live:
        for flag_owner in piece.carrying:
            assert state.flags[flag_owner].carrier == piece.id


@pytest.mark.parametrize("mode", ["full", "capture_base"])
@pytest.mark.parametrize("seed", range(5))
def test_random_playout(mode, seed):
    rng = random.Random(seed)
    state = new_game(
        mode,
        make_placements(mode, Player.A),
        make_placements(mode, Player.B),
        first_to_move=Player.A,
    )
    for _ in range(400):
        if state.winner is not None:
            break
        actions = legal_actions(state)
        assert actions, "legal_actions empty although the game is not over"
        state, _events = apply_action(state, rng.choice(actions))
        _assert_invariants(state)


def test_legal_actions_empty_when_game_over(short_game):
    from dataclasses import replace

    finished = replace(short_game, winner=Player.A)
    assert legal_actions(finished) == []
