import { useEffect, useRef, useState, useCallback } from "react";
import type { WSEvent } from "../types";
import { getWebSocketUrl } from "../utils/api";

interface UseWebSocketReturn {
  events: WSEvent[];
  connected: boolean;
  error: string | null;
  disconnect: () => void;
}

export function useWebSocket(taskId: string | null): UseWebSocketReturn {
  const [events, setEvents] = useState<WSEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const disconnect = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
      setConnected(false);
    }
  }, []);

  useEffect(() => {
    if (!taskId) return;

    const url = getWebSocketUrl(taskId);
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      setError(null);
    };

    ws.onmessage = (event) => {
      try {
        const parsed: WSEvent = JSON.parse(event.data);
        setEvents((prev) => [...prev, parsed]);
      } catch {
        // ignore parse errors
      }
    };

    ws.onerror = () => {
      setError("WebSocket connection failed");
      setConnected(false);
    };

    ws.onclose = () => {
      setConnected(false);
    };

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [taskId]);

  return { events, connected, error, disconnect };
}
