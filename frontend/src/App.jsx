import { useState, useEffect, useRef, useCallback } from "react";
import LiveVision from "./components/LiveVision";
import KnowledgeGraph from "./components/KnowledgeGraph";
import ProactiveAlerts from "./components/ProactiveAlerts";
import AgentTrace from "./components/AgentTrace";
import API from "./config";
import { useAstraWS } from "./hooks/useAstraWS";

// ── Helpers ──────────────────────────────────────────────────────────────────
const agentLabel = (a) => {
  if (a?.includes("mistral")) return "MISTRAL";
  if (a?.includes("llama"))   return "LLAMA";
  if (a?.includes("phi3"))    return "PHI3";
  if (a === "web_search_agent")  return "WEB";
  if (a === "memory")            return "MEMORY";
  if (a === "intent_handler")    return "SHORTCUT";
  if (a === "system_controller") return "SYSTEM";
  return (a || "ASTRA").toUpperCase().slice(0, 10);
};

const intentColor = (intent) => ({
  casual:    "#34d399",
  technical: "#60a5fa",
  research:  "#f59e0b",
  coding:    "#a78bfa",
  reasoning: "#fb923c",
  general:   "#94a3b8",
}[intent?.toLowerCase()] || "#94a3b8");

const modeAccent = (id) => ({
  jarvis: "#38bdf8",
  focus:  "#f97316",
  chill:  "#34d399",
  expert: "#c084fc",
  debug:  "#fbbf24",
}[id] || "#38bdf8");

// ── Fonts injection ───────────────────────────────────────────────────────────
const FONTS = `
  @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@300;400;500&display=swap');
`;

// ── Global styles ─────────────────────────────────────────────────────────────
const GLOBAL_CSS = `
  ${FONTS}
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body, #root { height: 100%; }

  ::-webkit-scrollbar { width: 4px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: rgba(148,163,184,0.15); border-radius: 4px; }

  textarea:focus { outline: none; }
  button { cursor: pointer; font-family: inherit; }

  @keyframes fadeSlideUp {
    from { opacity: 0; transform: translateY(10px); }
    to   { opacity: 1; transform: translateY(0); }
  }
  @keyframes pulse-ring {
    0%   { transform: scale(1);    opacity: 0.6; }
    100% { transform: scale(1.55); opacity: 0; }
  }
  @keyframes blink {
    0%, 100% { opacity: 1; }
    50%       { opacity: 0; }
  }
  @keyframes shimmer {
    0%   { background-position: -200% center; }
    100% { background-position:  200% center; }
  }
  @keyframes spin-slow {
    from { transform: rotate(0deg); }
    to   { transform: rotate(360deg); }
  }
  @keyframes thinking {
    0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
    40%           { transform: scale(1);   opacity: 1;   }
  }
`;

// ── Thinking dots ─────────────────────────────────────────────────────────────
function ThinkingDots() {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center", padding: "4px 0" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: "50%",
          background: "#4a6fa5",
          animation: `thinking 1.2s ease-in-out ${i * 0.16}s infinite`,
        }} />
      ))}
    </div>
  );
}

// ── Streaming cursor ──────────────────────────────────────────────────────────
function StreamCursor() {
  return (
    <span style={{
      display: "inline-block", width: 2, height: "1em",
      background: "#38bdf8", marginLeft: 2, verticalAlign: "middle",
      animation: "blink 0.65s steps(1) infinite", borderRadius: 1,
    }} />
  );
}

// ── Orb / avatar ─────────────────────────────────────────────────────────────
function AstraOrb({ active, accent = "#38bdf8", size = 36 }) {
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      {active && (
        <div style={{
          position: "absolute", inset: -4,
          borderRadius: "50%",
          border: `1.5px solid ${accent}`,
          animation: "pulse-ring 1.2s ease-out infinite",
          pointerEvents: "none",
        }} />
      )}
      <div style={{
        width: "100%", height: "100%", borderRadius: "50%",
        background: `radial-gradient(circle at 35% 35%, ${accent}30, ${accent}08)`,
        border: `1.5px solid ${accent}44`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: size * 0.36, fontWeight: 500,
        color: accent, fontFamily: "'JetBrains Mono', monospace",
        backdropFilter: "blur(8px)",
        boxShadow: active ? `0 0 20px ${accent}30, inset 0 0 12px ${accent}10` : "none",
        transition: "box-shadow 0.4s ease",
      }}>
        A
      </div>
    </div>
  );
}

