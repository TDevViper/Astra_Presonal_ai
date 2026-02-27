import { useState, useEffect, useRef } from "react";
import LiveVision from "./components/LiveVision";

const API = "http://127.0.0.1:5050";

const C = {
  bg: "#080808", surface: "#0f0f0f", surface2: "#141414",
  border: "#1a1a1a", border2: "#222222",
  green: "#00ff88", blue: "#0088ff", yellow: "#ffaa00",
  red: "#ff4444", purple: "#aa44ff", cyan: "#00ddff",
  dim: "#333333", text: "#e0e0e0", muted: "#555555", faint: "#2a2a2a"
};

const confColor = (s) => s >= 0.95 ? C.green : s >= 0.75 ? "#88ff00" : s >= 0.5 ? C.yellow : s >= 0.25 ? C.red : C.dim;
const confBar = (s, w = 8) => "█".repeat(Math.round(s * w)) + "░".repeat(w - Math.round(s * w));
const emojiFor = (e) => ({ joy:"😊", sad:"😢", angry:"😠", anxious:"😰", tired:"😴", surprised:"😲", neutral:"😐" }[e] || "😐");
const agentLabel = (a) => {
  if (a?.includes("mistral")) return "mistral";
  if (a?.includes("llama"))   return "llama3";
  if (a?.includes("phi3"))    return "phi3";
  if (a === "web_search_agent") return "websearch";
  if (a === "memory")           return "memory";
  if (a === "intent_handler")   return "shortcut";
  return a || "astra";
};

function VoiceButton({ onTranscript }) {
  const [state, setState] = useState("idle");
  const handle = async () => {
    if (state !== "idle") return;
    setState("listening");
    try {
      const r = await fetch(`${API}/voice/listen`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration: 5 })
      });
      const d = await r.json();
      if (d.text?.trim()) onTranscript(d.text.trim());
    } catch {}
    finally { setState("idle"); }
  };
  return (
    <button onClick={handle} disabled={state !== "idle"} style={{
      background: "transparent",
      border: `1px solid ${state === "listening" ? C.red : C.muted}`,
      borderRadius: 3, color: state === "listening" ? C.red : C.muted,
      fontFamily: "monospace", fontSize: 11, padding: "5px 10px",
      cursor: "pointer", letterSpacing: 1, transition: "all 0.2s",
      animation: state === "listening" ? "pulse 0.8s infinite" : "none"
    }}>
      {state === "listening" ? "● REC" : "🎤"}
    </button>
  );
}

function MemoryPanel({ memory, models, currentModel, onSwitchModel }) {
  const prefs     = memory?.preferences || {};
  const facts     = memory?.user_facts || [];
  const emotions  = memory?.emotional_patterns?.history?.slice(-5).reverse() || [];
  const summaries = memory?.conversation_summary || [];

  return (
    <div style={{
      width: 210, minWidth: 210, background: C.surface,
      borderRight: `1px solid ${C.border}`, padding: "16px 12px",
      fontFamily: "monospace", fontSize: 12, overflowY: "auto",
      display: "flex", flexDirection: "column", gap: 18
    }}>
      <div style={{ color: C.green, fontWeight: "bold", fontSize: 13, letterSpacing: 3 }}>◈ MEMORY</div>

      <Section label="USER">
        <Row icon="👤" val={prefs.name || "Arnav"} />
        {prefs.location && <Row icon="📍" val={prefs.location} />}
      </Section>

      {prefs.goals?.length > 0 && (
        <Section label="GOALS">
          {prefs.goals.slice(-2).map((g, i) => <Row key={i} icon="🎯" val={g} />)}
        </Section>
      )}

      {emotions.length > 0 && (
        <Section label="EMOTIONS">
          {emotions.map((e, i) => (
            <div key={i} style={{ display: "flex", justifyContent: "space-between", marginBottom: 3, color: C.text, opacity: 1 - i * 0.18 }}>
              <span>{emojiFor(e.label)} {e.label}</span>
              <span style={{ color: C.muted }}>{e.score?.toFixed(2)}</span>
            </div>
          ))}
        </Section>
      )}

      {facts.length > 0 && (
        <Section label={`FACTS (${facts.length})`}>
          {facts.slice(-3).map((f, i) => (
            <div key={i} style={{ color: C.muted, fontSize: 10, marginBottom: 3, lineHeight: 1.4 }}>
              · {f.fact?.slice(0, 50)}
            </div>
          ))}
        </Section>
      )}

      {summaries.length > 0 && (
        <Section label="CONTEXT">
          {summaries.slice(-2).map((s, i) => (
            <div key={i} style={{ color: C.muted, marginBottom: 6, lineHeight: 1.4, fontSize: 10 }}>
              📋 {s.summary?.slice(0, 70)}...
            </div>
          ))}
        </Section>
      )}

      <div style={{ marginTop: "auto" }}>
        <div style={{ color: C.muted, marginBottom: 8, fontSize: 10, letterSpacing: 1 }}>MODEL</div>
        {models.map(m => (
          <div key={m} onClick={() => onSwitchModel(m)} style={{
            display: "flex", alignItems: "center", gap: 7, padding: "5px 0",
            cursor: "pointer", color: currentModel === m ? C.green : C.muted,
            transition: "color 0.15s", borderBottom: `1px solid ${C.faint}`
          }}>
            <span style={{ fontSize: 7 }}>{currentModel === m ? "●" : "○"}</span>
            <span style={{ fontSize: 11 }}>{m.split(":")[0]}</span>
            {currentModel === m && <span style={{ fontSize: 9, color: C.green, marginLeft: "auto" }}>active</span>}
          </div>
        ))}
      </div>
    </div>
  );
}

