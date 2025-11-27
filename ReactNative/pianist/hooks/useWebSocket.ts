// hooks/useWebSocket.ts
import { useEffect, useRef, useState } from "react";
import { AppState, AppStateStatus } from "react-native";
import { SERVER_WS, ROOM, TOKEN } from "../constants/config";
import { apiPost } from "@/utils/api"; // <- přidáno, využijeme pro request-performer

type RobotState = {
  status: "shadow" | "song" | "idle" | "error";
  [key: string]: any;
  note?: number;
};

type RoleAssignedInfo = {
  type: "info";
  event: "role_assigned";
  role: "performer" | "watcher";
  device: string;
  room: string;
  client_id: string;
  message?: string;
  state?: RobotState;
};

type PresenceMember = {
  client_id: string;
  device: string;
  role: "performer" | "watcher";
  inactive?: boolean; // <- nový flag z presence
};

type PresenceMsg = {
  type: "presence";
  members: PresenceMember[];
  has_performer?: boolean;
  watchers?: number;
};

type RobotStateMsg = {
  type: "robot_state";
  state: RobotState;
  ts?: number;
};

type AnyMsg = PresenceMsg | RoleAssignedInfo | RobotStateMsg | Record<string, any>;
type ConnState = "idle" | "connecting" | "open" | "closing" | "closed";
type TimerId = ReturnType<typeof setInterval>;

type UseWebSocketOptions = {
  device: string;
  desiredRole?: "performer" | "watcher"; // už jen „hint“ pro UI, WS se připojuje vždy jako watcher
  echoSelf?: boolean;
  enabled?: boolean;
};

