from __future__ import annotations

from dataclasses import asdict

from dover_engine.actions import Action, Attack, Decline, Move, RunAground, TransferFlag
from dover_engine.engine import legal_actions
from dover_engine.state import FlagLoc, GameState
from dover_engine.types import Player


def _flag_dict(loc: FlagLoc) -> dict:
    if loc.carrier is not None:
        return {"carrier": loc.carrier}
    return {"square": list(loc.square), "sweeper_only": loc.sweeper_only}


def serialize_action(action: Action) -> dict:
    if isinstance(action, Move):
        out = {"type": "move", "piece_id": action.piece_id, "to": list(action.to)}
        if action.attack is not None:
            out["attack"] = list(action.attack)
        return out
    if isinstance(action, Attack):
        return {
            "type": "attack",
            "piece_id": action.piece_id,
            "target": list(action.target_square),
        }
    if isinstance(action, Decline):
        return {
            "type": "decline",
            "piece_id": action.piece_id,
            "target": list(action.target_square),
        }
    if isinstance(action, TransferFlag):
        return {
            "type": "transfer_flag",
            "from_piece": action.from_piece,
            "to_piece": action.to_piece,
        }
    if isinstance(action, RunAground):
        return {"type": "run_aground", "piece_id": action.piece_id}
    raise ValueError(f"unknown action {action!r}")


def parse_action(data: dict) -> Action:
    kind = data.get("type")
    if kind == "move":
        attack = data.get("attack")
        return Move(
            data["piece_id"],
            tuple(data["to"]),
            attack=tuple(attack) if attack is not None else None,
        )
    if kind == "attack":
        return Attack(data["piece_id"], tuple(data["target"]))
    if kind == "decline":
        return Decline(data["piece_id"], tuple(data["target"]))
    if kind == "transfer_flag":
        return TransferFlag(data["from_piece"], data["to_piece"])
    if kind == "run_aground":
        return RunAground(data["piece_id"])
    raise ValueError(f"unknown action type {kind!r}")


def serialize_event(event) -> dict:
    out = {"kind": type(event).__name__}
    for key, value in asdict(event).items():
        if hasattr(value, "value"):  # enums (Player, PieceType, Fate)
            value = value.value
        elif isinstance(value, tuple):
            value = list(value)
        out[key] = value
    return out


def project(state: GameState, viewer: Player) -> dict:
    """Per-recipient view. Own pieces carry their type; enemy pieces only if
    the viewer has learned it (combat reveal, wall crossing, mine hop) or the
    piece is sunk — casualties were shown publicly when they happened."""
    known = state.knowledge[viewer]
    pieces = []
    for piece in state.pieces.values():
        mine = piece.owner is viewer
        revealed = mine or piece.id in known or piece.square is None
        pieces.append(
            {
                "id": piece.id,
                "owner": piece.owner.value,
                "square": list(piece.square) if piece.square else None,
                "type": piece.type.value if revealed else None,
                "carrying": sorted(p.value for p in piece.carrying),
            }
        )

    return {
        "mode": state.mode,
        "you": viewer.value,
        "to_move": state.to_move.value,
        "winner": state.winner.value if isinstance(state.winner, Player) else state.winner,
        "pieces": pieces,
        "flags": {p.value: _flag_dict(loc) for p, loc in state.flags.items()},
        "legal_actions": [
            serialize_action(a) for a in legal_actions(state)
        ]
        if state.to_move is viewer
        else [],
    }
