import { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import API from "../config";

const TYPE_COLORS = {
  person:  "#00d4ff",
  project: "#00ff88",
  place:   "#ffaa00",
  concept: "#bf7fff",
  tool:    "#ff6b6b",
  emotion: "#ff88cc",
  event:   "#88ddff",
  default: "#4488aa",
};

const TYPE_ICONS = {
  person:  "◈",
  project: "◆",
  place:   "▲",
  concept: "●",
  tool:    "⚙",
  emotion: "♥",
  event:   "◎",
  default: "·",
};

function getColor(node) {
  return TYPE_COLORS[node?.entity_type] || TYPE_COLORS.default;
}
function getIcon(node) {
  return TYPE_ICONS[node?.entity_type] || TYPE_ICONS.default;
}
function nodeRadius(d) {
  return Math.max(12, Math.min(28, 10 + (d.degree || 0) * 2.5));
}

export default function KnowledgeGraph() {
  const svgRef       = useRef(null);
  const containerRef = useRef(null);
  const [graphData,  setGraphData]  = useState({ nodes: [], links: [] });
  const [stats,      setStats]      = useState(null);
  const [selected,   setSelected]   = useState(null);
  const [relations,  setRelations]  = useState([]);
  const [loading,    setLoading]    = useState(true);
  const [filterType, setFilterType] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [addForm,    setAddForm]    = useState({ show: false, subject: "", relation: "", object: "" });

  const fetchGraph = useCallback(async () => {
    setLoading(true);
    try {
      const [statsRes, queryRes] = await Promise.all([
        fetch(`${API}/knowledge/stats`),
        fetch(`${API}/knowledge/query`),
      ]);
      const statsData = await statsRes.json();
      const triples   = await queryRes.json();
      setStats(statsData);

      const nodeMap = new Map();
      triples.forEach(t => {
        [t.subject, t.object].forEach(label => {
          const key = label.toLowerCase().replace(/ /g, "_");
          if (!nodeMap.has(key)) {
            nodeMap.set(key, { id: key, label, entity_type: "default", degree: 0 });
          }
        });
      });

      (statsData.top_nodes || []).forEach(n => {
        if (nodeMap.has(n.node)) nodeMap.get(n.node).degree = n.degree;
      });

      const links = triples.map((t, i) => ({
        id:       i,
        source:   t.subject.toLowerCase().replace(/ /g, "_"),
        target:   t.object.toLowerCase().replace(/ /g, "_"),
        relation: t.relation,
        weight:   t.weight || 1,
      }));

      links.forEach(l => {
        if (nodeMap.has(l.source)) nodeMap.get(l.source).degree++;
        if (nodeMap.has(l.target)) nodeMap.get(l.target).degree++;
      });

      setGraphData({ nodes: [...nodeMap.values()], links });
    } catch (e) {
      console.error("Graph fetch failed:", e);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchGraph(); }, [fetchGraph]);

  const fetchRelations = useCallback(async (label) => {
    try {
      const r = await fetch(`${API}/knowledge/entity/${encodeURIComponent(label)}?depth=2`);
      setRelations(await r.json());
    } catch { setRelations([]); }
  }, []);

  useEffect(() => {
    if (!graphData.nodes.length || !svgRef.current || !containerRef.current) return;

    const W = containerRef.current.clientWidth;
    const H = containerRef.current.clientHeight;

    const visibleNodes = graphData.nodes.filter(n => {
      const typeOk   = filterType === "all" || n.entity_type === filterType;
      const searchOk = !searchTerm || n.label.toLowerCase().includes(searchTerm.toLowerCase());
      return typeOk && searchOk;
    });
    const visibleIds  = new Set(visibleNodes.map(n => n.id));
    const visibleLinks = graphData.links.filter(
      l => visibleIds.has(l.source?.id || l.source) && visibleIds.has(l.target?.id || l.target)
    );

    d3.select(svgRef.current).selectAll("*").remove();

    const svg = d3.select(svgRef.current).attr("width", W).attr("height", H);

    // Defs
    const defs = svg.append("defs");
    const glow = defs.append("filter").attr("id", "glow");
    glow.append("feGaussianBlur").attr("stdDeviation", "3").attr("result", "coloredBlur");
    const fm = glow.append("feMerge");
    fm.append("feMergeNode").attr("in", "coloredBlur");
    fm.append("feMergeNode").attr("in", "SourceGraphic");

    Object.entries(TYPE_COLORS).forEach(([type, color]) => {
      defs.append("marker")
        .attr("id", `arrow-${type}`)
        .attr("viewBox", "0 -4 8 8").attr("refX", 20).attr("refY", 0)
        .attr("markerWidth", 6).attr("markerHeight", 6).attr("orient", "auto")
        .append("path").attr("d", "M0,-4L8,0L0,4")
        .attr("fill", color).attr("opacity", 0.6);
    });

    // Grid
    const grid = svg.insert("g", ":first-child");
    d3.range(0, H, 40).forEach(y => {
      grid.append("line").attr("x1",0).attr("x2",W).attr("y1",y).attr("y2",y)
        .attr("stroke","rgba(0,212,255,0.03)");
    });
    d3.range(0, W, 40).forEach(x => {
      grid.append("line").attr("x1",x).attr("x2",x).attr("y1",0).attr("y2",H)
        .attr("stroke","rgba(0,212,255,0.03)");
    });

    const g = svg.append("g");

    svg.call(d3.zoom().scaleExtent([0.1, 4]).on("zoom", e => g.attr("transform", e.transform)));

    const sim = d3.forceSimulation(visibleNodes)
      .force("link",      d3.forceLink(visibleLinks).id(d => d.id).distance(d => 80 + (2 - d.weight) * 30))
      .force("charge",    d3.forceManyBody().strength(-220))
      .force("center",    d3.forceCenter(W / 2, H / 2))
      .force("collision", d3.forceCollide().radius(d => nodeRadius(d) + 10));

    const link = g.append("g").selectAll("line").data(visibleLinks).enter().append("line")
      .attr("stroke", d => {
        const s = visibleNodes.find(n => n.id === (d.source?.id || d.source));
        return getColor(s);
      })
      .attr("stroke-opacity", 0.3)
      .attr("stroke-width", d => Math.min(d.weight * 1.5, 3))
      .attr("marker-end", d => {
        const s = visibleNodes.find(n => n.id === (d.source?.id || d.source));
        return `url(#arrow-${s?.entity_type || "default"})`;
      });

    const edgeLabel = g.append("g").selectAll("text").data(visibleLinks).enter().append("text")
      .attr("font-size", 8).attr("font-family", "'Courier New', monospace")
      .attr("fill", "rgba(0,212,255,0.25)").attr("text-anchor", "middle").attr("letter-spacing", 1)
      .text(d => d.relation.replace(/_/g, " "));

    const node = g.append("g").selectAll("g").data(visibleNodes).enter().append("g")
      .style("cursor", "pointer")
      .call(d3.drag()
        .on("start", (e, d) => { if (!e.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on("drag",  (e, d) => { d.fx = e.x; d.fy = e.y; })
        .on("end",   (e, d) => { if (!e.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      )
      .on("click", (e, d) => {
        e.stopPropagation();
        setSelected(d);
        fetchRelations(d.label);

        const connected = new Set([d.id]);
        visibleLinks.forEach(l => {
          const src = l.source?.id || l.source;
          const tgt = l.target?.id || l.target;
          if (src === d.id) connected.add(tgt);
          if (tgt === d.id) connected.add(src);
        });

        node.select("circle").attr("opacity", n => connected.has(n.id) ? 1 : 0.12);
        node.select(".label").attr("opacity", n => connected.has(n.id) ? 1 : 0.08);
        link.attr("stroke-opacity", l => {
          const src = l.source?.id || l.source;
          const tgt = l.target?.id || l.target;
          return (src === d.id || tgt === d.id) ? 0.9 : 0.04;
        }).attr("stroke-width", l => {
          const src = l.source?.id || l.source;
          const tgt = l.target?.id || l.target;
          return (src === d.id || tgt === d.id) ? 2.5 : 0.5;
        });
      });

    svg.on("click", () => {
      setSelected(null); setRelations([]);
      node.select("circle").attr("opacity", 1);
      node.select(".label").attr("opacity", 1);
      link.attr("stroke-opacity", 0.3).attr("stroke-width", d => Math.min(d.weight * 1.5, 3));
    });

    node.append("circle")
      .attr("r", d => nodeRadius(d))
      .attr("fill", d => `${getColor(d)}18`)
      .attr("stroke", d => getColor(d))
      .attr("stroke-width", d => d.degree > 3 ? 2 : 1.5)
      .attr("filter", d => d.degree > 3 ? "url(#glow)" : null);

    node.append("text")
      .attr("text-anchor", "middle").attr("dominant-baseline", "central")
      .attr("font-size", d => nodeRadius(d) * 0.85)
      .attr("fill", d => getColor(d)).attr("filter", "url(#glow)")
      .attr("pointer-events", "none")
      .text(d => getIcon(d));

    node.append("text").attr("class", "label")
      .attr("text-anchor", "middle").attr("dy", d => nodeRadius(d) + 14)
      .attr("font-family", "'Courier New', monospace").attr("font-size", 9)
      .attr("letter-spacing", 1).attr("fill", d => getColor(d)).attr("opacity", 0.8)
      .attr("pointer-events", "none")
      .text(d => d.label.toUpperCase().slice(0, 14));

    sim.on("tick", () => {
      link
        .attr("x1", d => d.source.x).attr("y1", d => d.source.y)
        .attr("x2", d => d.target.x).attr("y2", d => d.target.y);
      edgeLabel
        .attr("x", d => (d.source.x + d.target.x) / 2)
        .attr("y", d => (d.source.y + d.target.y) / 2);
      node.attr("transform", d => `translate(${d.x},${d.y})`);
    });

    return () => sim.stop();
  }, [graphData, filterType, searchTerm, fetchRelations]);

  const submitAdd = async () => {
    const { subject, relation, object: obj } = addForm;
    if (!subject || !relation || !obj) return;
    try {
      await fetch(`${API}/knowledge/add`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, relation, object: obj }),
      });
      setAddForm({ show: false, subject: "", relation: "", object: "" });
      fetchGraph();
    } catch (e) { console.error(e); }
  };

  const entityTypes = ["all", ...Object.keys(TYPE_COLORS).filter(k => k !== "default")];

  return (
    <div style={{ display:"flex", height:"100%", background:"#00040a", fontFamily:"'Courier New',monospace", color:"#00d4ff", overflow:"hidden", position:"relative" }}>

      {/* LEFT PANEL */}
      <div style={{ width:220, minWidth:220, height:"100%", borderRight:"1px solid rgba(0,212,255,0.12)", background:"linear-gradient(180deg,rgba(0,8,18,0.98),rgba(0,4,12,0.99))", display:"flex", flexDirection:"column", overflow:"hidden", flexShrink:0 }}>

        <div style={{ padding:"16px 14px 12px", borderBottom:"1px solid rgba(0,212,255,0.1)" }}>
          <div style={{ fontSize:8, letterSpacing:4, color:"rgba(0,212,255,0.4)", marginBottom:4 }}>MEMORY TOPOLOGY</div>
          <div style={{ fontSize:13, letterSpacing:3, color:"#00d4ff", fontWeight:"bold", textShadow:"0 0 10px rgba(0,212,255,0.5)" }}>◈ KNOWLEDGE GRAPH</div>
        </div>

        {stats && (
          <div style={{ padding:"12px 14px", borderBottom:"1px solid rgba(0,212,255,0.08)" }}>
            <div style={{ fontSize:8, letterSpacing:3, color:"rgba(0,212,255,0.3)", marginBottom:8 }}>GRAPH METRICS</div>
            <div style={{ display:"flex", gap:8, marginBottom:10 }}>
              {[["NODES", stats.nodes], ["EDGES", stats.edges]].map(([label, val]) => (
                <div key={label} style={{ flex:1, background:"rgba(0,212,255,0.05)", border:"1px solid rgba(0,212,255,0.12)", padding:"8px 6px", textAlign:"center" }}>
                  <div style={{ fontSize:18, color:"#00d4ff", fontWeight:"bold", textShadow:"0 0 12px rgba(0,212,255,0.6)" }}>{val}</div>
                  <div style={{ fontSize:7, letterSpacing:2, color:"rgba(0,212,255,0.4)", marginTop:2 }}>{label}</div>
                </div>
              ))}
            </div>
            <div style={{ fontSize:8, letterSpacing:2, color:"rgba(0,212,255,0.3)", marginBottom:6 }}>TOP ENTITIES</div>
            {(stats.top_nodes || []).slice(0,5).map(n => (
              <div key={n.node} style={{ display:"flex", justifyContent:"space-between", marginBottom:4, padding:"3px 0", borderBottom:"1px solid rgba(0,212,255,0.05)" }}>
                <span style={{ fontSize:9, color:"rgba(0,212,255,0.6)", letterSpacing:1 }}>{n.node.replace(/_/g," ").toUpperCase().slice(0,14)}</span>
                <span style={{ fontSize:8, color:"#00ff88", background:"rgba(0,255,136,0.08)", padding:"1px 5px" }}>{n.degree}</span>
              </div>
            ))}
          </div>
        )}

        <div style={{ padding:"12px 14px", borderBottom:"1px solid rgba(0,212,255,0.08)" }}>
          <div style={{ fontSize:8, letterSpacing:3, color:"rgba(0,212,255,0.3)", marginBottom:8 }}>FILTER BY TYPE</div>
          <div style={{ display:"flex", flexDirection:"column", gap:3 }}>
            {entityTypes.map(type => (
              <button key={type} onClick={() => setFilterType(type)} style={{
                background: filterType===type ? `${TYPE_COLORS[type]||"#00d4ff"}18` : "transparent",
                border: `1px solid ${filterType===type ? (TYPE_COLORS[type]||"#00d4ff") : "rgba(0,212,255,0.1)"}`,
                color: filterType===type ? (TYPE_COLORS[type]||"#00d4ff") : "rgba(0,212,255,0.3)",
                fontFamily:"'Courier New',monospace", fontSize:9, padding:"5px 8px", cursor:"pointer",
                letterSpacing:2, textAlign:"left", display:"flex", alignItems:"center", gap:6, transition:"all 0.2s",
              }}>
                <span>{TYPE_ICONS[type]||"◈"}</span>
                <span>{type.toUpperCase()}</span>
                {filterType===type && <span style={{ marginLeft:"auto", fontSize:7, color:"#00ff88" }}>ACTIVE</span>}
              </button>
            ))}
          </div>
        </div>

        <div style={{ padding:"12px 14px", borderBottom:"1px solid rgba(0,212,255,0.08)" }}>
          <div style={{ fontSize:8, letterSpacing:3, color:"rgba(0,212,255,0.3)", marginBottom:6 }}>SEARCH NODE</div>
          <input value={searchTerm} onChange={e => setSearchTerm(e.target.value)} placeholder="FILTER..."
            style={{ width:"100%", background:"rgba(0,212,255,0.04)", border:"1px solid rgba(0,212,255,0.2)", color:"#00d4ff", fontFamily:"'Courier New',monospace", fontSize:10, padding:"6px 8px", outline:"none", letterSpacing:1, boxSizing:"border-box" }} />
        </div>

        <div style={{ padding:"10px 14px", marginTop:"auto" }}>
          <button onClick={fetchGraph} style={{ width:"100%", background:"rgba(0,212,255,0.06)", border:"1px solid rgba(0,212,255,0.2)", color:"rgba(0,212,255,0.7)", fontFamily:"'Courier New',monospace", fontSize:9, padding:"7px", cursor:"pointer", letterSpacing:2, transition:"all 0.2s" }}>
            ↻ REFRESH GRAPH
          </button>
        </div>
      </div>

      {/* MAIN CANVAS */}
      <div ref={containerRef} style={{ flex:1, position:"relative", overflow:"hidden" }}>

        {loading && (
          <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", background:"rgba(0,4,12,0.9)", zIndex:10, flexDirection:"column", gap:16 }}>
            <div style={{ fontSize:32, color:"#00d4ff", animation:"spin 2s linear infinite" }}>◈</div>
            <div style={{ fontSize:10, letterSpacing:4, color:"rgba(0,212,255,0.5)" }}>LOADING KNOWLEDGE GRAPH...</div>
          </div>
        )}

        {!loading && graphData.nodes.length === 0 && (
          <div style={{ position:"absolute", inset:0, display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column", gap:12 }}>
            <div style={{ fontSize:48, color:"rgba(0,212,255,0.2)" }}>◈</div>
            <div style={{ fontSize:12, letterSpacing:4, color:"rgba(0,212,255,0.4)" }}>KNOWLEDGE GRAPH EMPTY</div>
            <div style={{ fontSize:9, letterSpacing:2, color:"rgba(0,212,255,0.25)" }}>TALK TO ASTRA TO POPULATE THE GRAPH</div>
            <button onClick={() => setAddForm({...addForm, show:true})} style={{ marginTop:8, background:"rgba(0,212,255,0.08)", border:"1px solid rgba(0,212,255,0.3)", color:"#00d4ff", fontFamily:"'Courier New',monospace", fontSize:10, padding:"8px 20px", cursor:"pointer", letterSpacing:2 }}>
              + ADD FIRST ENTITY
            </button>
          </div>
        )}

        <svg ref={svgRef} style={{ width:"100%", height:"100%" }} />

        <div style={{ position:"absolute", top:16, left:16, right:16, display:"flex", justifyContent:"space-between", pointerEvents:"none" }}>
          <div style={{ fontSize:8, letterSpacing:3, color:"rgba(0,212,255,0.3)", background:"rgba(0,4,12,0.8)", padding:"4px 10px", border:"1px solid rgba(0,212,255,0.08)" }}>
            {graphData.nodes.length} ENTITIES · {graphData.links.length} RELATIONS
          </div>
          <div style={{ fontSize:8, letterSpacing:2, color:"rgba(0,212,255,0.25)", background:"rgba(0,4,12,0.8)", padding:"4px 10px", border:"1px solid rgba(0,212,255,0.08)" }}>
            DRAG · SCROLL TO ZOOM · CLICK TO EXPLORE
          </div>
        </div>

        <button onClick={() => setAddForm({...addForm, show:true})} style={{ position:"absolute", bottom:20, right:20, background:"rgba(0,212,255,0.08)", border:"1px solid rgba(0,212,255,0.35)", color:"#00d4ff", fontFamily:"'Courier New',monospace", fontSize:10, padding:"8px 16px", cursor:"pointer", letterSpacing:2, boxShadow:"0 0 20px rgba(0,212,255,0.1)" }}>
          + ADD KNOWLEDGE
        </button>

        {/* Legend */}
        <div style={{ position:"absolute", bottom:20, left:20, background:"rgba(0,4,12,0.85)", border:"1px solid rgba(0,212,255,0.1)", padding:"10px 14px" }}>
          <div style={{ fontSize:7, letterSpacing:3, color:"rgba(0,212,255,0.3)", marginBottom:8 }}>NODE TYPES</div>
          {Object.entries(TYPE_COLORS).filter(([k]) => k!=="default").map(([type, color]) => (
            <div key={type} style={{ display:"flex", alignItems:"center", gap:6, marginBottom:4 }}>
              <div style={{ width:6, height:6, borderRadius:"50%", background:color, boxShadow:`0 0 6px ${color}` }} />
              <span style={{ fontSize:8, color:"rgba(0,212,255,0.4)", letterSpacing:1 }}>{type.toUpperCase()}</span>
            </div>
          ))}
        </div>
      </div>

      {/* RIGHT PANEL — selected node */}
      {selected && (
        <div style={{ width:240, minWidth:240, height:"100%", borderLeft:"1px solid rgba(0,212,255,0.12)", background:"linear-gradient(180deg,rgba(0,8,18,0.98),rgba(0,4,12,0.99))", display:"flex", flexDirection:"column", overflow:"hidden", flexShrink:0 }}>
          <div style={{ padding:"16px 14px 12px", borderBottom:"1px solid rgba(0,212,255,0.1)", background:`${getColor(selected)}08` }}>
            <div style={{ fontSize:7, letterSpacing:3, color:"rgba(0,212,255,0.35)", marginBottom:6 }}>ENTITY DETAIL</div>
            <div style={{ fontSize:22, color:getColor(selected), filter:`drop-shadow(0 0 8px ${getColor(selected)})`, marginBottom:4 }}>{getIcon(selected)}</div>
            <div style={{ fontSize:12, letterSpacing:2, color:getColor(selected), fontWeight:"bold", wordBreak:"break-word", textShadow:`0 0 10px ${getColor(selected)}80` }}>{selected.label.toUpperCase()}</div>
            <div style={{ marginTop:4, fontSize:8, color:"rgba(0,212,255,0.3)", letterSpacing:2 }}>TYPE: {(selected.entity_type||"unknown").toUpperCase()}</div>
            <div style={{ fontSize:8, color:"rgba(0,212,255,0.3)", letterSpacing:2 }}>CONNECTIONS: {selected.degree}</div>
          </div>

          <div style={{ flex:1, overflowY:"auto", padding:"12px 14px" }}>
            <div style={{ fontSize:8, letterSpacing:3, color:"rgba(0,212,255,0.3)", marginBottom:10 }}>RELATIONS ({relations.length})</div>
            {relations.length === 0 && <div style={{ fontSize:9, color:"rgba(0,212,255,0.2)", textAlign:"center", marginTop:20 }}>NO RELATIONS FOUND</div>}
            {relations.map((r, i) => (
              <div key={i} style={{ marginBottom:8, padding:"8px", background:"rgba(0,212,255,0.03)", border:"1px solid rgba(0,212,255,0.08)" }}>
                <div style={{ display:"flex", alignItems:"center", gap:4, flexWrap:"wrap" }}>
                  <span style={{ fontSize:8, color:"#00d4ff", letterSpacing:1 }}>{r.subject.toUpperCase().slice(0,12)}</span>
                  <span style={{ fontSize:7, color:"rgba(0,212,255,0.3)", padding:"1px 4px", border:"1px solid rgba(0,212,255,0.15)", letterSpacing:1 }}>{r.relation.replace(/_/g," ")}</span>
                  <span style={{ fontSize:8, color:"#00ff88", letterSpacing:1 }}>{r.object.toUpperCase().slice(0,12)}</span>
                </div>
                <div style={{ marginTop:4, display:"flex", gap:1, alignItems:"center" }}>
                  {Array.from({length:10},(_,j) => (
                    <div key={j} style={{ width:3, height:3, background: j < Math.round((r.weight||1)*5) ? "#00d4ff" : "rgba(0,212,255,0.1)" }} />
                  ))}
                  <span style={{ fontSize:7, marginLeft:4, color:"rgba(0,212,255,0.35)" }}>{(r.weight||1).toFixed(1)}</span>
                </div>
              </div>
            ))}
          </div>

          <button onClick={() => { setSelected(null); setRelations([]); }} style={{ margin:"10px 14px", background:"transparent", border:"1px solid rgba(255,68,68,0.2)", color:"rgba(255,68,68,0.4)", fontFamily:"'Courier New',monospace", fontSize:9, padding:"6px", cursor:"pointer", letterSpacing:2 }}>
            ✕ CLOSE
          </button>
        </div>
      )}

      {/* ADD KNOWLEDGE MODAL */}
      {addForm.show && (
        <div style={{ position:"absolute", inset:0, background:"rgba(0,4,12,0.88)", display:"flex", alignItems:"center", justifyContent:"center", zIndex:100 }} onClick={() => setAddForm({...addForm, show:false})}>
          <div style={{ background:"linear-gradient(135deg,rgba(0,10,22,0.98),rgba(0,5,15,0.99))", border:"1px solid rgba(0,212,255,0.3)", padding:28, width:380, boxShadow:"0 0 60px rgba(0,212,255,0.1)" }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize:10, letterSpacing:4, color:"#00d4ff", marginBottom:20 }}>+ ADD KNOWLEDGE TRIPLE</div>
            {[["SUBJECT", "subject"], ["RELATION", "relation"], ["OBJECT", "object"]].map(([label, key]) => (
              <div key={key} style={{ marginBottom:14 }}>
                <div style={{ fontSize:8, letterSpacing:3, color:"rgba(0,212,255,0.4)", marginBottom:6 }}>{label}</div>
                <input value={addForm[key]} onChange={e => setAddForm({...addForm, [key]:e.target.value})}
                  placeholder={label==="RELATION" ? "e.g. works_on" : `Enter ${label.toLowerCase()}`}
                  style={{ width:"100%", background:"rgba(0,212,255,0.04)", border:"1px solid rgba(0,212,255,0.25)", color:"#00d4ff", fontFamily:"'Courier New',monospace", fontSize:11, padding:"8px 10px", outline:"none", letterSpacing:1, boxSizing:"border-box" }} />
              </div>
            ))}
            <div style={{ display:"flex", gap:10, marginTop:20 }}>
              <button onClick={submitAdd} style={{ flex:1, background:"rgba(0,212,255,0.1)", border:"1px solid rgba(0,212,255,0.4)", color:"#00d4ff", fontFamily:"'Courier New',monospace", fontSize:10, padding:"10px", cursor:"pointer", letterSpacing:2 }}>
                ◆ STORE
              </button>
              <button onClick={() => setAddForm({...addForm, show:false})} style={{ flex:1, background:"transparent", border:"1px solid rgba(255,68,68,0.2)", color:"rgba(255,68,68,0.4)", fontFamily:"'Courier New',monospace", fontSize:10, padding:"10px", cursor:"pointer", letterSpacing:2 }}>
                ✕ CANCEL
              </button>
            </div>
          </div>
        </div>
      )}

      <style>{`
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
      `}</style>
    </div>
  );
}
