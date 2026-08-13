import { useMemo, useState } from "react";
import { Board, HighlightKind } from "./Board";
import { useGame } from "./useGame";
import type { ActionMsg, PieceView, Side, Square } from "./types";
import { PIECE_NAMES, PIECE_SHORT } from "./types";

export default function App() {
  const [joined, setJoined] = useState<{
    room: string;
    side: Side;
    mode: string;
    ai: boolean;
    recall: number;
  } | null>(null);

  if (!joined) return <JoinScreen onJoin={setJoined} />;
  return <Game {...joined} />;
}

function JoinScreen({
  onJoin,
}: {
  onJoin: (j: {
    room: string;
    side: Side;
    mode: string;
    ai: boolean;
    recall: number;
  }) => void;
}) {
  const [room, setRoom] = useState("harbour");
  const [side, setSide] = useState<Side>("a");
  const [mode, setMode] = useState("capture_base");
  const [opponent, setOpponent] = useState("human");
  const [recall, setRecall] = useState("0.8");
  const ai = opponent === "computer";
  return (
    <div className="join">
      <h1>Dover Patrol</h1>
      <p className="subtitle">or NAVAL TACTICS — The Great Game</p>
      <label>
        Room
        <input value={room} onChange={(e) => setRoom(e.target.value)} />
      </label>
      <label>
        Opponent
        <select value={opponent} onChange={(e) => setOpponent(e.target.value)}>
          <option value="human">Human (two players)</option>
          <option value="computer">Computer</option>
        </select>
      </label>
      {ai ? (
        <label>
          Difficulty
          <select value={recall} onChange={(e) => setRecall(e.target.value)}>
            <option value="0.5">Easy (forgetful admiral)</option>
            <option value="0.8">Normal</option>
            <option value="1.0">Hard (perfect memory)</option>
          </select>
        </label>
      ) : (
        <label>
          Side
          <select value={side} onChange={(e) => setSide(e.target.value as Side)}>
            <option value="a">Blue (south)</option>
            <option value="b">Red (north)</option>
          </select>
        </label>
      )}
      <label>
        Game
        <select value={mode} onChange={(e) => setMode(e.target.value)}>
          <option value="capture_base">Capturing the Base (short, 24 pieces)</option>
          <option value="full">Full game (40 pieces + flag)</option>
        </select>
      </label>
      <button
        disabled={!room.trim()}
        onClick={() =>
          onJoin({
            room: room.trim(),
            side: ai ? "a" : side,
            mode,
            ai,
            recall: parseFloat(recall),
          })
        }
      >
        Join
      </button>
    </div>
  );
}

interface Dialog {
  to: Square;
  options: { label: string; action: ActionMsg }[];
}

