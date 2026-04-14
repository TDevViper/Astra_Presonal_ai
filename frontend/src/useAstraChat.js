import { useState, useRef, useCallback } from "react";
import API from "./config";
import useAstraWS from "./useAstraWS";

const getAuthHeader = () => ({
  "Authorization": `Bearer ${localStorage.getItem("astra_token") || ""}`,
  "X-API-Key": localStorage.getItem("astra_api_key") || ""
});

export default function useAstraChat({ currentModel, useStream }) {
  const [messages,     setMessages]     = useState([]);
  const [loading,      setLoading]      = useState(false);
  const [streaming,    setStreaming]     = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [proactiveAlerts, setProactiveAlerts] = useState([]);

  const abortRef    = useRef(null);
  const wsMetaRef   = useRef(null);
  const wsBufferRef = useRef("");

  const sendStream = useCallback(async (text) => {
    setLoading(true); setStreaming(true); setStreamBuffer("");
    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }]);
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const res = await fetch(API.stream, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ message: text }),
        signal: controller.signal,
      });
      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of decoder.decode(value).split("\n")) {
          if (line.startsWith("data:")) {
            try {
              const data = JSON.parse(line.slice(5));
              if (data.type === "token") {
                const tok = data.text ?? data.token ?? "";
                buf += tok; setStreamBuffer(buf);
              } else if (data.type === "done") {
                setMessages(prev => [...prev, { role: "assistant", content: buf, id: Date.now() + 1 }]);
                setStreamBuffer(""); setStreaming(false); setLoading(false);
              }
            } catch { /* ignore */ }
          }
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") {
        setMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}`, id: Date.now() + 1 }]);
      }
      setStreaming(false); setLoading(false);
    }
  }, []);

  const sendStandard = useCallback(async (text) => {
    setLoading(true);
    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }]);
    try {
      const r = await fetch(API.chat, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ message: text }),
      });
      const data = await r.json();
      setMessages(prev => [...prev, { role: "assistant", content: data.reply || data.response || "", id: Date.now() + 1 }]);
    } catch (e) {
      setMessages(prev => [...prev, { role: "assistant", content: `Error: ${e.message}`, id: Date.now() + 1 }]);
    } finally {
      setLoading(false);
    }
  }, []);

  const { send: wsSend, connected: wsConnected } = useAstraWS({
    onToken: (token) => { wsBufferRef.current += token; setStreamBuffer(wsBufferRef.current); },
    onMeta:  (meta)  => { wsMetaRef.current = meta; },
    onDone: () => {
      const buf  = wsBufferRef.current;
      const meta = wsMetaRef.current || {};
      setMessages(prev => [...prev, {
        role: "assistant", content: buf,
        agent:      meta.agent      || `ollama/${currentModel}`,
        intent:     meta.intent     || "general",
        confidence: meta.confidence || 0.8,
        id: Date.now() + 1,
      }]);
      setStreamBuffer(""); wsBufferRef.current = ""; wsMetaRef.current = null;
      setStreaming(false); setLoading(false);
    },
    onProactive: (msg) => {
      const id = Date.now();
      setProactiveAlerts(prev => [...prev.slice(-4), { id, text: msg }]);
      setTimeout(() => setProactiveAlerts(prev => prev.filter(a => a.id !== id)), 6000);
    },
    onError: (err) => {
      setMessages(prev => [...prev, { role: "assistant", content: `Error: ${err}`, id: Date.now() + 1 }]);
      setStreamBuffer(""); wsBufferRef.current = "";
      setStreaming(false); setLoading(false);
    },
  });

  const sendWS = useCallback((text) => {
    setLoading(true); setStreaming(true); setStreamBuffer("");
    wsBufferRef.current = ""; wsMetaRef.current = null;
    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }]);
    if (!wsSend(text)) sendStream(text);
  }, [wsSend, sendStream]);

  const send = useCallback((text, { useStream: us, wsConnected: wsc } = {}) => {
    if (!text || loading) return;
    if (us && wsc)  sendWS(text);
    else if (us)    sendStream(text);
    else            sendStandard(text);
  }, [loading, sendWS, sendStream, sendStandard]);

  return { messages, loading, streaming, streamBuffer, proactiveAlerts, wsConnected, send, sendWS, sendStream, sendStandard, abortRef };
}
