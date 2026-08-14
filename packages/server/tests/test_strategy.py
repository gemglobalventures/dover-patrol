"""The auto-arrangement should follow the rulebook's Hints on Play, not
just shuffle: harbour garrison, heavies at the back, cheap screen up front,
a scout beyond — and still vary from game to game."""
import random

import pytest

from dover_engine.board import BASE, HARBOUR
from dover_engine.state import validate_placements
from dover_engine.types import Player, PieceType

from dover_server.strategy import GARRISON, SCOUT, SCREEN, strategic_placements

T = PieceType
A, B = Player.A, Player.B


@pytest.mark.parametrize("mode", ["full", "capture_base"])
@pytest.mark.parametrize("player", [A, B])
@pytest.mark.parametrize("seed", range(8))
def test_layouts_are_always_legal(mode, player, seed):
    placements = strategic_placements(mode, player, random.Random(seed))
    validate_placements(mode, player, placements)  # must not raise


@pytest.mark.parametrize("mode", ["full", "capture_base"])
def test_hints_on_play_are_followed(mode):
    rng = random.Random(42)
    back_rows = 5 if mode == "full" else 3
    for player in Player:
        placements = strategic_placements(mode, player, rng)
        by_square = {sq: t for t, sq in placements}

        harbour = [
            t for sq, t in by_square.items()
            if sq in HARBOUR[player] and sq != BASE[player]
        ]
        assert harbour and all(t in GARRISON for t in harbour)

        front = back_rows - 1 if player is A else 11 - (back_rows - 1)
        front_pieces = [t for sq, t in by_square.items() if sq[1] == front]
        assert all(t in SCREEN for t in front_pieces)
        assert T.FLAGSHIP not in front_pieces and T.MINE not in front_pieces

        back = 0 if player is A else 11
        back_pieces = {t for sq, t in by_square.items() if sq[1] == back}
        for heavy in (T.FLAGSHIP, T.VICE_FLAGSHIP, T.BATTLE_SQUADRON):
            if any(t is heavy for t, _ in placements):
                assert heavy in back_pieces

        odd_row = back_rows if player is A else 11 - back_rows
        scout = [t for sq, t in by_square.items() if sq[1] == odd_row]
        assert len(scout) == 1 and scout[0] in SCOUT


def test_layouts_vary_between_games():
    layouts = {
        tuple(sorted((t.value, sq) for t, sq in
              strategic_placements("capture_base", A, random.Random(seed))))
        for seed in range(6)
    }
    assert len(layouts) > 1
