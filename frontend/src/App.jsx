import { useState, useEffect, useRef, useCallback } from "react";
import LiveVision from "./components/LiveVision";
import KnowledgeGraph from "./components/KnowledgeGraph";
import ProactiveAlerts from "./components/ProactiveAlerts";
import AgentTrace from "./components/AgentTrace";
import AmbientPanel from "./components/AmbientPanel";
import GuardianPanel from "./components/GuardianPanel";
import RequestTracePanel from "./components/RequestTracePanel";
import PluginManagerPanel from "./components/PluginManagerPanel";
import API, { API_KEY } from "./config";
import ChatPanel from "./components/ChatPanel.jsx";
import Dashboard from "./components/Dashboard.jsx";
import ErrorBoundary from "./components/ErrorBoundary.jsx";
import { useAstraWS } from "./hooks/useAstraWS";
import { ThinkingDots, StreamCursor, AstraOrb, StatBar } from "./components/Atoms";
import { SystemSidebar } from "./components/SystemSidebar";
import { Message } from "./components/Message";
import { ModePill } from "./components/ModePill";

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

const MODE_THEMES = {
  jarvis: {
    accent:      "#38bdf8",
    bg:          "#04090f",
    chatBg:      "#040c18",
    userBubble:  "#0d1e35",
    astraBubble: "#080f1c",
    glow:        "rgba(56,189,248,0.06)",
    label:       "JARVIS",
    hint:        "PERSONAL AI OS",
  },
  focus: {
    accent:      "#f97316",
    bg:          "#0f0800",
    chatBg:      "#0a0500",
    userBubble:  "#1a0e00",
    astraBubble: "#120900",
    glow:        "rgba(249,115,22,0.06)",
    label:       "FOCUS",
    hint:        "DEEP WORK MODE",
  },
  chill: {
    accent:      "#34d399",
    bg:          "#02100a",
    chatBg:      "#020d07",
    userBubble:  "#051a0e",
    astraBubble: "#041208",
    glow:        "rgba(52,211,153,0.06)",
    label:       "CHILL",
    hint:        "RELAXED MODE",
  },
  expert: {
    accent:      "#c084fc",
    bg:          "#08040f",
    chatBg:      "#060210",
    userBubble:  "#12073a",
    astraBubble: "#0d0520",
    glow:        "rgba(192,132,252,0.06)",
    label:       "EXPERT",
    hint:        "PRECISION MODE",
  },
  debug: {
    accent:      "#fbbf24",
    bg:          "#0f0c00",
    chatBg:      "#0a0800",
    userBubble:  "#1a1400",
    astraBubble: "#120f00",
    glow:        "rgba(251,191,36,0.06)",
    label:       "DEBUG",
    hint:        "SYSTEM TRACE MODE",
  },
};

const modeAccent = (id) => (MODE_THEMES[id] || MODE_THEMES.jarvis).accent;
const modeTheme  = (id) =>  MODE_THEMES[id] || MODE_THEMES.jarvis;

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

