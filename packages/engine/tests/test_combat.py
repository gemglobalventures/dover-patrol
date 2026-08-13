"""Combat resolution tests.

Ground truth is data/combat_matrix.csv, extracted from the Chris Brice
spreadsheet of the 1956 rulebook matrix. Semantics per the rulebook:
the loser is sunk and the winner remains on the square it occupied —
there is no advance into the defender's square.
"""
import csv
from pathlib import Path

import pytest

from dover_engine.combat import Fate, IllegalAttack, resolve
from dover_engine.types import PieceType

MATRIX_CSV = Path(__file__).resolve().parents[3] / "data" / "combat_matrix.csv"

CODE_TO_TYPE = {
    "10": PieceType.FLAGSHIP,
    "9": PieceType.VICE_FLAGSHIP,
    "8": PieceType.BATTLE_SQUADRON,
    "7": PieceType.BATTLESHIP,
    "6": PieceType.BATTLE_CRUISER,
    "5": PieceType.LIGHT_CRUISER,
    "4": PieceType.DESTROYER,
    "3": PieceType.AUXILIARY_CRUISER,
    "2": PieceType.MOTOR_TORPEDO_BOAT,
    "1": PieceType.PATROL_VESSEL,
    "ML": PieceType.MINE_LAYER,
    "MS": PieceType.MINE_SWEEPER,
    "SS": PieceType.SUBMARINE,
    "SUB": PieceType.SUBMARINE,
    "FB": PieceType.FLYING_BOAT,
    "MI": PieceType.MINE,
}


# The spreadsheet has MTB-attacks-Submarine resolving to the Submarine, but the
# rulebook is explicit that MTBs sink Submarines ("...and MOTOR TORPEDO BOATS
# (2), which sink them") with no direction dependence, and the design doc
# agrees. Treated as a transcription error in the 2003 spreadsheet.
CORRECTIONS = {("2", "SUB"): "2"}


def matrix_cases():
    with open(MATRIX_CSV, newline="") as f:
        rows = list(csv.reader(f))
    defender_codes = rows[0][1:]
    for row in rows[1:]:
        attacker_code, cells = row[0], row[1:]
        for defender_code, cell in zip(defender_codes, cells):
            cell = CORRECTIONS.get((attacker_code, defender_code), cell)
            yield attacker_code, defender_code, cell


@pytest.mark.parametrize(
    "attacker_code,defender_code,cell",
    list(matrix_cases()),
    ids=lambda v: str(v),
)
def test_matches_matrix(attacker_code, defender_code, cell):
    attacker = CODE_TO_TYPE[attacker_code]
    defender = CODE_TO_TYPE[defender_code]

    if cell == "cannot_attack":
        with pytest.raises(IllegalAttack):
            resolve(attacker, defender)
        return

    attacker_fate, defender_fate = resolve(attacker, defender)

    if cell == "both_sunk":
        assert (attacker_fate, defender_fate) == (Fate.SUNK, Fate.SUNK)
    elif cell == "no_effect":
        assert (attacker_fate, defender_fate) == (Fate.HOLDS, Fate.HOLDS)
    elif CODE_TO_TYPE[cell] is attacker and CODE_TO_TYPE[cell] is not defender:
        assert (attacker_fate, defender_fate) == (Fate.HOLDS, Fate.SUNK)
    elif CODE_TO_TYPE[cell] is defender and CODE_TO_TYPE[cell] is not attacker:
        assert (attacker_fate, defender_fate) == (Fate.SUNK, Fate.HOLDS)
    else:
        pytest.fail(f"ambiguous or unrecognised matrix cell {cell!r}")


def test_winner_never_advances():
    """Rulebook: the winner remains 'on the same space from which it attacked'."""
    assert set(Fate) == {Fate.SUNK, Fate.HOLDS}


def test_equal_values_both_sunk():
    assert resolve(PieceType.DESTROYER, PieceType.DESTROYER) == (Fate.SUNK, Fate.SUNK)


def test_mine_survives_killing_attacker():
    assert resolve(PieceType.FLAGSHIP, PieceType.MINE) == (Fate.SUNK, Fate.HOLDS)


def test_sweeper_destroys_mine_and_survives():
    assert resolve(PieceType.MINE_SWEEPER, PieceType.MINE) == (Fate.HOLDS, Fate.SUNK)


def test_flying_boat_scouting_is_noop_both_ways():
    assert resolve(PieceType.FLYING_BOAT, PieceType.FLAGSHIP) == (Fate.HOLDS, Fate.HOLDS)
    assert resolve(PieceType.FLAGSHIP, PieceType.FLYING_BOAT) == (Fate.HOLDS, Fate.HOLDS)


def test_torpedo_boat_sinks_submarine_but_not_vice_versa():
    assert resolve(PieceType.MOTOR_TORPEDO_BOAT, PieceType.SUBMARINE) == (Fate.HOLDS, Fate.SUNK)
    assert resolve(PieceType.SUBMARINE, PieceType.MOTOR_TORPEDO_BOAT) == (Fate.SUNK, Fate.HOLDS)


def test_mine_layer_and_mine_may_never_attack():
    for defender in PieceType:
        with pytest.raises(IllegalAttack):
            resolve(PieceType.MINE_LAYER, defender)
        with pytest.raises(IllegalAttack):
            resolve(PieceType.MINE, defender)
