// hooks/useAstraWS.js
// Persistent WebSocket connection to ASTRA backend
import { useEffect, useRef, useCallback, useState } from "react";
import { WS_URL } from "../config";

const RECONNECT_DELAY_MS = 2000;
const MAX_RECONNECT      = 5;

export function useAstraWS({ onToken, onMeta, onDone, onError, onProactive }) {
  const ws          = useRef(null);
  const reconnects  = useRef(0);
  const pingTimer   = useRef(null);
  const [connected, setConnected] = useState(false);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      reconnects.current = 0;
      setConnected(true);
      // Keepalive ping every 25s
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN) {
          socket.send(JSON.stringify({ type: "ping" }));
        }
      }, 25000);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "token":     onToken?.(msg.data);     break;
          case "meta":      onMeta?.(msg.data);      break;
          case "done":      onDone?.();              break;
          case "error":     onError?.(msg.data);     break;
          case "proactive": onProactive?.(msg.data); break;
          default: break;
        }
      } catch (e) {
        console.warn("WS parse error:", e);
      }
    };

    socket.onclose = () => {
      setConnected(false);
      clearInterval(pingTimer.current);
      if (reconnects.current < MAX_RECONNECT) {
        reconnects.current++;
        setTimeout(connect, RECONNECT_DELAY_MS * reconnects.current);
      }
    };

    socket.onerror = (e) => {
      console.warn("WebSocket error:", e);
      setConnected(false);
    };

    ws.current = socket;
  }, [onToken, onMeta, onDone, onError, onProactive]);

  useEffect(() => {
    connect();
    return () => {
      clearInterval(pingTimer.current);
      ws.current?.close();
    };
  }, [connect]);

  const send = useCallback((text, image = null) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: "chat", text, image }));
      return true;
    }
    return false;
  }, []);

  return { send, connected };
}
