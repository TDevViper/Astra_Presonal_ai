import { useState } from "react";

const NAV_ICONS = {
  chat:    "💬",
  memory:  "🧠", 
  vision:  "👁",
  tasks:   "📋",
  tools:   "⚡",
};

function JarvisSidebar({ activeNav, setActiveNav, messages, memory, health, models, currentModel, onSwitchModel }) {
  const convos = [];
  for (let i = messages.length - 1; i >= 0; i -= 2) {
    if (messages[i]) convos.push(messages[i]);
    if (convos.length >= 6) break;
  }

  return (
    <div style={{
      width: 260, flexShrink: 0, height: "100vh",
      background: "rgba(2,8,20,0.97)",
      borderRight: "1px solid rgba(56,189,248,0.08)",
      display: "flex", flexDirection: "column",
      fontFamily: "'JetBrains Mono', monospace",
    }}>
      {/* Logo */}
      <div style={{ padding: "20px 18px 16px", borderBottom: "1px solid rgba(56,189,248,0.06)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div style={{
            width: 34, height: 34, borderRadius: "50%",
            background: "radial-gradient(circle at 35% 35%, #38bdf830, #38bdf808)",
            border: "1.5px solid #38bdf844",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 14, color: "#38bdf8",
            boxShadow: "0 0 16px #38bdf820",
          }}>A</div>
          <div>
            <div style={{ fontSize: 13, fontWeight: 500, color: "#e2e8f0", letterSpacing: "0.15em" }}>ASTRA</div>
            <div style={{ fontSize: 9, color: "#38bdf860", letterSpacing: "0.1em" }}>JARVIS MODE</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <div style={{ padding: "12px 10px", borderBottom: "1px solid rgba(56,189,248,0.06)" }}>
        {Object.entries(NAV_ICONS).map(([key, icon]) => (
          <div key={key} onClick={() => setActiveNav(key)}
            style={{
              display: "flex", alignItems: "center", gap: 10,
              padding: "9px 10px", borderRadius: 8, marginBottom: 2,
              cursor: "pointer",
              background: activeNav === key ? "rgba(56,189,248,0.1)" : "transparent",
              border: `1px solid ${activeNav === key ? "rgba(56,189,248,0.2)" : "transparent"}`,
              color: activeNav === key ? "#38bdf8" : "#334e68",
              transition: "all 0.15s",
            }}>
            <span style={{ fontSize: 14 }}>{icon}</span>
            <span style={{ fontSize: 10, letterSpacing: "0.1em" }}>{key.toUpperCase()}</span>
            {key === "memory" && (
              <span style={{ marginLeft: "auto", fontSize: 9, color: "#38bdf860" }}>
                {memory?.user_facts?.length ?? 0}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Recent convos */}
      <div style={{ flex: 1, overflowY: "auto", padding: "12px 10px" }}>
        <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: "0.15em", marginBottom: 8, paddingLeft: 2 }}>
          RECENT
        </div>
        {convos.length === 0 && (
          <div style={{ fontSize: 10, color: "#1e3a5f", padding: "6px 10px" }}>No conversations yet</div>
        )}
        {convos.map((msg, i) => (
          <div key={i} style={{
            padding: "8px 10px", borderRadius: 6, marginBottom: 4,
            cursor: "pointer", border: "1px solid transparent",
            transition: "all 0.15s",
          }}
            onMouseEnter={e => e.currentTarget.style.background = "rgba(56,189,248,0.05)"}
            onMouseLeave={e => e.currentTarget.style.background = "transparent"}
          >
            <div style={{ fontSize: 10, color: "#4a6fa5", letterSpacing: "0.05em",
              whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {msg.content?.slice(0, 35) || "..."}
            </div>
          </div>
        ))}
      </div>

      {/* Models */}
      <div style={{ padding: "10px", borderTop: "1px solid rgba(56,189,248,0.06)" }}>
        <div style={{ fontSize: 9, color: "#1e3a5f", letterSpacing: "0.15em", marginBottom: 6, paddingLeft: 2 }}>
          MODELS
        </div>
        {(models || ["phi3:mini"]).map(m => (
          <div key={m} onClick={() => onSwitchModel?.(m)} style={{
            padding: "5px 10px", borderRadius: 5, marginBottom: 2, cursor: "pointer",
            fontSize: 9, letterSpacing: "0.05em",
            background: m === currentModel ? "rgba(56,189,248,0.1)" : "transparent",
            border: `1px solid ${m === currentModel ? "rgba(56,189,248,0.2)" : "transparent"}`,
            color: m === currentModel ? "#38bdf8" : "#2a4a6a",
            transition: "all 0.15s",
          }}>{m.toUpperCase()}</div>
        ))}
      </div>

      {/* System status */}
      <div style={{ padding: "10px 14px 14px", borderTop: "1px solid rgba(56,189,248,0.06)" }}>
        <div style={{ display: "flex", gap: 12 }}>
          {[["B", health?.brain], ["M", health?.memory], ["V", health?.voice], ["O", health?.ollama]].map(([k,v]) => (
            <div key={k} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 3 }}>
              <div style={{ width: 6, height: 6, borderRadius: "50%",
                background: v ? "#34d399" : "#475569",
                boxShadow: v ? "0 0 5px #34d39966" : "none" }} />
              <span style={{ fontSize: 8, color: "#1e3a5f" }}>{k}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function WelcomeScreen({ onQuickAction, accent }) {
  const actions = [
    { icon: "🔍", label: "Search Web", action: "search the web for " },
    { icon: "💻", label: "Run Code", action: "run this python code: " },
    { icon: "🧠", label: "My Memory", action: "what do you remember about me?" },
    { icon: "📊", label: "System Stats", action: "show me system stats" },
    { icon: "🗂️", label: "Git Status", action: "show git status" },
    { icon: "📅", label: "Calendar", action: "what are my tasks today?" },
  ];
  return (
    <div style={{ flex: 1, display: "flex", flexDirection: "column",
      alignItems: "center", justifyContent: "center", padding: 40 }}>
      {/* Orb */}
      <div style={{ position: "relative", marginBottom: 32 }}>
        <div style={{
          width: 80, height: 80, borderRadius: "50%",
          background: `radial-gradient(circle at 35% 35%, ${accent}25, ${accent}06)`,
          border: `1.5px solid ${accent}30`,
          display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 32, color: accent,
          boxShadow: `0 0 40px ${accent}20, inset 0 0 20px ${accent}08`,
          animation: "pulse-ring 3s ease-in-out infinite",
        }}>A</div>
      </div>
      <div style={{ fontSize: 22, fontWeight: 300, color: "#e2e8f0",
        letterSpacing: "0.2em", marginBottom: 8 }}>ASTRA</div>
      <div style={{ fontSize: 11, color: accent, opacity: 0.4,
        letterSpacing: "0.3em", marginBottom: 48,
        fontFamily: "'JetBrains Mono', monospace" }}>
        HOW CAN I HELP YOU TODAY?
      </div>
      {/* Quick action grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, maxWidth: 500, width: "100%" }}>
        {actions.map(({icon, label, action}) => (
          <div key={label} onClick={() => onQuickAction(action)}
            style={{
              padding: "16px 14px", borderRadius: 12, cursor: "pointer",
              background: "rgba(56,189,248,0.04)",
              border: "1px solid rgba(56,189,248,0.1)",
              display: "flex", flexDirection: "column", alignItems: "center", gap: 8,
              transition: "all 0.2s",
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = "rgba(56,189,248,0.1)";
              e.currentTarget.style.borderColor = "rgba(56,189,248,0.25)";
              e.currentTarget.style.transform = "translateY(-2px)";
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = "rgba(56,189,248,0.04)";
              e.currentTarget.style.borderColor = "rgba(56,189,248,0.1)";
              e.currentTarget.style.transform = "translateY(0)";
            }}
          >
            <span style={{ fontSize: 20 }}>{icon}</span>
            <span style={{ fontSize: 10, color: "#4a6fa5", letterSpacing: "0.08em",
              fontFamily: "'JetBrains Mono', monospace" }}>{label.toUpperCase()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

export function JarvisLayout({
  messages, streamBuffer, streaming, loading,
  input, setInput, send, onKey, inputRef, bottomRef,
  accent, currentModel, health, memory, models, onSwitchModel,
}) {
  const [activeNav, setActiveNav] = useState("chat");

  const handleQuickAction = (action) => {
    setInput(action);
    setTimeout(() => inputRef.current?.focus(), 50);
  };

  return (
    <div style={{
      height: "100vh", display: "flex",
      background: "#04090f",
      fontFamily: "'Space Grotesk', sans-serif",
      overflow: "hidden",
    }}>
      <style>{`
        @keyframes pulse-ring {
          0%, 100% { box-shadow: 0 0 30px ${accent}15, inset 0 0 15px ${accent}06; }
          50% { box-shadow: 0 0 50px ${accent}25, inset 0 0 25px ${accent}12; }
        }
        @keyframes fadeSlideUp {
          from { opacity: 0; transform: translateY(8px); }
          to   { opacity: 1; transform: translateY(0); }
        }
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
        @keyframes thinking {
          0%,80%,100%{transform:scale(0.6);opacity:0.4}
          40%{transform:scale(1);opacity:1}
        }
      `}</style>

      {/* Sidebar */}
      <JarvisSidebar
        activeNav={activeNav} setActiveNav={setActiveNav}
        messages={messages} memory={memory} health={health}
        models={models} currentModel={currentModel} onSwitchModel={onSwitchModel}
      />

      {/* Main area */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Top bar */}
        <div style={{
          height: 52, flexShrink: 0, display: "flex", alignItems: "center",
          padding: "0 24px", justifyContent: "space-between",
          borderBottom: "1px solid rgba(56,189,248,0.06)",
          background: "rgba(3,9,18,0.8)",
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 11, color: "#38bdf8", opacity: 0.6,
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.12em" }}>
              {activeNav.toUpperCase()}
            </span>
            {streaming && (
              <span style={{ fontSize: 9, color: "#34d399",
                fontFamily: "'JetBrains Mono', monospace",
                animation: "blink 1s steps(1) infinite" }}>● STREAMING</span>
            )}
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <div style={{ width: 6, height: 6, borderRadius: "50%",
              background: "#34d399", boxShadow: "0 0 6px #34d39966" }} />
            <span style={{ fontSize: 9, color: "#1e3a5f",
              fontFamily: "'JetBrains Mono', monospace" }}>LIVE</span>
          </div>
        </div>

        {/* Chat area */}
        <div style={{ flex: 1, overflowY: "auto", padding: "24px 32px",
          background: "#040c18" }}>
          {messages.length === 0
            ? <WelcomeScreen onQuickAction={handleQuickAction} accent={accent} />
            : (
              <>
                {messages.map(msg => (
                  <div key={msg.id} style={{
                    display: "flex", flexDirection: msg.role === "user" ? "row-reverse" : "row",
                    gap: 12, marginBottom: 20, alignItems: "flex-start",
                    animation: "fadeSlideUp 0.25s ease forwards",
                  }}>
                    {/* Avatar */}
                    {msg.role !== "user" ? (
                      <div style={{
                        width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                        background: `radial-gradient(circle at 35% 35%, ${accent}25, ${accent}06)`,
                        border: `1.5px solid ${accent}35`,
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 12, color: accent,
                        fontFamily: "'JetBrains Mono', monospace",
                      }}>A</div>
                    ) : (
                      <div style={{
                        width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                        background: "#0a1628", border: "1.5px solid rgba(148,163,184,0.1)",
                        display: "flex", alignItems: "center", justifyContent: "center",
                        fontSize: 11, color: "#4a6fa5",
                        fontFamily: "'JetBrains Mono', monospace",
                      }}>U</div>
                    )}
                    <div style={{ maxWidth: "68%", minWidth: 60 }}>
                      <div style={{
                        padding: "12px 16px",
                        background: msg.role === "user" ? "#0d1e35" : "#080f1c",
                        border: msg.role === "user"
                          ? `1px solid ${accent}20`
                          : "1px solid rgba(255,255,255,0.06)",
                        borderRadius: msg.role === "user" ? "16px 16px 4px 16px" : "16px 16px 16px 4px",
                        color: "rgba(226,232,240,0.92)", fontSize: 14, lineHeight: 1.7,
                        whiteSpace: "pre-wrap", wordBreak: "break-word",
                      }}>
                        {msg.content}
                      </div>
                      {msg.role !== "user" && (msg.agent || msg.intent) && (
                        <div style={{ display: "flex", gap: 8, marginTop: 4, paddingLeft: 4 }}>
                          {msg.agent && <span style={{ fontSize: 9, color: "#1e3a5f",
                            fontFamily: "'JetBrains Mono', monospace" }}>{msg.agent}</span>}
                          {msg.confidence && <span style={{ fontSize: 9, color: "#1e3a5f",
                            fontFamily: "'JetBrains Mono', monospace" }}>
                            {Math.round(msg.confidence*100)}%</span>}
                          {msg.intent && <span style={{ fontSize: 9, color: accent, opacity: 0.5,
                            fontFamily: "'JetBrains Mono', monospace" }}>{msg.intent}</span>}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
                {streaming && streamBuffer && (
                  <div style={{ display: "flex", flexDirection: "row", gap: 12,
                    marginBottom: 20, alignItems: "flex-start" }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%", flexShrink: 0,
                      background: `radial-gradient(circle at 35% 35%, ${accent}25, ${accent}06)`,
                      border: `1.5px solid ${accent}35`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, color: accent, fontFamily: "'JetBrains Mono', monospace",
                      boxShadow: `0 0 12px ${accent}20`,
                    }}>A</div>
                    <div style={{ maxWidth: "68%", padding: "12px 16px",
                      background: "#080f1c", border: `1px solid ${accent}15`,
                      borderRadius: "16px 16px 16px 4px",
                      color: "rgba(226,232,240,0.92)", fontSize: 14, lineHeight: 1.7,
                      whiteSpace: "pre-wrap" }}>
                      {streamBuffer}
                      <span style={{ display: "inline-block", width: 2, height: "1em",
                        background: accent, marginLeft: 2, verticalAlign: "middle",
                        animation: "blink 0.65s steps(1) infinite", borderRadius: 1 }} />
                    </div>
                  </div>
                )}
                {loading && !streaming && (
                  <div style={{ display: "flex", gap: 12, marginBottom: 20, alignItems: "center" }}>
                    <div style={{ width: 32, height: 32, borderRadius: "50%",
                      background: `radial-gradient(circle at 35% 35%, ${accent}25, ${accent}06)`,
                      border: `1.5px solid ${accent}35`,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 12, color: accent, fontFamily: "'JetBrains Mono', monospace" }}>A</div>
                    <div style={{ display: "flex", gap: 5 }}>
                      {[0,1,2].map(i => (
                        <div key={i} style={{ width: 7, height: 7, borderRadius: "50%",
                          background: accent, opacity: 0.6,
                          animation: `thinking 1.2s ease-in-out ${i*0.16}s infinite` }} />
                      ))}
                    </div>
                  </div>
                )}
              </>
            )
          }
          <div ref={bottomRef} />
        </div>

        {/* Input bar */}
        <div style={{ padding: "14px 24px 20px",
          background: "rgba(4,9,18,0.95)",
          borderTop: "1px solid rgba(56,189,248,0.06)" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 10,
            background: "rgba(4,12,24,0.9)",
            border: `1px solid ${loading ? accent+"30" : "rgba(56,189,248,0.1)"}`,
            borderRadius: 14, padding: "10px 14px",
            transition: "border-color 0.3s",
            boxShadow: loading ? `0 0 20px ${accent}10` : "none",
          }}>
            <div style={{ width: 2, height: 20, borderRadius: 2,
              background: loading ? `linear-gradient(to bottom, ${accent}, ${accent}44)` : "#1e3a5f",
              flexShrink: 0, transition: "background 0.3s" }} />
            <textarea ref={inputRef} value={input}
              onChange={e => setInput(e.target.value)} onKeyDown={onKey}
              placeholder="Speak to ASTRA..."
              rows={1}
              style={{
                flex: 1, background: "transparent", border: "none",
                color: "rgba(226,232,240,0.9)", fontSize: 14, resize: "none",
                fontFamily: "'Space Grotesk', sans-serif",
                lineHeight: 1.5, minHeight: 24, maxHeight: 120, padding: 0,
              }} />
            <button onClick={send} disabled={!input.trim() || loading}
              style={{
                padding: "6px 16px", borderRadius: 8, fontSize: 11,
                fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
                background: input.trim() ? `${accent}18` : "rgba(148,163,184,0.04)",
                border: `1px solid ${input.trim() ? accent+"35" : "#0d1f33"}`,
                color: input.trim() ? accent : "#1e3a5f",
                cursor: "pointer", transition: "all 0.18s",
              }}>SEND</button>
          </div>
          <div style={{ display: "flex", justifyContent: "space-between",
            marginTop: 6, paddingLeft: 4, fontSize: 9,
            fontFamily: "'JetBrains Mono', monospace",
            color: "#0f2040", letterSpacing: "0.08em" }}>
            <span>↵ ENTER to send · ⇧ENTER newline</span>
            <span>JARVIS · {currentModel.toUpperCase()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}


export function FocusLayout({ messages, streamBuffer, streaming, loading,
  input, setInput, send, onKey, inputRef, bottomRef, currentModel }) {
  return (
    <div style={{ height:"100vh", display:"flex", flexDirection:"column",
      alignItems:"center", background:"#0a0500", fontFamily:"'Space Grotesk', sans-serif" }}>
      <div style={{ width:"100%", maxWidth:720, padding:"24px 24px 0",
        display:"flex", justifyContent:"space-between" }}>
        <span style={{ fontSize:11, color:"#f97316", opacity:0.5,
          fontFamily:"'JetBrains Mono', monospace", letterSpacing:"0.2em" }}>
          FOCUS · {currentModel.toUpperCase()}
        </span>
        <span style={{ fontSize:10, color:"#f9731630",
          fontFamily:"'JetBrains Mono', monospace" }}>{messages.length} exchanges</span>
      </div>
      <div style={{ flex:1, width:"100%", maxWidth:720, overflowY:"auto", padding:"32px 24px" }}>
        {messages.length === 0 && (
          <div style={{ textAlign:"center", marginTop:"30vh", color:"#f97316",
            opacity:0.15, fontSize:13, fontFamily:"'JetBrains Mono', monospace",
            letterSpacing:"0.2em" }}>FOCUS MODE · READY</div>
        )}
        {messages.map(msg => (
          <div key={msg.id} style={{ marginBottom:28 }}>
            <span style={{ fontSize:10, fontFamily:"'JetBrains Mono', monospace",
              color: msg.role==="user" ? "#f97316" : "#64748b",
              opacity:0.5, marginBottom:6, display:"block", letterSpacing:"0.1em" }}>
              {msg.role === "user" ? "YOU" : "ASTRA"}
            </span>
            <p style={{ fontSize:15, lineHeight:1.85,
              color: msg.role==="user" ? "#fed7aa" : "rgba(226,232,240,0.85)",
              margin:0, whiteSpace:"pre-wrap" }}>{msg.content}</p>
          </div>
        ))}
        {streaming && streamBuffer && (
          <div style={{ marginBottom:28 }}>
            <span style={{ fontSize:10, fontFamily:"'JetBrains Mono', monospace",
              color:"#64748b", opacity:0.5, display:"block", marginBottom:6 }}>ASTRA</span>
            <p style={{ fontSize:15, lineHeight:1.85,
              color:"rgba(226,232,240,0.85)", margin:0 }}>{streamBuffer}</p>
          </div>
        )}
        {loading && !streaming && (
          <div style={{ color:"#f97316", opacity:0.4, fontSize:12,
            fontFamily:"'JetBrains Mono', monospace" }}>thinking...</div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ width:"100%", maxWidth:720, padding:"0 24px 40px" }}>
        <div style={{ borderTop:"1px solid rgba(249,115,22,0.15)", paddingTop:16,
          display:"flex", gap:12, alignItems:"flex-end" }}>
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={onKey}
            placeholder="Type here..." rows={1}
            style={{ flex:1, background:"transparent", border:"none", color:"#fed7aa",
              fontSize:15, resize:"none", fontFamily:"'Space Grotesk', sans-serif",
              lineHeight:1.6, minHeight:24, maxHeight:120, padding:0 }} />
          <button onClick={send} disabled={!input.trim() || loading}
            style={{ background:"none", border:"none",
              color: input.trim() ? "#f97316" : "#3a2000",
              fontSize:22, cursor:"pointer" }}>→</button>
        </div>
      </div>
    </div>
  );
}

export function ChillLayout({ messages, streamBuffer, streaming, loading,
  input, setInput, send, onKey, inputRef, bottomRef, currentModel }) {
  return (
    <div style={{ height:"100vh", display:"flex", flexDirection:"column",
      background:"#021008", fontFamily:"'Space Grotesk', sans-serif" }}>
      <div style={{ padding:"18px 24px", display:"flex", alignItems:"center", gap:12,
        borderBottom:"1px solid rgba(52,211,153,0.08)" }}>
        <div style={{ width:38, height:38, borderRadius:"50%",
          background:"rgba(52,211,153,0.1)", border:"1.5px solid rgba(52,211,153,0.25)",
          display:"flex", alignItems:"center", justifyContent:"center",
          fontSize:16, color:"#34d399" }}>✦</div>
        <div>
          <div style={{ fontSize:14, color:"#34d399", fontWeight:500 }}>Astra</div>
          <div style={{ fontSize:11, color:"#34d39950" }}>chill mode · {currentModel}</div>
        </div>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:"20px" }}>
        {messages.length === 0 && (
          <div style={{ textAlign:"center", marginTop:"28vh", color:"#34d399",
            opacity:0.18, fontSize:14 }}>Hey! What's on your mind? 🌿</div>
        )}
        {messages.map(msg => (
          <div key={msg.id} style={{ display:"flex", marginBottom:10,
            justifyContent: msg.role==="user" ? "flex-end" : "flex-start" }}>
            <div style={{ maxWidth:"72%", padding:"11px 16px",
              borderRadius: msg.role==="user" ? "20px 20px 4px 20px" : "20px 20px 20px 4px",
              background: msg.role==="user" ? "rgba(52,211,153,0.15)" : "rgba(255,255,255,0.04)",
              border: msg.role==="user" ? "1px solid rgba(52,211,153,0.25)" : "1px solid rgba(255,255,255,0.06)",
              color: msg.role==="user" ? "#a7f3d0" : "rgba(226,232,240,0.88)",
              fontSize:14, lineHeight:1.65, whiteSpace:"pre-wrap" }}>{msg.content}</div>
          </div>
        ))}
        {streaming && streamBuffer && (
          <div style={{ display:"flex", marginBottom:10, justifyContent:"flex-start" }}>
            <div style={{ maxWidth:"72%", padding:"11px 16px",
              borderRadius:"20px 20px 20px 4px",
              background:"rgba(255,255,255,0.04)",
              border:"1px solid rgba(52,211,153,0.12)",
              color:"rgba(226,232,240,0.88)", fontSize:14, lineHeight:1.65 }}>{streamBuffer}</div>
          </div>
        )}
        {loading && !streaming && (
          <div style={{ display:"flex", gap:5, padding:"10px 16px",
            background:"rgba(255,255,255,0.03)", borderRadius:20, width:"fit-content" }}>
            {[0,1,2].map(i => (
              <div key={i} style={{ width:7, height:7, borderRadius:"50%",
                background:"#34d399", opacity:0.4 }} />
            ))}
          </div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ padding:"10px 16px 28px", borderTop:"1px solid rgba(52,211,153,0.06)" }}>
        <div style={{ display:"flex", gap:10, alignItems:"flex-end",
          background:"rgba(255,255,255,0.03)", border:"1px solid rgba(52,211,153,0.12)",
          borderRadius:24, padding:"10px 16px" }}>
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={onKey}
            placeholder="Say something..." rows={1}
            style={{ flex:1, background:"transparent", border:"none", color:"#a7f3d0",
              fontSize:14, resize:"none", fontFamily:"'Space Grotesk', sans-serif",
              lineHeight:1.5, minHeight:22, maxHeight:100, padding:0 }} />
          <button onClick={send} disabled={!input.trim() || loading}
            style={{ width:32, height:32, borderRadius:"50%", border:"none",
              background: input.trim() ? "rgba(52,211,153,0.2)" : "transparent",
              color: input.trim() ? "#34d399" : "#1a4a30",
              fontSize:16, cursor:"pointer", transition:"all 0.2s" }}>↑</button>
        </div>
      </div>
    </div>
  );
}

export function ExpertLayout({ messages, streamBuffer, streaming, loading,
  input, setInput, send, onKey, inputRef, bottomRef, currentModel, health, memory }) {
  return (
    <div style={{ height:"100vh", display:"flex", flexDirection:"column",
      background:"#08040f", fontFamily:"'JetBrains Mono', monospace", fontSize:13 }}>
      <div style={{ padding:"7px 16px", background:"rgba(192,132,252,0.07)",
        borderBottom:"1px solid rgba(192,132,252,0.15)",
        display:"flex", gap:20, alignItems:"center",
        fontSize:10, color:"#c084fc", letterSpacing:"0.1em" }}>
        <span>ASTRA:EXPERT</span>
        <span>MODEL:{currentModel.toUpperCase()}</span>
        <span>MEM:{memory?.user_facts?.length ?? 0}</span>
        <span>BRAIN:{health?.brain ? "OK" : "ERR"}</span>
        <span style={{ marginLeft:"auto", color:"#c084fc40" }}>
          {new Date().toLocaleTimeString([],{hour12:false})}
        </span>
      </div>
      <div style={{ flex:1, overflowY:"auto", padding:16 }}>
        {messages.length === 0 && (
          <div style={{ color:"#c084fc30", lineHeight:2 }}>
            <div>ASTRA Expert Mode v5.1</div>
            <div>Awaiting query...</div>
          </div>
        )}
        {messages.map(msg => (
          <div key={msg.id} style={{ marginBottom:14 }}>
            <div style={{ color: msg.role==="user" ? "#c084fc" : "#7c3aed",
              marginBottom:3, fontSize:10, letterSpacing:"0.1em" }}>
              {msg.role==="user" ? ">>> USER"
                : `<<< ASTRA [${msg.agent||"llm"}] [${msg.intent||"?"}] [${msg.confidence?Math.round(msg.confidence*100)+"%":"?"}]`}
            </div>
            <div style={{ color: msg.role==="user" ? "#e9d5ff" : "#d1d5db",
              lineHeight:1.65, whiteSpace:"pre-wrap", paddingLeft:8,
              borderLeft:`2px solid ${msg.role==="user" ? "#c084fc30" : "#7c3aed25"}` }}>
              {msg.content}
            </div>
          </div>
        ))}
        {streaming && streamBuffer && (
          <div style={{ marginBottom:14 }}>
            <div style={{ color:"#7c3aed", marginBottom:3, fontSize:10 }}>{"<<< ASTRA [streaming...]"}</div>
            <div style={{ color:"#d1d5db", lineHeight:1.65, paddingLeft:8,
              borderLeft:"2px solid #7c3aed25", whiteSpace:"pre-wrap" }}>{streamBuffer}▋</div>
          </div>
        )}
        {loading && !streaming && (
          <div style={{ color:"#c084fc40", fontSize:11 }}>{"<<< PROCESSING..."}</div>
        )}
        <div ref={bottomRef} />
      </div>
      <div style={{ borderTop:"1px solid rgba(192,132,252,0.12)", padding:"8px 16px",
        display:"flex", gap:8, alignItems:"center", background:"rgba(192,132,252,0.03)" }}>
        <span style={{ color:"#c084fc", fontSize:12 }}>{">>>"}</span>
        <textarea ref={inputRef} value={input}
          onChange={e => setInput(e.target.value)} onKeyDown={onKey}
          placeholder="enter query..." rows={1}
          style={{ flex:1, background:"transparent", border:"none", color:"#e9d5ff",
            fontSize:13, resize:"none", fontFamily:"'JetBrains Mono', monospace",
            lineHeight:1.5, minHeight:20, maxHeight:80, padding:0 }} />
        <button onClick={send} disabled={!input.trim() || loading}
          style={{ background:"none", border:"1px solid rgba(192,132,252,0.25)",
            borderRadius:4, color:"#c084fc", padding:"2px 10px",
            fontSize:10, cursor:"pointer", letterSpacing:"0.1em" }}>EXEC</button>
      </div>
    </div>
  );
}

export function DebugLayout({ messages, streamBuffer, streaming, loading,
  input, setInput, send, onKey, inputRef, bottomRef, currentModel, health, memory }) {
  return (
    <div style={{ height:"100vh", display:"flex", background:"#0a0800",
      fontFamily:"'JetBrains Mono', monospace" }}>
      <div style={{ flex:1, display:"flex", flexDirection:"column",
        borderRight:"1px solid rgba(251,191,36,0.1)" }}>
        <div style={{ padding:"7px 14px", fontSize:10, color:"#fbbf24",
          letterSpacing:"0.12em", borderBottom:"1px solid rgba(251,191,36,0.1)",
          background:"rgba(251,191,36,0.04)" }}>
          [DEBUG] ASTRA v5.1 · {currentModel.toUpperCase()} · TRACE ACTIVE
        </div>
        <div style={{ flex:1, overflowY:"auto", padding:14 }}>
          {messages.length === 0 && (
            <div style={{ color:"#fbbf2430", fontSize:11, lineHeight:2 }}>
              <div>[SYS] debug mode active</div>
              <div>[SYS] awaiting input...</div>
            </div>
          )}
          {messages.map(msg => (
            <div key={msg.id} style={{ marginBottom:10, fontSize:12 }}>
              <div style={{ marginBottom:2 }}>
                <span style={{ color: msg.role==="user" ? "#fbbf24" : "#22c55e" }}>
                  {msg.role==="user" ? "[USR]" : "[AST]"}
                </span>
                {msg.role !== "user" && (
                  <span style={{ color:"#fbbf2450", fontSize:10, marginLeft:6 }}>
                    {msg.agent} · {msg.intent} · {msg.confidence?Math.round(msg.confidence*100)+"%":""}
                  </span>
                )}
              </div>
              <div style={{ color: msg.role==="user" ? "#fef3c7" : "#86efac",
                lineHeight:1.55, paddingLeft:8, whiteSpace:"pre-wrap" }}>{msg.content}</div>
            </div>
          ))}
          {streaming && streamBuffer && (
            <div style={{ marginBottom:10, fontSize:12 }}>
              <div style={{ color:"#22c55e", marginBottom:2 }}>
                [AST] <span style={{ color:"#fbbf2450", fontSize:10 }}>streaming...</span>
              </div>
              <div style={{ color:"#86efac", lineHeight:1.55, paddingLeft:8 }}>{streamBuffer}▋</div>
            </div>
          )}
          {loading && !streaming && (
            <div style={{ color:"#fbbf2440", fontSize:11 }}>[SYS] processing...</div>
          )}
          <div ref={bottomRef} />
        </div>
        <div style={{ padding:"8px 14px", borderTop:"1px solid rgba(251,191,36,0.1)",
          display:"flex", gap:8, alignItems:"center" }}>
          <span style={{ color:"#fbbf24", fontSize:12 }}>$</span>
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={onKey}
            placeholder="query..." rows={1}
            style={{ flex:1, background:"transparent", border:"none", color:"#fef3c7",
              fontSize:12, resize:"none", fontFamily:"'JetBrains Mono', monospace",
              lineHeight:1.5, minHeight:20, maxHeight:80, padding:0 }} />
          <button onClick={send} disabled={!input.trim() || loading}
            style={{ background:"rgba(251,191,36,0.08)",
              border:"1px solid rgba(251,191,36,0.25)", borderRadius:3,
              color:"#fbbf24", padding:"2px 8px", fontSize:10, cursor:"pointer" }}>RUN</button>
        </div>
      </div>
      <div style={{ width:200, padding:14, fontSize:11, color:"#fbbf2460", overflowY:"auto" }}>
        <div style={{ color:"#fbbf24", marginBottom:10, letterSpacing:"0.12em", fontSize:10 }}>[SYSTEM]</div>
        {[["BRAIN",health?.brain],["MEMORY",health?.memory],["VOICE",health?.voice],["OLLAMA",health?.ollama]].map(([k,v]) => (
          <div key={k} style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
            <span>{k}</span><span style={{ color: v?"#22c55e":"#ef4444" }}>{v?"OK":"ERR"}</span>
          </div>
        ))}
        <div style={{ margin:"12px 0 8px", color:"#fbbf24", letterSpacing:"0.12em", fontSize:10 }}>[MEMORY]</div>
        {[["FACTS",memory?.user_facts?.length??0],["TASKS",memory?.tasks?.filter(t=>t.status==="todo").length??0],["CONVOS",memory?.conversation_count??0]].map(([k,v]) => (
          <div key={k} style={{ display:"flex", justifyContent:"space-between", marginBottom:5 }}>
            <span>{k}</span><span style={{ color:"#fbbf24" }}>{v}</span>
          </div>
        ))}
        <div style={{ margin:"12px 0 8px", color:"#fbbf24", letterSpacing:"0.12em", fontSize:10 }}>[LOG]</div>
        <div style={{ fontSize:10, color:"#fbbf2440", lineHeight:1.9 }}>
          <div>brain.process() ok</div>
          <div>memory.load() ok</div>
          <div>model: {currentModel}</div>
          <div>ws: active</div>
        </div>
      </div>
    </div>
  );
}
