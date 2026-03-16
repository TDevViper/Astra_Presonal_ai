import { useState, useRef } from "react";
import API from "../config";

const S = {
  panel: {
    background: "linear-gradient(135deg, #0a0f1a 0%, #0a0a14 100%)",
    border: "1px solid #cc44ff33",
    borderRadius: "8px",
    padding: "14px 16px",
    fontFamily: "'JetBrains Mono', 'Fira Mono', monospace",
    color: "#cc44ff",
    marginBottom: "12px",
    position: "relative",
    overflow: "hidden",
  },
  scanline: {
    position: "absolute", top: 0, left: 0, right: 0, bottom: 0,
    background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(204,68,255,0.012) 2px, rgba(204,68,255,0.012) 4px)",
    pointerEvents: "none", borderRadius: "8px",
  },
  header: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    marginBottom: "10px", fontSize: "11px",
    letterSpacing: "0.15em", textTransform: "uppercase", color: "#cc44ff99",
  },
  dot: { width: 7, height: 7, borderRadius: "50%", background: "#cc44ff", boxShadow: "0 0 8px #cc44ff", display: "inline-block", marginRight: 8 },
  input: {
    width: "100%", background: "#060810",
    border: "1px solid #cc44ff33", borderRadius: "4px",
    color: "#cc44ff", fontFamily: "inherit", fontSize: "10px",
    padding: "5px 8px", outline: "none",
    boxSizing: "border-box", marginBottom: "6px",
  },
  textarea: {
    width: "100%", background: "#060810",
    border: "1px solid #cc44ff33", borderRadius: "4px",
    color: "#cc44ff", fontFamily: "inherit", fontSize: "10px",
    padding: "6px 8px", outline: "none",
    boxSizing: "border-box", resize: "vertical",
    minHeight: 80, marginBottom: "6px",
  },
  btn: (loading) => ({
    background: loading ? "#1a0a2a" : "#160a22",
    border: "1px solid #cc44ff55",
    color: loading ? "#cc44ff55" : "#cc44ff",
    borderRadius: "4px", padding: "5px 14px",
    fontSize: "10px", cursor: loading ? "not-allowed" : "pointer",
    fontFamily: "inherit", letterSpacing: "0.1em",
    transition: "all 0.2s",
  }),
  pluginRow: {
    display: "flex", alignItems: "center", justifyContent: "space-between",
    padding: "5px 8px", borderRadius: "4px",
    background: "#09050f", border: "1px solid #cc44ff18",
    marginBottom: "4px", fontSize: "10px",
  },
  pluginName: { color: "#cc44ffcc", flex: 1 },
  pluginStatus: (ok) => ({
    fontSize: "9px",
    color: ok ? "#00ffe7" : "#ff4466",
    border: `1px solid ${ok ? "#00ffe733" : "#ff446633"}`,
    borderRadius: "3px", padding: "1px 6px",
  }),
  result: (ok) => ({
    marginTop: 8, padding: "6px 10px",
    borderRadius: "4px",
    background: ok ? "#001a0d" : "#1a0008",
    border: `1px solid ${ok ? "#00ffe733" : "#ff446633"}`,
    color: ok ? "#00ffe7" : "#ff4466",
    fontSize: "10px",
  }),
};

const DEMO_PLUGINS = [
  { name: "web_search.py",    active: true  },
  { name: "code_executor.py", active: true  },
  { name: "memory_writer.py", active: true  },
  { name: "vision_hook.py",   active: false },
];

export default function PluginManagerPanel() {
  const [plugins, setPlugins]   = useState(DEMO_PLUGINS);
  const [filename, setFilename] = useState("");
  const [code, setCode]         = useState("");
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [expanded, setExpanded] = useState(false);

  async function deploy() {
    if (!filename.trim() || !code.trim()) return;
    setLoading(true); setResult(null);
    try {
      const endpoint = (API && API.pluginDeploy)
        || `${window.location.origin.replace(':3000',':8000')}/api/plugin/deploy`;
      const r = await fetch(endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ filename: filename.trim(), code }),
      });
      const j = await r.json();
      if (j.ok) {
        setResult({ ok: true, msg: `Deployed: ${j.filename}` });
        setPlugins(prev => {
          const exists = prev.find(p => p.name === j.filename);
          if (exists) return prev.map(p => p.name === j.filename ? { ...p, active: true } : p);
          return [...prev, { name: j.filename, active: true }];
        });
        setFilename(""); setCode("");
      } else {
        setResult({ ok: false, msg: j.error || "Deploy failed" });
      }
    } catch (e) {
      setResult({ ok: false, msg: e.message });
    }
    setLoading(false);
  }

  return (
    <div style={S.panel}>
      <div style={S.scanline} />
      <div style={S.header}>
        <span><span style={S.dot} />Plugin Manager</span>
        <button
          onClick={() => setExpanded(e => !e)}
          style={{ background:"none", border:"1px solid #cc44ff33", color:"#cc44ff88",
            borderRadius:"3px", padding:"1px 8px", fontSize:"9px",
            cursor:"pointer", fontFamily:"inherit", letterSpacing:"0.08em" }}
        >
          {expanded ? "▲ HIDE" : "▼ DEPLOY"}
        </button>
      </div>

      {/* Plugin list */}
      {plugins.map((p, i) => (
        <div key={i} style={S.pluginRow}>
          <span style={S.pluginName}>{p.name}</span>
          <span style={S.pluginStatus(p.active)}>{p.active ? "ACTIVE" : "INACTIVE"}</span>
        </div>
      ))}

      {/* Deploy form */}
      {expanded && (
        <div style={{ marginTop: 10, borderTop: "1px solid #cc44ff22", paddingTop: 10 }}>
          <div style={{ fontSize: 9, color: "#cc44ff55", letterSpacing: "0.12em", marginBottom: 6, textTransform: "uppercase" }}>Deploy New Plugin</div>
          <input
            style={S.input}
            placeholder="filename.py"
            value={filename}
            onChange={e => setFilename(e.target.value)}
          />
          <textarea
            style={S.textarea}
            placeholder="# paste plugin code here..."
            value={code}
            onChange={e => setCode(e.target.value)}
          />
          <button style={S.btn(loading)} onClick={deploy} disabled={loading}>
            {loading ? "DEPLOYING..." : "⬆ DEPLOY"}
          </button>
        </div>
      )}

      {result && (
        <div style={S.result(result.ok)}>{result.ok ? "✓ " : "✗ "}{result.msg}</div>
      )}
    </div>
  );
}
