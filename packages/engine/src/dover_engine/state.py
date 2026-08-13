from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .board import BASE, COLS, Square, in_bounds
from .types import Player, PieceType

T = PieceType

FULL_ROSTER: dict[PieceType, int] = {
    T.FLAGSHIP: 1,
    T.VICE_FLAGSHIP: 1,
    T.BATTLE_SQUADRON: 1,
    T.BATTLESHIP: 2,
    T.BATTLE_CRUISER: 3,
    T.LIGHT_CRUISER: 4,
    T.DESTROYER: 4,
    T.AUXILIARY_CRUISER: 4,
    T.MOTOR_TORPEDO_BOAT: 5,
    T.PATROL_VESSEL: 5,
    T.MINE_LAYER: 1,
    T.MINE_SWEEPER: 2,
    T.SUBMARINE: 3,
    T.FLYING_BOAT: 1,
    T.MINE: 3,
}

SHORT_ROSTER: dict[PieceType, int] = {
    T.VICE_FLAGSHIP: 1,
    T.BATTLE_SQUADRON: 1,
    T.BATTLESHIP: 1,
    T.BATTLE_CRUISER: 2,
    T.LIGHT_CRUISER: 2,
    T.DESTROYER: 2,
    T.AUXILIARY_CRUISER: 1,
    T.MOTOR_TORPEDO_BOAT: 4,
    T.PATROL_VESSEL: 3,
    T.MINE_LAYER: 1,
    T.MINE_SWEEPER: 1,
    T.SUBMARINE: 2,
    T.FLYING_BOAT: 1,
    T.MINE: 2,
}


class SetupError(Exception):
    pass


@dataclass(frozen=True)
class Piece:
    id: str
    type: PieceType
    owner: Player
    square: Square | None  # None = sunk
    carrying: frozenset[Player] = frozenset()  # whose flags this piece carries


@dataclass(frozen=True)
class FlagLoc:
    carrier: str | None = None
    square: Square | None = None
    sweeper_only: bool = False  # dropped by a mine kill: only a Mine Sweeper recovers it


@dataclass(frozen=True)
class GameState:
    mode: str
    pieces: dict[str, Piece]
    flags: dict[Player, FlagLoc]
    to_move: Player
    declined: frozenset[frozenset[str]] = frozenset()
    knowledge: dict[Player, dict[str, PieceType]] = field(default_factory=dict)
    transfer_window: frozenset[tuple[str, str]] = frozenset()
    winner: Player | str | None = None  # Player, "draw", or None while running

    def piece_at(self, square: Square) -> Piece | None:
        for piece in self.pieces.values():
            if piece.square == square:
                return piece
        return None


def _setup_zone(mode: str, player: Player) -> tuple[set[Square], int]:
    """Squares that must all be occupied, and the odd-piece row."""
    back_rows = 5 if mode == "full" else 3
    rows = range(back_rows) if player is Player.A else range(11, 11 - back_rows, -1)
    required = {
        (col, row)
        for row in rows
        for col in range(COLS)
        if (col, row) != BASE[player]
    }
    odd_row = back_rows if player is Player.A else 11 - back_rows
    return required, odd_row


def _validate_placements(mode: str, player: Player, placements) -> None:
    roster = FULL_ROSTER if mode == "full" else SHORT_ROSTER
    counts = Counter(t for t, _ in placements)
    if counts != Counter({t: n for t, n in roster.items() if n}):
        raise SetupError(f"{player}: placement roster does not match the {mode} roster")

    squares = [sq for _, sq in placements]
    if len(set(squares)) != len(squares):
        raise SetupError(f"{player}: two pieces on one square")
    if not all(in_bounds(sq) for sq in squares):
        raise SetupError(f"{player}: placement off the board")
    if BASE[player] in squares:
        raise SetupError(f"{player}: the base square must stay unoccupied")

    required, odd_row = _setup_zone(mode, player)
    on_odd_row = [sq for sq in squares if sq[1] == odd_row]
    if len(on_odd_row) != 1:
        raise SetupError(f"{player}: exactly one odd piece belongs on row {odd_row}")
    if set(squares) - {on_odd_row[0]} != required:
        raise SetupError(f"{player}: back rows must be completely filled")


def validate_placements(mode: str, player: Player, placements) -> None:
    """Public setup validation for a single player's placement list."""
    _validate_placements(mode, player, placements)


def new_game(mode, placements_a, placements_b, first_to_move) -> GameState:
    if mode not in ("full", "capture_base"):
        raise SetupError(f"unknown mode {mode!r}")
    for player, placements in ((Player.A, placements_a), (Player.B, placements_b)):
        _validate_placements(mode, player, placements)

    pieces: dict[str, Piece] = {}
    for player, placements in ((Player.A, placements_a), (Player.B, placements_b)):
        for i, (ptype, sq) in enumerate(placements):
            pid = f"{player.value}{i}"
            pieces[pid] = Piece(id=pid, type=ptype, owner=player, square=sq)

    flags = (
        {p: FlagLoc(square=BASE[p]) for p in Player} if mode == "full" else {}
    )
    return GameState(
        mode=mode,
        pieces=pieces,
        flags=flags,
        to_move=first_to_move,
        knowledge={Player.A: {}, Player.B: {}},
    )
