from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from dover_engine.state import FlagLoc, GameState, Piece
from dover_engine.types import Player, PieceType

from .rooms import Room, placements_from_json, placements_to_json


def rooms_dir() -> Path:
    d = Path(os.environ.get("DOVER_ROOMS_DIR", ".rooms"))
    d.mkdir(parents=True, exist_ok=True)
    return d


def _room_path(room_id: str) -> Path:
    safe = re.sub(r"[^A-Za-z0-9_-]", "_", room_id)[:60]
    digest = hashlib.sha1(room_id.encode()).hexdigest()[:8]
    return rooms_dir() / f"{safe}-{digest}.json"


def _sq(value):
    return list(value) if value is not None else None


def state_to_json(state: GameState) -> dict:
    return {
        "mode": state.mode,
        "to_move": state.to_move.value,
        "winner": state.winner.value if isinstance(state.winner, Player) else state.winner,
        "pieces": [
            {
                "id": p.id,
                "type": p.type.value,
                "owner": p.owner.value,
                "square": _sq(p.square),
                "carrying": sorted(f.value for f in p.carrying),
            }
            for p in state.pieces.values()
        ],
        "flags": {
            player.value: {
                "carrier": loc.carrier,
                "square": _sq(loc.square),
                "sweeper_only": loc.sweeper_only,
            }
            for player, loc in state.flags.items()
        },
        "declined": sorted(sorted(pair) for pair in state.declined),
        "knowledge": {
            player.value: {pid: t.value for pid, t in known.items()}
            for player, known in state.knowledge.items()
        },
        "transfer_window": sorted(list(pair) for pair in state.transfer_window),
    }


def state_from_json(data: dict) -> GameState:
    winner = data["winner"]
    if winner in ("a", "b"):
        winner = Player(winner)
    return GameState(
        mode=data["mode"],
        pieces={
            p["id"]: Piece(
                id=p["id"],
                type=PieceType(p["type"]),
                owner=Player(p["owner"]),
                square=tuple(p["square"]) if p["square"] is not None else None,
                carrying=frozenset(Player(f) for f in p["carrying"]),
            )
            for p in data["pieces"]
        },
        flags={
            Player(k): FlagLoc(
                carrier=loc["carrier"],
                square=tuple(loc["square"]) if loc["square"] is not None else None,
                sweeper_only=loc["sweeper_only"],
            )
            for k, loc in data["flags"].items()
        },
        to_move=Player(data["to_move"]),
        declined=frozenset(frozenset(pair) for pair in data["declined"]),
        knowledge={
            Player(k): {pid: PieceType(t) for pid, t in known.items()}
            for k, known in data["knowledge"].items()
        },
        transfer_window=frozenset(tuple(pair) for pair in data["transfer_window"]),
        winner=winner,
    )


def save_room(room: Room) -> None:
    agent = room.agent
    data = {
        "room_id": room.room_id,
        "mode": room.mode,
        "ai": room.ai,
        "ai_params": room.ai_params,
        "placements": {
            p.value: placements_to_json(room.placements[p])
            if room.placements[p] is not None
            else None
            for p in Player
        },
        "state": state_to_json(room.state) if room.state is not None else None,
        "moved_ids": sorted(room.moved_ids),
        "agent": {
            "seed": agent.seed,
            "attacked": sorted(list(pair) for pair in agent._attacked),
        }
        if agent is not None
        else None,
    }
    path = _room_path(room.room_id)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data))
    os.replace(tmp, path)


def load_room(room_id: str) -> Room | None:
    path = _room_path(room_id)
    if not path.exists():
        return None
    data = json.loads(path.read_text())
    room = Room(
        room_id=room_id,
        mode=data["mode"],
        ai=data["ai"],
        ai_params=data["ai_params"],
    )
    for p in Player:
        stored = data["placements"][p.value]
        room.placements[p] = placements_from_json(stored) if stored is not None else None
    if data["state"] is not None:
        room.state = state_from_json(data["state"])
    room.moved_ids = set(data["moved_ids"])
    if data["agent"] is not None:
        room.ai_params = dict(room.ai_params)
        agent = room.get_agent()
        agent.seed = data["agent"]["seed"]
        agent._attacked = {tuple(pair) for pair in data["agent"]["attacked"]}
    return room
