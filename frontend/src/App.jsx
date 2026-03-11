import { useState, useEffect, useRef, useCallback } from "react";
import LiveVision from "./components/LiveVision";
import KnowledgeGraph from "./components/KnowledgeGraph";
import ProactiveAlerts from "./components/ProactiveAlerts";
import AgentTrace from "./components/AgentTrace";
import API from "./config";
import { useAstraWS } from "./hooks/useAstraWS";

const agentLabel = (a) => {
  if (a?.includes("mistral")) return "MISTRAL";
  if (a?.includes("llama"))   return "LLAMA";
  if (a?.includes("phi3"))    return "PHI3";
  if (a === "web_search_agent")  return "WEBSEARCH";
  if (a === "memory")            return "MEMORY";
  if (a === "intent_handler")    return "SHORTCUT";
  if (a === "system_controller") return "SYSCTRL";
  if (a === "calendar")          return "CALENDAR";
  if (a === "chain_executor")    return "CHAIN";
  return (a || "ASTRA").toUpperCase().slice(0, 10);
};

const emotionColor = (e) => ({
  joy:"#00ff88", sad:"#4488ff", angry:"#ff4444",
  anxious:"#ffaa00", tired:"#8899aa", surprised:"#ff88ff", neutral:"#00d4ff"
}[e] || "#00d4ff");

// ── Waveform ────────────────────────────────────────────────────────────────
function Waveform({ active, color = "#00d4ff", bars = 28 }) {
  const [heights, setHeights] = useState(() => Array(bars).fill(0.08));
  const ref = useRef(null);
  useEffect(() => {
    if (!active) { setHeights(Array(bars).fill(0.08)); return; }
    const animate = () => {
      setHeights(Array(bars).fill(0).map((_, i) => {
        const c = Math.abs(i - bars / 2) / (bars / 2);
        return (1 - c * 0.45) * 0.3 + Math.random() * 0.7;
      }));
      ref.current = setTimeout(animate, 70);
    };
    animate();
    return () => clearTimeout(ref.current);
  }, [active, bars]);
  return (
    <div style={{ display:"flex", alignItems:"center", gap:2, height:32 }}>
      {heights.map((h, i) => (
        <div key={i} style={{
          width:2.5, borderRadius:2,
          height:`${Math.max(h*100, 6)}%`,
          background: active
            ? `linear-gradient(to top, ${color}88, ${color}ff)`
            : "rgba(0,212,255,0.1)",
          boxShadow: active ? `0 0 3px ${color}66` : "none",
          transition:"height 0.06s ease",
        }} />
      ))}
    </div>
  );
}

// ── Stat bar ────────────────────────────────────────────────────────────────
function StatBar({ label, value = 0, color = "#00d4ff" }) {
  const c = value > 80 ? "#ff4444" : value > 60 ? "#ffaa00" : color;
  return (
    <div style={{ marginBottom:6 }}>
      <div style={{ display:"flex", justifyContent:"space-between", fontSize:8, color:"rgba(0,212,255,0.4)", marginBottom:2, letterSpacing:1 }}>
        <span>{label}</span><span style={{ color:c }}>{value}%</span>
      </div>
      <div style={{ height:2, background:"rgba(0,212,255,0.06)", borderRadius:1, overflow:"hidden" }}>
        <div style={{ height:"100%", width:`${value}%`, borderRadius:1, background:c, boxShadow:`0 0 4px ${c}`, transition:"width 1.2s ease" }} />
      </div>
    </div>
  );
}

// ── Glass panel ─────────────────────────────────────────────────────────────
function GlassPanel({ children, style }) {
  return (
    <div style={{
      background:"rgba(0,212,255,0.02)",
      border:"1px solid rgba(0,212,255,0.08)",
      backdropFilter:"blur(10px)",
      padding:"9px 11px", marginBottom:8,
      ...style
    }}>{children}</div>
  );
}

function PanelLabel({ children }) {
  return (
    <div style={{ fontSize:7, letterSpacing:4, color:"rgba(0,212,255,0.28)", marginBottom:7, textTransform:"uppercase" }}>
      {children}
    </div>
  );
}

