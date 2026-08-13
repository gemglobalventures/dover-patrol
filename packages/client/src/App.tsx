import { useEffect, useMemo, useRef, useState } from "react";
import { Board, HighlightKind } from "./Board";
import { Battle, useGame } from "./useGame";
import type { ActionMsg, PieceView, PlacementMsg, Side, Square } from "./types";
import {
  PIECE_INFO,
  PIECE_NAMES,
  PIECE_SHORT,
  PIECE_VALUE,
  UNKNOWN_INFO,
  shipName,
} from "./types";
import { PieceArt } from "./PieceArt";

function MiniCard({
  type,
  owner,
  pieceId,
  faceDown = false,
  sunk = false,
}: {
  type: string | null;
  owner: Side;
  pieceId?: string;
  faceDown?: boolean;
  sunk?: boolean;
}) {
  const shown = faceDown ? null : type;
  const name = faceDown
    ? "?"
    : shipName(type, pieceId) ?? (type ? PIECE_NAMES[type] : "Unknown ship");
  const value = shown ? PIECE_VALUE[shown] : null;
  return (
    <div className={`mini-card${sunk ? " battle-sunk" : ""}`}>
      <div className={`mini-band band-${owner}`}>
        <span>{name}</span>
        <span>{value ?? ""}</span>
      </div>
      <PieceArt type={shown} owner={owner} />
    </div>
  );
}

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
  const [inspect, setInspect] = useState<string | null>(null);
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
    return <SetupScreen side={side} mode={mode} game={game} />;
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
  if (game.lastAction) {
    for (const sq of game.lastAction.from) highlights.set(sq.join(","), "last-from");
    for (const sq of game.lastAction.to) highlights.set(sq.join(","), "last-to");
  }
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
    if (!state || dialog) return;
    const key = `${col},${row}`;
    const clicked = live.find(
      (p) => p.square?.[0] === col && p.square?.[1] === row
    );
    setInspect(clicked ? clicked.id : null);
    if (!myTurn) return;

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
        {(() => {
          const p = inspect ? pieces.find((x) => x.id === inspect) : null;
          return p && p.square ? (
            <PieceCard type={p.type} owner={p.owner} pieceId={p.id} carrying={p.carrying} />
          ) : null;
        })()}
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
        {game.battles.length > 0 && (
          <BattleOverlay
            battle={game.battles[0]}
            pieces={pieces}
            onDone={game.dismissBattle}
          />
        )}
      </div>
    </div>
  );
}

function BattleOverlay({
  battle,
  pieces,
  onDone,
}: {
  battle: Battle;
  pieces: PieceView[];
  onDone: () => void;
}) {
  const [stage, setStage] = useState(0); // 0 clash, 1 reveal, 2 outcome

  useEffect(() => {
    setStage(0);
    const timers = [
      setTimeout(() => setStage(1), 800),
      setTimeout(() => setStage(2), 1800),
      setTimeout(onDone, 6000),
    ];
    return () => timers.forEach(clearTimeout);
  }, [battle, onDone]);

  const find = (id: string) => pieces.find((p) => p.id === id);
  const attacker = find(battle.attackerId);
  const defender = find(battle.defenderId);
  const aType = battle.attackerType ?? attacker?.type ?? null;
  const dType = battle.defenderType ?? defender?.type ?? null;
  const hazard = battle.kind === "hazard";
  const aFate = hazard ? "sunk" : battle.attackerFate;
  const dFate = hazard ? "holds" : battle.defenderFate;

  const outcome = hazard
    ? `${label(aType)} strikes a mine and is blown up!`
    : aFate === "sunk" && dFate === "sunk"
      ? "Both ships are sunk!"
      : dFate === "sunk"
        ? `${label(dType)} is sunk!`
        : aFate === "sunk"
          ? `${label(aType)} is sunk!`
          : "No effect — both remain on station.";

  return (
    <div
      className="battle-backdrop"
      onClick={() => (stage < 2 ? setStage(2) : onDone())}
    >
      <div className={`battle-card stage-${stage}`}>
        <div className="battle-title">
          {hazard ? "MINED!" : "ATTACK!"}
        </div>
        <div className="battle-row">
          <MiniCard
            type={aType}
            owner={attacker?.owner ?? "a"}
            pieceId={battle.attackerId}
            faceDown={stage < 1}
            sunk={stage >= 2 && aFate === "sunk"}
          />
          <span className="battle-vs">{hazard ? "\u2738" : "\u2694"}</span>
          <MiniCard
            type={dType}
            owner={defender?.owner ?? "b"}
            pieceId={battle.defenderId}
            faceDown={stage < 1}
            sunk={stage >= 2 && dFate === "sunk"}
          />
        </div>
        <div className="battle-outcome">{stage >= 2 ? outcome : " "}</div>
      </div>
    </div>
  );
}

function label(type: string | null | undefined): string {
  return type ? PIECE_NAMES[type] : "Unknown ship";
}

