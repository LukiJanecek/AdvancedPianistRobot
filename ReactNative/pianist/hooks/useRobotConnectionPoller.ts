// hooks/useRobotConnectionPoller.ts
import { useState, useEffect } from "react";
import { apiGet } from "../utils/api";

type RobotMode = "idle" | "shadow" | "song" | "error" | undefined;

type RobotStatusRaw = {
  connected: boolean;
  ip: string;
  port: number;
  status?: RobotMode;
  detail?: string | null;
  in_shadow_mode?: boolean;
  playing_song?: boolean;
};

export type RobotStatus = {
  online: boolean;
  ip?: string;
  port?: number;
  latency_ms?: number | null;
  error?: string | null;
  status?: RobotMode;
  detail?: string | null;
  in_shadow_mode?: boolean;
  playing_song?: boolean;
  shadow_start?: boolean;
  shadow_auto_stopped?: boolean;
};

const fetcher = async (path: string): Promise<RobotStatus> => {
  const t0 = Date.now();
  try {
    const raw: RobotStatusRaw = await apiGet(path);
    return {
      online: !!raw.connected,
      ip: raw.ip,
      port: raw.port,
      latency_ms: Date.now() - t0,
      error: null,
      status: raw.status,
      detail: raw.detail,
      in_shadow_mode: raw.in_shadow_mode,
      playing_song: raw.playing_song,
    };
  } catch (e: any) {
    return {
      online: false,
      ip: undefined,
      port: undefined,
      latency_ms: null,
      error: e?.message || "fetch failed",
    };
  }
};

export function useRobotConnectionPoller(
  intervalMs: number = 3000,
  isActive: boolean = true
) {
  const [status, setStatus] = useState<RobotStatus>({
    online: false,
    error: "No data",
    latency_ms: null,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    let timeout: ReturnType<typeof setTimeout> | null = null;

    if (!isActive) {
      // když screen není aktivní → nic nepollujeme
      setIsLoading(true);
      return () => {};
    }

    const poll = async () => {
      //console.log("[POLL] /Kuka/status ->", new Date().toISOString());

      const result = await fetcher("/Kuka/status");
      if (!isMounted) return;

      setStatus(result);
      setIsLoading(false);

      timeout = setTimeout(poll, intervalMs);
    };

    // první načtení hned
    poll();

    return () => {
      isMounted = false;
      if (timeout) clearTimeout(timeout);
    };
  }, [intervalMs, isActive]);

  return { status, isLoading };
}
