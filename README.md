# Dover Patrol

A digital implementation of the H.P. Gibson & Sons naval tactics game (1911; rules from the c.1956 edition, V&A collection record MISC.88-1988). Server-authoritative, two React clients, optional AI opponent.

Hidden-information naval game on an 8×12 board: 40 pieces plus a flag per side, combat resolved by a lookup matrix (not a Stratego-style comparison), passive mine/mine-layer adjacency kills, a persistent declined-attack rule, and per-observer knowledge tracking.

## Source documents

- [docs/DESIGN.md](docs/DESIGN.md) — full implementation design: board geometry, piece roster, combat rules, state model, architecture, AI approach, build order.
- [docs/Dover_patrol_rules.pdf](docs/Dover_patrol_rules.pdf) — transcription of the original rulebook.
- [docs/Dover_patrol_matrix.xls](docs/Dover_patrol_matrix.xls) — combat matrix spreadsheet (Chris Brice, 2003), extracted to [data/combat_matrix.csv](data/combat_matrix.csv).

## Combat matrix data

`data/combat_matrix.csv` is extracted programmatically from the spreadsheet. Rows are attackers, columns are defenders. Piece codes: numeric values `10`–`1` for the numbered ships (Flagship 10 … Patrol Vessel 1), `ML` Mine Layer, `MS` Mine Sweeper, `SS` Submarine, `FB` Flying Boat, `MI` Mine. A cell holds the winner's code, or `both_sunk`, `no_effect`, or `cannot_attack`.

Note: the matrix is authoritative where DESIGN.md §4 is coarser — e.g. Mine Sweeper attacking a Submarine is `no_effect` in the matrix, whereas the design doc's "anything else → attacker sunk" catch-all would have sunk the sweeper.

Passive hazards (mine / mine-layer adjacency kills) and the Flying Boat's harbour-wall and mine-jump moves are not in the matrix; see DESIGN.md §4.

## Planned architecture

```
packages/
  engine/        pure Python, zero I/O — apply(state, action) -> (state, events)
  server/        FastAPI + WebSockets, room registry, redaction
  ai/            belief model + determinized search, imports engine
  client/        Vite + React
```

Build order (DESIGN.md §10): engine first, tested exhaustively against the matrix; then server, client, the 24-piece short game as default mode, then the AI.
