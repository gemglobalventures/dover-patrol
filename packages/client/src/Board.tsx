import type { FlagView, PieceView, Side, Square } from "./types";
import { PIECE_SHORT } from "./types";

export type HighlightKind = "move" | "attack" | "transfer" | "selected";

interface BoardProps {
  perspective: Side;
  pieces: PieceView[];
  flags?: Partial<Record<Side, FlagView>>;
  highlights: Map<string, HighlightKind>;
  onCellClick: (col: number, row: number) => void;
}

const COLS = 8;
const ROWS = 12;
const BASES: Record<Side, Square> = { a: [0, 0], b: [7, 11] };

// Harbour wall edges (must match dover_engine.board): every 2x2 corner
// harbour boundary is walled except the entrance on the extreme left column.
const WALL_EDGES: [Square, Square][] = [
  [[1, 1], [1, 2]],
  [[1, 0], [2, 0]],
  [[1, 1], [2, 1]],
  [[6, 10], [6, 9]],
  [[6, 11], [5, 11]],
  [[6, 10], [5, 10]],
];

function wallClasses(col: number, row: number): string {
  let cls = "";
  for (const [p, q] of WALL_EDGES) {
    for (const [from, to] of [
      [p, q],
      [q, p],
    ] as [Square, Square][]) {
      if (from[0] !== col || from[1] !== row) continue;
      if (to[0] === col + 1) cls += " wall-e";
      if (to[0] === col - 1) cls += " wall-w";
      if (to[1] === row + 1) cls += " wall-n";
      if (to[1] === row - 1) cls += " wall-s";
    }
  }
  return cls;
}

export function Board({ perspective, pieces, flags, highlights, onCellClick }: BoardProps) {
  const byiSquare = new Map<string, PieceView>();
  for (const p of pieces) {
    if (p.square) byiSquare.set(`${p.square[0]},${p.square[1]}`, p);
  }
  const looseFlags = new Map<string, Side>();
  for (const [owner, loc] of Object.entries(flags ?? {})) {
    if (loc?.square) looseFlags.set(`${loc.square[0]},${loc.square[1]}`, owner as Side);
  }

  // Own side at the bottom of the screen.
  const rowOrder =
    perspective === "a"
      ? Array.from({ length: ROWS }, (_, i) => ROWS - 1 - i)
      : Array.from({ length: ROWS }, (_, i) => i);
  const colOrder =
    perspective === "a"
      ? Array.from({ length: COLS }, (_, i) => i)
      : Array.from({ length: COLS }, (_, i) => COLS - 1 - i);

  return (
    <div className="board">
      {rowOrder.map((row) => (
        <div className="board-row" key={row}>
          {colOrder.map((col) => {
            const key = `${col},${row}`;
            const piece = byiSquare.get(key);
            const hl = highlights.get(key);
            const isBase = (["a", "b"] as Side[]).find(
              (s) => BASES[s][0] === col && BASES[s][1] === row
            );
            const flagHere = looseFlags.get(key);
            return (
              <div
                key={key}
                className={`cell${wallClasses(col, row)}${hl ? ` hl-${hl}` : ""}${
                  isBase ? ` base base-${isBase}` : ""
                }`}
                onClick={() => onCellClick(col, row)}
                title={`${"abcdefgh"[col]}${row + 1}`}
              >
                {isBase && !piece && <span className="anchor">⚓</span>}
                {flagHere && <span className={`flag flag-${flagHere}`}>⚑</span>}
                {piece && (
                  <span className={`chip chip-${piece.owner}`}>
                    {piece.type ? PIECE_SHORT[piece.type] : "?"}
                    {piece.carrying.map((f) => (
                      <span key={f} className={`flag flag-${f}`}>
                        ⚑
                      </span>
                    ))}
                  </span>
                )}
              </div>
            );
          })}
        </div>
      ))}
    </div>
  );
}