// ── Thinking dots ────────────────────────────────────────────────────────────
function ThinkingDots() {
  const [dot, setDot] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setDot(d => (d + 1) % 4), 350);
    return () => clearInterval(t);
  }, []);
  return (
    <span style={{ color:"rgba(0,212,255,0.5)", fontFamily:"monospace", fontSize:13 }}>
      {["⠋","⠙","⠹","⠸"][dot]} thinking
    </span>
  );
}

// ── Streaming token renderer ─────────────────────────────────────────────────
function StreamingText({ tokens }) {
  return (
    <span style={{ whiteSpace:"pre-wrap", wordBreak:"break-word" }}>
      {tokens}
      <span style={{
        display:"inline-block", width:8, height:14,
        background:"#00d4ff", marginLeft:2, verticalAlign:"middle",
        animation:"blink 0.7s steps(1) infinite",
        borderRadius:1,
      }} />
    </span>
  );
}

// ── System sidebar ───────────────────────────────────────────────────────────
function SystemSidebar({ health, memory, models, currentModel, onSwitchModel }) {
  const [sysInfo, setSysInfo] = useState(null);
  const [time, setTime]       = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const r = await fetch(`${API}/execute`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body: JSON.stringify({ command:"system_info" })
        });
        if (r.ok) setSysInfo(await r.json());
      } catch {}
    };
    fetch_();
    const t = setInterval(fetch_, 30000);
    return () => clearInterval(t);
  }, []);

  const cpu  = sysInfo?.cpu?.percent  ?? 0;
  const ram  = sysInfo?.memory?.percent ?? 0;
  const disk = sysInfo?.disk?.percent ?? 0;

  return (
    <div style={{
      width:180, flexShrink:0, display:"flex", flexDirection:"column", gap:0,
      borderLeft:"1px solid rgba(0,212,255,0.07)", padding:"12px 10px",
      overflowY:"auto", fontSize:10, color:"rgba(0,212,255,0.7)",
    }}>
      {/* Clock */}
      <GlassPanel>
        <div style={{ fontSize:18, fontWeight:200, letterSpacing:3, color:"#00d4ff", textAlign:"center", fontFamily:"monospace" }}>
          {time.toLocaleTimeString([], { hour:"2-digit", minute:"2-digit", second:"2-digit" })}
        </div>
        <div style={{ fontSize:8, textAlign:"center", color:"rgba(0,212,255,0.3)", letterSpacing:2, marginTop:2 }}>
          {time.toLocaleDateString([], { weekday:"short", month:"short", day:"numeric" }).toUpperCase()}
        </div>
      </GlassPanel>

      {/* System */}
      <GlassPanel>
        <PanelLabel>SYSTEM</PanelLabel>
        <StatBar label="CPU"  value={cpu}  color="#00ff88" />
        <StatBar label="RAM"  value={ram}  color="#00d4ff" />
        <StatBar label="DISK" value={disk} color="#ffaa00" />
      </GlassPanel>

      {/* Services */}
      <GlassPanel>
        <PanelLabel>SERVICES</PanelLabel>
        {[
          ["BRAIN",   health?.brain   ?? false],
          ["MEMORY",  health?.memory  ?? false],
          ["VOICE",   health?.voice   ?? false],
          ["OLLAMA",  health?.ollama  ?? false],
        ].map(([name, ok]) => (
          <div key={name} style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
            <span style={{ letterSpacing:1, fontSize:8, color:"rgba(0,212,255,0.4)" }}>{name}</span>
            <span style={{ color: ok ? "#00ff88" : "#ff4444", fontSize:9 }}>{ok ? "●" : "○"}</span>
          </div>
        ))}
      </GlassPanel>

      {/* Model switcher */}
      <GlassPanel>
        <PanelLabel>NEURAL NET</PanelLabel>
        {(models || ["phi3:mini"]).map(m => (
          <div key={m} onClick={() => onSwitchModel?.(m)}
            style={{
              padding:"4px 7px", marginBottom:3, cursor:"pointer", borderRadius:2,
              fontSize:8, letterSpacing:1,
              background: currentModel === m ? "rgba(0,212,255,0.12)" : "transparent",
              color: currentModel === m ? "#00d4ff" : "rgba(0,212,255,0.35)",
              border: currentModel === m ? "1px solid rgba(0,212,255,0.25)" : "1px solid transparent",
              transition:"all 0.2s",
            }}>
            {m.toUpperCase()}
          </div>
        ))}
      </GlassPanel>

      {/* Memory stats */}
      <GlassPanel>
        <PanelLabel>MEMORY CORE</PanelLabel>
        <div style={{ fontSize:9, color:"rgba(0,212,255,0.35)", lineHeight:1.8 }}>
          <div>FACTS  <span style={{ color:"#00d4ff", float:"right" }}>{memory?.user_facts?.length ?? 0}</span></div>
          <div>TASKS  <span style={{ color:"#ffaa00", float:"right" }}>{memory?.tasks?.filter(t=>t.status==="todo").length ?? 0}</span></div>
          <div>CONVOS <span style={{ color:"#00ff88", float:"right" }}>{memory?.conversation_count ?? 0}</span></div>
        </div>
      </GlassPanel>
    </div>
  );
}