function PieceCard({
  type,
  owner,
  pieceId,
  carrying = [],
}: {
  type: string | null;
  owner: Side;
  pieceId?: string;
  carrying?: Side[];
}) {
  const named = shipName(type, pieceId);
  return (
    <div className="piece-card">
      <MiniCard type={type} owner={owner} pieceId={pieceId} />
      {named && type && (
        <div className="piece-card-head">
          <strong>{PIECE_NAMES[type]}</strong>
        </div>
      )}
      <p>{type ? PIECE_INFO[type] : UNKNOWN_INFO}</p>
      {carrying.length > 0 && (
        <p>
          Carrying the {carrying.map((f) => (f === "a" ? "Blue" : "Red")).join(" and ")}{" "}
          flag{carrying.length > 1 ? "s" : ""}.
        </p>
      )}
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
  mode,
  game,
}: {
  side: Side;
  mode: string;
  game: ReturnType<typeof useGame>;
}) {
  const [placed, setPlaced] = useState<PlacementMsg[]>([]);
  const [selectedType, setSelectedType] = useState<string | null>(null);
  const autoFill = useRef(false);
  const waiting = game.setupDone[side];

  // The first server proposal only tells us the roster (tray contents);
  // after an explicit Auto-arrange click it fills the board instead.
  useEffect(() => {
    if (game.proposal && autoFill.current) {
      setPlaced(game.proposal);
      setSelectedType(null);
      autoFill.current = false;
    }
  }, [game.proposal]);

  const roster = useMemo(() => {
    const counts = new Map<string, number>();
    for (const p of game.proposal ?? []) {
      counts.set(p.type, (counts.get(p.type) ?? 0) + 1);
    }
    return counts;
  }, [game.proposal]);

  const trayCounts = useMemo(() => {
    const counts = new Map(roster);
    for (const p of placed) {
      counts.set(p.type, (counts.get(p.type) ?? 0) - 1);
    }
    return counts;
  }, [roster, placed]);

  const trayTotal = [...trayCounts.values()].reduce((a, b) => a + b, 0);

  const backRows = mode === "full" ? 5 : 3;
  const zoneRows = side === "a"
    ? Array.from({ length: backRows }, (_, i) => i)
    : Array.from({ length: backRows }, (_, i) => 11 - i);
  const oddRow = side === "a" ? backRows : 11 - backRows;
  const base: [number, number] = side === "a" ? [0, 0] : [7, 11];
  const oddRowUsed = placed.some((p) => p.row === oddRow);

  function placeable(col: number, row: number): boolean {
    if (col === base[0] && row === base[1]) return false;
    if (placed.some((p) => p.col === col && p.row === row)) return false;
    if (zoneRows.includes(row)) return true;
    return row === oddRow && !oddRowUsed;
  }

  const pieces: PieceView[] = placed.map((p, i) => ({
    id: `setup-${i}`,
    owner: side,
    square: [p.col, p.row],
    type: p.type,
    carrying: [],
  }));

  const highlights = new Map<string, HighlightKind>();
  if (selectedType && !waiting) {
    for (const row of [...zoneRows, oddRow]) {
      for (let col = 0; col < 8; col++) {
        if (placeable(col, row)) highlights.set(`${col},${row}`, "move");
      }
    }
  }

  function clickCell(col: number, row: number) {
    if (waiting) return;
    const idx = placed.findIndex((p) => p.col === col && p.row === row);
    if (idx >= 0) {
      // Pick a placed ship back up into the tray.
      setPlaced(placed.filter((_, i) => i !== idx));
      setSelectedType(placed[idx].type);
      return;
    }
    if (selectedType && (trayCounts.get(selectedType) ?? 0) > 0 && placeable(col, row)) {
      setPlaced([...placed, { type: selectedType, col, row }]);
      if ((trayCounts.get(selectedType) ?? 0) <= 1) setSelectedType(null);
    }
  }

  return (
    <div className="game">
      <div className="side-panel">
        <h1>Dover Patrol</h1>
        <h2>Arrange your fleet</h2>
        <p>
          Pick a ship from the tray, then click a square on your side —
          one piece may stand on the row beyond your back rows. Clicking a
          placed ship returns it to the tray. Your opponent cannot see your
          placement.
        </p>
        {!waiting ? (
          <>
            <button
              onClick={() => {
                autoFill.current = true;
                game.requestShuffle();
              }}
            >
              Auto-arrange
            </button>
            <button onClick={() => setPlaced([])} disabled={placed.length === 0}>
              Clear
            </button>
            <button
              className="primary"
              disabled={trayTotal !== 0}
              onClick={() => game.submitSetup(placed)}
            >
              Ready{trayTotal > 0 ? ` (${trayTotal} to place)` : ""}
            </button>
            <div className="tray">
              {[...trayCounts.entries()]
                .filter(([, n]) => n > 0)
                .map(([type, n]) => (
                  <button
                    key={type}
                    className={`tray-chip chip-${side}${
                      selectedType === type ? " tray-selected" : ""
                    }`}
                    title={PIECE_NAMES[type]}
                    onClick={() =>
                      setSelectedType(selectedType === type ? null : type)
                    }
                  >
                    {PIECE_SHORT[type]}
                    {n > 1 ? ` ×${n}` : ""}
                  </button>
                ))}
            </div>
          </>
        ) : (
          <p>
            <strong>Waiting for the enemy admiral…</strong>
          </p>
        )}
        {game.error && <div className="error">{game.error}</div>}
        {selectedType && <PieceCard type={selectedType} owner={side} />}
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
