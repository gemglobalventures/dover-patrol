# Dover Patrol — Implementation Design

A digital implementation of the H.P. Gibson & Sons naval tactics game (1911, rules here taken from the c.1956 edition transcribed in the V&A collection record MISC.88-1988). Server-authoritative, two React clients, optional AI opponent.

---

## 1. Why this isn't just Stratego

Three properties of the original ruleset drive the whole architecture, and all three are places where a Stratego-derived implementation will be wrong:

1. **Combat is a lookup table, not a comparison.** A Submarine sinks a Flagship (value 10) but is sunk by a Motor Torpedo Boat (value 2). Several matchups resolve to "nothing happens, both pieces remain in place" — an outcome that does not fit a `winner: A | B | both` return type.
2. **Declining an attack is a persistent game state.** Attacking is optional. If you decline while back-to-back, your opponent may not attack that piece with that piece until one of them moves.
3. **Reveals are permanent and per-observer.** Pieces revealed in combat stay on the board. Knowledge is asymmetric and must be tracked per player, not as a global flag on the piece.

---

## 2. Board geometry

The V&A record gives 96 squares, with harbour and base at opposing corners and each player's harbour on their left.

96 = **8 columns × 12 rows**, and this is confirmed by the setup rule: pieces are arranged on the nearest 5 rows, with one odd piece "dispossessed of a space by the Flag" going on any square of the 6th row. Five rows of 8 = 40 spaces; 40 pieces plus a flag = 41; hence exactly one piece displaced to row 6. Any other width breaks that arithmetic.

```
cols 0..7, rows 0..11
Player A (south): setup rows 0-4, plus one piece on row 5
Player B (north): setup rows 11-7, plus one piece on row 6
```

Harbour: a walled region in each player's left-hand corner, containing the Base square. The wall is impassable to everything except the Flying Boat, with a single entrance gap.

Movement is one square, orthogonal only, onto an unoccupied square — including while carrying a flag. No diagonals anywhere in the game.

---

## 3. Piece roster (per side: 40 + flag)

| Type | Value | Qty | In 24-piece short game |
|---|---|---|---|
| Flagship | 10 | 1 | — |
| Vice-Flagship | 9 | 1 | 1 |
| Battle Squadron | 8 | 1 | 1 |
| Battleship | 7 | 2 | 1 |
| Battle Cruiser | 6 | 3 | 2 |
| Light Cruiser | 5 | 4 | 2 |
| Destroyer | 4 | 4 | 2 |
| Auxiliary Cruiser | 3 | 4 | 1 |
| Motor Torpedo Boat | 2 | 5 | 4 |
| Patrol Vessel | 1 | 5 | 3 |
| Mine Layer | — | 1 | 1 |
| Mine Sweeper | — | 2 | 1 |
| Submarine | — | 3 | 2 |
| Flying Boat | — | 1 | 1 |
| Mine | — | 3 | 2 |

The short game ("Capturing the Base") is in the original rulebook: 24 pieces on three back rows, no flag, **attacks are compulsory** when in position, and the winner is whoever first occupies the opponent's base. Ship this as a game mode — it's the best onboarding path and it isn't a house rule.

---

## 4. Combat matrix

Resolution returns a fate for each participant independently:

```python
class Fate(Enum):
    SUNK = "sunk"          # removed from board
    ADVANCES = "advances"  # survives, moves into defender's square
    HOLDS = "holds"        # survives, stays where it is
```

Attacker advancing only happens when the defender is SUNK and the attacker survives.

### Numbered vs numbered
Higher value sinks lower. Equal values: both sunk.

### Special cases (these override the numeric rule)

