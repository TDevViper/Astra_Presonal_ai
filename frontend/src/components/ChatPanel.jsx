import { useRef } from "react";

function ThinkingDots() {
  return (
    <div style={{ display: "flex", gap: 5, alignItems: "center", padding: "4px 0" }}>
      {[0, 1, 2].map(i => (
        <div key={i} style={{
          width: 7, height: 7, borderRadius: "50%", background: "#4a6fa5",
          animation: `thinking 1.2s ease-in-out ${i * 0.16}s infinite`,
        }} />
      ))}
    </div>
  );
}

function StreamCursor({ accent }) {
  return (
    <span style={{
      display: "inline-block", width: 2, height: "1em",
      background: accent, marginLeft: 2, verticalAlign: "middle",
      animation: "blink 0.65s steps(1) infinite", borderRadius: 1,
    }} />
  );
}

function AstraOrb({ active, accent = "#38bdf8", size = 36 }) {
  return (
    <div style={{ position: "relative", width: size, height: size, flexShrink: 0 }}>
      {active && (
        <div style={{
          position: "absolute", inset: -4, borderRadius: "50%",
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
        fontSize: size * 0.36, fontWeight: 500, color: accent,
        fontFamily: "'JetBrains Mono', monospace",
        boxShadow: active ? `0 0 20px ${accent}30, inset 0 0 12px ${accent}10` : "none",
        transition: "box-shadow 0.4s ease",
      }}>A</div>
    </div>
  );
}

const intentColor = (intent) => ({
  casual: "#34d399", technical: "#60a5fa", research: "#f59e0b",
  coding: "#a78bfa", reasoning: "#fb923c", general: "#94a3b8",
}[intent?.toLowerCase()] || "#94a3b8");

const agentLabel = (a) => {
  if (a?.includes("mistral")) return "MISTRAL";
  if (a?.includes("llama"))   return "LLAMA";
  if (a?.includes("phi3"))    return "PHI3";
  if (a === "web_search_agent")  return "WEB";
  if (a === "memory")            return "MEMORY";
  if (a === "intent_handler")    return "SHORTCUT";
  return (a || "ASTRA").toUpperCase().slice(0, 10);
};

function Message({ msg, isStreaming, accent, theme }) {
  theme = theme || {};
  const isUser = msg.role === "user";
  const iColor = intentColor(msg.intent);
  return (
    <div style={{
      display: "flex", flexDirection: isUser ? "row-reverse" : "row",
      gap: 12, marginBottom: 20, alignItems: "flex-start",
      animation: "fadeSlideUp 0.25s ease forwards",
    }}>
      {!isUser
        ? <AstraOrb active={isStreaming} accent={accent} size={34} />
        : (
          <div style={{
            width: 34, height: 34, borderRadius: "50%", flexShrink: 0,
            background: "#0a1628", border: "1.5px solid rgba(148,163,184,0.12)",
            display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 12, color: "#4a6fa5", fontFamily: "'JetBrains Mono', monospace",
          }}>U</div>
        )
      }
      <div style={{ maxWidth: "68%", minWidth: 60 }}>
        <div style={{
          padding: "13px 17px",
          background: isUser ? (theme.userBubble || "#0d1e35") : (theme.astraBubble || "#080f1c"),
          border: isUser ? `1px solid ${accent}20` : "1px solid rgba(255,255,255,0.07)",
          borderRadius: isUser ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
          color: "rgba(226,232,240,0.92)", fontSize: 14, lineHeight: 1.7,
          whiteSpace: "pre-wrap", wordBreak: "break-word", position: "relative",
        }}>
          {msg.content}
          {isStreaming && <StreamCursor accent={accent} />}
        </div>
        {!isUser && (msg.agent || msg.intent) && (
          <div style={{ display: "flex", gap: 10, marginTop: 5, paddingLeft: 4, alignItems: "center" }}>
            {msg.agent && <span style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: "#1e3a5f" }}>{agentLabel(msg.agent)}</span>}
            {msg.confidence && <span style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: "#1e3a5f" }}>{Math.round(msg.confidence * 100)}%</span>}
            {msg.intent && <span style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace", color: iColor, opacity: 0.7 }}>{msg.intent.toUpperCase()}</span>}
          </div>
        )}
      </div>
    </div>
  );
}

