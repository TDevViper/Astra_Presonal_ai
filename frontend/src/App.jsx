import { useState, useEffect, useRef, useCallback } from "react";
import LiveVision from "./components/LiveVision";
import KnowledgeGraph from "./components/KnowledgeGraph";
import ProactiveAlerts from "./components/ProactiveAlerts";
import API from "./config";

const agentLabel = (a) => {
  if (a?.includes("mistral")) return "MISTRAL";
  if (a?.includes("llama"))   return "LLAMA";
  if (a?.includes("phi3"))    return "PHI3";
  if (a === "web_search_agent")  return "WEBSEARCH";
  if (a === "memory")            return "MEMORY";
  if (a === "intent_handler")    return "SHORTCUT";
  if (a === "system_controller") return "SYSCTRL";
  if (a === "calendar")          return "CALENDAR";
  if (a === "whatsapp")          return "WHATSAPP";
  return (a || "ASTRA").toUpperCase();
};

const emotionColor = (e) => ({
  joy:"#00ff88", sad:"#4488ff", angry:"#ff4444",
  anxious:"#ffaa00", tired:"#8899aa", surprised:"#ff88ff", neutral:"#00d4ff"
}[e] || "#00d4ff");

function Waveform({ active, color = "#00d4ff", bars = 32 }) {
  const [heights, setHeights] = useState(() => Array(bars).fill(0.1));
  const timerRef = useRef(null);

  useEffect(() => {
    if (!active) {
      setHeights(Array(bars).fill(0.1));
      return;
    }
    const animate = () => {
      setHeights(Array(bars).fill(0).map((_, i) => {
        const center = Math.abs(i - bars / 2) / (bars / 2);
        return (1 - center * 0.5) * 0.35 + Math.random() * 0.65;
      }));
      timerRef.current = setTimeout(animate, 75);
    };
    animate();
    return () => clearTimeout(timerRef.current);
  }, [active, bars]);

  return (
    <div style={{ display:"flex", alignItems:"center", gap:2, height:36, padding:"0 4px" }}>
      {heights.map((h, i) => (
        <div key={i} style={{
          width:3, borderRadius:2,
          height:`${Math.max(h * 100, 8)}%`,
          background: active
            ? `linear-gradient(to top, ${color}99, ${color})`
            : `rgba(0,212,255,0.12)`,
          boxShadow: active ? `0 0 4px ${color}88` : "none",
          transition:"height 0.07s ease",
        }} />
      ))}
    </div>
  );
}

function StatBar({ label, value = 0, color = "#00d4ff" }) {
  const barColor = value > 80 ? "#ff4444" : value > 60 ? "#ffaa00" : color;
  return (
    <div style={{ marginBottom:7 }}>
      <div style={{ display:"flex", justifyContent:"space-between", fontSize:8, color:"rgba(0,212,255,0.45)", marginBottom:3, letterSpacing:1 }}>
        <span>{label}</span>
        <span style={{ color:barColor }}>{value}%</span>
      </div>
      <div style={{ height:2, background:"rgba(0,212,255,0.07)", borderRadius:1, overflow:"hidden" }}>
        <div style={{
          height:"100%", width:`${value}%`, borderRadius:1,
          background:barColor, boxShadow:`0 0 5px ${barColor}`,
          transition:"width 1.2s ease"
        }} />
      </div>
    </div>
  );
}

function GlassPanel({ children, style }) {
  return (
    <div style={{
      background:"rgba(0,212,255,0.025)",
      border:"1px solid rgba(0,212,255,0.09)",
      backdropFilter:"blur(12px)",
      padding:"10px 12px", marginBottom:9,
      ...style
    }}>{children}</div>
  );
}

function PanelLabel({ children }) {
  return (
    <div style={{ fontSize:7, letterSpacing:4, color:"rgba(0,212,255,0.3)", marginBottom:8, textTransform:"uppercase" }}>
      {children}
    </div>
  );
}

