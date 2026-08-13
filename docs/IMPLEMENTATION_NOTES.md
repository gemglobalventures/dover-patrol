# Implementation notes — rulings and deviations

Where the three sources disagree, precedence is: **rulebook PDF > combat
matrix spreadsheet > DESIGN.md**. Everything below is enforced by tests in
`packages/engine/tests/`.

## Corrections to DESIGN.md

1. **Combat winners do not advance.** The rulebook: "the lower valued is
   'sunk' (i.e., removed), the higher remaining on the same space from which
   it attacked." DESIGN.md §4's `Fate.ADVANCES` never occurs; the engine's
   `Fate` is just `SUNK | HOLDS`. This matters everywhere — captures of the
   flag square, mine sweeps, everything resolves with the survivor staying put.
2. **Mine Sweeper attacking a Submarine is "no effect"**, per the matrix,
   not "attacker sunk" as DESIGN.md §4's catch-all row implies.
3. **Attack declarations are simultaneous with the move into contact.**
   "An ATTACK is effected by a player moving a piece on to a space next to an
   opponent's piece ... at the same time saying 'Attack!' (or 'No Attack!')."
   There is no turn gap in which the defender could escape. `Move` therefore
   carries an optional `attack` target. A standing piece may still attack an
   adjacent enemy in lieu of moving (this is what the declined-pair rule
   regulates). The standalone `Decline` action is kept for protocol
   compatibility but is never forced on a player.

## Corrections to the spreadsheet

4. **MTB attacking a Submarine sinks it.** The spreadsheet cell says the
   Submarine wins, but the rulebook is explicit and direction-independent:
   "...and MOTOR TORPEDO BOATS (2), which sink them." Treated as a
   transcription error; `data/combat_matrix.csv` preserves the original cell
   and the test suite applies the correction.

## House rulings (rulebook silent or contradictory)

5. **Harbour geometry.** The rulebook gives no dimensions. Implemented as a
   2×2 region in each player's left-hand corner (A: cols 0–1 × rows 0–1,
   base (0,0); B mirrored at 180°, base (7,11)), walled except a single
   entrance gap on the extreme left-hand column — chosen because the Hints
   warn that an enemy "on the extreme edge ... can move down into the
   Harbour".
6. **Destroyer is exempt from the Mine Layer's passive adjacency kill**
   (DESIGN.md's noted ruling): it is the only piece that can sink a Mine
   Layer, which would be impossible if adjacency destroyed it first.
7. **Declined pairs bar both directions.** The rulebook sentence is
   genuinely ambiguous about whether the decliner or the declined-against is
   barred; the unordered-pair model (DESIGN.md §5) bars both until either
   piece moves, which is the conservative superset of both readings.
8. **Implicit declines.** Moving into contact with several enemy pieces and
   attacking one (or none) declines every other newly created attackable
   pair — that is the moment the player "refrain[s] from attacking when in a
   position to do so".
9. **Short-game compulsion applies to the on-move declaration only.**
   Standing pairs left in place by no-effect results (e.g. Flying Boat
   probes) do not force endless re-attacks — that literal reading would
   deadlock the game in a compulsory no-op loop.
10. **A flag dropped by a mine kill may only be reached by a Mine Sweeper**;
    other pieces may not even enter that square while the flag lies there
    (the rulebook only says who can *recover* it; forbidding entry avoids a
    piece standing uselessly on an unrecoverable flag).
11. **A flag dropped when a Mine Layer's adjacency kills the carrier** is an
    ordinary loose flag (the sweeper-only rule is written for mines).
12. **Run-aground generalises to both bases.** Any ship standing on a Base
    at its owner's turn must sail off; if it cannot, it is removed and any
    carried flags stay on that base square. The rulebook describes this for
    the capturer on the enemy base; the same logic covers a ship that has
    just deposited a flag on its own base.
13. **Flag transfers move every flag the giver carries** (the
    both-flags-on-one-ship case is possible after capturing with your own
    flag aboard).
14. **Hemming in an opponent in the short game wins outright** — the full
    game's own-flag-at-home requirement has no analogue without flags.
