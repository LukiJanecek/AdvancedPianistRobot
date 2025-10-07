import { useEffect, useRef, useState } from "react";
import { AppState, AppStateStatus } from "react-native";
import { SERVER_WS, ROOM, TOKEN } from "../constants/config";

type PresenceMsg = {
  type: "presence";
  members: Array<{ client_id: string; device: string; role: string }>;
  has_performer?: boolean;
  watchers?: number;
};

type AnyMsg = PresenceMsg | Record<string, any>;
type ConnState = "idle" | "connecting" | "open" | "closing" | "closed";


type TimerId = ReturnType<typeof setInterval>;

export function useWebSocket(
  device: string,
  desiredRole: "performer" | "watcher" = "performer",
  { echoSelf = false }: { echoSelf?: boolean } = {}
) {
  const [events, setEvents] = useState<AnyMsg[]>([]);
  const [presence, setPresence] = useState<PresenceMsg | null>(null);
  const [state, setState] = useState<ConnState>("idle");
  const [activeRole, setActiveRole] = useState<"performer" | "watcher">(desiredRole);

  const wsRef = useRef<WebSocket | null>(null);
  const hbRef = useRef<TimerId | null>(null);
  const retryRef = useRef<{ tries: number; lastCode?: number }>({ tries: 0 });

  const openSocket = (role: "performer" | "watcher") => {
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

    // DŮLEŽITÉ: SERVER_WS musí být ve tvaru "ws://192.168.1.50:8000/ws"
    const url = `${SERVER_WS}?${qp}`;

    setState("connecting");
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      retryRef.current = { tries: 0 };
      setState("open");
      setActiveRole(role);

      if (hbRef.current) clearInterval(hbRef.current);
      hbRef.current = setInterval(() => {
        try { wsRef.current?.send(JSON.stringify({ type: "ping", ts: Date.now() })); } catch {}
      }, 25_000);
    };

    ws.onmessage = (e) => {
      try {
        const msg: AnyMsg = JSON.parse(e.data);
        if (msg?.type === "presence") {
          setPresence(msg as PresenceMsg);
        } else if (msg?.type === "error" && (msg as any)?.reason === "performer_exists") {
          // Server poslal chybu těsně před zavřením
          setEvents((prev) => [...prev, msg]);
        } else {
          setEvents((prev) => [...prev, msg]);
        }
      } catch {
        // nevalidní JSON – ignoruj nebo loguj
      }
    };

    ws.onerror = () => {
      // RN WebSocket často dává onerror bez detailu, v onclose uvidíme víc
    };

    ws.onclose = (ev) => {
      setState("closed");
      if (hbRef.current) { clearInterval(hbRef.current); hbRef.current = null; }

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
    openSocket(desiredRole);

    const onAppState = (s: AppStateStatus) => {
      if (s === "active" && state !== "open" && !wsRef.current) {
        openSocket(activeRole);
      }
      if (s !== "active" && wsRef.current && state === "open") {
        // volitelné: šetřit baterii – zavřít při backgroundu
        // wsRef.current?.close();
      }
    };

    const sub = AppState.addEventListener("change", onAppState);

    return () => {
      sub.remove();
      if (hbRef.current) { clearInterval(hbRef.current); hbRef.current = null; }
      setState("closing");
      wsRef.current?.close();
      wsRef.current = null;
      setState("closed");
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [device, desiredRole, echoSelf]);

  const send = (obj: any) => {
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
  };
}
