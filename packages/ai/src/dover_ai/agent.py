from __future__ import annotations

import random
from collections import Counter, defaultdict

from dover_engine.actions import Action, Attack, Move
from dover_engine.engine import legal_actions
from dover_engine.state import GameState
from dover_engine.types import Player

from .beliefs import determinize, remembered_knowledge, sample_assignment
from .search import best_root_values


class Agent:
    """Determinized-search opponent (DESIGN.md §9): sample complete enemy
    fleets consistent with the belief state, search each sample, and vote on
    the root move. Difficulty degrades memory (`recall`), not search."""

    def __init__(self, player: Player, *, samples: int = 8, depth: int = 2,
                 recall: float = 1.0, seed: int = 0):
        self.player = player
        self.samples = samples
        self.depth = depth
        self.recall = recall
        self.seed = seed
        self.rng = random.Random(seed)
        # Pairs this agent has already attacked. Combat is deterministic, so
        # if both ships survived the exchange, the matchup is futile forever —
        # even (especially) when low recall makes the bot forget the reveal.
        self._attacked: set[tuple[str, str]] = set()

    def _attack_pair(self, state: GameState, action: Action) -> tuple[str, str] | None:
        target = (
            action.target_square
            if isinstance(action, Attack)
            else action.attack if isinstance(action, Move) else None
        )
        if target is None:
            return None
        defender = state.piece_at(target)
        if defender is None:
            return None
        attacker_id = action.piece_id
        return (attacker_id, defender.id)

    def _is_futile(self, state: GameState, action: Action) -> bool:
        pair = self._attack_pair(state, action)
        if pair is None or pair not in self._attacked:
            return False
        attacker = state.pieces.get(pair[0])
        defender = state.pieces.get(pair[1])
        return (
            attacker is not None
            and defender is not None
            and attacker.square is not None
            and defender.square is not None
        )

    def choose(self, state: GameState, moved_ids: set[str]) -> Action:
        if state.to_move is not self.player:
            raise ValueError("not this agent's turn")
        root_actions = legal_actions(state)
        if not root_actions:
            raise ValueError("no legal actions")
        useful = [a for a in root_actions if not self._is_futile(state, a)]
        if useful:
            root_actions = useful
        if len(root_actions) == 1:
            self._record(state, root_actions[0])
            return root_actions[0]

        knowledge = remembered_knowledge(
            state.knowledge[self.player], self.recall, self.seed
        )
        votes: Counter[int] = Counter()
        totals: dict[int, float] = defaultdict(float)
        for _ in range(self.samples):
            assignment = sample_assignment(
                state, self.player, moved_ids=moved_ids,
                rng=self.rng, knowledge=knowledge,
            )
            sample = determinize(state, assignment)
            values = best_root_values(sample, root_actions, self.depth, self.player)
            if not values:
                continue
            best = max(values, key=lambda i: values[i])
            votes[best] += 1
            for i, v in values.items():
                totals[i] += v

        if not votes:
            self._record(state, root_actions[0])
            return root_actions[0]
        top = max(votes.values())
        contenders = [i for i, n in votes.items() if n == top]
        winner = max(contenders, key=lambda i: totals[i])
        chosen = root_actions[winner]
        self._record(state, chosen)
        return chosen

    def _record(self, state: GameState, action: Action) -> None:
        pair = self._attack_pair(state, action)
        if pair is not None:
            self._attacked.add(pair)
