"""Persistence: rooms survive a server restart."""
from fastapi.testclient import TestClient

from dover_engine.actions import Attack
from dover_engine.engine import apply_action
from dover_engine.state import FlagLoc, GameState, Piece
from dover_engine.types import Player, PieceType

from dover_server.app import app, rooms
from dover_server.persist import load_room, save_room, state_from_json, state_to_json

from test_ws import do_setup, drain_until, game

T = PieceType
A, B = Player.A, Player.B


def test_state_round_trips_through_json():
    state = GameState(
        mode="full",
        pieces={
            "a0": Piece("a0", T.DESTROYER, A, (3, 3), carrying=frozenset({B})),
            "b0": Piece("b0", T.SUBMARINE, B, (3, 4)),
            "b1": Piece("b1", T.MINE, B, None),
        },
        flags={A: FlagLoc(square=(5, 5), sweeper_only=True), B: FlagLoc(carrier="a0")},
        to_move=B,
        declined=frozenset({frozenset({"a0", "b0"})}),
        knowledge={A: {"b0": T.SUBMARINE}, B: {}},
        transfer_window=frozenset({("a0", "a1")}),
        winner=None,
    )
    again = state_from_json(state_to_json(state))
    assert again == state


def test_room_survives_restart():
    with TestClient(app) as client:
        with game(client) as (ws_a, ws_b, state_a, state_b):
            mover = ws_a if state_a["to_move"] == "a" else ws_b
            mover_state = state_a if state_a["to_move"] == "a" else state_b
            move = next(x for x in mover_state["legal_actions"] if x["type"] == "move")
            mover.send_json(move)
            drain_until(ws_a, "state")
            saved_view = drain_until(ws_b, "state")["state"]

        rooms.clear()  # simulate a full server restart

        with client.websocket_connect("/ws/test/b") as ws_b2:
            joined = drain_until(ws_b2, "joined")
            assert joined["phase"] == "play"
            restored = drain_until(ws_b2, "state")["state"]
            assert restored["pieces"] == saved_view["pieces"]
            assert restored["to_move"] == saved_view["to_move"]


def test_ai_room_memory_survives_restart():
    with TestClient(app) as client:
        with client.websocket_connect(
            "/ws/persistbot/a?mode=capture_base&ai=1&ai_samples=2&ai_depth=1"
        ) as ws_a:
            drain_until(ws_a, "joined")
            do_setup(ws_a)
            drain_until(ws_a, "state")

        room_before = rooms["persistbot"]
        room_before.get_agent()._attacked.add(("b0", "a0"))
        save_room(room_before)
        rooms.clear()

        restored = load_room("persistbot")
        assert restored is not None
        assert restored.ai
        assert ("b0", "a0") in restored.get_agent()._attacked
        assert restored.state is not None
