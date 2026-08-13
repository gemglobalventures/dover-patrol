export type Side = "a" | "b";
export type Square = [number, number];

export interface PieceView {
  id: string;
  owner: Side;
  square: Square | null;
  type: string | null;
  carrying: Side[];
}

export interface FlagView {
  carrier?: string;
  square?: Square;
  sweeper_only?: boolean;
}

export type ActionMsg =
  | { type: "move"; piece_id: string; to: Square; attack?: Square }
  | { type: "attack"; piece_id: string; target: Square }
  | { type: "decline"; piece_id: string; target: Square }
  | { type: "transfer_flag"; from_piece: string; to_piece: string }
  | { type: "run_aground"; piece_id: string };

export interface ClientState {
  mode: "full" | "capture_base";
  you: Side;
  to_move: Side;
  winner: Side | "draw" | null;
  pieces: PieceView[];
  flags: Partial<Record<Side, FlagView>>;
  legal_actions: ActionMsg[];
}

export interface PlacementMsg {
  type: string;
  col: number;
  row: number;
}

export interface GameEvent {
  kind: string;
  [key: string]: unknown;
}

export type ServerMsg =
  | { type: "joined"; room: string; player: Side; mode: string; phase: string }
  | {
      type: "room_status";
      phase: string;
      connected: Record<Side, boolean>;
      setup_done: Record<Side, boolean>;
    }
  | { type: "setup_proposal"; placements: PlacementMsg[] }
  | { type: "state"; state: ClientState }
  | { type: "events"; events: GameEvent[] }
  | { type: "error"; reason: string };

export const PIECE_NAMES: Record<string, string> = {
  flagship: "Flagship",
  vice_flagship: "Vice-Flagship",
  battle_squadron: "Battle Squadron",
  battleship: "Battleship",
  battle_cruiser: "Battle Cruiser",
  light_cruiser: "Light Cruiser",
  destroyer: "Destroyer",
  auxiliary_cruiser: "Auxiliary Cruiser",
  motor_torpedo_boat: "Motor Torpedo Boat",
  patrol_vessel: "Patrol Vessel",
  mine_layer: "Mine Layer",
  mine_sweeper: "Mine Sweeper",
  submarine: "Submarine",
  flying_boat: "Flying Boat",
  mine: "Mine",
};

export const PIECE_SHORT: Record<string, string> = {
  flagship: "FS·10",
  vice_flagship: "VF·9",
  battle_squadron: "BS·8",
  battleship: "BB·7",
  battle_cruiser: "BC·6",
  light_cruiser: "LC·5",
  destroyer: "DD·4",
  auxiliary_cruiser: "AC·3",
  motor_torpedo_boat: "TB·2",
  patrol_vessel: "PV·1",
  mine_layer: "ML",
  mine_sweeper: "MS",
  submarine: "SS",
  flying_boat: "FB",
  mine: "MI",
};

export function describeEvent(e: GameEvent, pieces: PieceView[]): string {
  const name = (id: unknown) => {
    const p = pieces.find((x) => x.id === id);
    const label = p?.type ? PIECE_NAMES[p.type] : "Unknown ship";
    return `${p?.owner === "a" ? "Blue" : "Red"} ${label}`;
  };
  const side = (s: unknown) => (s === "a" ? "Blue" : "Red");
  switch (e.kind) {
    case "Moved":
      return `${name(e.piece_id)} moves to ${sq(e.to_square)}`;
    case "WallCrossed":
      return `${name(e.piece_id)} declares a Harbour Wall crossing — it is the Flying Boat!`;
    case "PassiveKill":
      return `${name(e.victim_id)} is blown up alongside ${name(e.hazard_id)}`;
    case "Combat":
      return `Combat: ${side(pieceOwner(e.attacker_id, pieces))} ${
        PIECE_NAMES[String(e.attacker_type)]
      } attacks ${PIECE_NAMES[String(e.defender_type)]} — attacker ${e.attacker_fate}, defender ${e.defender_fate}`;
    case "Declined":
      return `${name(e.piece_id)} declines to attack ${name(e.target_id)}`;
    case "FlagCaptured":
      return `${side(e.flag)} flag captured by ${name(e.by_piece)}!`;
    case "FlagPickedUp":
      return `${side(e.flag)} flag picked up by ${name(e.by_piece)}`;
    case "FlagDropped":
      return `${side(e.flag)} flag dropped at ${sq(e.square)}${
        e.sweeper_only ? " — only a Mine Sweeper can recover it" : ""
      }`;
    case "FlagTransferred":
      return `${side(e.flag)} flag transferred to ${name(e.to_piece)}`;
    case "FlagDeposited":
      return `${side(e.flag)} flag deposited on ${side(e.on_base_of)}'s base`;
    case "RanAground":
      return `${name(e.piece_id)} runs aground!`;
    case "GameOver":
      return e.winner === "draw" ? "The game is a draw." : `${side(e.winner)} wins!`;
    default:
      return e.kind;
  }
}

