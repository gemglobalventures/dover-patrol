"""The agent must always return a legal action, grab clearly free material,
and find a win-in-one."""
import random
import time

from dover_engine.actions import Attack, Move
from dover_engine.board import BASE, COLS
from dover_engine.engine import legal_actions
from dover_engine.state import SHORT_ROSTER, FlagLoc, GameState, Piece, new_game
from dover_engine.types import Player, PieceType

from dover_ai.agent import Agent

T = PieceType
A, B = Player.A, Player.B


def mk_state(spec, *, mode="full", to_move=B, knowledge_b=None):
    pieces = {
        pid: Piece(id=pid, type=t, owner=owner, square=sq)
        for pid, t, owner, sq in spec
    }
    flags = (
        {p: FlagLoc(square=BASE[p]) for p in Player} if mode == "full" else {}
    )
    return GameState(
        mode=mode,
        pieces=pieces,
        flags=flags,
        to_move=to_move,
        knowledge={A: {}, B: knowledge_b or {}},
    )


def short_game_start():
    def placements(player):
        types = [t for t, n in SHORT_ROSTER.items() for _ in range(n)]
        rows = range(3) if player is A else range(11, 8, -1)
        squares = [
            (c, r) for r in rows for c in range(COLS) if (c, r) != BASE[player]
        ]
        squares.append((4, 3) if player is A else (4, 8))
        return list(zip(types, squares))

    return new_game("capture_base", placements(A), placements(B), first_to_move=B)


def test_returns_a_legal_action_from_the_opening():
    state = short_game_start()
    agent = Agent(B, samples=4, depth=2, seed=1)
    action = agent.choose(state, moved_ids=set())
    assert action in legal_actions(state)


def test_takes_a_free_capture():
    # B's Battleship (7) stands beside a revealed enemy Destroyer (4) with no
    # counterplay on the board; sinking it is plainly best.
    state = mk_state(
        [
            ("b0", T.BATTLESHIP, B, (3, 4)),
            ("a0", T.DESTROYER, A, (3, 3)),
            ("a1", T.PATROL_VESSEL, A, (7, 0)),
        ],
        knowledge_b={"a0": T.DESTROYER},
    )
    agent = Agent(B, samples=6, depth=2, seed=2)
    action = agent.choose(state, moved_ids={"a0", "a1"})
    assert action == Attack("b0", (3, 3))


def test_finds_win_in_one():
    # Occupying the enemy base wins the short game outright.
    state = mk_state(
        [
            ("b0", T.DESTROYER, B, (0, 1)),
            ("a0", T.PATROL_VESSEL, A, (7, 5)),
        ],
        mode="capture_base",
    )
    agent = Agent(B, samples=4, depth=2, seed=3)
    action = agent.choose(state, moved_ids=set())
    assert action == Move("b0", (0, 0))


def test_opening_move_is_fast_enough():
    state = short_game_start()
    agent = Agent(B, samples=8, depth=2, seed=4)
    start = time.monotonic()
    agent.choose(state, moved_ids=set())
    assert time.monotonic() - start < 5.0


def test_ai_vs_ai_short_game_runs_clean():
    from dover_engine.engine import apply_action
    from dover_engine.events import Moved

    state = short_game_start()
    agents = {
        A: Agent(A, samples=2, depth=1, seed=10),
        B: Agent(B, samples=2, depth=1, recall=0.6, seed=11),
    }
    moved: set[str] = set()
    for _ in range(200):
        if state.winner is not None:
            break
        action = agents[state.to_move].choose(state, moved_ids=moved)
        state, events = apply_action(state, action)
        moved |= {e.piece_id for e in events if isinstance(e, Moved)}
    assert state.winner is not None or _ == 199


def test_agent_does_not_repeat_futile_attack():
    """A no-effect attack (e.g. submarine vs submarine) must not be repeated:
    combat is deterministic, so a pair that both survived is futile forever.
    With recall=0 the bot cannot remember the reveal, so only its own memory
    of having tried the attack can stop the loop."""
    from dover_engine.engine import apply_action

    state = mk_state(
        [
            ("b0", T.SUBMARINE, B, (3, 4)),
            ("a0", T.SUBMARINE, A, (3, 3)),
            ("b1", T.PATROL_VESSEL, B, (6, 8)),
            ("a1", T.PATROL_VESSEL, A, (0, 5)),
        ],
        mode="full",
        to_move=B,
    )
    agent = Agent(B, samples=6, depth=2, recall=0.0, seed=9)
    first = agent.choose(state, moved_ids={"a0", "a1"})
    assert first == Attack("b0", (3, 3)), "the forgetful bot should take the bait once"
    state, _ = apply_action(state, first)  # no effect: both submarines remain
    state, _ = apply_action(state, Move("a1", (0, 6)))
    second = agent.choose(state, moved_ids={"a0", "a1"})
    assert second != first