function SystemSidebar({ health, memory, models, currentModel, onSwitchModel }) {
  const [sysInfo, setSysInfo] = useState(null);
  const [time, setTime]       = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchSys = async () => {
      try {
        const r = await fetch(`${API}/execute`, {
          method:"POST", headers:{"Content-Type":"application/json"},
          body:JSON.stringify({ command:"system_info" })
        });
        if (r.ok) setSysInfo(await r.json());
      } catch {}
    };
    fetchSys();
    const t = setInterval(fetchSys, 12000);
    return () => clearInterval(t);
  }, []);

  const facts    = memory?.user_facts || [];
  const emotions = memory?.emotional_patterns?.history?.slice(-3).reverse() || [];

  return (
    <div style={{
      width:220, minWidth:220, height:"100vh",
      background:"linear-gradient(180deg,rgba(0,5,12,0.98) 0%,rgba(0,2,8,0.99) 100%)",
      borderRight:"1px solid rgba(0,212,255,0.07)",
      display:"flex", flexDirection:"column",
      fontFamily:"'Courier New',monospace",
      overflow:"hidden", position:"relative", flexShrink:0,
    }}>
      <div style={{ position:"absolute", top:0, left:0, right:0, height:1, background:"linear-gradient(90deg,transparent,#00d4ff60,transparent)" }} />

      <div style={{ padding:"16px 14px 12px", borderBottom:"1px solid rgba(0,212,255,0.07)" }}>
        <div style={{ fontSize:7, letterSpacing:5, color:"rgba(0,212,255,0.25)", marginBottom:3 }}>STARK INDUSTRIES</div>
        <div style={{ fontSize:13, letterSpacing:4, color:"#00d4ff", fontWeight:"bold", textShadow:"0 0 14px rgba(0,212,255,0.6)" }}>
          ◈ ASTRA v3.0
        </div>
        <div style={{ marginTop:9, display:"flex", alignItems:"center", gap:6 }}>
          <div style={{ width:5, height:5, borderRadius:"50%", background:"#00ff88", boxShadow:"0 0 8px #00ff88", animation:"pulse 2s infinite" }} />
          <span style={{ fontSize:9, letterSpacing:2, color:"rgba(0,255,136,0.7)" }}>
            {time.toLocaleTimeString("en-US",{hour12:false})}
          </span>
        </div>
      </div>

      <div style={{ flex:1, overflowY:"auto", padding:"10px 12px" }}>

        <GlassPanel>
          <PanelLabel>Operator</PanelLabel>
          <div style={{ fontSize:13, color:"#00d4ff", letterSpacing:2, fontWeight:"bold", textShadow:"0 0 10px rgba(0,212,255,0.5)" }}>
            {memory?.preferences?.name || "ARNAV"}
          </div>
          {memory?.preferences?.location && (
            <div style={{ fontSize:9, color:"rgba(0,212,255,0.35)", marginTop:4, letterSpacing:1 }}>▲ {memory.preferences.location}</div>
          )}
        </GlassPanel>

        {sysInfo?.cpu && (
          <GlassPanel>
            <PanelLabel>System Load</PanelLabel>
            <StatBar label="CPU"  value={sysInfo.cpu?.percent}    color="#00d4ff" />
            <StatBar label="RAM"  value={sysInfo.memory?.percent} color="#00ff88" />
            <StatBar label="DISK" value={sysInfo.disk?.percent}   color="#ffaa00" />
          </GlassPanel>
        )}

        {emotions.length > 0 && (
          <GlassPanel>
            <PanelLabel>Affect Scan</PanelLabel>
            {emotions.map((e,i) => (
              <div key={i} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:6 }}>
                <div style={{ display:"flex", alignItems:"center", gap:5 }}>
                  <div style={{ width:4, height:4, borderRadius:"50%", background:emotionColor(e.label), boxShadow:`0 0 5px ${emotionColor(e.label)}` }} />
                  <span style={{ fontSize:9, color:emotionColor(e.label), letterSpacing:1 }}>{e.label?.toUpperCase()}</span>
                </div>
                <span style={{ fontSize:8, color:"rgba(0,212,255,0.3)" }}>{(e.score*100).toFixed(0)}%</span>
              </div>
            ))}
          </GlassPanel>
        )}

        {facts.length > 0 && (
          <GlassPanel>
            <PanelLabel>Intel ({facts.length})</PanelLabel>
            {facts.slice(-5).map((f,i) => (
              <div key={i} style={{ fontSize:9, color:"rgba(0,212,255,0.38)", marginBottom:5, lineHeight:1.5, paddingLeft:7, borderLeft:"1px solid rgba(0,212,255,0.15)" }}>
                {f.fact?.slice(0,48)}
              </div>
            ))}
          </GlassPanel>
        )}

        <GlassPanel>
          <PanelLabel>Neural Net</PanelLabel>
          {models.map(m => (
            <div key={m} onClick={() => onSwitchModel(m)} style={{
              display:"flex", alignItems:"center", gap:8, padding:"5px 0",
              cursor:"pointer", borderBottom:"1px solid rgba(0,212,255,0.05)",
              color: currentModel===m ? "#00d4ff" : "rgba(0,212,255,0.22)",
              transition:"color 0.2s",
            }}>
              <div style={{
                width:5, height:5, borderRadius:"50%",
                background: currentModel===m ? "#00d4ff" : "transparent",
                border:"1px solid rgba(0,212,255,0.3)",
                boxShadow: currentModel===m ? "0 0 8px #00d4ff" : "none", flexShrink:0,
              }} />
              <span style={{ fontSize:9, letterSpacing:1 }}>{m.split(":")[0].toUpperCase()}</span>
              {currentModel===m && <span style={{ marginLeft:"auto", fontSize:7, color:"#00ff88", letterSpacing:1 }}>LIVE</span>}
            </div>
          ))}
        </GlassPanel>

        {health && (
          <GlassPanel>
            <PanelLabel>Services</PanelLabel>
            {[["OLLAMA",health.ollama?.status],["MEMORY",health.memory?.status],["VECTORS",health.vectors?.status]].map(([n,s]) => (
              <div key={n} style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
                <span style={{ fontSize:8, color:"rgba(0,212,255,0.38)", letterSpacing:1 }}>{n}</span>
                <span style={{ fontSize:8, color:s==="ok"?"#00ff88":"#ff4444", letterSpacing:1 }}>{s==="ok"?"◉ OK":"◎ ERR"}</span>
              </div>
            ))}
          </GlassPanel>
        )}
      </div>

      <div style={{ padding:"8px 14px", borderTop:"1px solid rgba(0,212,255,0.07)", fontSize:7, color:"rgba(0,212,255,0.12)", letterSpacing:3, textAlign:"center" }}>
        ASTRA · CLASSIFIED
      </div>
    </div>
  );
}

