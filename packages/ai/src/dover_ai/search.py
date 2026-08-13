from __future__ import annotations

from dover_engine.actions import Attack, Move
from dover_engine.engine import IllegalAction, apply_action, legal_actions
from dover_engine.state import GameState
from dover_engine.types import Player

from .evaluate import WIN, evaluate

BRANCH_CAP = 28  # below the root, consider only the most promising actions


def _order_key(state: GameState, action) -> float:
    """Cheap move ordering: attacks first, then forward progress."""
    if isinstance(action, Attack):
        return -100.0
    if isinstance(action, Move):
        if action.attack is not None:
            return -90.0
        piece = state.pieces[action.piece_id]
        forward = action.to[1] - piece.square[1]
        return -(forward if piece.owner is Player.A else -forward)
    return 0.0


def alphabeta(state: GameState, depth: int, alpha: float, beta: float, ai: Player) -> float:
    if state.winner is not None:
        base = evaluate(state, ai)
        # Prefer quicker wins (more depth remaining) and later losses.
        if base > 0:
            return base + depth
        if base < 0:
            return base - depth
        return 0.0
    if depth == 0:
        return evaluate(state, ai)

    actions = sorted(legal_actions(state), key=lambda a: _order_key(state, a))
    actions = actions[:BRANCH_CAP]
    maximizing = state.to_move is ai
    best = -WIN * 2 if maximizing else WIN * 2
    for action in actions:
        child, _ = apply_action(state, action)
        value = alphabeta(child, depth - 1, alpha, beta, ai)
        if maximizing:
            best = max(best, value)
            alpha = max(alpha, best)
        else:
            best = min(best, value)
            beta = min(beta, best)
        if beta <= alpha:
            break
    return best


def best_root_values(sample: GameState, root_actions, depth: int, ai: Player) -> dict:
    """Value of each root action within one determinized sample. Actions that
    are illegal under the sampled types are simply skipped."""
    values = {}
    alpha, beta = -WIN * 2, WIN * 2
    for i, action in enumerate(root_actions):
        try:
            child, _ = apply_action(sample, action)
        except IllegalAction:
            continue
        value = alphabeta(child, depth - 1, alpha, beta, ai)
        values[i] = value
        alpha = max(alpha, value)
    return values
