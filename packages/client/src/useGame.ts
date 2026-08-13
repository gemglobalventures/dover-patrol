import { useCallback, useEffect, useRef, useState } from "react";
import type {
  ActionMsg,
  ClientState,
  GameEvent,
  PlacementMsg,
  ServerMsg,
  Side,
} from "./types";
import { describeEvent } from "./types";

export interface Battle {
  kind: "combat" | "hazard";
  attackerId: string;
  defenderId: string;
  attackerType?: string;
  defenderType?: string;
  attackerFate?: string;
  defenderFate?: string;
}

export interface GameConnection {
  phase: string;
  state: ClientState | null;
  proposal: PlacementMsg[] | null;
  setProposal: (p: PlacementMsg[]) => void;
  log: string[];
  error: string | null;
  setupDone: Record<Side, boolean>;
  connected: boolean;
  battles: Battle[];
  dismissBattle: () => void;
  requestShuffle: () => void;
  submitSetup: (placements: PlacementMsg[]) => void;
  sendAction: (a: ActionMsg) => void;
}

export function useGame(
  room: string,
  side: Side,
  mode: string,
  ai = false,
  recall = 1.0
): GameConnection {
  const wsRef = useRef<WebSocket | null>(null);
  const [phase, setPhase] = useState("setup");
  const [state, setState] = useState<ClientState | null>(null);
  const [proposal, setProposal] = useState<PlacementMsg[] | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [battles, setBattles] = useState<Battle[]>([]);
  const [setupDone, setSetupDone] = useState<Record<Side, boolean>>({
    a: false,
    b: false,
  });
  const stateRef = useRef<ClientState | null>(null);

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const params = new URLSearchParams({ mode });
    if (ai) {
      params.set("ai", "1");
      params.set("recall", String(recall));
    }
    const ws = new WebSocket(
      `${proto}://${location.host}/ws/${encodeURIComponent(room)}/${side}?${params}`
    );
    wsRef.current = ws;
    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (raw) => {
      const msg: ServerMsg = JSON.parse(raw.data);
      switch (msg.type) {
        case "joined":
          setPhase(msg.phase);
          if (msg.phase === "setup") {
            ws.send(JSON.stringify({ type: "random_setup" }));
          }
          break;
        case "room_status":
          setPhase(msg.phase);
          setSetupDone(msg.setup_done);
          break;
        case "setup_proposal":
          setProposal(msg.placements);
          break;
        case "state":
          stateRef.current = msg.state;
          setState(msg.state);
          setPhase(msg.state.winner !== null ? "over" : "play");
          setError(null);
          break;
        case "events": {
          const pieces = stateRef.current?.pieces ?? [];
          const lines = msg.events.map((e: GameEvent) => describeEvent(e, pieces));
          setLog((old) => [...old, ...lines]);
          const drama: Battle[] = [];
          for (const e of msg.events) {
            if (e.kind === "Combat") {
              drama.push({
                kind: "combat",
                attackerId: String(e.attacker_id),
                defenderId: String(e.defender_id),
                attackerType: String(e.attacker_type),
                defenderType: String(e.defender_type),
                attackerFate: String(e.attacker_fate),
                defenderFate: String(e.defender_fate),
              });
            } else if (e.kind === "PassiveKill") {
              drama.push({
                kind: "hazard",
                attackerId: String(e.victim_id),
                defenderId: String(e.hazard_id),
              });
            }
          }
          if (drama.length) setBattles((old) => [...old, ...drama]);
          break;
        }
        case "error":
          setError(msg.reason);
          break;
      }
    };
    return () => ws.close();
  }, [room, side, mode, ai, recall]);

  const send = useCallback((data: object) => {
    wsRef.current?.send(JSON.stringify(data));
  }, []);

  return {
    phase,
    state,
    proposal,
    setProposal,
    log,
    error,
    setupDone,
    connected,
    battles,
    dismissBattle: useCallback(() => setBattles((old) => old.slice(1)), []),
    requestShuffle: useCallback(() => send({ type: "random_setup" }), [send]),
    submitSetup: useCallback(
      (placements: PlacementMsg[]) => send({ type: "setup", placements }),
      [send]
    ),
    sendAction: useCallback((a: ActionMsg) => send(a), [send]),
  };
}
