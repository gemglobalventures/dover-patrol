"""Belief model: distributions over unknown enemy pieces, constrained by the
roster, public casualties, the AI's knowledge map, and the fact that a piece
that has moved cannot be a Mine."""
import random
from collections import Counter

from dover_engine.state import SHORT_ROSTER, FlagLoc, GameState, Piece
from dover_engine.types import Player, PieceType

from dover_ai.beliefs import remembered_knowledge, sample_assignment, determinize

T = PieceType
A, B = Player.A, Player.B


def mk_state(spec, knowledge_a=None, mode="capture_base"):
    pieces = {
        pid: Piece(id=pid, type=t, owner=owner, square=sq)
        for pid, t, owner, sq in spec
    }
    return GameState(
        mode=mode,
        pieces=pieces,
        flags={},
        to_move=A,
        knowledge={A: knowledge_a or {}, B: {}},
    )


def short_enemy_fleet():
    """A full short-game enemy fleet for B, plus one A scout piece."""
    types = [t for t, n in SHORT_ROSTER.items() for _ in range(n)]
    spec = [(f"b{i}", t, B, (i % 8, 8 + i // 8)) for i, t in enumerate(types)]
    spec.append(("a0", T.DESTROYER, A, (0, 0)))
    return spec


def test_sample_respects_roster_and_knowledge():
    spec = short_enemy_fleet()
    state = mk_state(spec, knowledge_a={"b0": state_type(spec, "b0")})
    rng = random.Random(1)
    for _ in range(30):
        assignment = sample_assignment(state, A, moved_ids=set(), rng=rng,
                                       knowledge=state.knowledge[A])
        # Known piece keeps its known type; all others get a type.
        assert assignment["b0"] is state_type(spec, "b0")
        counts = Counter(assignment.values())
        assert counts == Counter(
            {t: n for t, n in SHORT_ROSTER.items() if n}
        )


def state_type(spec, pid):
    return next(t for p, t, *_ in spec if p == pid)


def test_moved_pieces_are_never_mines():
    spec = short_enemy_fleet()
    state = mk_state(spec)
    moved = {"b0", "b1", "b2", "b3", "b4"}
    rng = random.Random(2)
    for _ in range(50):
        assignment = sample_assignment(state, A, moved_ids=moved, rng=rng,
                                       knowledge={})
        for pid in moved:
            assert assignment[pid] is not T.MINE


def test_sunk_casualties_leave_the_pool():
    spec = short_enemy_fleet()
    # Sink both enemy submarines (public casualties).
    spec = [
        (pid, t, o, None if t is T.SUBMARINE and o is B else sq)
        for pid, t, o, sq in spec
    ]
    state = mk_state(spec)
    rng = random.Random(3)
    for _ in range(30):
        assignment = sample_assignment(state, A, moved_ids=set(), rng=rng,
                                       knowledge={})
        assert Counter(assignment.values())[T.SUBMARINE] == 0


def test_recall_forgets_a_fraction_of_knowledge():
    knowledge = {f"b{i}": T.DESTROYER for i in range(100)}
    full = remembered_knowledge(knowledge, recall=1.0, seed=7)
    none = remembered_knowledge(knowledge, recall=0.0, seed=7)
    half = remembered_knowledge(knowledge, recall=0.5, seed=7)
    assert len(full) == 100
    assert len(none) == 0
    assert 25 < len(half) < 75
    # Forgetting is stable across turns for the same seed.
    assert remembered_knowledge(knowledge, recall=0.5, seed=7) == half


def test_determinize_builds_consistent_full_info_state():
    spec = short_enemy_fleet()
    state = mk_state(spec)
    rng = random.Random(4)
    assignment = sample_assignment(state, A, moved_ids=set(), rng=rng, knowledge={})
    sample = determinize(state, assignment)
    for pid, ptype in assignment.items():
        assert sample.pieces[pid].type is ptype
    # Own pieces and geometry untouched.
    assert sample.pieces["a0"].type is T.DESTROYER
    assert all(
        sample.pieces[pid].square == state.pieces[pid].square
        for pid in state.pieces
    )