function Game({
  room,
  side,
  mode,
  ai,
  recall,
}: {
  room: string;
  side: Side;
  mode: string;
  ai: boolean;
  recall: number;
}) {
  const game = useGame(room, side, mode, ai, recall);
  const [selected, setSelected] = useState<string | null>(null);
  const [swapFrom, setSwapFrom] = useState<number | null>(null);
  const [dialog, setDialog] = useState<Dialog | null>(null);

  const state = game.state;
  const myTurn = state !== null && state.to_move === state.you && state.winner === null;

  const actionsFor = useMemo(() => {
    const map = new Map<string, ActionMsg[]>();
    for (const a of state?.legal_actions ?? []) {
      const pid =
        a.type === "transfer_flag" ? a.from_piece : (a as { piece_id: string }).piece_id;
      map.set(pid, [...(map.get(pid) ?? []), a]);
    }
    return map;
  }, [state]);

  if (game.phase === "setup") {
    return (
      <SetupScreen
        side={side}
        game={game}
        swapFrom={swapFrom}
        setSwapFrom={setSwapFrom}
      />
    );
  }
  if (!state) return <div className="join"><h1>Connecting…</h1></div>;

  const pieces = state.pieces;
  const live = pieces.filter((p) => p.square !== null);
  const sunk = pieces.filter((p) => p.square === null);
  const selectedPiece = live.find((p) => p.id === selected) ?? null;
  const myActions = selected ? actionsFor.get(selected) ?? [] : [];
  const mustRunAground = (state.legal_actions ?? []).every(
    (a) => a.type === "run_aground"
  );

  const highlights = new Map<string, HighlightKind>();
  if (selectedPiece?.square) {
    highlights.set(selectedPiece.square.join(","), "selected");
    for (const a of myActions) {
      if (a.type === "move") highlights.set(a.to.join(","), "move");
      if (a.type === "attack") highlights.set(a.target.join(","), "attack");
      if (a.type === "transfer_flag") {
        const rec = live.find((p) => p.id === a.to_piece);
        if (rec?.square) highlights.set(rec.square.join(","), "transfer");
      }
    }
  }

  function clickCell(col: number, row: number) {
    if (!state || !myTurn || dialog) return;
    const key = `${col},${row}`;
    const clicked = live.find(
      (p) => p.square?.[0] === col && p.square?.[1] === row
    );

    if (selectedPiece && highlights.has(key) && highlights.get(key) !== "selected") {
      const kind = highlights.get(key)!;
      if (kind === "move") {
        const variants = myActions.filter(
          (a): a is Extract<ActionMsg, { type: "move" }> =>
            a.type === "move" && a.to[0] === col && a.to[1] === row
        );
        const withAttack = variants.filter((v) => v.attack);
        if (withAttack.length === 0) {
          game.sendAction(variants[0]);
        } else {
          setDialog({
            to: [col, row],
            options: [
              ...withAttack.map((v) => ({
                label: `Attack ${describeTarget(v.attack!, live)}`,
                action: v,
              })),
              ...variants
                .filter((v) => !v.attack)
                .map((v) => ({ label: "No Attack!", action: v })),
            ],
          });
          return;
        }
      } else if (kind === "attack") {
        const attack = myActions.find(
          (a) => a.type === "attack" && a.target[0] === col && a.target[1] === row
        );
        const decline = myActions.find(
          (a) => a.type === "decline" && a.target[0] === col && a.target[1] === row
        );
        const options = [];
        if (attack) options.push({ label: "Attack!", action: attack });
        if (decline) options.push({ label: "No Attack (bar this pair)", action: decline });
        setDialog({ to: [col, row], options });
        return;
      } else if (kind === "transfer") {
        const transfer = myActions.find(
          (a) =>
            a.type === "transfer_flag" &&
            live.find((p) => p.id === a.to_piece)?.square?.join(",") === key
        );
        if (transfer) game.sendAction(transfer);
      }
      setSelected(null);
      return;
    }

    if (clicked && clicked.owner === state.you && actionsFor.has(clicked.id)) {
      setSelected(clicked.id === selected ? null : clicked.id);
    } else {
      setSelected(null);
    }
  }

  return (
    <div className="game">
      <div className="side-panel">
        <h1>Dover Patrol</h1>
        <div className={`turn turn-${state.to_move}`}>
          {state.winner
            ? state.winner === "draw"
              ? "Draw."
              : `${state.winner === "a" ? "Blue" : "Red"} wins!`
            : myTurn
              ? "Your move"
              : "Opponent's move"}
        </div>
        <div className="you">
          You are {state.you === "a" ? "Blue (south)" : "Red (north)"} · room “{room}”
        </div>
        {mustRunAground && myTurn && (
          <button
            className="danger"
            onClick={() =>
              game.sendAction(state.legal_actions[0])
            }
          >
            Run aground (no way off the base)
          </button>
        )}
        {game.error && <div className="error">{game.error}</div>}
        <Casualties sunk={sunk} you={state.you} />
        <div className="log">
          {game.log.slice().reverse().map((line, i) => (
            <div key={game.log.length - i}>{line}</div>
          ))}
        </div>
      </div>
      <div className="board-wrap">
        <Board
          perspective={state.you}
          pieces={live}
          flags={state.flags}
          highlights={highlights}
          onCellClick={clickCell}
        />
        {dialog && (
          <div className="dialog">
            {dialog.options.map((o, i) => (
              <button
                key={i}
                onClick={() => {
                  game.sendAction(o.action);
                  setDialog(null);
                  setSelected(null);
                }}
              >
                {o.label}
              </button>
            ))}
            <button className="ghost" onClick={() => setDialog(null)}>
              Cancel
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function describeTarget(sq: Square, live: PieceView[]): string {
  const p = live.find((x) => x.square?.[0] === sq[0] && x.square?.[1] === sq[1]);
  const label = p?.type ? PIECE_NAMES[p.type] : "unknown ship";
  return `the ${label} at ${"abcdefgh"[sq[0]]}${sq[1] + 1}`;
}

function Casualties({ sunk, you }: { sunk: PieceView[]; you: Side }) {
  const mine = sunk.filter((p) => p.owner === you);
  const theirs = sunk.filter((p) => p.owner !== you);
  if (sunk.length === 0) return null;
  const list = (ps: PieceView[]) =>
    ps.map((p) => (p.type ? PIECE_SHORT[p.type] : "?")).join(" ");
  return (
    <div className="casualties">
      {theirs.length > 0 && <div>Enemy losses: {list(theirs)}</div>}
      {mine.length > 0 && <div>Your losses: {list(mine)}</div>}
    </div>
  );
}

function SetupScreen({
  side,
  game,
  swapFrom,
  setSwapFrom,
}: {
  side: Side;
  game: ReturnType<typeof useGame>;
  swapFrom: number | null;
  setSwapFrom: (i: number | null) => void;
}) {
  const proposal = game.proposal;
  const pieces: PieceView[] = (proposal ?? []).map((p, i) => ({
    id: `setup-${i}`,
    owner: side,
    square: [p.col, p.row],
    type: p.type,
    carrying: [],
  }));
  const highlights = new Map<string, HighlightKind>();
  if (swapFrom !== null && proposal) {
    const p = proposal[swapFrom];
    highlights.set(`${p.col},${p.row}`, "selected");
  }
  const waiting = game.setupDone[side];

  function clickCell(col: number, row: number) {
    if (!proposal || waiting) return;
    const idx = proposal.findIndex((p) => p.col === col && p.row === row);
    if (swapFrom === null) {
      if (idx >= 0) setSwapFrom(idx);
    } else {
      if (idx >= 0 && idx !== swapFrom) {
        const next = proposal.map((p, i) => {
          if (i === swapFrom) return { ...p, col: proposal[idx].col, row: proposal[idx].row };
          if (i === idx) return { ...p, col: proposal[swapFrom].col, row: proposal[swapFrom].row };
          return p;
        });
        game.setProposal(next);
      }
      setSwapFrom(null);
    }
  }

  return (
    <div className="game">
      <div className="side-panel">
        <h1>Dover Patrol</h1>
        <h2>Arrange your fleet</h2>
        <p>
          Click two of your ships to swap them, or shuffle for a fresh
          arrangement. Your opponent cannot see your placement.
        </p>
        {!waiting ? (
          <>
            <button onClick={game.requestShuffle}>Shuffle</button>
            <button className="primary" disabled={!proposal} onClick={game.submitSetup}>
              Ready
            </button>
          </>
        ) : (
          <p>
            <strong>Waiting for the enemy admiral…</strong>
          </p>
        )}
        {game.error && <div className="error">{game.error}</div>}
        <div className="you">
          Opponent {game.setupDone[side === "a" ? "b" : "a"] ? "is ready" : "still arranging"}.
        </div>
      </div>
      <div className="board-wrap">
        <Board
          perspective={side}
          pieces={pieces}
          highlights={highlights}
          onCellClick={clickCell}
        />
      </div>
    </div>
  );
}