// ══════════════════════════════════════════════════════════════════════════════
// MAIN APP
// ══════════════════════════════════════════════════════════════════════════════
export default function App() {
  const [messages,     setMessages]     = useState([]);
  const [, setProactiveAlerts] = useState([]);
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
  const theme  = modeTheme(currentMode);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamBuffer]);

  // Health + memory poll
  useEffect(() => {
    const poll = async () => {
      try {
        const [h, m, mdl, modeData] = await Promise.all([
          fetch(API.health,   {headers:{"X-API-Key":API_KEY}}).then(r=>r.json()).catch(()=>({})),
          fetch(API.memory,   {headers:{"X-API-Key":API_KEY}}).then(r=>r.json()).catch(()=>({})),
          fetch(API.model,    {headers:{"X-API-Key":API_KEY}}).then(r=>r.json()).catch(()=>({})),
          fetch(API.modeList, {headers:{"X-API-Key":API_KEY}}).then(r=>r.json()).catch(()=>({})),
        ]);
        setHealth(h);
        setMemory(m);
        if (mdl.available)    setModels(mdl.available);
        if (mdl.current)      setCurrentModel(mdl.current);
        if (modeData.modes)   setModes(modeData.modes);
        if (modeData.current) setCurrentMode(modeData.current);
      } catch { /* ignore */ }
    };
    poll();
    const t = setInterval(poll, 20000);
    return () => clearInterval(t);
  }, []);

  // Switch model
  const switchModel = useCallback(async (model) => {
    try {
      await fetch(API.modelSet, {
        method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
        body: JSON.stringify({ model }),
      });
      setCurrentModel(model);
    } catch { /* ignore */ }
  }, []);

  // Switch mode
  const switchMode = useCallback(async (modeId) => {
    try {
      const r = await fetch(API.modeSet, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: modeId }),
      });
      const d = await r.json();
      if (d.mode) {
        setCurrentMode(d.mode);
        setTab("chat"); // reset to chat tab on mode switch
      }
    } catch { /* ignore */ }
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
        method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
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
          } catch { /* ignore */ }
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
        method: "POST", headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
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
    { id: "chat",      label: "Interface" },
    { id: "vision",    label: "Vision"    },
    { id: "graph",     label: "Memory"    },
    { id: "dashboard", label: "Dashboard" },
  ];

  return (
    <div style={{
      height: "100vh", display: "flex", flexDirection: "column",
      background: theme.bg,
      transition: "background 0.6s ease",
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
          background: `radial-gradient(circle, ${accent}12 0%, transparent 70%)`,
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
              color: accent,
              opacity: 0.6,
              fontFamily: "'JetBrains Mono', monospace",
              transition: "color 0.4s ease",
            }}>
              {theme.hint} · {currentModel.toUpperCase()}
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
              <div ref={chatBoxRef} style={{ flex: 1, overflowY: "auto", minHeight: 0, padding: "24px 28px 140px 28px", background: theme.chatBg, transition: "background 0.6s ease" }}>
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
                      color: accent,
                      opacity: 0.25,
                      transition: "color 0.4s ease",
                    }}>{theme.hint} · AWAITING INPUT</div>
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
                  <Message key={msg.id} msg={msg} isStreaming={false} accent={accent} theme={theme} />
                ))}

                {streaming && streamBuffer && (
                  <Message
                    msg={{ role: "assistant", content: streamBuffer, agent: `ollama/${currentModel}` }}
                    isStreaming={true}
                    accent={accent}
                    theme={theme}
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

              {/* Dynamic 3D Island Input */}
              <div style={{
                position: "absolute", bottom: 28, left: "50%", transform: "translateX(-50%)",
                width: "100%", maxWidth: "840px", padding: "0 24px",
                zIndex: 50,
              }}>
                <div style={{
                  display: "flex", flexDirection: "column", gap: 10,
                  background: "rgba(10,15,25,0.75)",
                  backdropFilter: "blur(32px)",
                  WebkitBackdropFilter: "blur(32px)",
                  borderTop: "1px solid rgba(255,255,255,0.15)",
                  borderLeft: "1px solid rgba(255,255,255,0.05)",
                  borderBottom: "1px solid rgba(0,0,0,0.8)",
                  borderRight: "1px solid rgba(0,0,0,0.8)",
                  borderRadius: 24,
                  padding: "12px 16px",
                  transition: "all 0.4s cubic-bezier(0.16,1,0.3,1)",
                  boxShadow: `0 20px 40px rgba(0,0,0,0.6), inset 0 1px 1px rgba(255,255,255,0.1), ${loading ? `0 0 40px ${accent}30` : '0 0 0 transparent'}`,
                }}
                onFocus={(e) => { e.currentTarget.style.boxShadow = `0 20px 40px rgba(0,0,0,0.6), inset 0 1px 1px rgba(255,255,255,0.1), 0 0 30px ${accent}25, inset 0 0 20px ${accent}10`; e.currentTarget.style.borderColor = `${accent}50`; }}
                onBlur={(e) => { e.currentTarget.style.boxShadow = `0 20px 40px rgba(0,0,0,0.6), inset 0 1px 1px rgba(255,255,255,0.1), ${loading ? `0 0 40px ${accent}30` : '0 0 0 transparent'}`; e.currentTarget.style.borderColor = "rgba(255,255,255,0.15)"; }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
                    {/* Glowing input accent dot */}
                    <div style={{
                      width: 10, height: 10, borderRadius: "50%",
                      background: loading ? accent : "#1e3a5f",
                      boxShadow: loading ? `0 0 16px ${accent}, inset 0 2px 4px rgba(255,255,255,0.5)` : "inset 0 2px 4px rgba(0,0,0,0.6)",
                      border: `1px solid ${loading ? 'transparent' : 'rgba(255,255,255,0.1)'}`,
                      transition: "all 0.3s ease",
                      flexShrink: 0,
                    }} />

                    <textarea
                      ref={inputRef}
                      value={input}
                      onChange={e => setInput(e.target.value)}
                      onKeyDown={onKey}
                      placeholder="Message ASTRA..."
                      rows={1}
                      style={{
                        flex: 1, background: "transparent", border: "none",
                        color: "rgba(255,255,255,0.9)", fontSize: 15,
                        resize: "none", fontFamily: "'Space Grotesk', sans-serif",
                        lineHeight: 1.5, minHeight: 24, maxHeight: 160, padding: "4px 0",
                      }}
                    />

                    {/* Controls */}
                    <div style={{display: "flex", gap: 8, alignItems: "center"}}>
                      <button onClick={() => setUseStream(s => !s)} title="Toggle Stream" style={{
                        fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
                        letterSpacing: "0.1em", padding: "6px 12px", borderRadius: 10,
                        background: useStream ? `linear-gradient(to bottom, ${accent}30, ${accent}10)` : "rgba(0,0,0,0.4)",
                        borderTop: `1px solid ${useStream ? accent + "60" : "rgba(255,255,255,0.1)"}`,
                        borderBottom: "1px solid rgba(0,0,0,0.6)",
                        borderLeft: `1px solid ${useStream ? accent + "40" : "transparent"}`,
                        borderRight: `1px solid ${useStream ? accent + "40" : "transparent"}`,
                        color: useStream ? accent : "#64748b",
                        boxShadow: useStream ? `inset 0 1px 2px rgba(255,255,255,0.2), 0 4px 10px rgba(0,0,0,0.3)` : "inset 0 2px 4px rgba(0,0,0,0.4)",
                        transition: "all 0.2s transform active:scale-95",
                      }}>
                        SSE
                      </button>

                      {streaming ? (
                        <button onClick={stopStream} style={{
                          padding: "8px 20px", borderRadius: 12, fontSize: 11, fontWeight: "bold",
                          fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
                          background: "linear-gradient(to bottom, #ef4444, #b91c1c)",
                          borderTop: "1px solid #fca5a5", borderBottom: "1px solid #7f1d1d",
                          color: "#fff", textShadow: "0 1px 2px rgba(0,0,0,0.6)",
                          boxShadow: "0 6px 16px rgba(239, 68, 68, 0.4), inset 0 1px 2px rgba(255,255,255,0.3)",
                          cursor: "pointer", transition: "transform 0.1s active:scale-95"
                        }}>STOP</button>
                      ) : (
                        <button onClick={send} disabled={!input.trim() || loading} style={{
                          padding: "8px 22px", borderRadius: 12, fontSize: 11, fontWeight: "bold",
                          fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
                          background: (input.trim() && !loading) ? `linear-gradient(to bottom, ${accent}, ${accent}b0)` : "linear-gradient(to bottom, #1e293b, #0f172a)",
                          borderTop: `1px solid ${(input.trim() && !loading) ? "#ffffff60" : "rgba(255,255,255,0.1)"}`, 
                          borderBottom: "1px solid rgba(0,0,0,0.8)",
                          color: (input.trim() && !loading) ? "#fff" : "#475569",
                          textShadow: (input.trim() && !loading) ? "0 1px 2px rgba(0,0,0,0.6)" : "none",
                          boxShadow: (input.trim() && !loading) ? `0 6px 16px ${accent}60, inset 0 1px 2px rgba(255,255,255,0.4)` : "inset 0 2px 4px rgba(0,0,0,0.4)",
                          transition: "all 0.2s ease cursor-pointer active:scale-95",
                          cursor: (input.trim() && !loading) ? "pointer" : "not-allowed"
                        }}>SEND</button>
                      )}
                    </div>
                  </div>
                  
                  {/* Subtle island hint */}
                  {(!input.trim() && !loading) && (
                    <div style={{
                      textAlign: "center", fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                      color: "#475569", letterSpacing: "0.15em", marginTop: -2, paddingBottom: 2
                    }}>
                      {currentMode.toUpperCase()} MODE · {currentModel.toUpperCase()}
                    </div>
                  )}
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
              {tab === "chat" && <ErrorBoundary><AgentTrace messages={messages} /></ErrorBoundary>}


      </div>

      <ProactiveAlerts />
    </div>
  );
}