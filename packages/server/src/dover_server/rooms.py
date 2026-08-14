from __future__ import annotations

import random
from dataclasses import dataclass, field

from dover_engine.board import BASE, COLS
from dover_engine.state import (
    FULL_ROSTER,
    SHORT_ROSTER,
    GameState,
    SetupError,
    new_game,
    validate_placements,
)
from dover_engine.types import Player, PieceType

Placements = list[tuple[PieceType, tuple[int, int]]]


def setup_zone(mode: str, player: Player) -> tuple[list, int]:
    back_rows = 5 if mode == "full" else 3
    rows = range(back_rows) if player is Player.A else range(11, 11 - back_rows, -1)
    squares = [
        (col, row)
        for row in rows
        for col in range(COLS)
        if (col, row) != BASE[player]
    ]
    odd_row = back_rows if player is Player.A else 11 - back_rows
    return squares, odd_row


def random_placements(mode: str, player: Player, rng: random.Random) -> Placements:
    roster = FULL_ROSTER if mode == "full" else SHORT_ROSTER
    types = [t for t, n in roster.items() for _ in range(n)]
    rng.shuffle(types)
    squares, odd_row = setup_zone(mode, player)
    squares = squares + [(rng.randrange(COLS), odd_row)]
    return list(zip(types, squares))


def placements_to_json(placements: Placements) -> list[dict]:
    return [
        {"type": t.value, "col": sq[0], "row": sq[1]} for t, sq in placements
    ]


def placements_from_json(data: list[dict]) -> Placements:
    return [(PieceType(p["type"]), (p["col"], p["row"])) for p in data]


@dataclass
class Room:
    room_id: str
    mode: str
    sockets: dict = field(default_factory=lambda: {Player.A: None, Player.B: None})
    placements: dict = field(default_factory=lambda: {Player.A: None, Player.B: None})
    state: GameState | None = None
    rng: random.Random = field(default_factory=random.Random)
    ai: bool = False  # the computer always sails as Player B
    ai_params: dict = field(default_factory=dict)
    agent: object | None = None
    moved_ids: set = field(default_factory=set)

    def get_agent(self):
        if self.agent is None:
            from dover_ai.agent import Agent

            self.agent = Agent(
                Player.B,
                samples=int(self.ai_params.get("samples", 12)),
                depth=int(self.ai_params.get("depth", 2)),
                recall=float(self.ai_params.get("recall", 1.0)),
                seed=self.rng.randrange(2**31),
            )
        return self.agent

    @property
    def phase(self) -> str:
        if self.state is None:
            return "setup"
        return "over" if self.state.winner is not None else "play"

    def reset(self) -> None:
        """Abandon any running game and return the room to the setup phase."""
        self.state = None
        self.placements = {Player.A: None, Player.B: None}
        self.moved_ids = set()
        self.agent = None  # a fresh admiral with a fresh memory

    def submit_setup(self, player: Player, placements: Placements) -> None:
        if self.state is not None:
            raise SetupError("the game has already started")
        validate_placements(self.mode, player, placements)
        self.placements[player] = placements
        if all(self.placements[p] is not None for p in Player):
            self.state = new_game(
                self.mode,
                self.placements[Player.A],
                self.placements[Player.B],
                first_to_move=self.rng.choice([Player.A, Player.B]),
            )