// ── Stat bar ──────────────────────────────────────────────────────────────────
function StatBar({ label, value = 0 }) {
  const color = value > 85 ? "#f87171" : value > 65 ? "#fbbf24" : "#34d399";
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{
        display: "flex", justifyContent: "space-between",
        fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
        color: "#4a6fa5", marginBottom: 4, letterSpacing: "0.05em",
      }}>
        <span>{label}</span>
        <span style={{ color }}>{value.toFixed(0)}%</span>
      </div>
      <div style={{
        height: 3, background: "#0d1f33",
        borderRadius: 2, overflow: "hidden",
      }}>
        <div style={{
          height: "100%", width: `${value}%`,
          background: `linear-gradient(90deg, ${color}99, ${color})`,
          borderRadius: 2,
          transition: "width 1.4s cubic-bezier(0.4,0,0.2,1)",
          boxShadow: `0 0 6px ${color}66`,
        }} />
      </div>
    </div>
  );
}

// ── System sidebar ────────────────────────────────────────────────────────────
function SystemSidebar({ health, memory, models, currentModel, onSwitchModel }) {
  const [sysInfo, setSysInfo] = useState(null);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const r = await fetch(API.stats);
        if (r.ok) setSysInfo(await r.json());
      } catch {}
    };
    fetchStats();
    const t = setInterval(fetchStats, 10000);
    return () => clearInterval(t);
  }, []);

  const cpu  = sysInfo?.cpu?.percent  ?? 0;
  const ram  = sysInfo?.memory?.percent ?? 0;
  const disk = sysInfo?.disk?.percent  ?? 0;

  const services = [
    { name: "BRAIN",  ok: health?.brain  ?? false },
    { name: "MEMORY", ok: health?.memory ?? false },
    { name: "VOICE",  ok: health?.voice  ?? false },
    { name: "OLLAMA", ok: health?.ollama ?? false },
  ];

  return (
    <div style={{
      width: 200, flexShrink: 0,
      borderLeft: "1px solid rgba(148,163,184,0.07)",
      background: "#030912",
      backdropFilter: "blur(24px)",
      padding: "20px 14px",
      display: "flex", flexDirection: "column", gap: 0,
      overflowY: "auto",
    }}>

      {/* Clock */}
      <div style={{
        textAlign: "center", marginBottom: 20,
        paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)",
      }}>
        <div style={{
          fontSize: 22, fontWeight: 300, letterSpacing: "0.12em",
          fontFamily: "'JetBrains Mono', monospace", color: "#e2e8f0",
        }}>
          {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
        </div>
        <div style={{
          fontSize: 9, letterSpacing: "0.15em", marginTop: 4,
          color: "#2a4a6a", fontFamily: "'JetBrains Mono', monospace",
        }}>
          {time.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" }).toUpperCase()}
        </div>
      </div>

      {/* System stats */}
      <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>SYSTEM</div>
        <StatBar label="CPU"  value={cpu} />
        <StatBar label="RAM"  value={ram} />
        <StatBar label="DISK" value={disk} />
      </div>

      {/* Services */}
      <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>SERVICES</div>
        {services.map(({ name, ok }) => (
          <div key={name} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            marginBottom: 8,
          }}>
            <span style={{ fontSize: 10, color: "#2a4a6a", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em" }}>
              {name}
            </span>
            <div style={{
              width: 6, height: 6, borderRadius: "50%",
              background: ok ? "#34d399" : "#475569",
              boxShadow: ok ? "0 0 6px #34d39966" : "none",
              transition: "all 0.3s",
            }} />
          </div>
        ))}
      </div>

      {/* Models */}
      <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>MODELS</div>
        {(models || ["phi3:mini"]).map(m => {
          const active = m === currentModel;
          return (
            <div key={m} onClick={() => onSwitchModel?.(m)} style={{
              padding: "6px 9px", marginBottom: 4, borderRadius: 6,
              fontSize: 9, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em",
              cursor: "pointer",
              background: active ? "rgba(56,189,248,0.1)" : "transparent",
              color: active ? "#38bdf8" : "#2a4a6a",
              border: `1px solid ${active ? "rgba(56,189,248,0.2)" : "transparent"}`,
              transition: "all 0.18s ease",
            }}>
              {m.toUpperCase()}
            </div>
          );
        })}
      </div>

      {/* Memory core */}
      <div>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>MEMORY CORE</div>
        {[
          { label: "FACTS",  val: memory?.user_facts?.length ?? 0,                              color: "#38bdf8" },
          { label: "TASKS",  val: memory?.tasks?.filter(t => t.status === "todo").length ?? 0,  color: "#fbbf24" },
          { label: "CONVOS", val: memory?.conversation_count ?? 0,                              color: "#34d399" },
        ].map(({ label, val, color }) => (
          <div key={label} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            marginBottom: 7,
          }}>
            <span style={{ fontSize: 10, color: "#2a4a6a", fontFamily: "'JetBrains Mono', monospace" }}>
              {label}
            </span>
            <span style={{
              fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
              color, fontWeight: 500,
            }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────
function Message({ msg, isStreaming, accent }) {
  const isUser = msg.role === "user";
  const iColor = intentColor(msg.intent);

  return (
    <div style={{
      display: "flex",
      flexDirection: isUser ? "row-reverse" : "row",
      gap: 12, marginBottom: 20,
      alignItems: "flex-start",
      animation: "fadeSlideUp 0.25s ease forwards",
    }}>
      {/* Avatar */}
      {!isUser
        ? <AstraOrb active={isStreaming} accent={accent} size={34} />
        : (
          <div style={{
            width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
            background: "#0a1628",
            border: "1.5px solid rgba(148,163,184,0.12)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, color: "#4a6fa5",
            fontFamily: "'JetBrains Mono', monospace",
          }}>U</div>
        )
      }

      <div style={{ maxWidth: "68%", minWidth: 60 }}>
        {/* Bubble */}
        <div style={{
          padding: "13px 17px",
          background: isUser
            ? "#0d1e35"
            : "#080f1c",
          border: isUser
            ? "1px solid rgba(56,189,248,0.14)"
            : "1px solid rgba(255,255,255,0.07)",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          backdropFilter: "blur(16px)",
          boxShadow: isUser
            ? "0 4px 24px rgba(56,189,248,0.06)"
            : "0 4px 24px rgba(0,0,0,0.25)",
          color: "rgba(226,232,240,0.92)",
          fontSize: 14, lineHeight: 1.7,
          fontFamily: "'Space Grotesk', sans-serif",
          whiteSpace: "pre-wrap", wordBreak: "break-word",
          position: "relative", overflow: "hidden",
        }}>
          {/* Top sheen */}
          <div style={{
            position: "absolute", top: 0, left: 0, right: 0, height: 1,
            background: isUser
              ? "linear-gradient(90deg, transparent, rgba(56,189,248,0.25), transparent)"
              : "linear-gradient(90deg, transparent, rgba(255,255,255,0.06), transparent)",
            pointerEvents: "none",
          }} />
          {msg.content}
          {isStreaming && <StreamCursor />}
        </div>

        {/* Meta row */}
        {!isUser && (msg.agent || msg.intent) && (
          <div style={{
            display: "flex", gap: 10, marginTop: 5, alignItems: "center",
            paddingLeft: 4,
          }}>
            {msg.agent && (
              <span style={{
                fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                color: "#1e3a5f", letterSpacing: "0.08em",
              }}>
                {agentLabel(msg.agent)}
              </span>
            )}
            {msg.confidence && (
              <span style={{
                fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                color: "#1e3a5f",
              }}>
                {Math.round(msg.confidence * 100)}%
              </span>
            )}
            {msg.intent && (
              <span style={{
                fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                color: iColor, opacity: 0.7, letterSpacing: "0.05em",
              }}>
                {msg.intent.toUpperCase()}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Mode pill ─────────────────────────────────────────────────────────────────
function ModePill({ mode, active, onClick }) {
  const accent = modeAccent(mode.id);
  return (
    <button onClick={onClick} title={mode.description} style={{
      padding: "5px 12px", borderRadius: 20,
      fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
      letterSpacing: "0.1em",
      background: active ? `${accent}18` : "transparent",
      border: `1px solid ${active ? accent + "44" : "#0d1f33"}`,
      color: active ? accent : "#2a4a6a",
      transition: "all 0.18s ease",
      boxShadow: active ? `0 0 12px ${accent}22` : "none",
    }}>
      {mode.emoji} {mode.name?.toUpperCase()}
    </button>
  );
}

// ══════════════════════════════════════════════════════════════════════════════
// MAIN APP
// ══════════════════════════════════════════════════════════════════════════════
export default function App() {
  const [messages,     setMessages]     = useState([]);
  const [proactiveAlerts, setProactiveAlerts] = useState([]);
  const [feedback,     setFeedback]     = useState({});
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [streaming,    setStreaming]     = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [tab,          setTab]          = useState("chat");
  const [health,       setHealth]       = useState({});
  const [memory,       setMemory]       = useState({});
  const [models,       setModels]       = useState([]);
  const [currentModel, setCurrentModel] = useState("phi3:mini");
  const [useStream,    setUseStream]    = useState(true);
  const [currentMode,  setCurrentMode]  = useState("jarvis");
  const [modes,        setModes]        = useState([]);

  const bottomRef = useRef(null);
  const inputRef  = useRef(null);
  const abortRef  = useRef(null);
  const chatBoxRef = useRef(null);

  const accent = modeAccent(currentMode);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  // Health + memory poll
  useEffect(() => {
    const poll = async () => {
      try {
        const [h, m, mdl, modeData] = await Promise.all([
          fetch(API.health).then(r => r.json()).catch(() => ({})),
          fetch(API.memory).then(r => r.json()).catch(() => ({})),
          fetch(API.model).then(r => r.json()).catch(() => ({})),
          fetch(API.modeList).then(r => r.json()).catch(() => ({})),
        ]);
        setHealth(h);
        setMemory(m);
        if (mdl.available)    setModels(mdl.available);
        if (mdl.current)      setCurrentModel(mdl.current);
        if (modeData.modes)   setModes(modeData.modes);
        if (modeData.current) setCurrentMode(modeData.current);
      } catch {}
    };
    poll();
    const t = setInterval(poll, 20000);
    return () => clearInterval(t);
  }, []);

  // Switch model
  const switchModel = useCallback(async (model) => {
    try {
      await fetch(API.modelSet, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model }),
      });
      setCurrentModel(model);
    } catch {}
  }, []);

  // Switch mode
  const switchMode = useCallback(async (modeId) => {
    try {
      const r = await fetch(API.modeSet, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: modeId }),
      });
      const d = await r.json();
      if (d.mode) setCurrentMode(d.mode);
    } catch {}
  }, []);

  // Stream via HTTP SSE
  const sendStream = useCallback(async (text) => {
    setLoading(true); setStreaming(true); setStreamBuffer("");
    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }]);

    let buffer = "";
    try {
      const controller = new AbortController();
      abortRef.current = controller;
      const res = await fetch(API.stream, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }), signal: controller.signal,
      });
      const reader  = res.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of decoder.decode(value).split("\n")) {
          if (!line.startsWith("data:")) continue;
          try {
            const data = JSON.parse(line.slice(5));
            if (data.type === "token") {
              const tok = data.text ?? data.token ?? "";
              if (tok) { buffer += tok; setStreamBuffer(buffer); }
            }
            if (data.type === "done") {
              if (!buffer && data.full) { buffer = data.full; setStreamBuffer(buffer); }
            }
          } catch {}
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") { buffer = "Connection error."; setStreamBuffer(buffer); }
    }

    setMessages(prev => [...prev, {
      role: "assistant", content: buffer,
      agent: `ollama/${currentModel}`, id: Date.now() + 1,
    }]);
    setStreamBuffer(""); setStreaming(false); setLoading(false);
  }, [currentModel]);

  // Standard HTTP
  const sendStandard = useCallback(async (text) => {
    setLoading(true);
    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }]);
    try {
      const r = await fetch(API.chat, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text }),
      });
      const data = await r.json();
      setMessages(prev => [...prev, {
        role: "assistant", content: data.reply,
        agent: data.agent, intent: data.intent,
        confidence: data.confidence, id: Date.now() + 1,
      }]);
    } catch {
      setMessages(prev => [...prev, { role: "assistant", content: "Connection error.", id: Date.now() + 1 }]);
    }
    setLoading(false);
  }, []);

  // WebSocket
  const wsMetaRef   = useRef(null);
  const wsBufferRef = useRef("");

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

  const handleFeedback = useCallback((msgId, value) => {
    setMessages(prev => prev.map(m => m.id === msgId ? { ...m, feedback: value } : m));
  }, []);

  const sendWS = useCallback((text) => {
    setLoading(true); setStreaming(true); setStreamBuffer("");
    wsBufferRef.current = ""; wsMetaRef.current = null;
    setMessages(prev => [...prev, { role: "user", content: text, id: Date.now() }]);
    if (!wsSend(text)) sendStream(text);
  }, [wsSend, sendStream]);

  const send = useCallback(() => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    if (useStream && wsConnected) sendWS(text);
    else if (useStream)           sendStream(text);
    else                          sendStandard(text);
    inputRef.current?.focus();
  }, [input, loading, useStream, sendWS, sendStream, sendStandard, wsConnected]);

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  useEffect(() => {
    const handle = (e) => {
      if ((e.ctrlKey || e.metaKey) && e.code === "Space") {
        e.preventDefault(); inputRef.current?.focus();
      }
      if (e.key === "Escape" && (loading || streaming)) {
        abortRef.current?.abort(); setStreaming(false); setLoading(false);
      }
    };
    window.addEventListener("keydown", handle);
    return () => window.removeEventListener("keydown", handle);
  }, [loading, streaming]);

  const exportChat = () => {
    const lines = messages.map(m => {
      const role = m.role === "user" ? "**You**" : "**ASTRA**";
      const meta = m.role === "assistant" && m.agent
        ? `\n*${m.agent} · ${m.intent || ""} · ${m.confidence ? Math.round(m.confidence * 100) + "%" : ""}*`
        : "";
      return role + "\n" + m.content + meta;
    });
    const md = "# ASTRA Conversation\n\n" + lines.join("\n\n---\n\n");
    const blob = new Blob([md], { type: "text/markdown" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = "astra-chat-" + Date.now() + ".md";
    a.click(); URL.revokeObjectURL(url);
  };

  const stopStream = () => { abortRef.current?.abort(); setStreaming(false); setLoading(false); };

  // ── Tabs ──────────────────────────────────────────────────────────────────
  const TABS = [
    { id: "chat",   label: "Interface" },
    { id: "vision", label: "Vision"    },
    { id: "graph",  label: "Memory"    },
  ];

  return (
    <div style={{
      height: "100vh", display: "flex", flexDirection: "column",
      background: "#04090f",
      color: "rgba(226,232,240,0.9)",
      fontFamily: "'Space Grotesk', sans-serif",
      overflow: "hidden",
      position: "relative",
    }}>
      <style>{GLOBAL_CSS}</style>

      {/* Ambient background blobs */}
      <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", zIndex: 0 }}>
        <div style={{
          position: "absolute", top: "-20%", right: "-10%",
          width: 600, height: 600, borderRadius: "50%",
          background: `radial-gradient(circle, ${accent}08 0%, transparent 70%)`,
          transition: "background 0.6s ease",
        }} />
        <div style={{
          position: "absolute", bottom: "-15%", left: "-8%",
          width: 500, height: 500, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(99,102,241,0.06) 0%, transparent 70%)",
        }} />
      </div>

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <header style={{
        display: "flex", alignItems: "center", justifyContent: "space-between",
        padding: "0 24px", height: 58,
        background: "rgba(3,9,18,0.95)",
        backdropFilter: "blur(24px)",
        borderBottom: "1px solid rgba(148,163,184,0.07)",
        position: "relative", zIndex: 10, flexShrink: 0,
      }}>
        {/* Logo */}
        <div style={{ display: "flex", alignItems: "center", gap: 13 }}>
          <AstraOrb active={loading || streaming} accent={accent} size={38} />
          <div>
            <div style={{
              fontSize: 16, fontWeight: 600, letterSpacing: "0.22em",
              color: "#e2e8f0",
            }}>ASTRA</div>
            <div style={{
              fontSize: 8, letterSpacing: "0.18em",
              color: "#2a4a6a",
              fontFamily: "'JetBrains Mono', monospace",
            }}>
              PERSONAL AI · {currentModel.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <nav style={{ display: "flex", gap: 2 }}>
          {TABS.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={{
              padding: "6px 18px", borderRadius: 8,
              fontSize: 11, fontWeight: tab === t.id ? 500 : 400,
              letterSpacing: "0.06em",
              background: tab === t.id ? "#0d1f33" : "transparent",
              border: `1px solid ${tab === t.id ? "#1e3a5f" : "transparent"}`,
              color: tab === t.id ? "rgba(226,232,240,0.9)" : "#2a4a6a",
              transition: "all 0.18s ease",
            }}>
              {t.label}
            </button>
          ))}
        </nav>

        {/* Mode switcher */}
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          {modes.map(m => (
            <ModePill key={m.id} mode={m} active={m.id === currentMode} onClick={() => switchMode(m.id)} />
          ))}
        </div>

        <button onClick={exportChat} title="Export chat as Markdown" style={{background:"none",border:"1px solid #1e3a5f",borderRadius:6,padding:"4px 10px",fontSize:9,fontFamily:"'JetBrains Mono',monospace",color:"#2a4a6a",cursor:"pointer",letterSpacing:"0.08em"}}>EXPORT</button>

        {/* Status dot */}
        <div style={{ display: "flex", alignItems: "center", gap: 7 }}>
          <div style={{
            width: 6, height: 6, borderRadius: "50%",
            background: wsConnected ? "#34d399" : "#475569",
            boxShadow: wsConnected ? "0 0 8px #34d39988" : "none",
          }} />
          <span style={{
            fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
            color: "#1e3a5f", letterSpacing: "0.1em",
          }}>
            {wsConnected ? "LIVE" : "SSE"}
          </span>
        </div>
      </header>

      {/* ── Body ───────────────────────────────────────────────────────── */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", position: "relative", zIndex: 1 }}>

        {/* Main */}
        {tab === "chat" && (
          <SystemSidebar
            health={health} memory={memory}
            models={models} currentModel={currentModel}
            onSwitchModel={switchModel}
          />
        )}

        <main style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

          {tab === "chat" && (
            <>
              {/* Messages */}
              <div ref={chatBoxRef} style={{ flex: 1, overflowY: "auto", minHeight: 0, padding: "24px 28px", background: "#040c18" }}>
                {messages.length === 0 && (
                  <div style={{
                    height: "100%", display: "flex", flexDirection: "column",
                    alignItems: "center", justifyContent: "center", gap: 10,
                    color: "#0d1f33",
                  }}>
                    <div style={{
                      fontSize: 56, fontWeight: 200, letterSpacing: "0.3em",
                      color: "#0d1f33",
                    }}>ASTRA</div>
                    <div style={{
                      fontSize: 10, letterSpacing: "0.25em",
                      fontFamily: "'JetBrains Mono', monospace",
                      color: "#0f2040",
                    }}>SYSTEMS READY · AWAITING INPUT</div>
                    <div style={{
                      marginTop: 24, display: "flex", gap: 24,
                      fontSize: 11, color: "#0f2040",
                    }}>
                      {["Ask me anything", "Play music", "Send a message", "Check system"].map(hint => (
                        <div key={hint} onClick={() => setInput(hint)} style={{
                          padding: "8px 16px", borderRadius: 10,
                          border: "1px solid rgba(148,163,184,0.08)",
                          cursor: "pointer",
                          transition: "all 0.18s",
                        }}
                          onMouseEnter={e => e.target.style.borderColor = "#0f2040"}
                          onMouseLeave={e => e.target.style.borderColor = "#0d1f33"}
                        >
                          {hint}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {messages.map(msg => (
                  <Message key={msg.id} msg={msg} isStreaming={false} accent={accent} />
                ))}

                {streaming && streamBuffer && (
                  <Message
                    msg={{ role: "assistant", content: streamBuffer, agent: `ollama/${currentModel}` }}
                    isStreaming={true}
                    accent={accent}
                  />
                )}

                {loading && !streaming && (
                  <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
                    <AstraOrb active={true} accent={accent} size={34} />
                    <ThinkingDots />
                  </div>
                )}

                <div ref={bottomRef} />
              </div>

              {/* Input bar */}
              <div style={{
                padding: "14px 24px 18px",
                background: "rgba(6,13,26,0.6)",
                backdropFilter: "blur(24px)",
                borderTop: "1px solid rgba(148,163,184,0.06)",
              }}>
                <div style={{
                  display: "flex", alignItems: "center", gap: 12,
                  background: "rgba(4,12,24,0.9)",
                  border: `1px solid ${loading ? accent + "30" : "#0d1f33"}`,
                  borderRadius: 14,
                  padding: "10px 14px",
                  transition: "border-color 0.3s ease",
                  boxShadow: loading ? `0 0 20px ${accent}10` : "none",
                }}>
                  {/* Accent line */}
                  <div style={{
                    width: 2, height: 22, borderRadius: 2,
                    background: loading
                      ? `linear-gradient(to bottom, ${accent}, ${accent}44)`
                      : "#1e3a5f",
                    transition: "background 0.3s ease",
                    flexShrink: 0,
                  }} />

                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={onKey}
                    placeholder="Speak to ASTRA..."
                    rows={1}
                    style={{
                      flex: 1, background: "transparent", border: "none",
                      color: "rgba(226,232,240,0.9)", fontSize: 14,
                      resize: "none", fontFamily: "'Space Grotesk', sans-serif",
                      lineHeight: 1.5, minHeight: 24, maxHeight: 120, padding: 0,
                    }}
                  />

                  {/* Stream toggle */}
                  <button onClick={() => setUseStream(s => !s)} style={{
                    fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                    letterSpacing: "0.1em", padding: "4px 8px", borderRadius: 6,
                    background: useStream ? `${accent}18` : "transparent",
                    border: `1px solid ${useStream ? accent + "40" : "#0d1f33"}`,
                    color: useStream ? accent : "#1e3a5f",
                    transition: "all 0.18s",
                  }}>
                    {useStream ? "STREAM" : "STATIC"}
                  </button>

                  {streaming ? (
                    <button onClick={stopStream} style={{
                      padding: "7px 16px", borderRadius: 8, fontSize: 11,
                      fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
                      background: "rgba(248,113,113,0.12)",
                      border: "1px solid rgba(248,113,113,0.25)",
                      color: "#f87171",
                    }}>STOP</button>
                  ) : (
                    <button onClick={send} disabled={!input.trim() || loading} style={{
                      padding: "7px 18px", borderRadius: 8, fontSize: 11,
                      fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
                      background: input.trim() ? `${accent}18` : "rgba(148,163,184,0.05)",
                      border: `1px solid ${input.trim() ? accent + "40" : "#0d1f33"}`,
                      color: input.trim() ? accent : "#1e3a5f",
                      transition: "all 0.18s ease",
                    }}>SEND</button>
                  )}
                </div>

                <div style={{
                  display: "flex", justifyContent: "space-between",
                  marginTop: 7, paddingLeft: 4,
                  fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                  color: "#0f2040", letterSpacing: "0.08em",
                }}>
                  <span>↵ ENTER to send · ⇧ENTER newline</span>
                  <span>{currentMode.toUpperCase()} MODE · {currentModel.toUpperCase()}</span>
                </div>
              </div>
            </>
          )}

          {tab === "vision" && (
            <div style={{ flex: 1, padding: 24, overflow: "auto" }}>
              <LiveVision />
            </div>
          )}

          {tab === "graph" && (
            <div style={{ flex: 1, overflow: "hidden" }}>
              <KnowledgeGraph />
            </div>
          )}
        </main>

        {/* Agent trace */}
        <AgentTrace messages={messages} />


      </div>

      <ProactiveAlerts />
    </div>
  );
}