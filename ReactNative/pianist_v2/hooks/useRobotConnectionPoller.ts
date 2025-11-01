import { useEffect, useRef, useState } from "react"; //import useSWR from "swr";
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
  /*const { data, error, isLoading } = useSWR<RobotStatus>(
    "/robot/status",
    fetcher,
    {
      refreshInterval: 2000,    
      revalidateOnFocus: true,   
      shouldRetryOnError: true,  
    }
  );*/

  const [status, setStatus] = useState<RobotStatus>({
    online: false,
    error: "No data yet",
    latency_ms: null,
  });

  const [isLoading, setIsLoading] = useState(true);
  const [isError, setIsError] = useState<null | string>(null);

  const intervalRef = useRef<number | null>(null);

  useEffect(() => {
    let isMounted = true;

    const poll = async () => {
      const t0 = Date.now();
      try {
        const raw: RobotStatusRaw = await apiGet("/robot/status");

        if (!isMounted) return;

        setStatus({
          online: !!raw.connected,
          ip: raw.ip,
          port: raw.port,
          latency_ms: Date.now() - t0,
          error: null,
        });

        setIsLoading(false);
        setIsError(null);
      } catch (e: any) {
        if (!isMounted) return;

        setStatus({
          online: false,
          latency_ms: null,
          error: e?.message || "fetch failed",
        });

        setIsLoading(false);
        setIsError(e?.message || "fetch failed");
      }
    };

    // první fetch hned
    poll();

    // pak interval každé 2s
    intervalRef.current = setInterval(poll, 2000);

    return () => {
      isMounted = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
      }
    };
  }, []);

  return {
    status,
    isLoading,
    isError,
  };

  /*return {
    status: data ?? { online: false, error: "No data" },
    isLoading,
    isError: error,
  };*/
}


