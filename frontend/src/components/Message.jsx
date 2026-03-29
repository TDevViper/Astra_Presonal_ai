import React from "react";
import { StreamCursor } from "./Atoms";

function Message({ msg, isStreaming, accent, theme }) {
  theme = theme || MODE_THEMES.jarvis;
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
            ? (theme?.userBubble  || "#0d1e35")
            : (theme?.astraBubble || "#080f1c"),
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

export { Message };
