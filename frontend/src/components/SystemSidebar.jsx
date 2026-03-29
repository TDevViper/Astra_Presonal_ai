import React, { useState, useEffect } from "react";
import { StatBar } from "./Atoms";

function SystemSidebar({ health, memory, models, currentModel, onSwitchModel }) {
  const [sysInfo, setSysInfo] = useState(null);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetchStats = async () => {
      try {
        const r = await fetch(API.stats);
        if (r.ok) setSysInfo(await r.json());
      } catch { /* ignore */ }
    };
    fetchStats();
    const t = setInterval(fetchStats, 10000);
    return () => clearInterval(t);
  }, []);

  const cpu  = sysInfo?.cpu?.percent  ?? 0;
  const ram  = sysInfo?.memory?.percent ?? 0;
  const disk = sysInfo?.disk?.percent  ?? 0;

  const services = [
    { name: "BRAIN",  ok: health?.brain  ?? false },
    { name: "MEMORY", ok: health?.memory ?? false },
    { name: "VOICE",  ok: health?.voice  ?? false },
    { name: "OLLAMA", ok: health?.ollama ?? false },
  ];

  return (
    <div style={{
      width: 200, flexShrink: 0,
      borderLeft: "1px solid rgba(148,163,184,0.07)",
      background: "#030912",
      backdropFilter: "blur(24px)",
      padding: "20px 14px",
      display: "flex", flexDirection: "column", gap: 0,
      overflowY: "auto",
    }}>

      {/* Clock */}
      <div style={{
        textAlign: "center", marginBottom: 20,
        paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)",
      }}>
        <div style={{
          fontSize: 22, fontWeight: 300, letterSpacing: "0.12em",
          fontFamily: "'JetBrains Mono', monospace", color: "#e2e8f0",
        }}>
          {time.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false })}
        </div>
        <div style={{
          fontSize: 9, letterSpacing: "0.15em", marginTop: 4,
          color: "#2a4a6a", fontFamily: "'JetBrains Mono', monospace",
        }}>
          {time.toLocaleDateString([], { weekday: "short", day: "numeric", month: "short" }).toUpperCase()}
        </div>
      </div>

      {/* System stats */}
      <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>SYSTEM</div>
        <StatBar label="CPU"  value={cpu} />
        <StatBar label="RAM"  value={ram} />
        <StatBar label="DISK" value={disk} />
      </div>

      {/* Services */}
      <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>SERVICES</div>
        {services.map(({ name, ok }) => (
          <div key={name} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            marginBottom: 8,
          }}>
            <span style={{ fontSize: 10, color: "#2a4a6a", fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em" }}>
              {name}
            </span>
            <div style={{
              width: 6, height: 6, borderRadius: "50%",
              background: ok ? "#34d399" : "#475569",
              boxShadow: ok ? "0 0 6px #34d39966" : "none",
              transition: "all 0.3s",
            }} />
          </div>
        ))}
      </div>

      {/* Models */}
      <div style={{ marginBottom: 20, paddingBottom: 16, borderBottom: "1px solid rgba(148,163,184,0.06)" }}>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>MODELS</div>
        {(models || ["phi3:mini"]).map(m => {
          const active = m === currentModel;
          return (
            <div key={m} onClick={() => onSwitchModel?.(m)} style={{
              padding: "6px 9px", marginBottom: 4, borderRadius: 6,
              fontSize: 9, fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.05em",
              cursor: "pointer",
              background: active ? "rgba(56,189,248,0.1)" : "transparent",
              color: active ? "#38bdf8" : "#2a4a6a",
              border: `1px solid ${active ? "rgba(56,189,248,0.2)" : "transparent"}`,
              transition: "all 0.18s ease",
            }}>
              {m.toUpperCase()}
            </div>
          );
        })}
      </div>

      {/* Memory core */}
      <div>
        <div style={{
          fontSize: 8, letterSpacing: "0.2em", color: "#1e3a5f",
          fontFamily: "'JetBrains Mono', monospace", marginBottom: 12,
        }}>MEMORY CORE</div>
        {[
          { label: "FACTS",  val: memory?.user_facts?.length ?? 0,                              color: "#38bdf8" },
          { label: "TASKS",  val: memory?.tasks?.filter(t => t.status === "todo").length ?? 0,  color: "#fbbf24" },
          { label: "CONVOS", val: memory?.conversation_count ?? 0,                              color: "#34d399" },
        ].map(({ label, val, color }) => (
          <div key={label} style={{
            display: "flex", justifyContent: "space-between", alignItems: "center",
            marginBottom: 7,
          }}>
            <span style={{ fontSize: 10, color: "#2a4a6a", fontFamily: "'JetBrains Mono', monospace" }}>
              {label}
            </span>
            <span style={{
              fontSize: 11, fontFamily: "'JetBrains Mono', monospace",
              color, fontWeight: 500,
            }}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Message bubble ────────────────────────────────────────────────────────────

export { SystemSidebar };
