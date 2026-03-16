import { useEffect, useState, useRef } from "react";
import API from "../config";

const AMBIENT_STYLE = {
  panel: {
    background: "linear-gradient(135deg, #0a0f1a 0%, #0d1520 100%)",
    border: "1px solid #00ffe733",
    borderRadius: "8px",
    padding: "14px 16px",
    fontFamily: "'JetBrains Mono', 'Fira Mono', monospace",
    color: "#00ffe7",
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
    color: "#00ffe799",
  },
  dot: (active) => ({
    width: 7,
    height: 7,
    borderRadius: "50%",
    background: active ? "#00ffe7" : "#1a3a3a",
    boxShadow: active ? "0 0 8px #00ffe7" : "none",
    display: "inline-block",
    marginRight: 8,
    transition: "all 0.4s",
  }),
  grid: {
    display: "grid",
    gridTemplateColumns: "1fr 1fr",
    gap: "8px",
  },
  metric: {
    background: "#060d18",
    border: "1px solid #00ffe722",
    borderRadius: "5px",
    padding: "8px 10px",
  },
  label: {
    fontSize: "9px",
    letterSpacing: "0.12em",
    color: "#00ffe755",
    textTransform: "uppercase",
    marginBottom: "3px",
  },
  value: {
    fontSize: "18px",
    fontWeight: "700",
    color: "#00ffe7",
    lineHeight: 1,
  },
  sub: {
    fontSize: "9px",
    color: "#00ffe755",
    marginTop: "2px",
  },
  bar: (pct, color) => ({
    height: "3px",
    background: "#0d1a2a",
    borderRadius: "2px",
    marginTop: "5px",
    overflow: "hidden",
  }),
  barFill: (pct, color) => ({
    height: "100%",
    width: `${Math.min(pct, 100)}%`,
    background: color || "#00ffe7",
    borderRadius: "2px",
    transition: "width 0.6s ease",
    boxShadow: `0 0 6px ${color || "#00ffe7"}`,
  }),
  events: {
    marginTop: "10px",
    maxHeight: "72px",
    overflowY: "auto",
  },
  event: {
    fontSize: "10px",
    color: "#00ffe799",
    borderLeft: "2px solid #00ffe733",
    paddingLeft: "7px",
    marginBottom: "4px",
    lineHeight: 1.4,
  },
  scanline: {
    position: "absolute",
    top: 0, left: 0, right: 0, bottom: 0,
    background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0,255,231,0.015) 2px, rgba(0,255,231,0.015) 4px)",
    pointerEvents: "none",
    borderRadius: "8px",
  },
};

function Bar({ pct, color }) {
  return (
    <div style={AMBIENT_STYLE.bar(pct, color)}>
      <div style={AMBIENT_STYLE.barFill(pct, color)} />
    </div>
  );
}

export default function AmbientPanel() {
  const [data, setData] = useState(null);
  const [active, setActive] = useState(false);
  const [error, setError] = useState(null);
  const timerRef = useRef(null);

  async function fetchAmbient() {
    try {
      const r = await fetch(API.ambient || `${window.location.origin.replace(':3000',':8000')}/system/stats`);
      if (!r.ok) throw new Error(r.status);
      const j = await r.json();
      setData(j);
      setActive(true);
      setError(null);
    } catch (e) {
      setError("AMBIENT FEED OFFLINE");
      setActive(false);
    }
  }

  useEffect(() => {
    fetchAmbient();
    timerRef.current = setInterval(fetchAmbient, 5000);
    return () => clearInterval(timerRef.current);
  }, []);

  // Fallback demo data so panel is never blank
  const d = data || {
    cpu: {percent:42}, memory: {percent:67}, gpu: {percent:28}, disk: {percent:55},
    uptime: "04:22:11", threads: 18, load: 1.4,
    events: ["System nominal", "Inference engine ready", "Memory indexed"],
  };

  return (
    <div style={AMBIENT_STYLE.panel}>
      <div style={AMBIENT_STYLE.scanline} />
      <div style={AMBIENT_STYLE.header}>
        <span>
          <span style={AMBIENT_STYLE.dot(active)} />
          Ambient Monitor
        </span>
        <span style={{ color: error ? "#ff4466" : "#00ffe744", fontSize: "9px" }}>
          {error ? "● OFFLINE" : "● LIVE"}
        </span>
      </div>

      <div style={AMBIENT_STYLE.grid}>
        <div style={AMBIENT_STYLE.metric}>
          <div style={AMBIENT_STYLE.label}>CPU</div>
          <div style={AMBIENT_STYLE.value}>{d.cpu?.percent ?? "--"}<span style={{ fontSize: 11 }}>%</span></div>
          <Bar pct={d.cpu?.percent} color="#00ffe7" />
        </div>
        <div style={AMBIENT_STYLE.metric}>
          <div style={AMBIENT_STYLE.label}>RAM</div>
          <div style={AMBIENT_STYLE.value}>{d.memory?.percent ?? "--"}<span style={{ fontSize: 11 }}>%</span></div>
          <Bar pct={d.memory?.percent} color="#00b4ff" />
        </div>
        <div style={AMBIENT_STYLE.metric}>
          <div style={AMBIENT_STYLE.label}>GPU</div>
          <div style={AMBIENT_STYLE.value}>{d.gpu?.percent ?? "--"}<span style={{ fontSize: 11 }}>%</span></div>
          <Bar pct={d.gpu?.percent} color="#7affb2" />
        </div>
        <div style={AMBIENT_STYLE.metric}>
          <div style={AMBIENT_STYLE.label}>Disk</div>
          <div style={AMBIENT_STYLE.value}>{d.disk?.percent ?? "--"}<span style={{ fontSize: 11 }}>%</span></div>
          <Bar pct={d.disk?.percent} color="#ffb300" />
        </div>
      </div>

      <div style={{ marginTop: 8, display: "flex", gap: 8, fontSize: 10, color: "#00ffe766" }}>
        <span>UP {"--"}</span>
        <span>·</span>
        <span>{"--"} THR</span>
        <span>·</span>
        <span>LOAD {"--"}</span>
      </div>

      {d.events?.length > 0 && (
        <div style={AMBIENT_STYLE.events}>
          {[...d.events].reverse().map((ev, i) => (
            <div key={i} style={AMBIENT_STYLE.event}>{ev}</div>
          ))}
        </div>
      )}
    </div>
  );
}