// ── ArcReactor ───────────────────────────────────────────────────────────────
function ArcReactor({ active, emotion }) {
  const color  = emotionColor(emotion);
  const [pulse, setPulse] = useState(0);
  useEffect(() => {
    if (!active) return;
    const t = setInterval(() => setPulse(p => (p + 1) % 3), 600);
    return () => clearInterval(t);
  }, [active]);
  return (
    <div style={{ width:44, height:44, position:"relative", flexShrink:0 }}>
      {[38, 28, 18].map((size, i) => (
        <div key={i} style={{
          position:"absolute",
          top:"50%", left:"50%",
          transform:"translate(-50%,-50%)",
          width:size, height:size,
          borderRadius:"50%",
          border:`1px solid ${color}`,
          opacity: active ? (0.9 - i * 0.2) + (pulse === i ? 0.3 : 0) : 0.2,
          boxShadow: active ? `0 0 ${6 + i * 4}px ${color}44` : "none",
          transition:"opacity 0.4s ease",
        }} />
      ))}
      <div style={{
        position:"absolute", top:"50%", left:"50%",
        transform:"translate(-50%,-50%)",
        width:8, height:8, borderRadius:"50%",
        background: active ? color : "rgba(0,212,255,0.2)",
        boxShadow: active ? `0 0 10px ${color}` : "none",
        transition:"all 0.4s",
      }} />
    </div>
  );
}

// ── Chat message ──────────────────────────────────────────────────────────────
function Message({ msg, isStreaming }) {
  const isUser  = msg.role === "user";
  const emotion = msg.emotion || "neutral";
  const color   = emotionColor(emotion);

  return (
    <div style={{
      display:"flex", justifyContent: isUser ? "flex-end" : "flex-start",
      marginBottom:14, alignItems:"flex-start", gap:10,
    }}>
      {!isUser && (
        <div style={{
          width:28, height:28, borderRadius:"50%", flexShrink:0, marginTop:4,
          border:`1px solid ${color}44`,
          display:"flex", alignItems:"center", justifyContent:"center",
          fontSize:10, color:color,
        }}>A</div>
      )}
      <div style={{ maxWidth:"72%", minWidth:60 }}>
        <div style={{
          padding:"11px 15px",
          background: isUser
            ? "rgba(0,212,255,0.08)"
            : "rgba(255,255,255,0.03)",
          border: isUser
            ? "1px solid rgba(0,212,255,0.18)"
            : `1px solid ${color}22`,
          backdropFilter:"blur(12px)",
          color:"rgba(255,255,255,0.88)",
          fontSize:13.5, lineHeight:1.65,
          whiteSpace:"pre-wrap", wordBreak:"break-word",
          position:"relative", overflow:"hidden",
        }}>
          {/* Sheen overlay */}
          <div style={{
            position:"absolute", top:0, left:0, right:0, height:1,
            background: `linear-gradient(90deg, transparent, ${color}33, transparent)`,
            pointerEvents:"none",
          }} />
          {isStreaming
            ? <StreamingText tokens={msg.content} />
            : msg.content
          }
        </div>
        {/* Metadata row */}
        {!isUser && msg.agent && (
          <div style={{ marginTop:4, display:"flex", gap:8, alignItems:"center" }}>
            <span style={{ fontSize:8, color:"rgba(0,212,255,0.25)", letterSpacing:2 }}>
              {agentLabel(msg.agent)}
            </span>
            {msg.confidence && (
              <span style={{ fontSize:8, color:"rgba(0,212,255,0.2)" }}>
                {Math.round(msg.confidence * 100)}%
              </span>
            )}
            {msg.intent && (
              <span style={{ fontSize:8, color:"rgba(0,212,255,0.2)", letterSpacing:1 }}>
                {msg.intent.toUpperCase()}
              </span>
            )}
          </div>
        )}
      </div>
      {isUser && (
        <div style={{
          width:28, height:28, borderRadius:"50%", flexShrink:0, marginTop:4,
          border:"1px solid rgba(0,212,255,0.2)",
          display:"flex", alignItems:"center", justifyContent:"center",
          fontSize:10, color:"rgba(0,212,255,0.5)",
        }}>U</div>
      )}
    </div>
  );
}

