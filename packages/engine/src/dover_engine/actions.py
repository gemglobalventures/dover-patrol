from __future__ import annotations

from dataclasses import dataclass

from .board import Square


@dataclass(frozen=True)
class Move:
    piece_id: str
    to: Square


@dataclass(frozen=True)
class Attack:
    piece_id: str
    target_square: Square


@dataclass(frozen=True)
class Decline:
    piece_id: str
    target_square: Square


@dataclass(frozen=True)
class TransferFlag:
    from_piece: str
    to_piece: str


@dataclass(frozen=True)
class RunAground:
    """Forced resolution: a ship on a base with no legal square to move off to."""

    piece_id: str


Action = Move | Attack | Decline | TransferFlag | RunAground