| Attacker | Defender | Result |
|---|---|---|
| Submarine | any numbered except MTB(2) | defender SUNK |
| Submarine | Motor Torpedo Boat (2) | attacker SUNK |
| Submarine | Mine Layer | nothing (both HOLD) |
| Submarine | Submarine | nothing |
| Submarine | Mine | attacker SUNK |
| Submarine | Mine Sweeper | defender SUNK |
| Motor Torpedo Boat (2) | Submarine | defender SUNK |
| Motor Torpedo Boat (2) | Flying Boat | defender SUNK |
| Destroyer (4) | Flying Boat | defender SUNK |
| Destroyer (4) | Mine Layer | defender SUNK |
| Mine Sweeper | Mine | defender SUNK, attacker survives |
| Mine Sweeper | Mine Sweeper / Mine Layer / Flying Boat | nothing |
| Mine Sweeper | anything else | attacker SUNK |
| Flying Boat | anything except MTB(2) / Destroyer(4) | nothing |
| Flying Boat | Mine | nothing |
| Mine Layer | anything | **illegal** — Mine Layer may never attack |
| any other piece | Mine Sweeper | defender SUNK |
| any other piece | Mine | attacker SUNK, mine remains |
| any other piece | Mine Layer | attacker SUNK, layer remains |

### Passive hazards — resolved on movement, not on attack

Mines and Mine Layers destroy on *adjacency*, whether or not an attack is declared:

- Moving into a square orthogonally adjacent to an **enemy Mine** destroys the moving piece automatically, and the mine is revealed. Exempt: Mine Sweeper, Mine Layer, Flying Boat.
- Moving adjacent to an **enemy Mine Layer** destroys the moving piece automatically. Exempt: Mine Sweeper, Submarine, Flying Boat, another Mine Layer, and Destroyer (see below).

Mines never move and may never be touched — the rulebook explicitly forbids feinting a mine move as unsporting. Enforce that by making mines immovable in the engine rather than trusting the UI.

**Known ambiguity:** the rules say a Mine Layer can be sunk only by a Destroyer, but also that any piece entering adjacency is blown up. Taken together the Destroyer must be exempt from the passive kill, otherwise nothing could ever sink a layer. Implement it that way and note it as a house ruling in the UI.

### The Flying Boat
- Only piece the Harbour Wall does not block; crossing it **must be declared**, which forces a partial reveal to the opponent.
- May jump two squares orthogonally over a Mine, as a draughts capture, to reach the square beyond.
- Brought down only by MTB(2) or Destroyer(4). Everything else is a no-op both ways, which also makes it a free scout: attack a piece purely to learn its value.

---

## 5. The declined-attack rule

An attack requires both pieces orthogonally adjacent ("back to back"). The attacker declares `ATTACK` or `NO ATTACK`; either way the turn passes.

If A declines against B, **A's piece may not attack B's piece** until one of them moves. Model as:

```python
declined: set[frozenset[PieceId]]   # unordered pairs
```

Clear any pair containing a piece when that piece moves or is removed. This is not cosmetic — it lets a player park a strong piece next to a suspected mine and refuse engagement, which is a real defensive line.

Also: a player may not ask an opponent to declare a piece's value without a legitimate attack. So `revealValue` must never exist as a client-callable action.

---

## 6. State model

```python
@dataclass(frozen=True)
class Piece:
    id: PieceId
    type: PieceType
    owner: PlayerId
    square: Square | None      # None = sunk
    carrying_flag: PlayerId | None

@dataclass(frozen=True)
class GameState:
    pieces: dict[PieceId, Piece]
    flags: dict[PlayerId, FlagLocation]   # ON_BASE | CARRIED_BY(pid) | LOOSE_AT(square)
    to_move: PlayerId
    declined: frozenset[frozenset[PieceId]]
    knowledge: dict[PlayerId, dict[PieceId, PieceType]]
    mode: Literal["full", "capture_base"]
    winner: PlayerId | None
```

`knowledge[X][pid]` = what player X has learned about piece `pid`. Populated on combat reveals and on declared Harbour Wall crossings. The AI reads its own knowledge map and nothing else — this is what keeps it honest, and it's why the belief model in §9 falls out naturally.

### Redaction

The server projects state per recipient. Never send full state and filter client-side.

```python
def project(state: GameState, viewer: PlayerId) -> ClientState:
    # own pieces: full type
    # enemy pieces: {id, square, owner} + type only if in knowledge[viewer]
    # flags: location visible; carrier identity visible (it's on the board)
```

---

## 7. Flag rules (full game only)

