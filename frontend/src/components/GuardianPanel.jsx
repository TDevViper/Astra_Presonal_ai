import { useEffect, useState } from "react";

const S = {
  panel: {
    background: "linear-gradient(135deg, #0a0f1a 0%, #120a0a 100%)",
    border: "1px solid #ff446633",
    borderRadius: "8px",
    padding: "14px 16px",
    fontFamily: "'JetBrains Mono', 'Fira Mono', monospace",
    color: "#ff4466",
    marginBottom: "12px",
    position: "relative",
    overflow: "hidden",
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: "10px",
    fontSize: "11px",
    letterSpacing: "0.15em",
    textTransform: "uppercase",
  },
  dot: (level) => {
    const colors = { ok: "#00ffe7", warn: "#ffb300", alert: "#ff4466" };
    const c = colors[level] || "#00ffe7";
    return {
      width: 7, height: 7, borderRadius: "50%",
      background: c, boxShadow: `0 0 8px ${c}`,
      display: "inline-block", marginRight: 8,
      animation: level === "alert" ? "pulse 1s infinite" : "none",
    };
  },
  scanline: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(255,68,102,0.012) 2px, rgba(255,68,102,0.012) 4px)",
    pointerEvents: "none", borderRadius: "8px",
  },
  row: {
    display: "flex", justifyContent: "space-between", alignItems: "center",
    padding: "5px 8px",
    borderRadius: "4px",
    marginBottom: "4px",
    fontSize: "10px",
    background: "#0d0810",
    border: "1px solid #ff446618",
  },
  badge: (level) => {
    const map = {
      OK:    { bg: "#002a1a", color: "#00ffe7", border: "#00ffe733" },
      WARN:  { bg: "#2a1a00", color: "#ffb300", border: "#ffb30033" },
      ALERT: { bg: "#2a000a", color: "#ff4466", border: "#ff446633" },
      BLOCK: { bg: "#1a001a", color: "#cc44ff", border: "#cc44ff33" },
    };
    const s = map[level] || map.OK;
    return {
      background: s.bg, color: s.color,
      border: `1px solid ${s.border}`,
      borderRadius: "3px", padding: "1px 6px",
      fontSize: "9px", letterSpacing: "0.08em",
    };
  },
  log: {
    marginTop: "8px",
    maxHeight: "80px",
    overflowY: "auto",
    borderTop: "1px solid #ff446622",
    paddingTop: "6px",
  },
  logEntry: (level) => ({
    fontSize: "9px",
    color: level === "ALERT" ? "#ff4466" : level === "WARN" ? "#ffb300" : "#ff446677",
    borderLeft: `2px solid ${level === "ALERT" ? "#ff4466" : level === "WARN" ? "#ffb300" : "#ff446633"}`,
    paddingLeft: "6px",
    marginBottom: "3px",
    lineHeight: 1.5,
  }),
};

const DEMO_CHECKS = [
  { name: "API Auth",        status: "OK"    },
  { name: "Rate Limiter",    status: "OK"    },
  { name: "Prompt Firewall", status: "OK"    },
  { name: "Output Filter",   status: "WARN"  },
  { name: "Plugin Sandbox",  status: "OK"    },
  { name: "Memory ACL",      status: "OK"    },
];

const DEMO_LOG = [
  { ts: "14:32:11", msg: "Prompt injection attempt blocked", level: "ALERT" },
  { ts: "14:31:58", msg: "Output filter triggered: PII detected", level: "WARN" },
  { ts: "14:30:44", msg: "API auth validated — token ok", level: "OK" },
  { ts: "14:28:02", msg: "Rate limit: 3 req/s sustained", level: "WARN" },
  { ts: "14:25:19", msg: "Plugin sandbox initialised", level: "OK" },
];

export default function GuardianPanel() {
  const [checks] = useState(DEMO_CHECKS);
  const [log] = useState(DEMO_LOG);
  const [, setTick] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 6000);
    return () => clearInterval(id);
  }, []);

  const overallLevel =
    checks.some(c => c.status === "ALERT") ? "alert" :
    checks.some(c => c.status === "WARN")  ? "warn"  : "ok";

  const overallLabel =
    overallLevel === "alert" ? "THREAT DETECTED" :
    overallLevel === "warn"  ? "ANOMALY FLAGGED" : "ALL SYSTEMS SECURE";

  return (
    <div style={S.panel}>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
      <div style={S.scanline} />

      <div style={S.header}>
        <span>
          <span style={S.dot(overallLevel)} />
          Guardian
        </span>
        <span style={{
          fontSize: "9px",
          color: overallLevel === "ok" ? "#00ffe7" : overallLevel === "warn" ? "#ffb300" : "#ff4466",
        }}>
          {overallLabel}
        </span>
      </div>

      {checks.map((c, i) => (
        <div key={i} style={S.row}>
          <span style={{ color: "#ff446699" }}>{c.name}</span>
          <span style={S.badge(c.status)}>{c.status}</span>
        </div>
      ))}

      <div style={S.log}>
        {log.map((e, i) => (
          <div key={i} style={S.logEntry(e.level)}>
            <span style={{ opacity: 0.5 }}>{e.ts} </span>{e.msg}
          </div>
        ))}
      </div>
    </div>
  );
}
