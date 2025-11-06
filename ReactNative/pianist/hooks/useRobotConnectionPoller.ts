import { useState, useEffect } from 'react';

//import useSWR from "swr";
//import { SERVER_WS } from "../constants/config"; 
import { apiGet } from "../utils/api";

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
      ip: undefined,
      port: undefined,
      latency_ms: null,
      error: e?.message || "fetch failed",
    };
  }
};

export function useRobotConnectionPoller(intervalMs: number = 2000) {
  const [status, setStatus] = useState<RobotStatus>({
    online: false,
    error: "No data",
    latency_ms: null,
  });
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    let isMounted = true;
    let timer: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      const result = await fetcher("/robot/status");
      if (!isMounted) return;

      setStatus(result);
      setIsLoading(false);
    };

    // první načtení hned
    poll();
    // periodický polling
    timer = setInterval(poll, intervalMs);

    return () => {
      isMounted = false;
      if (timer) {
        clearInterval(timer);
      }
    };
  }, [intervalMs]);

  return { status, isLoading };
}

/*
export function useRobotConnectionPollerSWR() {
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
*/