- Flag sits on its Base and **cannot** be moved by its owner pre-emptively.
- Captured by an enemy piece moving onto the Base. The capturing ship must move off the Base on the next turn; if it's blocked, it "runs aground" (removed) and the flag stays.
- A flag-carrying ship **may not attack** the ship carrying the other flag.
- Equal-value attack on a carrier: both sink, flag drops to the carrier's square, claimable by the first piece of either side to reach it.
- Carrier blown up by a mine: flag drops and is recoverable **only by a Mine Sweeper**.
- Flag may be transferred to an adjacent friendly piece; this costs a move and must happen on the turn immediately after getting into position, or not at all.
- **Win: both flags on your own base.** You cannot deposit the enemy flag unless your own flag is in your possession and on your side of the board.
- Stalemate win: immobilising your opponent wins only if your own flag is on your base — otherwise the game is a draw.

---

## 8. Architecture

```
packages/
  engine/        pure Python, zero I/O — apply(state, action) -> (state, events)
  server/        FastAPI + WebSockets, room registry, redaction
  ai/            belief model + determinized search, imports engine
  client/        Vite + React
```

**Build the engine first and alone.** It's a pure function with no transport, no async, no framework. Both the server and the AI depend on it, and it's the only part you can meaningfully unit-test against the 1956 rulebook. Every matchup in §4 becomes a test case; the passive-hazard and declined-attack rules get their own suites.

Vite over Remix here — no SEO surface, no SSR story, and the app is a single stateful screen.

### Protocol

Client sends intents only; the server validates and never trusts a proposed outcome.

```
→ {type: "move", piece_id, to}
→ {type: "attack", piece_id, target_square}
→ {type: "decline", piece_id, target_square}
→ {type: "transfer_flag", from_piece, to_piece}
→ {type: "setup", placements: [{piece_id, square}]}

← {type: "state", state: <redacted>}
← {type: "event", event: {kind: "combat", square, attacker: <type>, defender: <type>, outcome}}
← {type: "error", reason}
```

Send `state` and `event` separately — the client needs the event stream to animate reveals and to render the combat log, and reconstructing "what just happened" by diffing two redacted states is miserable.

Rooms live in memory keyed by room ID. Reach for Supabase only if you want resumable games across disconnects; for a game with your daughter on the same network, you don't.

---

## 9. AI opponent

Minimax alone doesn't apply — this is imperfect information. Use **determinization**:

1. **Belief state.** For each unknown enemy piece, hold a distribution over remaining unrevealed types, constrained by the roster in §3 (you know exactly what 40 pieces they started with).

2. **Evidence updates.**
   - It moved → it is not a Mine.
   - It has never moved and sits in the back rows → mine probability up.
   - It sank a value-6 → it is 7+, or a Submarine.
   - It was sunk by a Motor Torpedo Boat without a value being shown → Submarine or Flying Boat.
   - It declined an attack → weak evidence of low value or of protecting something.
   - It crossed the Harbour Wall → it is the Flying Boat (forced reveal).

3. **Search.** Sample ~50 complete assignments consistent with the beliefs, run 3–4 ply minimax on each with a positional eval, and vote on the root move. Cheap, parallelisable, and known to work well on Stratego-family games.

4. **Evaluation terms:** material (numeric values, with auxiliaries hand-weighted — a Submarine is worth far more than its zero value suggests), distance to enemy base, flag safety, and an information term rewarding moves that reveal little.

5. **Difficulty: degrade memory, not search depth.** A bot that forgets 40% of previously revealed pieces plays like a distracted human and is beatable in a satisfying way. A bot with a shallower search just plays badly, which reads as broken rather than easy. Expose it as a `recall` parameter in [0,1].

---

## 10. Build order

1. Engine: state, movement, combat matrix, passive hazards. Test against §4 exhaustively.
2. Engine: declined-attack tracking, flag lifecycle, win conditions.
3. Server: rooms, redaction, two-client hot game over WebSocket.
4. Client: board, setup phase, attack/decline dialog, combat log.
5. Ship the 24-piece short game as the default mode.
6. AI: random-legal baseline, then belief model, then determinized search.

Step 5 before step 6. The short game is playable against a human immediately and is the version worth playing first anyway.
