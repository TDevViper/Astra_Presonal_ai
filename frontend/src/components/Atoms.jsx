import React, { useState, useEffect } from "react";

export function ThinkingDots() {
  return (
    <div className="flex gap-1.5 items-center py-1">
      {[0, 1, 2].map(i => (
        <div key={i} className="w-1.5 h-1.5 rounded-full bg-slate-600"
          style={{ animation: `thinking 1.2s ease-in-out ${i * 0.16}s infinite` }} />
      ))}
    </div>
  );
}

export function StreamCursor() {
  return (
    <span className="inline-block w-0.5 h-[1em] bg-sky-400 ml-0.5 align-middle
      animate-pulse rounded-sm" />
  );
}

export function AstraOrb({ active, accent = "#38bdf8", size = 36 }) {
  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      {active && (
        <div className="absolute rounded-full border animate-ping pointer-events-none"
          style={{ inset: -4, borderColor: accent, opacity: 0.4 }} />
      )}
      <div className="w-full h-full rounded-full flex items-center justify-center
        font-mono font-medium backdrop-blur-sm transition-shadow duration-400"
        style={{
          background: `radial-gradient(circle at 35% 35%, ${accent}30, ${accent}08)`,
          border: `1.5px solid ${accent}44`,
          fontSize: size * 0.36,
          color: accent,
          boxShadow: active ? `0 0 20px ${accent}30` : "none",
        }}>A</div>
    </div>
  );
}

export function StatBar({ label, value = 0 }) {
  const color = value > 85 ? "#f87171" : value > 65 ? "#fbbf24" : "#34d399";
  return (
    <div className="mb-2.5">
      <div className="flex justify-between text-[10px] font-mono mb-1">
        <span className="text-slate-500">{label}</span>
        <span style={{ color }}>{value.toFixed(0)}%</span>
      </div>
      <div className="h-[3px] bg-slate-800 rounded-full overflow-hidden">
        <div className="h-full rounded-full transition-all duration-1000"
          style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}
