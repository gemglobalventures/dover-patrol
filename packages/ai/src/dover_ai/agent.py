from __future__ import annotations

import random
from collections import Counter, defaultdict

from dover_engine.actions import Action
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

    def choose(self, state: GameState, moved_ids: set[str]) -> Action:
        if state.to_move is not self.player:
            raise ValueError("not this agent's turn")
        root_actions = legal_actions(state)
        if not root_actions:
            raise ValueError("no legal actions")
        if len(root_actions) == 1:
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
            return root_actions[0]
        top = max(votes.values())
        contenders = [i for i, n in votes.items() if n == top]
        winner = max(contenders, key=lambda i: totals[i])
        return root_actions[winner]
