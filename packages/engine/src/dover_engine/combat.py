from __future__ import annotations

from enum import Enum

from .types import PieceType


class Fate(Enum):
    SUNK = "sunk"
    HOLDS = "holds"


class IllegalAttack(Exception):
    pass


_SUNK_HOLDS = (Fate.SUNK, Fate.HOLDS)
_HOLDS_SUNK = (Fate.HOLDS, Fate.SUNK)
_BOTH_HOLD = (Fate.HOLDS, Fate.HOLDS)
_BOTH_SUNK = (Fate.SUNK, Fate.SUNK)

T = PieceType


def resolve(attacker: PieceType, defender: PieceType) -> tuple[Fate, Fate]:
    """Resolve a declared attack, returning (attacker_fate, defender_fate).

    The winner remains on the square it attacked from; the loser is removed.
    Passive mine / mine-layer adjacency kills are movement rules, not combat,
    and are handled elsewhere.
    """
    if attacker in (T.MINE_LAYER, T.MINE):
        raise IllegalAttack(f"{attacker.value} may never attack")

    if attacker is T.MINE_SWEEPER:
        if defender is T.MINE:
            return _HOLDS_SUNK
        if defender in (T.MINE_LAYER, T.MINE_SWEEPER, T.SUBMARINE, T.FLYING_BOAT):
            return _BOTH_HOLD
        return _SUNK_HOLDS  # sunk by every numbered ship

    if attacker is T.SUBMARINE:
        if defender is T.MOTOR_TORPEDO_BOAT:
            return _SUNK_HOLDS
        if defender is T.MINE:
            return _SUNK_HOLDS
        if defender in (T.MINE_LAYER, T.SUBMARINE, T.FLYING_BOAT):
            return _BOTH_HOLD
        return _HOLDS_SUNK  # sinks all numbered ships and the Mine Sweeper

    if attacker is T.FLYING_BOAT:
        if defender in (T.MOTOR_TORPEDO_BOAT, T.DESTROYER):
            return _SUNK_HOLDS
        return _BOTH_HOLD

    # Numbered attackers from here on.
    if defender is T.MINE:
        return _SUNK_HOLDS
    if defender is T.MINE_LAYER:
        if attacker is T.DESTROYER:
            return _HOLDS_SUNK  # the only piece that can sink a Mine Layer
        return _SUNK_HOLDS
    if defender is T.MINE_SWEEPER:
        return _HOLDS_SUNK
    if defender is T.SUBMARINE:
        if attacker is T.MOTOR_TORPEDO_BOAT:
            return _HOLDS_SUNK
        return _SUNK_HOLDS
    if defender is T.FLYING_BOAT:
        if attacker in (T.MOTOR_TORPEDO_BOAT, T.DESTROYER):
            return _HOLDS_SUNK
        return _BOTH_HOLD

    from .types import VALUE

    a, d = VALUE[attacker], VALUE[defender]
    assert a is not None and d is not None
    if a == d:
        return _BOTH_SUNK
    return _HOLDS_SUNK if a > d else _SUNK_HOLDS
