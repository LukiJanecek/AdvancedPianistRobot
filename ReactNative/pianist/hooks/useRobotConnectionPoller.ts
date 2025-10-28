import useSWR from "swr";
import { SERVER_WS } from "../constants/config"; 
import { apiGet, apiPost } from "../utils/api";

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
    "/robot/status",
    fetcher,
    {
      refreshInterval: 2000,    
      revalidateOnFocus: true,   
      shouldRetryOnError: true,  
    }
  );

  return {
    status: data ?? { online: false, error: "No data" },
    isLoading,
    isError: error,
  };
}