// ════════════════════════════════════════════════════════════════════════════
// MAIN APP
// ════════════════════════════════════════════════════════════════════════════
export default function App() {
  const [messages,     setMessages]     = useState([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [streaming,    setStreaming]     = useState(false);
  const [streamBuffer, setStreamBuffer] = useState("");
  const [tab,          setTab]          = useState("chat");
  const [health,       setHealth]       = useState({});
  const [memory,       setMemory]       = useState({});
  const [models,       setModels]       = useState([]);
  const [currentModel, setCurrentModel] = useState("phi3:mini");
  const [emotion,      setEmotion]      = useState("neutral");
  const [voicePlaying, setVoicePlaying] = useState(false);
  const [useStream,    setUseStream]    = useState(true);
  const [currentMode,  setCurrentMode]  = useState("jarvis");
  const [modes,        setModes]        = useState([]);

  const bottomRef  = useRef(null);
  const inputRef   = useRef(null);
  const abortRef   = useRef(null);

  // ── Auto-scroll ──────────────────────────────────────────────────────────
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior:"smooth" });
  }, [messages, streamBuffer]);

  // ── Health + Memory poll ─────────────────────────────────────────────────
  useEffect(() => {
    const poll = async () => {
      try {
        const [h, m, mdl, modeData] = await Promise.all([
          fetch(`${API}/health`).then(r => r.json()).catch(() => ({})),
          fetch(`${API}/memory`).then(r => r.json()).catch(() => ({})),
          fetch(`${API}/model`).then(r => r.json()).catch(() => ({})),
          fetch(`${API}/mode/list`).then(r => r.json()).catch(() => ({})),
        ]);
        setHealth(h);
        setMemory(m);
        if (mdl.available) setModels(mdl.available);
        if (mdl.current)   setCurrentModel(mdl.current);
        if (modeData.modes) setModes(modeData.modes);
        if (modeData.current) setCurrentMode(modeData.current);
      } catch {}
    };
    poll();
    const t = setInterval(poll, 20000);
    return () => clearInterval(t);
  }, []);

  // ── Switch model ─────────────────────────────────────────────────────────
  const switchModel = useCallback(async (model) => {
    try {
      await fetch(`${API}/model/set`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ model })
      });
      setCurrentModel(model);
    } catch {}
  }, []);

  // ── Switch mode ─────────────────────────────────────────────────────────────
  const switchMode = useCallback(async (modeId) => {
    try {
      const r = await fetch(`${API}/mode/set`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ mode:modeId })
      });
      const d = await r.json();
      if (d.mode) setCurrentMode(d.mode);
    } catch {}
  }, []);

  // ── Send message — streaming ─────────────────────────────────────────────
  const sendStream = useCallback(async (text) => {
    setLoading(true);
    setStreaming(true);
    setStreamBuffer("");

    const userMsg = { role:"user", content:text, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);

    let buffer = "";
    try {
      const controller = new AbortController();
      abortRef.current = controller;

      const res = await fetch(`${API}/chat/stream`, {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ message:text }),
        signal: controller.signal,
      });

      const reader = res.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const text_ = decoder.decode(value);
        const lines = text_.split("\n");
        for (const line of lines) {
          if (!line.startsWith("data:")) continue;
          try {
            const data = JSON.parse(line.slice(5));
            if (data.token) {
              buffer += data.token;
              setStreamBuffer(buffer);
            }
            if (data.done) break;
          } catch {}
        }
      }
    } catch (e) {
      if (e.name !== "AbortError") {
        buffer = "Connection error. Is the backend running?";
        setStreamBuffer(buffer);
      }
    }

    // Commit streamed message
    const assistantMsg = {
      role:"assistant", content:buffer,
      agent:`ollama/${currentModel}`,
      id: Date.now() + 1,
    };
    setMessages(prev => [...prev, assistantMsg]);
    setStreamBuffer("");
    setStreaming(false);
    setLoading(false);
  }, [currentModel]);

  // ── Send message — standard ──────────────────────────────────────────────
  const sendStandard = useCallback(async (text) => {
    setLoading(true);
    const userMsg = { role:"user", content:text, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);

    try {
      const r = await fetch(`${API}/chat`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body: JSON.stringify({ message:text }),
      });
      const data = await r.json();
      setEmotion(data.emotion || "neutral");
      setMessages(prev => [...prev, {
        role:"assistant", content:data.reply,
        agent:data.agent, intent:data.intent,
        confidence:data.confidence, emotion:data.emotion,
        id: Date.now() + 1,
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role:"assistant", content:"Connection error.",
        id: Date.now() + 1,
      }]);
    }
    setLoading(false);
  }, []);

  // ── WebSocket setup ──────────────────────────────────────────────────────
  const wsMetaRef   = useRef(null);
  const wsBufferRef = useRef("");

  const { send: wsSend, connected: wsConnected } = useAstraWS({
    onToken: (token) => {
      wsBufferRef.current += token;
      setStreamBuffer(wsBufferRef.current);
    },
    onMeta: (meta) => {
      wsMetaRef.current = meta;
    },
    onDone: () => {
      const buffer = wsBufferRef.current;
      const meta   = wsMetaRef.current || {};
      setMessages(prev => [...prev, {
        role: "assistant", content: buffer,
        agent:      meta.agent      || `ollama/${currentModel}`,
        intent:     meta.intent     || "general",
        confidence: meta.confidence || 0.8,
        emotion:    meta.emotion    || "neutral",
        id: Date.now() + 1,
      }]);
      setStreamBuffer("");
      wsBufferRef.current  = "";
      wsMetaRef.current    = null;
      setStreaming(false);
      setLoading(false);
    },
    onError: (err) => {
      setMessages(prev => [...prev, {
        role: "assistant", content: `Error: ${err}`,
        id: Date.now() + 1,
      }]);
      setStreamBuffer("");
      wsBufferRef.current = "";
      setStreaming(false);
      setLoading(false);
    },
  });

  // ── Send via WebSocket (with HTTP fallback) ───────────────────────────────
  const sendStreamWS = useCallback((text) => {
    setLoading(true);
    setStreaming(true);
    setStreamBuffer("");
    wsBufferRef.current = "";
    wsMetaRef.current   = null;

    const userMsg = { role: "user", content: text, id: Date.now() };
    setMessages(prev => [...prev, userMsg]);

    const sent = wsSend(text);
    if (!sent) {
      // WS not ready — fall back to HTTP stream
      sendStream(text);
    }
  }, [wsSend, sendStream]);

  const send = useCallback(() => {
    const text = input.trim();
    if (!text || loading) return;
    setInput("");
    if (useStream && wsConnected) sendStreamWS(text);
    else if (useStream) sendStream(text);
    else           sendStandard(text);
    inputRef.current?.focus();
  }, [input, loading, useStream, sendStream, sendStandard]);

  const onKey = (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); }
  };

  const stopStream = () => {
    abortRef.current?.abort();
    setStreaming(false);
    setLoading(false);
  };

  // ── Tabs ─────────────────────────────────────────────────────────────────
  const tabs = [
    { id:"chat",   label:"◈  INTERFACE" },
    { id:"vision", label:"◉  VISION"    },
    { id:"graph",  label:"⬡  MEMORY"    },
  ];

  const tabStyle = (id) => ({
    padding:"8px 16px", cursor:"pointer",
    fontSize:9, letterSpacing:3, fontWeight:500,
    color: tab === id ? "#00d4ff" : "rgba(0,212,255,0.3)",
    borderBottom: tab === id ? "1px solid #00d4ff" : "1px solid transparent",
    background:"transparent", border:"none",
    borderBottom: tab === id ? "1px solid #00d4ff" : "1px solid transparent",
    transition:"all 0.2s",
  });

  return (
    <div style={{
      background:"#050a0f", color:"rgba(255,255,255,0.85)",
      height:"100vh", display:"flex", flexDirection:"column",
      fontFamily:"-apple-system, 'SF Pro Display', sans-serif",
      overflow:"hidden",
    }}>
      <style>{`
        * { box-sizing: border-box; }
        ::-webkit-scrollbar { width:3px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:rgba(0,212,255,0.15); border-radius:2px; }
        textarea:focus { outline:none; }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
      `}</style>

      {/* Header */}
      <div style={{
        display:"flex", alignItems:"center", justifyContent:"space-between",
        padding:"10px 20px",
        borderBottom:"1px solid rgba(0,212,255,0.08)",
        background:"rgba(0,0,0,0.4)",
        backdropFilter:"blur(20px)",
      }}>
        <div style={{ display:"flex", alignItems:"center", gap:12 }}>
          <ArcReactor active={loading || streaming} emotion={emotion} />
          <div>
            <div style={{ fontSize:15, fontWeight:300, letterSpacing:5, color:"#00d4ff" }}>ASTRA</div>
            <div style={{ fontSize:7, letterSpacing:4, color:"rgba(0,212,255,0.3)" }}>
              PERSONAL AI · {currentModel.toUpperCase()}
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display:"flex", gap:0 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)} style={tabStyle(t.id)}>
              {t.label}
            </button>
          ))}
        </div>

        {/* Mode switcher */}
        <div style={{ display:"flex", gap:3, padding:"0 12px", borderLeft:"1px solid rgba(0,212,255,0.1)", alignItems:"center" }}>
          {modes.map(m => {
            const active = m.id === currentMode;
            const col = { jarvis:"#00d4ff", focus:"#ff6b35", chill:"#00ff88", expert:"#bf5fff", debug:"#ffaa00" }[m.id] || "#00d4ff";
            return (
              <button key={m.id} onClick={() => switchMode(m.id)} title={m.description} style={{
                background: active ? `${col}18` : "transparent",
                border: `1px solid ${active ? col+"66" : "rgba(0,212,255,0.08)"}`,
                color: active ? col : "rgba(0,212,255,0.22)",
                fontFamily:"'Courier New',monospace", fontSize:8,
                padding:"4px 9px", cursor:"pointer", letterSpacing:1,
                boxShadow: active ? `0 0 8px ${col}44` : "none",
                transition:"all 0.18s",
              }}>
                {m.emoji} {m.name}
              </button>
            );
          })}
        </div>

        {/* Voice waveform */}
        <div style={{ width:100, display:"flex", alignItems:"center", gap:8 }}>
          <Waveform active={voicePlaying} color="#00ff88" bars={16} />
          <div style={{
            fontSize:7, letterSpacing:3,
            color: voicePlaying ? "#00ff88" : "rgba(0,212,255,0.2)",
          }}>
            {voicePlaying ? "SPEAKING" : "IDLE"}
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ flex:1, display:"flex", overflow:"hidden" }}>

        {/* Main content */}
        <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden" }}>

          {tab === "chat" && (
            <>
              {/* Messages */}
              <div style={{ flex:1, overflowY:"auto", padding:"20px 24px" }}>
                {messages.length === 0 && (
                  <div style={{
                    height:"100%", display:"flex", flexDirection:"column",
                    alignItems:"center", justifyContent:"center", gap:8,
                    color:"rgba(0,212,255,0.15)",
                  }}>
                    <div style={{ fontSize:48, fontWeight:100, letterSpacing:12 }}>ASTRA</div>
                    <div style={{ fontSize:9, letterSpacing:6 }}>SYSTEMS READY · AWAITING INPUT</div>
                  </div>
                )}
                {messages.map(msg => (
                  <Message key={msg.id} msg={msg} isStreaming={false} />
                ))}
                {/* Live streaming message */}
                {streaming && streamBuffer && (
                  <Message
                    msg={{ role:"assistant", content:streamBuffer, agent:`ollama/${currentModel}` }}
                    isStreaming={true}
                  />
                )}
                {/* Thinking indicator */}
                {loading && !streaming && (
                  <div style={{ marginBottom:14, paddingLeft:38 }}>
                    <ThinkingDots />
                  </div>
                )}
                <div ref={bottomRef} />
              </div>

              {/* Input bar */}
              <div style={{
                padding:"12px 20px",
                borderTop:"1px solid rgba(0,212,255,0.07)",
                background:"rgba(0,0,0,0.5)",
                backdropFilter:"blur(20px)",
              }}>
                <div style={{
                  display:"flex", alignItems:"center", gap:10,
                  background:"rgba(0,212,255,0.04)",
                  border:"1px solid rgba(0,212,255,0.12)",
                  padding:"6px 12px",
                }}>
                  <Waveform active={loading} color="#00d4ff" bars={20} />
                  <textarea
                    ref={inputRef}
                    value={input}
                    onChange={e => setInput(e.target.value)}
                    onKeyDown={onKey}
                    placeholder="speak to ASTRA..."
                    rows={1}
                    style={{
                      flex:1, background:"transparent", border:"none",
                      color:"rgba(255,255,255,0.85)", fontSize:14,
                      resize:"none", fontFamily:"inherit", lineHeight:1.5,
                      minHeight:24, maxHeight:120, padding:0,
                    }}
                  />
                  {/* Stream toggle */}
                  <div
                    onClick={() => setUseStream(s => !s)}
                    title={useStream ? "Streaming ON" : "Streaming OFF"}
                    style={{
                      fontSize:8, letterSpacing:2, cursor:"pointer",
                      color: useStream ? "#00ff88" : "rgba(0,212,255,0.25)",
                      padding:"3px 6px",
                      border: `1px solid ${useStream ? "rgba(0,255,136,0.3)" : "rgba(0,212,255,0.1)"}`,
                    }}>
                    SSE
                  </div>
                  {streaming
                    ? <button onClick={stopStream} style={{
                        background:"rgba(255,68,68,0.15)", border:"1px solid rgba(255,68,68,0.3)",
                        color:"#ff4444", fontSize:9, letterSpacing:2, padding:"5px 10px", cursor:"pointer",
                      }}>STOP</button>
                    : <button onClick={send} disabled={!input.trim() || loading} style={{
                        background: input.trim() ? "rgba(0,212,255,0.1)" : "transparent",
                        border:`1px solid ${input.trim() ? "rgba(0,212,255,0.3)" : "rgba(0,212,255,0.08)"}`,
                        color: input.trim() ? "#00d4ff" : "rgba(0,212,255,0.2)",
                        fontSize:9, letterSpacing:2, padding:"5px 12px", cursor:"pointer",
                        transition:"all 0.2s",
                      }}>SEND</button>
                  }
                </div>
                <div style={{ marginTop:5, display:"flex", gap:16, fontSize:8, color:"rgba(0,212,255,0.2)", letterSpacing:1 }}>
                  <span>ENTER to send · SHIFT+ENTER newline</span>
                  <span style={{ marginLeft:"auto" }}>
                    {useStream ? "⚡ STREAMING" : "◉ STANDARD"} · {currentModel.toUpperCase()}
                  </span>
                </div>
              </div>
            </>
          )}

          {tab === "vision" && (
            <div style={{ flex:1, padding:20, overflow:"auto" }}>
              <LiveVision />
            </div>
          )}

          {tab === "graph" && (
            <div style={{ flex:1, overflow:"hidden" }}>
              <KnowledgeGraph />
            </div>
          )}
        </div>

        {/* Sidebar */}
        {tab === "chat" && (
          <SystemSidebar
            health={health} memory={memory}
            models={models} currentModel={currentModel}
            onSwitchModel={switchModel}
          />
        )}
      </div>

      {/* Proactive alerts */}
      <AgentTrace messages={messages} />
      <ProactiveAlerts />
      
    </div>
  );
}