function ConfBar({ value }) {
  const segs   = 10;
  const filled = Math.round((value||0) * segs);
  const color  = value >= 0.9 ? "#00ff88" : value >= 0.6 ? "#00d4ff" : value >= 0.3 ? "#ffaa00" : "#ff4444";
  return (
    <span style={{ display:"flex", gap:1.5, alignItems:"center" }}>
      {Array.from({length:segs},(_,i) => (
        <span key={i} style={{ display:"inline-block", width:3, height:8, background:i<filled?color:"rgba(0,212,255,0.08)", boxShadow:i<filled?`0 0 4px ${color}`:"none" }} />
      ))}
      <span style={{ marginLeft:4, color, fontSize:9 }}>{((value||0)*100).toFixed(0)}%</span>
    </span>
  );
}

function ArcReactor({ active, size = 44 }) {
  return (
    <div style={{ position:"relative", width:size, height:size, flexShrink:0 }}>
      <div style={{ position:"absolute", inset:0, borderRadius:"50%", border:"1px solid rgba(0,212,255,0.3)", animation:active?"spin 8s linear infinite":"none" }}>
        {[0,90,180,270].map(deg => (
          <div key={deg} style={{
            position:"absolute", width:4, height:4, borderRadius:"50%",
            background:"#00d4ff", top:"50%", left:"50%",
            transform:`rotate(${deg}deg) translateX(${size/2-2}px) translate(-50%,-50%)`,
            boxShadow:"0 0 6px #00d4ff",
          }} />
        ))}
      </div>
      <div style={{ position:"absolute", inset:8, borderRadius:"50%", border:"1px solid rgba(0,212,255,0.5)", animation:active?"spin 4s linear infinite reverse":"none" }} />
      <div style={{
        position:"absolute", inset:size*0.35, borderRadius:"50%",
        background: active
          ? "radial-gradient(circle,#ffffff 0%,#00d4ff 40%,#0055ff 100%)"
          : "radial-gradient(circle,#0a1a2a 0%,#050d14 100%)",
        boxShadow: active ? "0 0 20px rgba(0,212,255,0.9),0 0 50px rgba(0,100,255,0.4)" : "none",
        transition:"all 0.5s ease",
      }} />
    </div>
  );
}

