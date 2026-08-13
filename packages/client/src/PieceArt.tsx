import type { Side } from "./types";

/* Silhouettes in the style of the original H.P. Gibson card pieces: a dark
   navy profile on a white card body, with a masthead pennant added in the
   owner's colour so sides stay readable on screen. */

const INK = "#1b2a3d";
const CARD = "#f5f2e8";
const SHADOW = "#b9c3c9";
const PENNANT: Record<Side, string> = { a: "#2b6ca3", b: "#a33132" };

const WL = 36; // waterline
const CX = 80; // centre

interface ShipSpec {
  len: number;
  superW: number;
  superH: number;
  funnels: number;
  foreTurrets: number;
  aftTurrets: number;
  kingposts?: boolean;
}

const WARSHIPS: Record<string, ShipSpec> = {
  flagship: { len: 122, superW: 48, superH: 9, funnels: 3, foreTurrets: 2, aftTurrets: 2 },
  vice_flagship: { len: 114, superW: 44, superH: 8, funnels: 3, foreTurrets: 2, aftTurrets: 1 },
  battleship: { len: 100, superW: 38, superH: 8, funnels: 2, foreTurrets: 1, aftTurrets: 1 },
  battle_cruiser: { len: 104, superW: 30, superH: 7, funnels: 3, foreTurrets: 1, aftTurrets: 1 },
  light_cruiser: { len: 88, superW: 26, superH: 6, funnels: 2, foreTurrets: 1, aftTurrets: 0 },
  destroyer: { len: 72, superW: 18, superH: 5, funnels: 2, foreTurrets: 1, aftTurrets: 0 },
  auxiliary_cruiser: { len: 84, superW: 22, superH: 7, funnels: 1, foreTurrets: 0, aftTurrets: 0, kingposts: true },
  motor_torpedo_boat: { len: 46, superW: 10, superH: 4, funnels: 0, foreTurrets: 0, aftTurrets: 0 },
  patrol_vessel: { len: 52, superW: 12, superH: 6, funnels: 1, foreTurrets: 0, aftTurrets: 0 },
  mine_layer: { len: 62, superW: 16, superH: 6, funnels: 1, foreTurrets: 0, aftTurrets: 0 },
  mine_sweeper: { len: 60, superW: 14, superH: 6, funnels: 1, foreTurrets: 0, aftTurrets: 0 },
};

