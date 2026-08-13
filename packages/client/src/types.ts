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
