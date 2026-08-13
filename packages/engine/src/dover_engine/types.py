from __future__ import annotations

from enum import Enum


class PieceType(Enum):
    FLAGSHIP = "flagship"
    VICE_FLAGSHIP = "vice_flagship"
    BATTLE_SQUADRON = "battle_squadron"
    BATTLESHIP = "battleship"
    BATTLE_CRUISER = "battle_cruiser"
    LIGHT_CRUISER = "light_cruiser"
    DESTROYER = "destroyer"
    AUXILIARY_CRUISER = "auxiliary_cruiser"
    MOTOR_TORPEDO_BOAT = "motor_torpedo_boat"
    PATROL_VESSEL = "patrol_vessel"
    MINE_LAYER = "mine_layer"
    MINE_SWEEPER = "mine_sweeper"
    SUBMARINE = "submarine"
    FLYING_BOAT = "flying_boat"
    MINE = "mine"


# Numeric fleet values; auxiliaries have none.
VALUE: dict[PieceType, int | None] = {
    PieceType.FLAGSHIP: 10,
    PieceType.VICE_FLAGSHIP: 9,
    PieceType.BATTLE_SQUADRON: 8,
    PieceType.BATTLESHIP: 7,
    PieceType.BATTLE_CRUISER: 6,
    PieceType.LIGHT_CRUISER: 5,
    PieceType.DESTROYER: 4,
    PieceType.AUXILIARY_CRUISER: 3,
    PieceType.MOTOR_TORPEDO_BOAT: 2,
    PieceType.PATROL_VESSEL: 1,
    PieceType.MINE_LAYER: None,
    PieceType.MINE_SWEEPER: None,
    PieceType.SUBMARINE: None,
    PieceType.FLYING_BOAT: None,
    PieceType.MINE: None,
}


class Player(Enum):
    A = "a"  # south side, setup rows 0-4, base (0, 0)
    B = "b"  # north side, setup rows 11-7, base (7, 11)

    @property
    def opponent(self) -> "Player":
        return Player.B if self is Player.A else Player.A
