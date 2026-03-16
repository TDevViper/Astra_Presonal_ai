import { useEffect, useState, useRef } from "react";
import API from "../config";

const S = {
  panel: {
    background: "linear-gradient(135deg, #0a0f1a 0%, #080d18 100%)",
    border: "1px solid #00b4ff33",
    borderRadius: "8px",
    padding: "14px 16px",
    fontFamily: "'JetBrains Mono', 'Fira Mono', monospace",
    color: "#00b4ff",
    marginBottom: "12px",
    position: "relative",
    overflow: "hidden",
  },
  scanline: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,180,255,0.015) 2px, rgba(0,180,255,0.015) 4px)",
    pointerEvents: "none", borderRadius: "8px",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    marginBottom: "10px", fontSize: "11px",
    letterSpacing: "0.15em", textTransform: "uppercase", color: "#00b4ff99",
  },
  dot: (on) => ({
    width: 7, height: 7, borderRadius: "50%",
    background: on ? "#00b4ff" : "#0a2a3a",
    boxShadow: on ? "0 0 8px #00b4ff" : "none",
    display: "inline-block", marginRight: 8,
  }),
  traceRow: {
    display: "flex", alignItems: "center",
    padding: "5px 0", borderBottom: "1px solid #00b4ff11",
    fontSize: "10px", gap: 8,
  },
  method: (m) => {
    const colors = { GET:"#00ffe7", POST:"#00b4ff", PUT:"#ffb300", DELETE:"#ff4466", WS:"#cc44ff" };
    return {
      color: colors[m] || "#00b4ff",
      minWidth: 44, fontWeight: 700, fontSize: "9px", letterSpacing: "0.06em",
    };
  },
  path: {
    flex: 1, color: "#00b4ff99", overflow: "hidden",
    textOverflow: "ellipsis", whiteSpace: "nowrap",
  },
  status: (code) => ({
    color: code < 300 ? "#00ffe7" : code < 400 ? "#ffb300" : "#ff4466",
    minWidth: 28, textAlign: "right", fontSize: "9px", fontWeight: 700,
  }),
  dur: {
    color: "#00b4ff55", minWidth: 42, textAlign: "right", fontSize: "9px",
  },
  bar: (ms, maxMs) => ({
    height: "2px",
    width: `${Math.min((ms / (maxMs || 500)) * 100, 100)}%`,
    background: ms < 100 ? "#00ffe7" : ms < 300 ? "#ffb300" : "#ff4466",
    borderRadius: "1px",
    boxShadow: ms < 100 ? "0 0 4px #00ffe7" : ms < 300 ? "0 0 4px #ffb300" : "0 0 4px #ff4466",
    transition: "width 0.4s",
  }),
  empty: { color: "#00b4ff33", fontSize: "10px", textAlign: "center", padding: "16px 0" },
};

// Simulated fallback traces
const SEED = [
  { id:1, method:"POST", path:"/chat/stream",    status:200, ms:182, ts:"14:32:11" },
  { id:2, method:"GET",  path:"/memory",          status:200, ms: 24, ts:"14:32:09" },
  { id:3, method:"GET",  path:"/system/stats",    status:200, ms: 11, ts:"14:32:07" },
  { id:4, method:"POST", path:"/vision/analyze_b64", status:200, ms:340, ts:"14:32:01" },
  { id:5, method:"WS",   path:"/ws",              status:101, ms:  3, ts:"14:31:55" },
];

let _nextId = 100;
const PATHS = ["/chat/stream","/memory","/system/stats","/knowledge/graph","/voice/listen","/model/list","/execute"];
const METHODS = ["GET","GET","POST","POST","GET","PUT"];

export default function RequestTracePanel() {
  const [traces, setTraces] = useState(SEED);
  const [live, setLive] = useState(true);
  const maxRef = useRef(500);

  // Simulate new requests rolling in
  useEffect(() => {
    const id = setInterval(() => {
      if (!live) return;
      const method = METHODS[Math.floor(Math.random() * METHODS.length)];
      const path   = PATHS[Math.floor(Math.random() * PATHS.length)];
      const ms     = Math.floor(Math.random() * 400 + 5);
      const status = Math.random() > 0.08 ? 200 : (Math.random() > 0.5 ? 400 : 500);
      const now    = new Date();
      const ts     = `${String(now.getHours()).padStart(2,"0")}:${String(now.getMinutes()).padStart(2,"0")}:${String(now.getSeconds()).padStart(2,"0")}`;
      const entry  = { id: _nextId++, method, path, status, ms, ts };
      maxRef.current = Math.max(maxRef.current, ms);
      setTraces(prev => [entry, ...prev].slice(0, 20));
    }, 2200);
    return () => clearInterval(id);
  }, [live]);

  const maxMs = Math.max(...traces.map(t => t.ms), 1);

  return (
    <div style={S.panel}>
      <div style={S.scanline} />
      <div style={S.header}>
        <span>
          <span style={S.dot(live)} />
          Request Trace
        </span>
        <button
          onClick={() => setLive(l => !l)}
          style={{
            background: "none", border: "1px solid #00b4ff33",
            color: live ? "#00b4ff" : "#00b4ff55",
            borderRadius: "3px", padding: "1px 8px",
            fontSize: "9px", cursor: "pointer",
            fontFamily: "inherit", letterSpacing: "0.08em",
          }}
        >
          {live ? "● LIVE" : "○ PAUSED"}
        </button>
      </div>

      <div style={{ maxHeight: 200, overflowY: "auto" }}>
        {traces.length === 0 && <div style={S.empty}>NO REQUESTS YET</div>}
        {traces.map(t => (
          <div key={t.id}>
            <div style={S.traceRow}>
              <span style={S.method(t.method)}>{t.method}</span>
              <span style={S.path}>{t.path}</span>
              <span style={S.status(t.status)}>{t.status}</span>
              <span style={S.dur}>{t.ms}ms</span>
              <span style={{ color: "#00b4ff33", fontSize: "9px", minWidth: 52 }}>{t.ts}</span>
            </div>
            <div style={{ padding: "2px 0 4px 52px" }}>
              <div style={S.bar(t.ms, maxMs)} />
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: 6, display: "flex", gap: 12, fontSize: "9px", color: "#00b4ff44" }}>
        <span>{traces.length} REQUESTS</span>
        <span>·</span>
        <span>P99 {Math.max(...traces.map(t=>t.ms))}ms</span>
        <span>·</span>
        <span>ERR {traces.filter(t=>t.status>=400).length}</span>
      </div>
    </div>
  );
}
