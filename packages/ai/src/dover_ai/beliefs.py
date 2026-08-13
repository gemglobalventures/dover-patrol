from __future__ import annotations

import hashlib
import random
from collections import Counter
from dataclasses import replace

from dover_engine.state import FULL_ROSTER, SHORT_ROSTER, GameState
from dover_engine.types import Player, PieceType

T = PieceType


def remembered_knowledge(knowledge: dict, recall: float, seed: int) -> dict:
    """Difficulty works by degrading memory, not search: each revealed piece
    is remembered with probability `recall`. The forgetting is a stable
    per-piece coin so a forgotten piece stays forgotten across turns."""
    if recall >= 1.0:
        return dict(knowledge)
    kept = {}
    for pid, ptype in knowledge.items():
        digest = hashlib.sha256(f"{seed}:{pid}".encode()).digest()
        coin = int.from_bytes(digest[:8], "big") / 2**64
        if coin < recall:
            kept[pid] = ptype
    return kept


def sample_assignment(state: GameState, ai: Player, *, moved_ids: set[str],
                      rng: random.Random, knowledge: dict) -> dict[str, PieceType]:
    """One complete assignment of types to enemy pieces, consistent with the
    roster, public casualties, the (possibly degraded) knowledge map, and the
    rule that a piece that has moved cannot be a Mine. Mines are biased
    toward unmoved pieces deep in enemy territory."""
    enemy = ai.opponent
    roster = FULL_ROSTER if state.mode == "full" else SHORT_ROSTER
    pool = Counter({t: n for t, n in roster.items() if n})

    assignment: dict[str, T] = {}
    hidden: list = []
    for piece in state.pieces.values():
        if piece.owner is not enemy:
            continue
        if piece.square is None:
            pool[piece.type] -= 1  # casualties are public
        elif piece.id in knowledge:
            assignment[piece.id] = knowledge[piece.id]
            pool[knowledge[piece.id]] -= 1
        else:
            hidden.append(piece)
    assert all(n >= 0 for n in pool.values()), "knowledge inconsistent with roster"

    # The hidden pieces are a draw without replacement from the remaining
    # pool — the pool may be larger than the number of hidden pieces when
    # the AI still remembers revealed ships that are alive elsewhere.
    rest = [t for t, n in pool.items() for _ in range(n)]
    rng.shuffle(rest)
    draw, extra = rest[: len(hidden)], rest[len(hidden):]

    # A piece that has moved cannot be a Mine; swap surplus mines back out.
    eligible = [p for p in hidden if p.id not in moved_ids]
    spare_non_mines = [t for t in extra if t is not T.MINE]
    while draw.count(T.MINE) > len(eligible) and spare_non_mines:
        draw[draw.index(T.MINE)] = spare_non_mines.pop()

    # Mines go to unmoved pieces, weighted toward the owner's back rows.
    others = [t for t in draw if t is not T.MINE]
    for _ in range(draw.count(T.MINE)):
        weights = [
            1 + (p.square[1] if enemy is Player.B else 11 - p.square[1])
            for p in eligible
        ]
        pick = rng.choices(range(len(eligible)), weights=weights)[0]
        assignment[eligible.pop(pick).id] = T.MINE

    rng.shuffle(others)
    for piece in hidden:
        if piece.id not in assignment:
            assignment[piece.id] = others.pop()
    return assignment


def determinize(state: GameState, assignment: dict[str, PieceType]) -> GameState:
    """A full-information state where every enemy piece has its sampled type."""
    pieces = dict(state.pieces)
    for pid, ptype in assignment.items():
        if pieces[pid].type is not ptype:
            pieces[pid] = replace(pieces[pid], type=ptype)
    return replace(state, pieces=pieces)