function Warship({
  spec,
  owner,
  scale = 1,
  dx = 0,
  dy = 0,
  pennant = true,
}: {
  spec: ShipSpec;
  owner: Side;
  scale?: number;
  dx?: number;
  dy?: number;
  pennant?: boolean;
}) {
  const { len, superW, superH, funnels, foreTurrets, aftTurrets, kingposts } = spec;
  const half = len / 2;
  const deck = 30;
  const superY = deck - superH;
  const parts: JSX.Element[] = [];

  parts.push(
    <path
      key="hull"
      d={`M ${CX - half} 30 L ${CX + half - 9} 30 Q ${CX + half} 31 ${CX + half} 34 L ${CX + half - 3} ${WL + 2} L ${CX - half + 3} ${WL + 2} L ${CX - half} 33 Z`}
      fill={INK}
    />
  );
  parts.push(
    <rect key="super" x={CX - superW / 2} y={superY} width={superW} height={superH} fill={INK} />
  );
  for (let i = 0; i < funnels; i++) {
    const x = CX - ((funnels - 1) * 9) / 2 + i * 9 - 2.5;
    parts.push(<rect key={`f${i}`} x={x} y={superY - 9} width={5} height={9} fill={INK} />);
  }
  for (let i = 0; i < foreTurrets; i++) {
    const x = CX + superW / 2 + 6 + i * 11;
    parts.push(
      <g key={`ft${i}`}>
        <rect x={x - 4} y={deck - 4} width={8} height={4} rx={1.5} fill={INK} />
        <line x1={x} y1={deck - 3} x2={x + 9} y2={deck - 5.5} stroke={INK} strokeWidth={1.4} />
      </g>
    );
  }
  for (let i = 0; i < aftTurrets; i++) {
    const x = CX - superW / 2 - 8 - i * 11;
    parts.push(
      <g key={`at${i}`}>
        <rect x={x - 4} y={deck - 4} width={8} height={4} rx={1.5} fill={INK} />
        <line x1={x} y1={deck - 3} x2={x - 9} y2={deck - 5.5} stroke={INK} strokeWidth={1.4} />
      </g>
    );
  }
  const mastX = CX + superW / 2 + 2;
  parts.push(
    <g key="masts">
      <line x1={mastX} y1={deck} x2={mastX} y2={11} stroke={INK} strokeWidth={1.2} />
      <line x1={CX - superW / 2 - 2} y1={deck} x2={CX - superW / 2 - 2} y2={16} stroke={INK} strokeWidth={1} />
      <line x1={mastX} y1={14} x2={CX - superW / 2 - 2} y2={18} stroke={INK} strokeWidth={0.6} />
      {pennant && <path d={`M ${mastX} 11 L ${mastX + 11} 13.5 L ${mastX} 16 Z`} fill={PENNANT[owner]} />}
    </g>
  );
  if (kingposts) {
    parts.push(
      <g key="king">
        <line x1={CX + half - 16} y1={deck} x2={CX + half - 16} y2={15} stroke={INK} strokeWidth={1.2} />
        <line x1={CX - half + 14} y1={deck} x2={CX - half + 14} y2={15} stroke={INK} strokeWidth={1.2} />
      </g>
    );
  }
  return (
    <g transform={`translate(${dx} ${dy}) translate(${CX * (1 - scale)} ${WL * (1 - scale)}) scale(${scale})`}>
      {parts}
    </g>
  );
}

function BattleSquadron({ owner }: { owner: Side }) {
  // The original card shows the squadron as stacked ships.
  const spec: ShipSpec = { len: 108, superW: 40, superH: 8, funnels: 2, foreTurrets: 2, aftTurrets: 1 };
  return (
    <g>
      <Warship spec={spec} owner={owner} scale={0.62} dx={-16} dy={-15} pennant={false} />
      <Warship spec={spec} owner={owner} scale={0.62} dx={16} dy={-7.5} pennant={false} />
      <Warship spec={spec} owner={owner} scale={0.62} dx={0} dy={0} />
    </g>
  );
}

function Extras({ type }: { type: string }) {
  if (type === "mine_layer") {
    return (
      <g>
        {[0, 1, 2].map((i) => (
          <circle key={i} cx={CX - 30 + i * 8} cy={27} r={3} fill={INK} />
        ))}
        <line x1={CX - 34} y1={30} x2={CX - 8} y2={30} stroke={INK} strokeWidth={1} />
      </g>
    );
  }
  if (type === "mine_sweeper") {
    return (
      <g>
        <line x1={CX - 26} y1={28} x2={CX - 50} y2={42} stroke={INK} strokeWidth={1.4} />
        <circle cx={CX - 50} cy={42} r={2.5} fill={INK} />
      </g>
    );
  }
  if (type === "motor_torpedo_boat") {
    // Bow spray for the fast boat.
    return (
      <path
        d={`M ${CX + 24} ${WL + 1} Q ${CX + 30} ${WL - 4} ${CX + 34} ${WL + 1}`}
        stroke={SHADOW}
        strokeWidth={1.6}
        fill="none"
      />
    );
  }
  return null;
}

function Submarine({ owner }: { owner: Side }) {
  return (
    <g>
      <path
        d={`M ${CX - 54} 38 Q ${CX - 58} 36.5 ${CX - 54} 35 L ${CX + 48} 34 Q ${CX + 58} 36 ${CX + 48} 40 L ${CX - 50} 41 Z`}
        fill={INK}
      />
      <path d={`M ${CX - 6} 35 L ${CX - 4} 26 L ${CX + 8} 26 L ${CX + 10} 35 Z`} fill={INK} />
      <line x1={CX} y1={26} x2={CX} y2={17} stroke={INK} strokeWidth={1.4} />
      <line x1={CX + 6} y1={26} x2={CX + 6} y2={20} stroke={INK} strokeWidth={1.2} />
      <path d={`M ${CX} 17 L ${CX + 9} 19 L ${CX} 21 Z`} fill={PENNANT[owner]} />
    </g>
  );
}

