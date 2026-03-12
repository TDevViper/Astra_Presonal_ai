// hooks/useAstraWS.js
import { useEffect, useRef, useCallback, useState } from "react";
import { WS_URL } from "../config";

const RECONNECT_DELAY_MS = 3000;
const MAX_RECONNECT      = 10;

export function useAstraWS({ onToken, onMeta, onDone, onError, onProactive }) {
  const ws             = useRef(null);
  const reconnects     = useRef(0);
  const pingTimer      = useRef(null);
  const reconnectTimer = useRef(null);
  const [connected, setConnected] = useState(false);

  const onTokenRef     = useRef(onToken);
  const onMetaRef      = useRef(onMeta);
  const onDoneRef      = useRef(onDone);
  const onErrorRef     = useRef(onError);
  const onProactiveRef = useRef(onProactive);

  useEffect(() => { onTokenRef.current     = onToken;     }, [onToken]);
  useEffect(() => { onMetaRef.current      = onMeta;      }, [onMeta]);
  useEffect(() => { onDoneRef.current      = onDone;      }, [onDone]);
  useEffect(() => { onErrorRef.current     = onError;     }, [onError]);
  useEffect(() => { onProactiveRef.current = onProactive; }, [onProactive]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN ||
        ws.current?.readyState === WebSocket.CONNECTING) return;

    const socket = new WebSocket(WS_URL);

    socket.onopen = () => {
      reconnects.current = 0;
      setConnected(true);
      clearTimeout(reconnectTimer.current);
      pingTimer.current = setInterval(() => {
        if (socket.readyState === WebSocket.OPEN)
          socket.send(JSON.stringify({ type: "ping" }));
      }, 25000);
    };

    socket.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        switch (msg.type) {
          case "token":     onTokenRef.current?.(msg.data);     break;
          case "meta":      onMetaRef.current?.(msg.data);      break;
          case "done":      onDoneRef.current?.();              break;
          case "error":     onErrorRef.current?.(msg.data);     break;
          case "proactive": onProactiveRef.current?.(msg.data); break;
          default: break;
        }
      } catch (e) { console.warn("WS parse error:", e); }
    };

    socket.onclose = () => {
      setConnected(false);
      clearInterval(pingTimer.current);
      if (reconnects.current < MAX_RECONNECT) {
        reconnects.current++;
        const delay = RECONNECT_DELAY_MS * Math.min(reconnects.current, 5);
        reconnectTimer.current = setTimeout(connect, delay);
      }
    };

    socket.onerror = () => { setConnected(false); };
    ws.current = socket;
  }, []);

  useEffect(() => {
    connect();
    return () => {
      clearInterval(pingTimer.current);
      clearTimeout(reconnectTimer.current);
      reconnects.current = MAX_RECONNECT;
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