function Section({ label, children }) {
  return (
    <div>
      <div style={{ color: C.muted, marginBottom: 7, fontSize: 9, letterSpacing: 2, borderBottom: `1px solid ${C.faint}`, paddingBottom: 4 }}>{label}</div>
      {children}
    </div>
  );
}

function Row({ icon, val }) {
  return (
    <div style={{ display: "flex", gap: 6, marginBottom: 4, color: C.text, alignItems: "flex-start" }}>
      <span style={{ flexShrink: 0, fontSize: 11 }}>{icon}</span>
      <span style={{ wordBreak: "break-word", lineHeight: 1.4, fontSize: 11 }}>{String(val)}</span>
    </div>
  );
}

function Message({ msg }) {
  const isUser   = msg.role === "user";
  const isSystem = msg.role === "system";

  if (isSystem) return (
    <div style={{ color: C.dim, fontFamily: "monospace", fontSize: 10, padding: "6px 0", textAlign: "center", letterSpacing: 1 }}>
      ── {msg.content} ──
    </div>
  );

  return (
    <div style={{ marginBottom: 18, display: "flex", flexDirection: "column", alignItems: isUser ? "flex-end" : "flex-start" }}>
      <div style={{ fontSize: 10, color: C.muted, marginBottom: 5, fontFamily: "monospace", display: "flex", gap: 8 }}>
        {isUser ? (
          <span style={{ color: C.blue, letterSpacing: 1 }}>YOU</span>
        ) : (
          <>
            <span style={{ color: C.green, letterSpacing: 1 }}>ASTRA</span>
            <span style={{ color: C.dim }}>·</span>
            <span>{agentLabel(msg.agent)}</span>
            {msg.intent && <><span style={{ color: C.dim }}>·</span><span style={{ color: C.dim }}>{msg.intent}</span></>}
          </>
        )}
      </div>

      <div style={{
        maxWidth: "78%", padding: "10px 14px",
        background: isUser ? "#0a1628" : C.surface,
        border: `1px solid ${isUser ? "#003388" : C.border2}`,
        borderRadius: 3, fontFamily: "monospace", fontSize: 13,
        color: C.text, lineHeight: 1.65, whiteSpace: "pre-wrap", wordBreak: "break-word"
      }}>
        {msg.content}
      </div>

      {!isUser && msg.confidence !== undefined && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 6, fontSize: 10, fontFamily: "monospace", color: C.muted }}>
          <span style={{ color: confColor(msg.confidence) }}>{confBar(msg.confidence)} {msg.confidence?.toFixed(2)}</span>
          <span>{msg.confidence_emoji} {msg.confidence_label}</span>
          {msg.emotion && msg.emotion !== "neutral" && <span>{emojiFor(msg.emotion)} {msg.emotion}</span>}
          {msg.tool_used      && <span style={{ color: C.cyan }}>⚡ tool</span>}
          {msg.memory_updated && <span style={{ color: C.yellow }}>💾 saved</span>}
        </div>
      )}

      {msg.citations?.length > 0 && (
        <div style={{ marginTop: 6, fontSize: 10, fontFamily: "monospace", maxWidth: "78%" }}>
          {msg.citations.slice(0, 3).map(c => (
            <div key={c.index} style={{ color: C.muted, marginBottom: 3 }}>
              <span style={{ color: C.blue }}>[{c.index}]</span>{" "}
              <a href={c.url} target="_blank" rel="noreferrer"
                style={{ color: C.muted, textDecoration: "none" }}
                onMouseOver={e => e.target.style.color = C.text}
                onMouseOut={e => e.target.style.color = C.muted}>
                {c.title?.slice(0, 65)}
              </a>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [tab, setTab]               = useState("chat");
  const [messages, setMessages]     = useState([]);
  const [input, setInput]           = useState("");
  const [loading, setLoading]       = useState(false);
  const [memory, setMemory]         = useState({});
  const [models]                    = useState(["phi3:mini", "mistral:latest", "llama3.2:3b"]);
  const [currentModel, setCurrentModel] = useState("phi3:mini");
  const [status, setStatus]         = useState("connecting...");
  const [speakReplies, setSpeakReplies] = useState(false);
  const [wakeActive, setWakeActive] = useState(false);
  const endRef   = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => { checkHealth(); fetchMemory(); inputRef.current?.focus(); }, []); // eslint-disable-line
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const checkHealth = async () => {
    try {
      const r = await fetch(`${API}/health`);
      if (r.ok) {
        const d = await r.json();
        setStatus("online");
        setCurrentModel(d.model || "phi3:mini");
        addSystem("ASTRA ENGINE ONLINE");
      }
    } catch {
      setStatus("offline");
      addSystem("⚠️ Backend offline — run: python app.py");
    }
  };

  const fetchMemory = async () => {
    try { const r = await fetch(`${API}/memory`); if (r.ok) setMemory(await r.json()); } catch {}
  };

  const addSystem = (text) => setMessages(p => [...p, { role: "system", content: text, id: Date.now() }]);

  const sendMessage = async (text = input.trim()) => {
    if (!text || loading) return;
    setInput("");
    setMessages(p => [...p, { role: "user", content: text, id: Date.now() }]);
    setLoading(true);
    try {
      const r = await fetch(`${API}/chat`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text })
      });
      const data = await r.json();
      setMessages(p => [...p, {
        role: "assistant", content: data.reply,
        agent: data.agent, intent: data.intent, emotion: data.emotion,
        confidence: data.confidence, confidence_label: data.confidence_label,
        confidence_emoji: data.confidence_emoji,
        tool_used: data.tool_used, memory_updated: data.memory_updated,
        citations: data.citations, id: Date.now()
      }]);
      if (speakReplies && data.reply) {
        fetch(`${API}/voice/say`, {
          method: "POST", headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: data.reply })
        });
      }
      if (data.memory_updated) fetchMemory();
    } catch { addSystem("Connection error — is backend running?"); }
    finally { setLoading(false); inputRef.current?.focus(); }
  };

  const switchModel = async (model) => {
    try {
      await fetch(`${API}/model/switch`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model })
      });
      setCurrentModel(model);
      addSystem(`switched to ${model}`);
    } catch {}
  };

  const clearMemory = async () => {
    await fetch(`${API}/memory`, { method: "DELETE" });
    setMemory({});
    addSystem("memory cleared");
  };

  const toggleWake = async () => {
    if (wakeActive) {
      await fetch(`${API}/voice/stop`, { method: "POST" });
      setWakeActive(false);
    } else {
      await fetch(`${API}/voice/start`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode: "wake_word" })
      });
      setWakeActive(true);
    }
  };

  return (
    <div style={{ display: "flex", height: "100vh", background: C.bg, color: C.text, fontFamily: "monospace", overflow: "hidden" }}>

      <MemoryPanel memory={memory} models={models} currentModel={currentModel} onSwitchModel={switchModel} />

      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Header */}
        <div style={{
          padding: "10px 20px", borderBottom: `1px solid ${C.border}`,
          display: "flex", justifyContent: "space-between", alignItems: "center",
          background: C.surface, flexShrink: 0
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <span style={{ color: C.green, fontSize: 17, fontWeight: "bold", letterSpacing: 4 }}>ASTRA</span>
            <span style={{ color: C.dim, fontSize: 10 }}>v3.0</span>

            <div style={{
              fontSize: 10, padding: "2px 8px",
              border: `1px solid ${status === "online" ? C.green : C.red}`,
              color: status === "online" ? C.green : C.red,
              borderRadius: 2, display: "flex", alignItems: "center", gap: 5
            }}>
              <span style={{
                display: "inline-block", width: 5, height: 5, borderRadius: "50%",
                background: status === "online" ? C.green : C.red,
                animation: status === "online" ? "pulse 2s infinite" : "none"
              }} />
              {status === "online" ? "LIVE" : "OFFLINE"}
            </div>

            {/* Tabs */}
            <div style={{ display: "flex", gap: 2, marginLeft: 4 }}>
              {[["chat", "◈ CHAT"], ["vision", "◎ VISION"]].map(([t, label]) => (
                <button key={t} onClick={() => setTab(t)} style={{
                  background: tab === t ? `${C.green}15` : "transparent",
                  border: `1px solid ${tab === t ? C.green : C.dim}`,
                  borderRadius: 3, color: tab === t ? C.green : C.muted,
                  fontFamily: "monospace", fontSize: 10, padding: "3px 10px",
                  cursor: "pointer", letterSpacing: 1, transition: "all 0.15s"
                }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ fontSize: 10, color: C.blue }}>[{currentModel.split(":")[0]}]</span>
            <button onClick={toggleWake} style={{
              background: wakeActive ? `${C.purple}22` : "transparent",
              border: `1px solid ${wakeActive ? C.purple : C.dim}`,
              borderRadius: 3, color: wakeActive ? C.purple : C.muted,
              fontFamily: "monospace", fontSize: 10, padding: "3px 9px",
              cursor: "pointer", letterSpacing: 1
            }}>
              {wakeActive ? "◈ WAKE" : "◯ WAKE"}
            </button>
            <span onClick={clearMemory}
              style={{ color: C.muted, cursor: "pointer", fontSize: 11 }}
              onMouseOver={e => e.target.style.color = C.red}
              onMouseOut={e => e.target.style.color = C.muted}>
              clear
            </span>
          </div>
        </div>

        {/* Content */}
        {tab === "vision" ? (
          <div style={{ flex: 1, overflow: "hidden" }}>
            <LiveVision onAnalysis={(entry) => { if (entry.question) addSystem(`👁️ ${entry.jarvis}`); }} />
          </div>
        ) : (
          <>
            <div style={{ flex: 1, overflowY: "auto", padding: "24px 28px" }}>
              {messages.length === 0 && (
                <div style={{ textAlign: "center", marginTop: 80, color: C.muted }}>
                  <div style={{ fontSize: 36, marginBottom: 14, color: C.green }}>◈</div>
                  <div style={{ fontSize: 14, color: C.green, letterSpacing: 3, marginBottom: 8 }}>ASTRA ENGINE READY</div>
                  <div style={{ fontSize: 11, color: C.dim }}>chat · voice · vision · memory · web search</div>
                  <div style={{ fontSize: 11, marginTop: 20, color: C.dim, lineHeight: 2 }}>
                    try: "search latest AI news"<br />
                    switch to ◎ VISION to see what ASTRA sees
                  </div>
                </div>
              )}
              {messages.map(msg => <Message key={msg.id} msg={msg} />)}
              {loading && <div style={{ fontFamily: "monospace", fontSize: 12, color: C.green }}>ASTRA ▋</div>}
              <div ref={endRef} />
            </div>

            <div style={{ padding: "12px 24px 20px", borderTop: `1px solid ${C.border}`, background: C.surface, flexShrink: 0 }}>
              <div style={{ display: "flex", gap: 8, marginBottom: 10, alignItems: "center" }}>
                <VoiceButton onTranscript={sendMessage} />
                <button onClick={() => setSpeakReplies(p => !p)} style={{
                  background: speakReplies ? `${C.purple}22` : "transparent",
                  border: `1px solid ${speakReplies ? C.purple : C.dim}`,
                  borderRadius: 3, color: speakReplies ? C.purple : C.muted,
                  fontFamily: "monospace", fontSize: 10, padding: "4px 10px",
                  cursor: "pointer", letterSpacing: 1
                }}>
                  {speakReplies ? "🔊 SPEAK ON" : "🔇 SPEAK"}
                </button>
                <span style={{ marginLeft: "auto", fontSize: 10, color: C.dim }}>
                  {messages.filter(m => m.role !== "system").length} msgs
                </span>
              </div>

              <div style={{
                display: "flex", alignItems: "center", gap: 10,
                border: `1px solid ${loading ? C.dim : C.green}`,
                borderRadius: 3, padding: "8px 12px",
                background: C.surface2, transition: "border-color 0.2s"
              }}>
                <span style={{ color: C.green, fontSize: 14 }}>›</span>
                <input ref={inputRef} value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === "Enter" && !e.shiftKey && sendMessage()}
                  placeholder="type a message..." disabled={loading}
                  style={{
                    flex: 1, background: "transparent", border: "none",
                    outline: "none", color: C.text, fontFamily: "monospace",
                    fontSize: 13, caretColor: C.green
                  }}
                />
                <span style={{ color: C.muted, fontSize: 10, letterSpacing: 1 }}>
                  {loading ? "thinking..." : "enter ↵"}
                </span>
              </div>
            </div>
          </>
        )}
      </div>

      <style>{`
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 3px; }
        ::-webkit-scrollbar-track { background: ${C.bg}; }
        ::-webkit-scrollbar-thumb { background: ${C.border2}; border-radius: 2px; }
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }
        input::placeholder { color: ${C.dim}; }
        button:hover { opacity: 0.85; }
      `}</style>
    </div>
  );
}