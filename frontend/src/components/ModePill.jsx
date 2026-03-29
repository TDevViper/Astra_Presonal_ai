import React from "react";

export function ModePill({ mode, active, onClick, accent }) {
  return (
    <button onClick={onClick} title={mode.description}
      className={`px-3 py-1 rounded-full text-[9px] font-mono tracking-widest
        transition-all duration-200 border
        ${active
          ? "border-current shadow-[0_0_12px_currentColor/20]"
          : "border-transparent text-slate-600 hover:text-slate-400"}`}
      style={active ? { color: accent, backgroundColor: `${accent}18`, borderColor: `${accent}44` } : {}}>
      {mode.emoji} {mode.name?.toUpperCase()}
    </button>
  );
}
