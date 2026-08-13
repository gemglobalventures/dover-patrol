from __future__ import annotations

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from dover_engine.engine import IllegalAction, apply_action
from dover_engine.state import SetupError
from dover_engine.types import Player

from .projection import parse_action, project, serialize_event
from .rooms import Room, placements_from_json, placements_to_json, random_placements

app = FastAPI(title="Dover Patrol")

rooms: dict[str, Room] = {}


async def _send_states(room: Room) -> None:
    for player in Player:
        ws = room.sockets[player]
        if ws is not None and room.state is not None:
            await ws.send_json(
                {"type": "state", "state": project(room.state, player)}
            )


async def _broadcast(room: Room, message: dict) -> None:
    for player in Player:
        ws = room.sockets[player]
        if ws is not None:
            await ws.send_json(message)


async def _room_status(room: Room) -> None:
    await _broadcast(
        room,
        {
            "type": "room_status",
            "phase": room.phase,
            "connected": {p.value: room.sockets[p] is not None for p in Player},
            "setup_done": {p.value: room.placements[p] is not None for p in Player},
        },
    )


@app.websocket("/ws/{room_id}/{side}")
async def game_socket(ws: WebSocket, room_id: str, side: str, mode: str = "capture_base"):
    await ws.accept()
    if side not in ("a", "b"):
        await ws.send_json({"type": "error", "reason": "side must be 'a' or 'b'"})
        await ws.close()
        return
    player = Player(side)
    room = rooms.setdefault(room_id, Room(room_id=room_id, mode=mode))
    old = room.sockets[player]
    if old is not None:
        # Take over the seat: a refresh or reconnect replaces the stale socket.
        room.sockets[player] = None
        try:
            await old.close()
        except Exception:
            pass

    room.sockets[player] = ws
    await ws.send_json(
        {
            "type": "joined",
            "room": room_id,
            "player": side,
            "mode": room.mode,
            "phase": room.phase,
        }
    )
    if room.state is not None:
        await ws.send_json({"type": "state", "state": project(room.state, player)})
    await _room_status(room)

    try:
        while True:
            data = await ws.receive_json()
            await _handle_message(room, player, ws, data)
    except WebSocketDisconnect:
        if room.sockets[player] is ws:  # a takeover may already own the seat
            room.sockets[player] = None
            try:
                await _room_status(room)
            except Exception:
                pass


async def _handle_message(room: Room, player: Player, ws: WebSocket, data: dict) -> None:
    kind = data.get("type")
    try:
        if kind == "random_setup":
            placements = random_placements(room.mode, player, room.rng)
            await ws.send_json(
                {"type": "setup_proposal", "placements": placements_to_json(placements)}
            )
        elif kind == "setup":
            room.submit_setup(player, placements_from_json(data["placements"]))
            await _room_status(room)
            if room.state is not None:
                await _send_states(room)
        elif kind in ("move", "attack", "decline", "transfer_flag", "run_aground"):
            if room.state is None:
                raise IllegalAction("the game has not started")
            if room.state.to_move is not player:
                raise IllegalAction("it is not your turn")
            new_state, events = apply_action(room.state, parse_action(data))
            room.state = new_state
            await _broadcast(
                room,
                {"type": "events", "events": [serialize_event(e) for e in events]},
            )
            await _send_states(room)
        else:
            await ws.send_json({"type": "error", "reason": f"unknown message type {kind!r}"})
    except (IllegalAction, SetupError, KeyError, ValueError) as exc:
        await ws.send_json({"type": "error", "reason": str(exc)})
