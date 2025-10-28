import useSWR from "swr";
import { SERVER_WS } from "../constants/config"; 

type RobotStatusRaw = {
  connected: boolean;
  ip: string;
  port: number;
};

export type RobotStatus = {
  online: boolean;
  ip?: string;
  port?: number;
  latency_ms?: number | null;
  error?: string | null;
};

const fetcher = async (url: string): Promise<RobotStatus> => {
  const t0 = Date.now();
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const raw: RobotStatusRaw = await res.json();
    return {
      online: !!raw.connected,
      ip: raw.ip,
      port: raw.port,
      latency_ms: Date.now() - t0,
      error: null,
    };
  } catch (e: any) {
    return {
      online: false,
      latency_ms: null,
      error: e?.message || "fetch failed",
    };
  }
};

export function useRobotConnectionPoller() {
  const { data, error, isLoading } = useSWR<RobotStatus>(
    `${SERVER_WS}/robot/status`,
    fetcher,
    {
      refreshInterval: 2000,     // ping každé 2 s
      revalidateOnFocus: true,   // obnov po návratu do appky
      shouldRetryOnError: true,  // retry při chybě
    }
  );

  return {
    status: data ?? { online: false, error: "No data" },
    isLoading,
    isError: error,
  };
}


