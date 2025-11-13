import { useEffect, useRef, useState } from "react";
import { AppState, AppStateStatus } from "react-native";
import { SERVER_WS, ROOM, TOKEN } from "../constants/config";

type RoleAssignedInfo = {
  type: "info";
  event: "role_assigned";
  role: "performer" | "watcher";
  device: string;
  room: string;
  client_id: string;
  message?: string;
  note?:number;
  state?: RobotState;
};

type PresenceMsg = {
  type: "presence";
  members: Array<{ client_id: string; device: string; role: string }>;
  has_performer?: boolean;
  watchers?: number;
  note?:number;
  state?: RobotState;
};

type RobotState = {
  status: "shadow" | "song" | "idle" | "error";
  [key: string]: any;
  note?:number;
};

type RobotStateMsg = {
  type: "robot_state";
  state: RobotState;
  ts?: number;
  note?:number;
};

type AnyMsg = PresenceMsg | RoleAssignedInfo | RobotStateMsg | Record<string, any>;
type ConnState = "idle" | "connecting" | "open" | "closing" | "closed";

type TimerId = ReturnType<typeof setInterval>;

type UseWebSocketOptions = {
  device: string;
  desiredRole?: "performer" | "watcher";
  echoSelf?: boolean;
  enabled?: boolean; 
};

export function useWebSocket(opts: UseWebSocketOptions
  /*device: string,
  desiredRole: "performer" | "watcher" = "performer",
  { echoSelf = false }: { echoSelf?: boolean } = {},
  { enabled = true }: UseWebSocketOptions = {}*/
) {
  const {
    device,
    desiredRole = "performer",
    echoSelf = false,
    enabled = true,
  } = opts;

  const [events, setEvents] = useState<AnyMsg[]>([]);
  const [presence, setPresence] = useState<PresenceMsg | null>(null);
  const [state, setState] = useState<ConnState>("idle");
  const [activeRole, setActiveRole] = useState<"performer" | "watcher" | "undefined">("undefined");

  const wsRef = useRef<WebSocket | null>(null);
  const hbRef = useRef<TimerId | null>(null);
  const retryRef = useRef<{ tries: number; lastCode?: number }>({ tries: 0 });
  const [selfClientId, setSelfClientId] = useState<string | null>(null);

  const [robotState, setRobotState] = useState<RobotState | null>(null);

  const enabledRef = useRef<boolean>(enabled);        // <- nový guard
  enabledRef.current = enabled;

  const cleanupTimersAndSocket = () => {
    if (hbRef.current) { clearInterval(hbRef.current); hbRef.current = null; }
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {}
      wsRef.current = null;
    }
  };

  const openSocket = (role: "performer" | "watcher" | "undefined") => {
    if (wsRef.current) {
      try { wsRef.current.close(); } catch {}
      wsRef.current = null;
    }

    const qp = new URLSearchParams({
      room: ROOM,
      token: TOKEN,
      device,
      role,
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
        try { wsRef.current?.send(JSON.stringify({ type: "ping", ts: Date.now() })); } catch {}
      }, 25_000);
    };

    ws.onmessage = (e) => {
      try {
        const msg: AnyMsg = JSON.parse(e.data);

        if (msg?.type === "info" && (msg as any)?.event === "role_downgraded") {
          setActiveRole("watcher");
          setEvents((prev) => [...prev, msg]);
          return;
        }

        if (msg?.type === "info" && (msg as any)?.event === "role_upgraded") {
          setActiveRole("performer");
          setEvents((prev) => [...prev, msg]);
          return;
        }

        if (msg?.type === "info" && (msg as any)?.event === "role_assigned") {
          const info = msg as RoleAssignedInfo;
          setActiveRole((msg as any).role === "performer" ? "performer" : "watcher");
          setSelfClientId(info.client_id);  
          setEvents((prev) => [...prev, msg]);
          return;
        }

        // --- PRESENCE ---
        if (msg?.type === "presence") {
          setPresence(msg as PresenceMsg);
          return;
        }

        // NEW: STAV ROBOTA Z BACKENDU
        if (msg?.type === "robot_state") {
          setRobotState(msg.state);
          setEvents((prev) => [...prev, msg]);
          return;
        }

        // --- ERROR ZPRÁVY ---
        if (msg?.type === "error" && (msg as any)?.reason === "performer_exists") {
          setEvents((prev) => [...prev, msg]);
          return;
        }

        // Ostatní zprávy si jen logujeme do events
        setEvents((prev) => [...prev, msg]);
      } catch {
        // ignore
      }
    };

    ws.onerror = () => {
      // RN WebSocket často dává onerror bez detailu, v onclose uvidíme víc
    };

    ws.onclose = (ev) => {
      setState("closed");
      setActiveRole("undefined");
      if (hbRef.current) { clearInterval(hbRef.current); hbRef.current = null; }

      setRobotState(null);

      // Auto-reconnect s exponenciálním backoffem (max ~10 s)
      const { tries } = retryRef.current;
      const nextDelay = Math.min(10_000, 500 * Math.pow(1.8, tries));
      retryRef.current = { tries: tries + 1, lastCode: ev.code };

      // Pokud jsme byli performer a server nás vyhodil kvůli druhému performerovi (4403),
      // přepneme na watcher a hned zkusíme znovu.
      if (ev.code === 4403 && role === "performer") {
        setActiveRole("watcher");
        setTimeout(() => openSocket("watcher"), 300);
        return;
      }

      // Ostatní případy – zkusíme zachovat poslední roli
      setTimeout(() => openSocket(role), nextDelay);
    };
  };

  // Lifecycle + app foreground/background
  useEffect(() => {
    if (enabled) {
      openSocket(desiredRole);
    } else {
      // vypnuto → okamžitě zavřít
      cleanupTimersAndSocket();
      setState("closed");
      setRobotState(null);
      setActiveRole("undefined");
    }

    const onAppState = (s: AppStateStatus) => {
      if (!enabledRef.current) return;
      if (s === "active" && state !== "open" && !wsRef.current) {
        openSocket(activeRole === "undefined" ? desiredRole : activeRole);
      }
      // případně můžeš zavírat v backgroundu
      // if (s !== "active" && wsRef.current && state === "open") wsRef.current.close();
    };

    const sub = AppState.addEventListener("change", onAppState);

    return () => {
      sub.remove();
      if (hbRef.current) { clearInterval(hbRef.current); hbRef.current = null; }
      setState("closing");
      wsRef.current?.close();
      wsRef.current = null;
      setState("closed");
      setRobotState(null);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [device, desiredRole, echoSelf, enabled]);

  const canControl = () => state === "open" && activeRole === "performer";

  const send = (obj: any) => {
    const isControlMsg = obj?.type === "note_on" || obj?.type === "note_off" || obj?.type === "sustain";

    if (isControlMsg && !canControl()) return false;

    if (state !== "open" || !wsRef.current) return false;
    
    try {
      wsRef.current.send(JSON.stringify(obj));
      return true;
    } catch {
      return false;
    }
  };
  
  return {
    events,
    presence,          // {members, has_performer, watchers}
    send,
    state,             // 'idle' | 'connecting' | 'open' | 'closing' | 'closed'
    role: activeRole,  // skutečně aktivní role po handshake/rejectu
    canControl: canControl(), // <- volitelné: předej do UI
    clientId: selfClientId, // <- vlastní client_id přidělené serverem
    robotState,       // <- aktuální stav robota z backendu
  };  
}
