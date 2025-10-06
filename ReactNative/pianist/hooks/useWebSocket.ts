import { useEffect, useRef, useState } from "react";
import { SERVER_URL, ROOM, TOKEN } from "../constants/config";

export function useWebSocket(device: string, role: string = "performer") {
  const [events, setEvents] = useState<any[]>([]);
  const [presence, setPresence] = useState<any[]>([]);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    const url = `${SERVER_URL}?room=${ROOM}&token=${TOKEN}&device=${device}&role=${role}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data);
      if (msg.type === "presence") {
        setPresence(msg.members);
      } else {
        setEvents((prev) => [...prev, msg]);
      }
    };

    return () => {
      ws.close();
    };
  }, [device, role]);

  const send = (obj: any) => {
    wsRef.current?.send(JSON.stringify(obj));
  };

  return { events, presence, send };
}
