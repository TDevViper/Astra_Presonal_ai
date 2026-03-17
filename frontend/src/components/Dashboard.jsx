import { useState, useEffect, useRef } from "react";
import API from "../config";

const KEY = "91008d3c8ce5f66e23dd68c0fb6117adae0c5e2ebcc3995c5fd054c41108cc2e";
const H = { "X-API-Key": KEY };

function ScoreRing({ score, level }) {
  const color = level === "healthy" ? "#34d399" : level === "warning" ? "#fbbf24" : "#f87171";
  const r = 52, circ = 2 * Math.PI * r;
  const fill = (score / 100) * circ;
  return (
    <div style={{ position: "relative", width: 140, height: 140, flexShrink: 0 }}>
      <svg width="140" height="140" style={{ transform: "rotate(-90deg)" }}>
        <circle cx="70" cy="70" r={r} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="10"/>
        <circle cx="70" cy="70" r={r} fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${fill} ${circ}`} strokeLinecap="round"
          style={{ transition: "stroke-dasharray 1s ease" }}/>
      </svg>
      <div style={{
        position: "absolute", inset: 0, display: "flex",
        flexDirection: "column", alignItems: "center", justifyContent: "center",
      }}>
        <div style={{ fontSize: 32, fontWeight: 600, color, fontFamily: "'JetBrains Mono', monospace" }}>
          {score}
        </div>
        <div style={{ fontSize: 9, color: color, opacity: 0.7,
          letterSpacing: "0.15em", fontFamily: "'JetBrains Mono', monospace" }}>
          {level?.toUpperCase()}
        </div>
      </div>
    </div>
  );
}

function MetricBar({ label, value, max, unit = "%", color }) {
  const pct = Math.min(100, (value / max) * 100);
  const c = color || (pct > 85 ? "#f87171" : pct > 65 ? "#fbbf24" : "#34d399");
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between",
        fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
        color: "#4a6fa5", marginBottom: 5, letterSpacing: "0.05em" }}>
        <span>{label}</span>
        <span style={{ color: c }}>{typeof value === "number" ? value.toFixed(1) : value}{unit}</span>
      </div>
      <div style={{ height: 4, background: "rgba(255,255,255,0.05)", borderRadius: 2, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${pct}%`, borderRadius: 2,
          background: `linear-gradient(90deg, ${c}88, ${c})`,
          transition: "width 0.8s cubic-bezier(0.4,0,0.2,1)",
          boxShadow: `0 0 6px ${c}44`,
        }}/>
      </div>
    </div>
  );
}

function TrendBadge({ trend }) {
  const cfg = {
    improving: { icon: "↑", color: "#34d399", label: "IMPROVING" },
    stable:    { icon: "→", color: "#38bdf8", label: "STABLE"    },
    degrading: { icon: "↓", color: "#f87171", label: "DEGRADING" },
    unknown:   { icon: "?", color: "#64748b", label: "UNKNOWN"   },
  }[trend] || { icon: "?", color: "#64748b", label: "UNKNOWN" };
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      padding: "2px 8px", borderRadius: 20, fontSize: 9,
      fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
      background: `${cfg.color}15`, border: `1px solid ${cfg.color}30`,
      color: cfg.color,
    }}>
      {cfg.icon} {cfg.label}
    </span>
  );
}