export function useWebSocket(opts: UseWebSocketOptions) {
  const {
    device,
    desiredRole = "performer", // můžeš si podle toho třeba defaultně ukázat tlačítko „Chci hrát“
    echoSelf = false,
    enabled = true,
  } = opts;

  const [events, setEvents] = useState<AnyMsg[]>([]);
  const [presence, setPresence] = useState<PresenceMsg | null>(null);
  const [state, setState] = useState<ConnState>("idle");
  const [activeRole, setActiveRole] =
    useState<"performer" | "watcher" | "undefined">("undefined");

  const wsRef = useRef<WebSocket | null>(null);
  const hbRef = useRef<TimerId | null>(null);
  const retryRef = useRef<{ tries: number; lastCode?: number }>({ tries: 0 });
  const [selfClientId, setSelfClientId] = useState<string | null>(null);
  const [robotState, setRobotState] = useState<RobotState | null>(null);

  const enabledRef = useRef<boolean>(enabled);
  enabledRef.current = enabled;

  const cleanupTimersAndSocket = () => {
    if (hbRef.current) {
      clearInterval(hbRef.current);
      hbRef.current = null;
    }
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }
  };

  // ⚙️ WS připojení – vždy jako watcher
  const openSocket = () => {
    // zavři případný starý socket
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {}
      wsRef.current = null;
    }

    const qp = new URLSearchParams({
      room: ROOM,
      token: TOKEN,
      device,
      role: "watcher", // <- klíčová změna: vždy watcher
      echo_self: String(echoSelf),
    }).toString();

    const url = `${SERVER_WS}?${qp}`;

    setState("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = { tries: 0 };
      setState("open");

      if (hbRef.current) clearInterval(hbRef.current);
      hbRef.current = setInterval(() => {
        try {
          wsRef.current?.send(
            JSON.stringify({ type: "ping", ts: Date.now() })
          );
        } catch {}
      }, 25_000);
    };

    ws.onmessage = (e) => {
      try {
        const msg: AnyMsg = JSON.parse(e.data);

        // --- INFO zprávy o rolích ---
        if (msg?.type === "info") {
          const event = (msg as any).event;

          if (event === "role_upgraded" || event === "role_changed") {
            const newRole =
              (msg as any).role === "performer" ? "performer" : "watcher";
            setActiveRole(newRole);
            setEvents((prev) => [...prev, msg]);
            return;
          }

          if (event === "role_assigned") {
            const info = msg as RoleAssignedInfo;
            const newRole =
              info.role === "performer" ? "performer" : "watcher";
            setActiveRole(newRole);
            setSelfClientId(info.client_id);
            setEvents((prev) => [...prev, msg]);
            return;
          }

          if (event === "kicked") {
            setEvents((prev) => [...prev, msg]);
            setActiveRole("undefined");
            return;
          }
        }

        // --- PRESENCE ---
        if (msg?.type === "presence") {
          setPresence(msg as PresenceMsg);
          return;
        }

        // --- STAV ROBOTA ---
        if (msg?.type === "robot_state") {
          setRobotState((msg as RobotStateMsg).state);
          setEvents((prev) => [...prev, msg]);
          return;
        }

        // --- ERROR zprávy (např. z jiných částí backendu) ---
        if (msg?.type === "error") {
          setEvents((prev) => [...prev, msg]);
          return;
        }

        // ostatní – jen log
        setEvents((prev) => [...prev, msg]);
      } catch {
        // ignore parse error
      }
    };

    ws.onerror = () => {
      // RN WebSocket často dává onerror bez detailu, onclose to případně upřesní
    };

    ws.onclose = (ev) => {
      setState("closed");
      setActiveRole("undefined");
      if (hbRef.current) {
        clearInterval(hbRef.current);
        hbRef.current = null;
      }
      setRobotState(null);

      // Auto-reconnect (exponenciální backoff, max ~10 s)
      const { tries } = retryRef.current;
      const nextDelay = Math.min(10_000, 500 * Math.pow(1.8, tries));
      retryRef.current = { tries: tries + 1, lastCode: ev.code };

      setTimeout(() => {
        if (enabledRef.current) openSocket();
      }, nextDelay);
    };
  };

  // Lifecycle + foreground/background
  useEffect(() => {
    if (enabled) {
      openSocket();
    } else {
      cleanupTimersAndSocket();
      setState("closed");
      setRobotState(null);
      setActiveRole("undefined");
    }

    const onAppState = (s: AppStateStatus) => {
      if (!enabledRef.current) return;
      if (s === "active" && state !== "open" && !wsRef.current) {
        openSocket();
      }
      // případně zavírat v backgroundu:
      // if (s !== "active" && wsRef.current && state === "open") wsRef.current.close();
    };

    const sub = AppState.addEventListener("change", onAppState);

    return () => {
      sub.remove();
      if (hbRef.current) {
        clearInterval(hbRef.current);
        hbRef.current = null;
      }
      setState("closing");
      wsRef.current?.close();
      wsRef.current = null;
      setState("closed");
      setRobotState(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [device, echoSelf, enabled]);

  const canControl = () => state === "open" && activeRole === "performer";

  const send = (obj: any) => {
    const isControlMsg =
      obj?.type === "note_on" ||
      obj?.type === "note_off" ||
      obj?.type === "sustain";

    if (isControlMsg && !canControl()) return false;
    if (state !== "open" || !wsRef.current) return false;

    try {
      wsRef.current.send(JSON.stringify(obj));
      return true;
    } catch {
      return false;
    }
  };

  const requestPerformer = async () => {
    if (!selfClientId) {
      return { ok: false, reason: "no_client_id" as const };
    }

    try {
      // backend: POST /WS/{room}/request-performer?client_id=...
      await apiPost(`/WS/${ROOM}/request-performer?client_id=${selfClientId}`);
      // server pošle přes WS info {type:'info', event:'role_changed', role:'performer'}
      return { ok: true as const, reason: "granted" as const };
    } catch (e: any) {
      const status = e?.status;

      if (status === 409) {
        // performer existuje a je aktivní → zamítnuto
        return { ok: false as const, reason: "conflict" as const };
      }

      return { ok: false as const, reason: "network" as const, error: e };
    }
  };

  return {
    events,
    presence,       // {members: [{..., inactive}], has_performer, watchers}
    send,
    state,          // 'idle' | 'connecting' | 'open' | 'closing' | 'closed'
    role: activeRole,
    canControl: canControl(),
    clientId: selfClientId,
    robotState,
    requestPerformer, // <- NOVÉ: zavolej z UI, když chceš roli performera
  };
}