function FlyingBoat({ owner }: { owner: Side }) {
  const y = 24;
  return (
    <g>
      <path
        d={`M ${CX - 30} ${y} L ${CX + 26} ${y - 2} L ${CX + 23} ${y + 4} Q ${CX} ${y + 9} ${CX - 22} ${y + 5} Z`}
        fill={INK}
      />
      <line x1={CX - 18} y1={y - 9} x2={CX + 18} y2={y - 9} stroke={INK} strokeWidth={2.6} />
      <line x1={CX - 22} y1={y - 1} x2={CX + 22} y2={y - 1} stroke={INK} strokeWidth={2.6} />
      <line x1={CX - 13} y1={y - 9} x2={CX - 13} y2={y - 1} stroke={INK} strokeWidth={1} />
      <line x1={CX + 13} y1={y - 9} x2={CX + 13} y2={y - 1} stroke={INK} strokeWidth={1} />
      <path d={`M ${CX - 30} ${y} L ${CX - 39} ${y - 8} L ${CX - 34} ${y + 1} Z`} fill={INK} />
      <rect x={CX + 6} y={y + 4} width={9} height={3} rx={1.5} fill={INK} />
      <path d={`M ${CX + 26} ${y - 2} L ${CX + 35} ${y - 0.5} L ${CX + 26} ${y + 1} Z`} fill={PENNANT[owner]} />
    </g>
  );
}

function MineTrio() {
  // The original Mine card pictures a row of moored mines.
  return (
    <g>
      {[
        { x: CX - 26, r: 7 },
        { x: CX + 2, r: 9 },
        { x: CX + 30, r: 6 },
      ].map(({ x, r }, i) => (
        <g key={i}>
          <circle cx={x} cy={WL - r * 0.3} r={r} fill={INK} />
          {[-70, -30, 20, 65].map((deg) => {
            const rad = ((deg - 90) * Math.PI) / 180;
            return (
              <line
                key={deg}
                x1={x + Math.cos(rad) * r}
                y1={WL - r * 0.3 + Math.sin(rad) * r}
                x2={x + Math.cos(rad) * (r + 4)}
                y2={WL - r * 0.3 + Math.sin(rad) * (r + 4)}
                stroke={INK}
                strokeWidth={1.8}
              />
            );
          })}
          <line x1={x} y1={WL + r * 0.5} x2={x} y2={WL + 8} stroke={INK} strokeWidth={1} strokeDasharray="2 1.5" />
        </g>
      ))}
    </g>
  );
}

export function PieceArt({ type, owner }: { type: string | null; owner: Side }) {
  return (
    <svg viewBox="0 0 160 46" className="piece-art" role="img">
      <rect x={0} y={0} width={160} height={46} fill={CARD} />
      {type !== null && type !== "flying_boat" && (
        <line x1={8} y1={WL + 5.5} x2={152} y2={WL + 5.5} stroke={SHADOW} strokeWidth={1} />
      )}
      {type === null ? (
        <text x={CX} y={32} textAnchor="middle" fontSize={26} fontWeight="bold" fill={INK}>
          ?
        </text>
      ) : type === "submarine" ? (
        <Submarine owner={owner} />
      ) : type === "flying_boat" ? (
        <FlyingBoat owner={owner} />
      ) : type === "mine" ? (
        <MineTrio />
      ) : type === "battle_squadron" ? (
        <BattleSquadron owner={owner} />
      ) : (
        <>
          <Warship spec={WARSHIPS[type]} owner={owner} />
          <Extras type={type} />
        </>
      )}
    </svg>
  );
}