function TraceRow({ trace }) {
  const [open, setOpen] = useState(false);
  const total = trace.total_ms;
  const color = total > 10000 ? "#f87171" : total > 3000 ? "#fbbf24" : "#34d399";
  const agentShort = (trace.agent || "?").replace("ollama/", "").toUpperCase().slice(0, 12);
  return (
    <div style={{
      borderBottom: "1px solid rgba(255,255,255,0.04)",
      cursor: "pointer",
    }} onClick={() => setOpen(o => !o)}>
      <div style={{
        display: "flex", alignItems: "center", gap: 12,
        padding: "10px 0", fontSize: 11,
        fontFamily: "'JetBrains Mono', monospace",
      }}>
        <span style={{ color: "#1e3a5f", fontSize: 9, minWidth: 70 }}>
          {trace.request_id?.slice(0, 8)}
        </span>
        <span style={{
          padding: "1px 6px", borderRadius: 4, fontSize: 9,
          background: "rgba(56,189,248,0.08)", color: "#38bdf8",
          border: "1px solid rgba(56,189,248,0.15)",
        }}>{trace.intent?.toUpperCase()}</span>
        <span style={{ color: "#4a6fa5", flex: 1 }}>{agentShort}</span>
        <span style={{ color, fontWeight: 500 }}>
          {total >= 1000 ? `${(total/1000).toFixed(1)}s` : `${total}ms`}
        </span>
        <span style={{ color: "#1e3a5f", fontSize: 9 }}>{open ? "▲" : "▼"}</span>
      </div>
      {open && trace.steps?.length > 0 && (
        <div style={{ paddingBottom: 10, paddingLeft: 82 }}>
          {trace.steps.filter(s => s.ms > 0).map((s, i) => (
            <div key={i} style={{
              display: "flex", gap: 12, marginBottom: 4,
              fontSize: 10, fontFamily: "'JetBrains Mono', monospace",
              color: "#4a6fa5",
            }}>
              <span style={{ color: "#1e3a5f", minWidth: 80 }}>└ {s.step}</span>
              <span style={{ color: s.ms > 5000 ? "#f87171" : "#34d399" }}>
                {s.ms >= 1000 ? `${(s.ms/1000).t(2)}s` : `${s.ms}ms`}
              </span>
              {s.meta && <span style={{ color: "#1e3a5f" }}>{s.meta}</span>}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function MiniSparkline({ scores }) {
  if (!scores?.length) return null;
  const max = 100, min = 0, h = 40, w = 160;
  const pts = scores.map((s, i) => {
    const x = (i / Math.max(scores.length - 1, 1)) * w;
    const y = h - ((s - min) / (max - min)) * h;
    return `${x},${y}`;
  }).join(" ");
  return (
    <svg width={w} height={h} style={{ overflow: "visible" }}>
      <polyline points={pts} fill="none" stroke="#38bdf8" strokeWidth="1.5"
        strokeLinejoin="round" strokeLinecap="round"/>
      {scores.map((s, i) => {
        const x = (i / Math.max(scores.length - 1, 1)) * w;
        const y = h - ((s - min) / (max - min)) * h;
        return <circle key={i} cx={x} cy={y} r="2.5" fill="#38bdf8"/>;
      })}
    </svg>
  );
}

export default function Dashboard() {
  const [health, setHealth] = useState(null);
  const [traces, setTraces] = useState([]);
  const [stats,  setStats]  = useState(null);
  const [tick,   setTick]   = useState(0);
  const [lastUpdated, setLastUpdated] = useState(null);

  const fetchAll = async () => {
    try {
      const [h, t] = await Promise.all([
        fetch(API.healthScore, { headers: H }).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(API.traces,      { headers: H }).then(r => r.ok ? r.json() : null).catch(() => null),
      ]);
      if (h) setHealth(h);
      if (t) { setTraces(t.traces || []); setStats(t.stats || null); }
      setLastUpdated(new Date());
      setTick(n => n + 1);
    } catch {}
  };

  useEffect(() => {
    fetchAll();
    const id = setInterval(fetchAll, 10000);
    return () => clearInterval(id);
  }, []);

  const score   = health?.score ?? 0;
  const level   = health?.level ?? "unknown";
  const trend   = health?.trend?.trend ?? "unknown";
  const scores  = health?.trend?.recent_scores ?? [];
  const ttc     = health?.trend?.time_to_critical;
  const accent  = "#38bdf8";

  // Stats from traces
  const llmAvg  = stats?.per_step_avg?.llm;
  const avgTotal = stats?.avg_total_ms;
  const reqCount = stats?.requests ?? 0;

  // Intent distribution
  const intentCounts = {};
  traces.forEach(t => { intentCounts[t.intent] = (intentCounts[t.intent] || 0) + 1; });
  const intentColors = { casual: "#34d399", technical: "#60a5fa", research: "#f59e0b",
    coding: "#a78bfa", reasoning: "#fb923c", general: "#94a3b8", shortcut: "#38bdf8", error: "#f87171" };

  return (
    <div style={{
      minHeight: "100vh", background: "#04090f",
      color: "rgba(226,232,240,0.9)",
      fontFamily: "'Space Grotesk', sans-serif",
      padding: "28px 32px",
    }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between",
        alignItems: "center", marginBottom: 28 }}>
        <div>
          <div style={{ fontSize: 18, fontWeight: 500, letterSpacing: "0.15em",
            fontFamily: "'JetBrains Mono', monospace", color: accent }}>
            ASTRA DASHBOARD
          </div>
          <div style={{ fontSize: 10, color: "#1e3a5f", letterSpacing: "0.1em",
            fontFamily: "'JetBrains Mono', monospace", marginTop: 3 }}>
            OBSERVABILITY · HEALTH · TRACES
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          {lastUpdated && (
            <span style={{ fontSize: 9, color: "#1e3a5f",
              fontFamily: "'JetBrains Mono', monospace" }}>
              updated {lastUpdated.toLocaleTimeString([], {hour12: false})}
            </span>
          )}
          <button onClick={fetchAll} style={{
            padding: "5px 12px", borderRadius: 6, fontSize: 9, cursor: "pointer",
            fontFamily: "'JetBrains Mono', monospace", letterSpacing: "0.1em",
            background: `${accent}15`, border: `1px solid ${accent}30`, color: accent,
          }}>↺ REFRESH</button>
        </div>
      </div>

      {/* Top row — Health + Metrics */} <div style={{ display: "grid", gridTemplateColumns: "auto 1fr 1fr", gap: 16, marginBottom: 16 }}>

        {/* Score ring */}
        <div style={{
          padding: "24px", borderRadius: 14,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
          display: "flex", flexDirection: "column", alignItems: "center", gap: 16,
        }}>
          <ScoreRing score={score} level={level} />
          <TrendBadge trend={trend} />
          {scores.length > 1 && <MiniSparkline scores={scores} />}
          {ttc && (
            <div style={{ fontSize: 9, color: "#f87171",
              fontFamily: "'JetBrains Mono', monospace", textAlign: "center" }}>
              ⚠ critical in ~{ttc}min
            </div>
          )}
        </div>

        {/* System metrics */}
        <div style={{
          padding: "20px 24px", borderRadius: 14,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          <div style={{ fontSize: 9, letterSpacing: "0.18em", color: "#1e3a5f",
            fontFamily: "'JetBrains Mono', monospace", marginBottom: 16 }}>SYSTEM</div>
          {health ? <>
            <MetricBar label="CPU" value={health.cpu_percent} max={100} />
            <MetricBar label="RAM" value={health.ram_percent} max={100} />
            <MetricBar label="DISK" value={health.disk_percent} max={100} />
            <MetricBar label="MEMORY PRESSURE" value={health.memory_pressure * 100} max={100} color="#a78bfa"/>
            <MetricBar label="SWAP" value={health.swap_mb} max={4000} unit="MB" color="#fbbf24"/>
          </> : <div style={{ color: "#1e3a5f", fontSize: 11 }}>Loading...</div>}
          {health && (
            <div style={{ marginTop: 10, fontSize: 10, color: "#2a4a6a",
              fontFamily: "'JetBrains Mono', monospace" }}>
              {health.ram_available_gb}GB available
            </div>
          )}
        </div>

        {/* Request stats */}
        <div style={{
          padding: "20px 24px", borderRadius: 14,
          background: "rgba(255,255,255,0.02)",
          border: "1px solid rgba(255,255,255,0.06)",
        }}>
          <div style={{ fontSize: 9, letterSpacing: "0.18em", color: "#1e3a5f",
            fontFamily: "'JetBrains Mono', monospace", marginBottom: 16 }}>REQUESTS</div>

          {[
            ["TOTAL REQUESTS", reqCount, "#38bdf8"],
            ["AVG LATENCY",   avgTotal  ? `${(avgTotal/1000).toFixed(2)}s`  : "—", "#34d399"],
            ["AVG LLM TIME",  llmAvg    ? `${(llmAvg/1000).toFixed(2)}s`   : "—", "#a78bfa"],
            ["P95 LATENCY",   stats?.p95_ms ? `${(stats.p95_ms/1000).toFixed(2)}s` : "—", "#fbbf24"],
          ].map(([label, val, color]) => (
            <div key={label} style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
                color: "#1e3a5f", letterSpacing: "0.08em", marginBottom: 4 }}>{label}</div>
              <div style={{ fontSize: 20, fontWeight: 500,
          fontFamily: "'JetBrains Mono', monospace", color }}>{val}</div>
            </div>
          ))}

          {/* Intent distribution */}
          <div style={{ marginTop: 8 }}>
            <div style={{ fontSize: 9, letterSpacing: "0.08em", color: "#1e3a5f",
              fontFamily: "'JetBrains Mono', monospace", marginBottom: 8 }}>INTENTS</div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 5 }}>
              {Object.entries(intentCounts).map(([intent, count]) => (
                <span key={intent} style={{
                  padding: "2px 7px", borderRadius: 20, fontSize: 9,
                  fontFamily: "'JetBrains Mono', monospace",
                  background: `${intentColors[intent] || "#94a3b8"}15`,
                  border: `1px solid ${intentColors[intent] || "#94a3b8"}30`,
                  color: intentColors[intent] || "#94a3b8",
                }}>{intent} ({count})</span>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Traces table */}
      <div style={{
        padding: "20px 24px", borderRadius: 14,
        background: "rgba(255,255,255,0.02)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}>
        <div style={{ display: "flex", justifyContent: "space-between",
          alignItems: "center", marginBottom: 16 }}>
          <div style={{ fontSize: 9, letterSpacing: "0.18em", color: "#1e3a5f",
            fontFamily: "'JetBrains Mono', monospace" }}>
            REQUEST TRACES ({traces.length})
          </div>
          <div style={{ fontSize: 9, color: "#1e3a5f",
            fontFamily: "'JetBrains Mono', monospace" }}>
            click to expand steps
          </div>
        </div>

        {/* Header */}
        <div style={{ display: "flex", gap: 12, paddingBottom: 8,
          borderBottom: "1px solid rgba(255,255,255,0.06)",
          fontSize: 9, fontFamily: "'JetBrains Mono', monospace",
          color: "#1e3a5f", letterSpacing: "0.08em" }}>
          <span style={{ minWidth: 70 }}>ID</span>
          <span style={{ minWidth: 80 }}>INTENT</span>
          <span style={{ flex: 1 }}>AGENT</span>
          <span>LATENCY</span>
        </div>

        {traces.length === 0 && (
          <div style={{ padding: "20px 0", color: "#1e3a5f", fontSize: 11,
            fontFamily: "'JetBrains Mono', monospace", textAlign: "center" }}>
            No traces yet — send a message to ASTRA
          </div>
        )}

        {[...traces].reverse().map(trace => (
          <TraceRow key={trace.request_id} trace={trace} />
        ))}
      </div>
    </div>
  );
}
