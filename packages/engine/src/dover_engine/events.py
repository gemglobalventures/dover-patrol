from __future__ import annotations

from dataclasses import dataclass

from .board import Square
from .combat import Fate
from .types import Player, PieceType


@dataclass(frozen=True)
class Moved:
    piece_id: str
    from_square: Square
    to_square: Square


@dataclass(frozen=True)
class WallCrossed:
    """A Flying Boat declared a Harbour Wall crossing (public reveal)."""

    piece_id: str


@dataclass(frozen=True)
class PassiveKill:
    """A piece was blown up by moving adjacent to an enemy Mine or Mine Layer."""

    victim_id: str
    hazard_id: str


@dataclass(frozen=True)
class Combat:
    attacker_id: str
    defender_id: str
    attacker_type: PieceType
    defender_type: PieceType
    attacker_fate: Fate
    defender_fate: Fate


@dataclass(frozen=True)
class Declined:
    piece_id: str
    target_id: str


@dataclass(frozen=True)
class FlagCaptured:
    flag: Player
    by_piece: str


@dataclass(frozen=True)
class FlagDropped:
    flag: Player
    square: Square
    sweeper_only: bool


@dataclass(frozen=True)
class FlagPickedUp:
    flag: Player
    by_piece: str


@dataclass(frozen=True)
class FlagTransferred:
    flag: Player
    from_piece: str
    to_piece: str


@dataclass(frozen=True)
class FlagDeposited:
    flag: Player
    on_base_of: Player


@dataclass(frozen=True)
class RanAground:
    piece_id: str


@dataclass(frozen=True)
class GameOver:
    winner: Player | str  # Player or "draw"


Event = (
    Moved
    | WallCrossed
    | PassiveKill
    | Combat
    | Declined
    | FlagCaptured
    | FlagDropped
    | FlagPickedUp
    | FlagTransferred
    | FlagDeposited
    | RanAground
    | GameOver
)
