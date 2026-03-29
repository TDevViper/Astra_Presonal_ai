import React from "react";

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

export { ModePill };
