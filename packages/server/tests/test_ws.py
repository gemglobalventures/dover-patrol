"""WebSocket protocol: join, setup, redacted play."""
from contextlib import contextmanager

import pytest
from fastapi.testclient import TestClient

from dover_server.app import app, rooms


@pytest.fixture(autouse=True)
def clear_rooms():
    rooms.clear()
    yield
    rooms.clear()


def drain_until(ws, msg_type):
    """Read messages until one of msg_type arrives; fail fast on error."""
    for _ in range(30):
        msg = ws.receive_json()
        if msg["type"] == msg_type:
            return msg
        if msg["type"] == "error" and msg_type != "error":
            raise AssertionError(f"unexpected error: {msg['reason']}")
    raise AssertionError(f"no {msg_type} message received")


def do_setup(ws):
    ws.send_json({"type": "random_setup"})
    proposal = drain_until(ws, "setup_proposal")
    ws.send_json({"type": "setup", "placements": proposal["placements"]})


@contextmanager
def game(client, mode="capture_base"):
    with client.websocket_connect(f"/ws/test/a?mode={mode}") as ws_a:
        with client.websocket_connect("/ws/test/b") as ws_b:
            assert drain_until(ws_a, "joined")["player"] == "a"
            assert drain_until(ws_b, "joined")["player"] == "b"
            do_setup(ws_a)
            do_setup(ws_b)
            state_a = drain_until(ws_a, "state")["state"]
            state_b = drain_until(ws_b, "state")["state"]
            yield ws_a, ws_b, state_a, state_b


def whoever_moves(ws_a, ws_b, state_a, state_b):
    """First mover is chosen by lot; return (mover_ws, mover_state, other_ws)."""
    if state_a["to_move"] == "a":
        return ws_a, state_a, ws_b
    return ws_b, state_b, ws_a


def test_join_and_setup_reaches_play():
    with TestClient(app) as client, game(client) as (ws_a, ws_b, state_a, state_b):
        assert state_a["mode"] == "capture_base"
        assert state_a["you"] == "a" and state_b["you"] == "b"
        assert len(state_a["pieces"]) == 48


def test_enemy_types_are_hidden():
    with TestClient(app) as client, game(client) as (_, __, state_a, ___):
        assert all(p["type"] is None for p in state_a["pieces"] if p["owner"] == "b")
        assert all(p["type"] is not None for p in state_a["pieces"] if p["owner"] == "a")


def test_move_broadcasts_events_and_states():
    with TestClient(app) as client, game(client) as (ws_a, ws_b, state_a, state_b):
        mover, mover_state, other = whoever_moves(ws_a, ws_b, state_a, state_b)
        move = next(a for a in mover_state["legal_actions"] if a["type"] == "move")
        mover.send_json(move)
        events_m = drain_until(mover, "events")["events"]
        events_o = drain_until(other, "events")["events"]
        assert any(e["kind"] == "Moved" for e in events_m)
        assert events_m == events_o
        new_m = drain_until(mover, "state")["state"]
        new_o = drain_until(other, "state")["state"]
        assert new_m["to_move"] == new_o["to_move"] != mover_state["to_move"]
        assert new_o["legal_actions"]


def test_acting_out_of_turn_is_rejected():
    with TestClient(app) as client, game(client) as (ws_a, ws_b, state_a, state_b):
        mover, mover_state, other = whoever_moves(ws_a, ws_b, state_a, state_b)
        move = next(a for a in mover_state["legal_actions"] if a["type"] == "move")
        other.send_json(move)
        err = drain_until(other, "error")
        assert "turn" in err["reason"].lower()


def test_bad_setup_is_rejected():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/solo/a?mode=full") as ws_a:
            drain_until(ws_a, "joined")
            ws_a.send_json(
                {"type": "setup", "placements": [{"type": "flagship", "col": 0, "row": 0}]}
            )
            err = drain_until(ws_a, "error")
            assert err["reason"]


def test_reconnect_takes_over_the_seat():
    with TestClient(app) as client:
        with client.websocket_connect("/ws/dup/a?mode=full") as ws1:
            drain_until(ws1, "joined")
            with client.websocket_connect("/ws/dup/a") as ws2:
                joined = drain_until(ws2, "joined")
                assert joined["player"] == "a"