export default function ChatPanel({
  messages, streamBuffer, streaming, loading,
  input, setInput, send, onKey, inputRef, bottomRef,
  accent, theme, currentModel, currentMode, useStream, setUseStream,
  streaming: isStreaming, stopStream,
}) {
  const HINTS = ["Ask me anything", "Play music", "Send a message", "Check system"];

  return (
    <>
      {/* Messages */}
      <div style={{
        flex: 1, overflowY: "auto", minHeight: 0,
        padding: "24px 28px", background: theme?.chatBg || "#040c18",
        transition: "background 0.6s ease",
      }}>
        {messages.length === 0 && (
          <div style={{ height: "100%", display: "flex", flexDirection: "column",
            alignItems: "center", justifyContent: "center", gap: 10 }}>
            <div style={{ fontSize: 56, fontWeight: 200, letterSpacing: "0.3em", color: "#0d1f33" }}>ASTRA</div>
            <div style={{ fontSize: 10, letterSpacing: "0.25em",
              fontFamily: "'JetBrains Mono', monospace", color: accent, opacity: 0.2 }}>
              SYSTEMS READY · AWAITING INPUT
            </div>
            <div style={{ marginTop: 24, display: "flex", gap: 24, fontSize: 11, color: "#0f2040" }}>
              {HINTS.map(hint => (
                <div key={hint} onClick={() => setInput(hint)} style={{
                  padding: "8px 16px", borderRadius: 10,
                  border: "1px solid rgba(148,163,184,0.08)", cursor: "pointer",
                }}>{hint}</div>
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
            isStreaming={true} accent={accent} theme={theme}
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
        background: "rgba(6,13,26,0.6)", backdropFilter: "blur(24px)",
        borderTop: "1px solid rgba(148,163,184,0.06)",
      }}>
        <div style={{
          display: "flex", alignItems: "center", gap: 12,
          background: "rgba(4,12,24,0.9)",
          border: `1px solid ${loading ? accent + "30" : "#0d1f33"}`,
          borderRadius: 14, padding: "10px 14px",
          transition: "border-color 0.3s ease",
          boxShadow: loading ? `0 0 20px ${accent}10` : "none",
        }}>
          <div style={{
            width: 2, height: 22, borderRadius: 2, flexShrink: 0,
            background: loading ? `linear-gradient(to bottom, ${accent}, ${accent}44)` : "#1e3a5f",
            transition: "background 0.3s ease",
          }} />
          <textarea ref={inputRef} value={input}
            onChange={e => setInput(e.target.value)} onKeyDown={onKey}
            placeholder="Speak to ASTRA..." rows={1}
            style={{
              flex: 1, background: "transparent", border: "none",
              color: "rgba(226,232,240,0.9)", fontSize: 14, resize: "none",
              fontFamily: "'Space Grotesk', sans-serif",
              lineHeight: 1.5, minHeight: 24, maxHeight: 120, padding: 0,
            }} />
          <button onClick={() => setUseStream(s => !s)} style={{
            fontSize: 9, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
            padding: "4px 8px", borderRadius: 6,
            background: useStream ? `${accent}18` : "transparent",
            border: `1px solid ${useStream ? accent + "40" : "#0d1f33"}`,
            color: useStream ? accent : "#1e3a5f", transition: "all 0.18s",
          }}>{useStream ? "STREAM" : "STATIC"}</button>
          {isStreaming ? (
            <button onClick={stopStream} style={{
              padding: "7px 16px", borderRadius: 8, fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace",
              background: "rgba(248,113,113,0.12)",
              border: "1px solid rgba(248,113,113,0.25)", color: "#f87171",
            }}>STOP</button>
          ) : (
            <button onClick={send} disabled={!input.trim() || loading} style={{
              padding: "7px 18px", borderRadius: 8, fontSize: 11,
              fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.08em",
              background: input.trim() ? `${accent}18` : "rgba(148,163,184,0.05)",
              border: `1px solid ${input.trim() ? accent + "40" : "#0d1f33"}`,
              color: input.trim() ? accent : "#1e3a5f", transition: "all 0.18s ease",
            }}>SEND</button>
          )}
        </div>
        <div style={{
          display: "flex", justifyContent: "space-between",
          marginTop: 7, paddingLeft: 4, fontSize: 9,
          fontFamily: "'JetBrains Mono', monospace", color: "#0f2040", letterSpacing: "0.08em",
        }}>
          <span>↵ ENTER to send · ⇧ENTER newline</span>
          <span>{currentMode.toUpperCase()} MODE · {currentModel.toUpperCase()}</span>
        </div>
      </div>
    </>
  );
}
