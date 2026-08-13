from __future__ import annotations

from dover_engine.board import BASE
from dover_engine.state import GameState
from dover_engine.types import VALUE, Player, PieceType

T = PieceType

# Hand-weighted worth of the auxiliaries — a Submarine is worth far more
# than its missing numeric value suggests.
AUX_VALUE = {
    T.SUBMARINE: 8.0,
    T.MINE_SWEEPER: 4.0,
    T.MINE_LAYER: 3.0,
    T.FLYING_BOAT: 3.0,
    T.MINE: 2.0,
}

WIN = 1000.0


def piece_worth(ptype: PieceType) -> float:
    value = VALUE[ptype]
    return float(value) if value is not None else AUX_VALUE[ptype]


def _advance(player: Player, row: int) -> int:
    return row if player is Player.A else 11 - row


def evaluate(state: GameState, ai: Player) -> float:
    """Static evaluation from `ai`'s point of view."""
    if state.winner is not None:
        if state.winner == "draw":
            return 0.0
        return WIN if state.winner is ai else -WIN

    score = 0.0
    best_dist = {Player.A: 99, Player.B: 99}
    for piece in state.pieces.values():
        if piece.square is None:
            continue
        sign = 1.0 if piece.owner is ai else -1.0
        score += sign * piece_worth(piece.type)
        if piece.type is not T.MINE:
            score += sign * 0.03 * _advance(piece.owner, piece.square[1])
            enemy_base = BASE[piece.owner.opponent]
            dist = abs(piece.square[0] - enemy_base[0]) + abs(
                piece.square[1] - enemy_base[1]
            )
            best_dist[piece.owner] = min(best_dist[piece.owner], dist)

    if state.mode == "capture_base":
        # Pressure on the enemy base is the whole game.
        score += 0.12 * (best_dist[ai.opponent] - best_dist[ai])

    for flag_owner, loc in state.flags.items():
        holder = None if loc.carrier is None else state.pieces[loc.carrier].owner
        if flag_owner is ai:
            if holder is ai.opponent:
                score -= 6.0
                carrier_sq = state.pieces[loc.carrier].square
                dist_home = abs(carrier_sq[0] - BASE[ai.opponent][0]) + abs(
                    carrier_sq[1] - BASE[ai.opponent][1]
                )
                score -= 0.1 * (22 - dist_home)
        else:
            if holder is ai:
                score += 6.0
                carrier_sq = state.pieces[loc.carrier].square
                dist_home = abs(carrier_sq[0] - BASE[ai][0]) + abs(
                    carrier_sq[1] - BASE[ai][1]
                )
                score += 0.1 * (22 - dist_home)
    return score