function Message({ msg }) {
  const isUser   = msg.role === "user";
  const isSystem = msg.role === "system";

  if (isSystem) return (
    <div style={{ textAlign:"center", padding:"4px 0", margin:"4px 0", fontSize:9, letterSpacing:3, color:"rgba(0,212,255,0.18)", fontFamily:"'Courier New',monospace" }}>
      ── {msg.content} ──
    </div>
  );

  const eColor = msg.emotion ? emotionColor(msg.emotion) : (isUser ? "#3388ff" : "#00d4ff");

  return (
    <div style={{ marginBottom:20, display:"flex", flexDirection:"column", alignItems:isUser?"flex-end":"flex-start", animation:"fadeUp 0.25s ease-out" }}>
      <div style={{ fontSize:8, letterSpacing:2, marginBottom:5, fontFamily:"'Courier New',monospace", display:"flex", alignItems:"center", gap:6, color:isUser?"rgba(50,136,255,0.6)":"rgba(0,212,255,0.45)" }}>
        {isUser ? <span>OPERATOR</span> : (
          <>
            <span style={{ color:"#00d4ff" }}>ASTRA</span>
            <span style={{ color:"rgba(0,212,255,0.18)" }}>◆</span>
            <span>{agentLabel(msg.agent)}</span>
            {msg.intent && <><span style={{ color:"rgba(0,212,255,0.18)" }}>◆</span><span style={{ color:"rgba(0,212,255,0.28)" }}>{msg.intent?.toUpperCase()}</span></>}
          </>
        )}
      </div>

      <div style={{
        maxWidth:"76%", padding:"13px 17px",
        background: isUser
          ? "linear-gradient(135deg,rgba(0,60,140,0.35) 0%,rgba(0,30,80,0.45) 100%)"
          : "linear-gradient(135deg,rgba(0,212,255,0.04) 0%,rgba(0,10,25,0.6) 100%)",
        border:`1px solid ${isUser?"rgba(0,100,255,0.25)":"rgba(0,212,255,0.12)"}`,
        backdropFilter:"blur(16px)",
        boxShadow: isUser
          ? "inset 0 0 30px rgba(0,80,180,0.08), 0 4px 20px rgba(0,0,0,0.3)"
          : "inset 0 0 30px rgba(0,212,255,0.02), 0 4px 20px rgba(0,0,0,0.3)",
        fontFamily:"'Courier New',monospace", fontSize:13,
        color: isUser ? "rgba(180,220,255,0.9)" : "rgba(200,240,255,0.85)",
        lineHeight:1.75, whiteSpace:"pre-wrap", wordBreak:"break-word",
        position:"relative", overflow:"hidden",
      }}>
        {/* Glass sheen */}
        <div style={{ position:"absolute", top:0, left:0, right:0, height:"40%", background:"linear-gradient(180deg,rgba(255,255,255,0.025) 0%,transparent 100%)", pointerEvents:"none" }} />
        {msg.content}
        {msg.streaming && (
          <span style={{ display:"inline-block", width:8, height:14, background:"#00d4ff", marginLeft:3, verticalAlign:"middle", animation:"blink 0.7s step-end infinite" }} />
        )}
      </div>

      {!isUser && msg.confidence !== undefined && (
        <div style={{ display:"flex", gap:12, marginTop:5, flexWrap:"wrap", fontSize:9, fontFamily:"'Courier New',monospace", color:"rgba(0,212,255,0.28)", letterSpacing:1 }}>
          <ConfBar value={msg.confidence} />
          {msg.emotion && msg.emotion !== "neutral" && (
            <span style={{ color:emotionColor(msg.emotion) }}>● {msg.emotion?.toUpperCase()}</span>
          )}
          {msg.tool_used     && <span style={{ color:"#00ff88" }}>⚡ TOOL</span>}
          {msg.memory_updated && <span style={{ color:"#ffaa00" }}>◈ SAVED</span>}
        </div>
      )}

      {msg.citations?.length > 0 && (
        <div style={{ marginTop:5, maxWidth:"76%", fontFamily:"'Courier New',monospace" }}>
          {msg.citations.slice(0,3).map(c => (
            <div key={c.index} style={{ fontSize:9, marginBottom:3, color:"rgba(0,212,255,0.28)" }}>
              <span style={{ color:"rgba(0,100,255,0.6)" }}>[{c.index}]</span>{" "}
              <a href={c.url} target="_blank" rel="noreferrer" style={{ color:"rgba(0,212,255,0.28)", textDecoration:"none" }}>{c.title?.slice(0,55)}</a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ThinkingDots() {
  return (
    <div style={{ display:"flex", alignItems:"center", gap:14, padding:"8px 0", fontFamily:"'Courier New',monospace" }}>
      <ArcReactor active={true} size={40} />
      <div>
        <div style={{ fontSize:10, letterSpacing:3, color:"rgba(0,212,255,0.5)", marginBottom:6 }}>ASTRA PROCESSING</div>
        <div style={{ display:"flex", gap:4 }}>
          {[0,1,2,3,4].map(i => (
            <div key={i} style={{ width:3, height:14, background:"#00d4ff", boxShadow:"0 0 6px #00d4ff", animation:`waveBar 1s ease-in-out ${i*0.1}s infinite` }} />
          ))}
        </div>
      </div>
    </div>
  );
}

function VoiceButton({ onTranscript, speaking }) {
  const [state, setState] = useState("idle");

  const handle = async () => {
    if (state !== "idle") return;
    setState("listening");
    try {
      const r = await fetch(`${API}/voice/listen`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ duration:5 }) });
      const d = await r.json();
      if (d.text?.trim()) onTranscript(d.text.trim());
    } catch (e) { console.error(e); }
    finally { setState("idle"); }
  };

  const color = state === "listening" ? "#ff4444" : speaking ? "#00ff88" : "#00d4ff";

  return (
    <button onClick={handle} disabled={state!=="idle"} style={{ position:"relative", background:"transparent", border:"none", cursor:state==="idle"?"pointer":"default", padding:0 }}>
      <div style={{
        width:38, height:38, borderRadius:"50%",
        border:`2px solid ${color}`,
        display:"flex", alignItems:"center", justifyContent:"center",
        background:`${color}12`,
        boxShadow:`0 0 ${state==="listening"?"20px":"10px"} ${color}44`,
        animation: state==="listening" ? "voicePulse 0.8s ease-in-out infinite" : "none",
        transition:"all 0.3s ease",
      }}>
        <span style={{ fontSize:15 }}>{state==="listening" ? "●" : "🎤"}</span>
      </div>
      {state==="listening" && (
        <div style={{ position:"absolute", inset:-5, borderRadius:"50%", border:`1px solid ${color}40`, animation:"ripple 1s ease-out infinite" }} />
      )}
    </button>
  );
}

export default function App() {
  const [tab,          setTab]          = useState("chat");
  const [messages,     setMessages]     = useState([]);
  const [input,        setInput]        = useState("");
  const [loading,      setLoading]      = useState(false);
  const [memory,       setMemory]       = useState({});
  const [models,       setModels]       = useState([]);
  const [currentModel, setCurrentModel] = useState("phi3:mini");
  const [status,       setStatus]       = useState("connecting");
  const [health,       setHealth]       = useState(null);
  const [speakReplies, setSpeakReplies] = useState(false);
  const [wakeActive,   setWakeActive]   = useState(false);
  const [isSpeaking,   setIsSpeaking]   = useState(false);
  const endRef   = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    checkHealth();
    fetchMemory();
    inputRef.current?.focus();
    fetch(`${API}/model/list`)
      .then(r => r.json())
      .then(d => setModels(d.models?.length ? d.models : ["phi3:mini"]))
      .catch(() => setModels(["phi3:mini"]));
  }, []); // eslint-disable-line

  useEffect(() => { endRef.current?.scrollIntoView({ behavior:"smooth" }); }, [messages]);

  const checkHealth = async () => {
    try {
      const r = await fetch(`${API}/health`);
      if (r.ok) {
        const d = await r.json();
        setHealth(d);
        setStatus("online");
        setCurrentModel(d.model || "phi3:mini");
        addSystem("ASTRA NEURAL CORE ONLINE · ALL SYSTEMS NOMINAL");
      }
    } catch {
      setStatus("offline");
      addSystem("BACKEND OFFLINE — RUN: python app.py");
    }
  };

  const fetchMemory = async () => {
    try {
      const r = await fetch(`${API}/memory`);
      if (r.ok) setMemory(await r.json());
    } catch {}
  };

  const addSystem = (text) => setMessages(p => [...p, { role:"system", content:text, id:Date.now() }]);

  const sendMessage = async (text = input.trim()) => {
    if (!text || loading) return;
    setInput("");
    setMessages(p => [...p, { role:"user", content:text, id:Date.now() }]);
    setLoading(true);

    const streamId = Date.now() + 99999;
    setMessages(p => [...p, { role:"assistant", content:"", id:streamId, agent:"astra", intent:"", streaming:true }]);

    try {
      const response = await fetch(`${API}/chat/stream`, {
        method:"POST", headers:{"Content-Type":"application/json"},
        body:JSON.stringify({ message:text })
      });

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = decoder.decode(value);
        const lines = chunk.split("\n").filter(l => l.startsWith("data: "));
        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6));
            if (data.type === "meta") {
              setMessages(p => p.map(m => m.id===streamId ? {...m, agent:data.model, intent:data.intent} : m));
            }
            if (data.type === "token") {
              setMessages(p => p.map(m => m.id===streamId ? {...m, content:m.content+data.text} : m));
            }
            if (data.type === "done") {
              setMessages(p => p.map(m => m.id===streamId ? {
                ...m, streaming:false,
                confidence:data.confidence, emotion:data.emotion,
                tool_used:data.tool_used, memory_updated:data.memory_updated,
                agent:data.agent, intent:data.intent,
              } : m));
              if (speakReplies && data.full) {
                setIsSpeaking(true);
                fetch(`${API}/voice/say`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ text:data.full }) })
                  .finally(() => setTimeout(() => setIsSpeaking(false), (data.full?.length||0)*55));
              }
              if (data.memory_updated) fetchMemory();
            }
          } catch {}
        }
      }
    } catch {
      addSystem("CONNECTION ERROR — IS BACKEND RUNNING?");
      setMessages(p => p.filter(m => m.id!==streamId));
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const switchModel = async (model) => {
    try {
      await fetch(`${API}/model/switch`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ model }) });
      setCurrentModel(model);
      addSystem(`NEURAL NET SWITCHED → ${model.toUpperCase()}`);
    } catch {}
  };

  const clearMemory = async () => {
    await fetch(`${API}/memory`, { method:"DELETE" });
    setMemory({});
    addSystem("MEMORY CORE WIPED");
  };

  const toggleWake = async () => {
    if (wakeActive) {
      await fetch(`${API}/voice/stop`, { method:"POST" });
      setWakeActive(false);
    } else {
      await fetch(`${API}/voice/start`, { method:"POST", headers:{"Content-Type":"application/json"}, body:JSON.stringify({ mode:"wake_word" }) });
      setWakeActive(true);
    }
  };

  const msgCount = messages.filter(m => m.role !== "system").length;

  const tabs = [
    { id:"chat",   label:"◈ INTERFACE" },
    { id:"vision", label:"◎ VISION"    },
    { id:"graph",  label:"◈ MEMORY"    },
  ];

  return (
    <div style={{ display:"flex", height:"100vh", overflow:"hidden", background:"#00030a", fontFamily:"'Courier New',monospace" }}>

      {/* Animated background grid */}
      <div style={{
        position:"fixed", inset:0, pointerEvents:"none", zIndex:0,
        backgroundImage:`linear-gradient(rgba(0,212,255,0.025) 1px,transparent 1px),linear-gradient(90deg,rgba(0,212,255,0.025) 1px,transparent 1px)`,
        backgroundSize:"44px 44px",
      }} />

      {/* Scan line */}
      <div style={{ position:"fixed", top:0, left:0, right:0, bottom:0, pointerEvents:"none", zIndex:9999, overflow:"hidden" }}>
        <div style={{ position:"absolute", left:0, right:0, height:2, background:"linear-gradient(90deg,transparent,rgba(0,212,255,0.1),transparent)", animation:"scanline 10s linear infinite" }} />
      </div>

      <SystemSidebar
        health={health}
        memory={memory}
        models={models}
        currentModel={currentModel}
        onSwitchModel={switchModel}
      />

      <div style={{ flex:1, display:"flex", flexDirection:"column", overflow:"hidden", position:"relative", zIndex:1 }}>

        {/* Header */}
        <div style={{
          padding:"10px 24px",
          borderBottom:"1px solid rgba(0,212,255,0.1)",
          background:"linear-gradient(90deg,rgba(0,5,14,0.97) 0%,rgba(0,3,10,0.98) 100%)",
          display:"flex", justifyContent:"space-between", alignItems:"center",
          flexShrink:0, position:"relative",
        }}>
          <div style={{ position:"absolute", bottom:0, left:0, right:0, height:1, background:"linear-gradient(90deg,transparent,rgba(0,212,255,0.35),transparent)" }} />

          <div style={{ display:"flex", alignItems:"center", gap:18 }}>
            <ArcReactor active={status==="online"} size={46} />
            <div>
              <div style={{ fontSize:20, fontWeight:"bold", letterSpacing:6, color:"#00d4ff", textShadow:"0 0 20px rgba(0,212,255,0.7),0 0 50px rgba(0,212,255,0.2)" }}>
                ASTRA
              </div>
              <div style={{ fontSize:7, letterSpacing:4, color:"rgba(0,212,255,0.3)", marginTop:1 }}>
                ADVANCED SYSTEM FOR TACTICAL REASONING & AUTOMATION
              </div>
            </div>

            {/* Tabs */}
            <div style={{ display:"flex", gap:3, marginLeft:12 }}>
              {tabs.map(({ id, label }) => (
                <button key={id} onClick={() => setTab(id)} style={{
                  background: tab===id ? "rgba(0,212,255,0.08)" : "transparent",
                  border:`1px solid ${tab===id?"rgba(0,212,255,0.45)":"rgba(0,212,255,0.12)"}`,
                  color: tab===id ? "#00d4ff" : "rgba(0,212,255,0.28)",
                  fontFamily:"'Courier New',monospace", fontSize:10,
                  padding:"5px 14px", cursor:"pointer", letterSpacing:2,
                  boxShadow: tab===id ? "0 0 12px rgba(0,212,255,0.12)" : "none",
                  transition:"all 0.2s",
                }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display:"flex", gap:10, alignItems:"center" }}>
            {/* Live waveform when speaking */}
            {isSpeaking && <Waveform active={true} color="#00ff88" bars={20} />}

            {/* Status */}
            <div style={{ display:"flex", alignItems:"center", gap:5 }}>
              <div style={{ width:5, height:5, borderRadius:"50%", background:status==="online"?"#00ff88":"#ff4444", boxShadow:`0 0 8px ${status==="online"?"#00ff88":"#ff4444"}`, animation:"pulse 2s infinite" }} />
              <span style={{ fontSize:8, letterSpacing:2, color:status==="online"?"rgba(0,255,136,0.6)":"rgba(255,68,68,0.6)" }}>
                {status.toUpperCase()}
              </span>
            </div>

            <div style={{ width:1, height:18, background:"rgba(0,212,255,0.12)" }} />

            <span style={{ fontSize:8, letterSpacing:2, color:"rgba(0,212,255,0.35)" }}>
              {currentModel?.split(":")[0]?.toUpperCase()}
            </span>
            <span style={{ fontSize:8, letterSpacing:1, color:"rgba(0,212,255,0.25)" }}>
              {msgCount} MSG
            </span>

            <div style={{ width:1, height:18, background:"rgba(0,212,255,0.12)" }} />

            {[
              { label:wakeActive?"◉ WAKE":"◎ WAKE",    active:wakeActive,    onClick:toggleWake,               activeColor:"#00d4ff" },
              { label:speakReplies?"◉ VOICE":"◎ VOICE", active:speakReplies,  onClick:()=>setSpeakReplies(p=>!p), activeColor:"#00ff88" },
            ].map(({ label, active, onClick, activeColor }) => (
              <button key={label} onClick={onClick} style={{
                background: active ? `${activeColor}12` : "transparent",
                border:`1px solid ${active?activeColor+"55":"rgba(0,212,255,0.12)"}`,
                color: active ? activeColor : "rgba(0,212,255,0.28)",
                fontFamily:"'Courier New',monospace", fontSize:9,
                padding:"4px 10px", cursor:"pointer", letterSpacing:2,
                boxShadow: active ? `0 0 10px ${activeColor}20` : "none",
                transition:"all 0.2s",
              }}>{label}</button>
            ))}

            <button onClick={clearMemory} style={{
              background:"transparent", border:"1px solid rgba(255,68,68,0.18)",
              color:"rgba(255,68,68,0.35)", fontFamily:"'Courier New',monospace",
              fontSize:9, padding:"4px 10px", cursor:"pointer", letterSpacing:2, transition:"all 0.2s",
            }}
              onMouseOver={e => e.currentTarget.style.borderColor="rgba(255,68,68,0.55)"}
              onMouseOut={e  => e.currentTarget.style.borderColor="rgba(255,68,68,0.18)"}
            >✕ WIPE</button>
          </div>
        </div>

        {/* Content */}
        {tab === "vision" ? (
          <div style={{ flex:1, overflow:"hidden" }}>
            <LiveVision onAnalysis={(entry) => { if (entry.question) addSystem(`◎ ${entry.jarvis}`); }} />
          </div>
        ) : tab === "graph" ? (
          <div style={{ flex:1, overflow:"hidden" }}>
            <KnowledgeGraph />
          </div>
        ) : (
          <>
            {/* Messages */}
            <div style={{ flex:1, overflowY:"auto", padding:"28px 36px", background:"transparent" }}>

              {messages.length === 0 && (
                <div style={{ textAlign:"center", marginTop:"13vh" }}>
                  <div style={{ marginBottom:24, display:"flex", justifyContent:"center" }}>
                    <ArcReactor active={status==="online"} size={72} />
                  </div>
                  <div style={{ fontSize:20, letterSpacing:8, color:"#00d4ff", marginBottom:6, fontWeight:"bold", textShadow:"0 0 24px rgba(0,212,255,0.5)" }}>
                    ASTRA ONLINE
                  </div>
                  <div style={{ fontSize:9, letterSpacing:4, color:"rgba(0,212,255,0.28)", marginBottom:36 }}>
                    ADVANCED PERSONAL AI · ALL SYSTEMS READY
                  </div>
                  <div style={{ display:"flex", gap:10, justifyContent:"center", flexWrap:"wrap" }}>
                    {["what's playing","open spotify","my schedule today","message mom I'm home","volume up","battery status"].map(cmd => (
                      <button key={cmd} onClick={() => sendMessage(cmd)} style={{
                        background:"rgba(0,212,255,0.04)", border:"1px solid rgba(0,212,255,0.15)",
                        color:"rgba(0,212,255,0.45)", fontFamily:"'Courier New',monospace",
                        fontSize:10, padding:"7px 16px", cursor:"pointer", letterSpacing:1,
                        backdropFilter:"blur(8px)", transition:"all 0.2s",
                      }}
                        onMouseOver={e => { e.currentTarget.style.background="rgba(0,212,255,0.09)"; e.currentTarget.style.color="#00d4ff"; e.currentTarget.style.borderColor="rgba(0,212,255,0.4)"; }}
                        onMouseOut={e  => { e.currentTarget.style.background="rgba(0,212,255,0.04)"; e.currentTarget.style.color="rgba(0,212,255,0.45)"; e.currentTarget.style.borderColor="rgba(0,212,255,0.15)"; }}
                      >{cmd}</button>
                    ))}
                  </div>
                </div>
              )}

              {messages.map(msg => <Message key={msg.id} msg={msg} />)}
              {loading && <ThinkingDots />}
              <div ref={endRef} />
            </div>

            {/* Input bar */}
            <div style={{
              padding:"14px 36px 22px",
              borderTop:"1px solid rgba(0,212,255,0.08)",
              background:"linear-gradient(0deg,rgba(0,2,8,0.98) 0%,rgba(0,4,12,0.95) 100%)",
              flexShrink:0, position:"relative",
            }}>
              <div style={{ position:"absolute", top:0, left:0, right:0, height:1, background:"linear-gradient(90deg,transparent,rgba(0,212,255,0.25),transparent)" }} />

              <div style={{
                display:"flex", alignItems:"center", gap:14, padding:"12px 18px",
                background:"rgba(0,212,255,0.025)",
                border:`1px solid ${loading?"rgba(0,212,255,0.08)":"rgba(0,212,255,0.22)"}`,
                backdropFilter:"blur(20px)",
                boxShadow: loading ? "none" : "0 0 30px rgba(0,212,255,0.04), inset 0 0 30px rgba(0,212,255,0.02)",
                transition:"all 0.3s",
                position:"relative", overflow:"hidden",
              }}>
                {/* Glass sheen */}
                <div style={{ position:"absolute", top:0, left:0, right:0, height:"45%", background:"linear-gradient(180deg,rgba(255,255,255,0.02) 0%,transparent 100%)", pointerEvents:"none" }} />

                <VoiceButton onTranscript={sendMessage} speaking={isSpeaking} />

                {/* Waveform in input when speaking */}
                <Waveform active={loading || isSpeaking} color={isSpeaking?"#00ff88":"#00d4ff"} bars={18} />

                <div style={{ width:1, height:22, background:"rgba(0,212,255,0.15)" }} />

                <span style={{ color:"rgba(0,212,255,0.35)", fontSize:16 }}>›</span>

                <input
                  ref={inputRef}
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key==="Enter" && !e.shiftKey && sendMessage()}
                  placeholder="ENTER COMMAND..."
                  disabled={loading}
                  style={{
                    flex:1, background:"transparent", border:"none", outline:"none",
                    color:"rgba(200,240,255,0.85)", fontFamily:"'Courier New',monospace",
                    fontSize:13, caretColor:"#00d4ff", letterSpacing:1,
                  }}
                />

                <span style={{ fontSize:9, color:"rgba(0,212,255,0.2)", letterSpacing:2, flexShrink:0 }}>
                  {loading ? "PROCESSING..." : "ENTER ↵"}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      <ProactiveAlerts />

      <style>{`
        * { box-sizing:border-box; margin:0; padding:0; }
        ::-webkit-scrollbar { width:2px; }
        ::-webkit-scrollbar-track { background:transparent; }
        ::-webkit-scrollbar-thumb { background:rgba(0,212,255,0.15); border-radius:1px; }
        input::placeholder { color:rgba(0,212,255,0.18); letter-spacing:2px; }
        button { outline:none; }
        @keyframes scanline  { 0%{transform:translateY(-100vh)} 100%{transform:translateY(100vh)} }
        @keyframes spin      { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes pulse     { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes blink     { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes fadeUp    { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
        @keyframes waveBar   { 0%,100%{transform:scaleY(0.3);opacity:0.3} 50%{transform:scaleY(1);opacity:1} }
        @keyframes voicePulse{ 0%,100%{box-shadow:0 0 20px rgba(255,68,68,0.4)} 50%{box-shadow:0 0 40px rgba(255,68,68,0.8)} }
        @keyframes ripple    { 0%{transform:scale(1);opacity:0.6} 100%{transform:scale(1.9);opacity:0} }
      `}</style>
    </div>
  );
}
