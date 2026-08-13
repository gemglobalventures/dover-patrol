"""Redaction: the server projects state per recipient and never ships
information a player has not legitimately learned."""
from dover_engine.actions import Attack, Move
from dover_engine.engine import apply_action
from dover_engine.state import FlagLoc, GameState, Piece
from dover_engine.types import Player, PieceType

from dover_server.projection import project

T = PieceType
A, B = Player.A, Player.B


def mk(spec, **kwargs):
    pieces = {}
    for entry in spec:
        pid, ptype, owner, sq = entry[:4]
        carrying = entry[4] if len(entry) > 4 else frozenset()
        pieces[pid] = Piece(id=pid, type=ptype, owner=owner, square=sq, carrying=carrying)
    defaults = dict(
        mode="full",
        pieces=pieces,
        flags={p: FlagLoc(square=(0, 0) if p is A else (7, 11)) for p in Player},
        to_move=A,
        knowledge={A: {}, B: {}},
    )
    defaults.update(kwargs)
    return GameState(**defaults)


def piece_by_id(view, pid):
    return next(p for p in view["pieces"] if p["id"] == pid)


def test_own_pieces_show_types_enemy_hidden():
    state = mk([("a0", T.FLAGSHIP, A, (3, 3)), ("b0", T.DESTROYER, B, (5, 5))])
    view = project(state, A)
    assert piece_by_id(view, "a0")["type"] == "flagship"
    assert piece_by_id(view, "b0")["type"] is None
    assert piece_by_id(view, "b0")["owner"] == "b"


def test_revealed_enemy_type_is_shown():
    state = mk(
        [("a0", T.FLYING_BOAT, A, (3, 3)), ("b0", T.FLAGSHIP, B, (3, 4))]
    )
    state, _ = apply_action(state, Attack("a0", (3, 4)))
    assert project(state, A)["pieces"] and piece_by_id(project(state, A), "b0")["type"] == "flagship"
    assert piece_by_id(project(state, B), "a0")["type"] == "flying_boat"


def test_sunk_enemy_pieces_show_types():
    # Types are shown publicly the moment combat happens, so casualties are open.
    state = mk([("a0", T.BATTLESHIP, A, (3, 3)), ("b0", T.DESTROYER, B, (3, 4))])
    state, _ = apply_action(state, Attack("a0", (3, 4)))
    view_a = project(state, A)
    b0 = piece_by_id(view_a, "b0")
    assert b0["square"] is None and b0["type"] == "destroyer"


def test_legal_actions_only_for_player_to_move():
    state = mk([("a0", T.DESTROYER, A, (3, 3)), ("b0", T.DESTROYER, B, (5, 5))])
    assert project(state, A)["legal_actions"]
    assert project(state, B)["legal_actions"] == []


def test_flags_serialised():
    state = mk(
        [("a0", T.DESTROYER, A, (3, 3), frozenset({B}))],
        flags={A: FlagLoc(square=(0, 0)), B: FlagLoc(carrier="a0")},
    )
    view = project(state, B)
    assert view["flags"]["a"] == {"square": [0, 0], "sweeper_only": False}
    assert view["flags"]["b"] == {"carrier": "a0"}


def test_move_actions_serialised_round_trippable():
    state = mk([("a0", T.DESTROYER, A, (3, 3)), ("b0", T.DESTROYER, B, (3, 5))])
    view = project(state, A)
    kinds = {a["type"] for a in view["legal_actions"]}
    assert "move" in kinds
    sample = next(a for a in view["legal_actions"] if a["type"] == "move")
    assert isinstance(sample["to"], list) and len(sample["to"]) == 2