function pieceOwner(id: unknown, pieces: PieceView[]): Side | undefined {
  return pieces.find((p) => p.id === id)?.owner;
}

function sq(v: unknown): string {
  const [c, r] = v as Square;
  return `${"abcdefgh"[c]}${r + 1}`;
}

export const PIECE_INFO: Record<string, string> = {
  flagship:
    "Value 10, the most powerful ship afloat: sinks any lower-valued ship it attacks or that attacks it. Only another Flagship (mutual destruction), a Submarine or a Mine can send it down.",
  vice_flagship:
    "Value 9. Sinks everything below it; lost only to the Flagship, an equal, a Submarine or a Mine.",
  battle_squadron:
    "Value 8. A heavy unit — beaten only by values 9 and 10, Submarines and Mines.",
  battleship:
    "Value 7. Sinks value 6 and below; beaten by 8 and above, Submarines and Mines.",
  battle_cruiser:
    "Value 6. Sinks value 5 and below; beaten by 7 and above, Submarines and Mines.",
  light_cruiser:
    "Value 5. Sinks value 4 and below; beaten by 6 and above, Submarines and Mines.",
  destroyer:
    "Value 4 — the workhorse. The only ship that can sink a Mine Layer, and one of the two that can bring down the Flying Boat. Sinks value 3 and below; beaten by 5 and above, Submarines and Mines.",
  auxiliary_cruiser:
    "Value 3. Sinks value 2 and below; beaten by 4 and above, Submarines and Mines.",
  motor_torpedo_boat:
    "Value 2, but deadly out of proportion: it sinks Submarines and brings down the Flying Boat. Sinks the Patrol Vessel; beaten by value 3 and above, and by Mines.",
  patrol_vessel:
    "Value 1, the humblest ship — it sinks nothing but the enemy's Patrol Vessel (mutually). Useful for scouting attacks that force the enemy to show a piece.",
  mine_layer:
    "No value; may move but never attack. Any enemy ship that comes alongside is blown up — except Mine Sweepers, Submarines, Flying Boats, Destroyers and other Mine Layers. Only a Destroyer can sink it.",
  mine_sweeper:
    "No value. The only piece that can destroy a Mine — and the only one that can recover a Flag lost to one. Against anything else its attacks achieve nothing (or sink it: every numbered ship beats it). Keep it guarded.",
  submarine:
    "No value, but sinks every numbered ship — except the Motor Torpedo Boat (2), which sinks it. No effect against Mine Layers, Flying Boats or other Submarines; blown up by Mines. Worth far more than its blank face suggests.",
  flying_boat:
    "The scout. Attacking with it (or being attacked) reveals the enemy piece and nothing sinks — except against Motor Torpedo Boats (2) and Destroyers (4), which bring it down. The only piece that may cross the Harbour Wall (the crossing must be declared) and it may hop two squares over a Mine, as in draughts.",
  mine:
    "Never moves — ever. Any enemy ship that moves alongside is blown up, except Mine Sweepers, Mine Layers and Flying Boats. Only a Mine Sweeper can destroy it. A Flag lost to a Mine can be recovered only by a Mine Sweeper.",
};

export const UNKNOWN_INFO =
  "An enemy ship of unknown class. Its identity is shown only when combat touches it — or you can probe it with a cheap attack and pay the price of the reveal.";

export const PIECE_VALUE: Record<string, number | null> = {
  flagship: 10,
  vice_flagship: 9,
  battle_squadron: 8,
  battleship: 7,
  battle_cruiser: 6,
  light_cruiser: 5,
  destroyer: 4,
  auxiliary_cruiser: 3,
  motor_torpedo_boat: 2,
  patrol_vessel: 1,
  mine_layer: null,
  mine_sweeper: null,
  submarine: null,
  flying_boat: null,
  mine: null,
};

// Individual ship names from the original card pieces.
export const SHIP_NAMES: Record<string, string[]> = {
  battleship: ["HMS Surrey", "HMS Lancashire"],
  battle_cruiser: ["HMS Birmingham", "HMS Manchester", "HMS Glasgow"],
  light_cruiser: ["HMS Vixen", "HMS Greyhound", "HMS Lion", "HMS Viper"],
  destroyer: ["HMS Seagull", "HMS Eagle", "HMS Albatross", "HMS Kingfisher"],
  auxiliary_cruiser: ["HMS Mosquito", "HMS Hornet", "HMS Gnat", "HMS Bee"],
  submarine: ["Submarine E1", "Submarine E2", "Submarine E3"],
};

export function shipName(type: string | null, pieceId?: string): string | null {
  if (!type || !pieceId) return null;
  const names = SHIP_NAMES[type];
  if (!names) return null;
  const n = parseInt(pieceId.replace(/\D/g, ""), 10);
  return Number.isNaN(n) ? null : names[n % names.length];
}
