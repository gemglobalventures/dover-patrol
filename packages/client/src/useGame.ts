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

export interface GameConnection {
  phase: string;
  state: ClientState | null;
  proposal: PlacementMsg[] | null;
  setProposal: (p: PlacementMsg[]) => void;
  log: string[];
  error: string | null;
  setupDone: Record<Side, boolean>;
  connected: boolean;
  requestShuffle: () => void;
  submitSetup: () => void;
  sendAction: (a: ActionMsg) => void;
}

export function useGame(room: string, side: Side, mode: string): GameConnection {
  const wsRef = useRef<WebSocket | null>(null);
  const [phase, setPhase] = useState("setup");
  const [state, setState] = useState<ClientState | null>(null);
  const [proposal, setProposal] = useState<PlacementMsg[] | null>(null);
  const [log, setLog] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [connected, setConnected] = useState(false);
  const [setupDone, setSetupDone] = useState<Record<Side, boolean>>({
    a: false,
    b: false,
  });
  const stateRef = useRef<ClientState | null>(null);

  useEffect(() => {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(
      `${proto}://${location.host}/ws/${encodeURIComponent(room)}/${side}?mode=${mode}`
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
          break;
        }
        case "error":
          setError(msg.reason);
          break;
      }
    };
    return () => ws.close();
  }, [room, side, mode]);

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
    requestShuffle: useCallback(() => send({ type: "random_setup" }), [send]),
    submitSetup: useCallback(() => {
      if (proposal) send({ type: "setup", placements: proposal });
    }, [send, proposal]),
    sendAction: useCallback((a: ActionMsg) => send(a), [send]),
  };
}
