import React, { useState, useEffect } from "react";

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

export { ThinkingDots, StreamCursor, AstraOrb, StatBar };
