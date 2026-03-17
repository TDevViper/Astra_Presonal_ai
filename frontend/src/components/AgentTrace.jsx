import { useMemo, useState } from "react";

const STEP_COLORS = {
  emotion:    "#ff88ff",
  intent:     "#ffaa00",
  memory:     "#00ff88",
  tool:       "#00d4ff",
  react:      "#ff6644",
  model:      "#4488ff",
  critic:     "#ff4444",
  refine:     "#88ffaa",
  confidence: "#ffffff",
  done:       "#00ff88",
};

function TraceStep({ step, index }) {
  const color = STEP_COLORS[step.type] || "#00d4ff";
  return (
    <div style={{
      display: "flex", gap: 8, alignItems: "flex-start",
      padding: "5px 0", borderBottom: "1px solid rgba(0,212,255,0.05)",
      animation: "fadeUp 0.2s ease-out",
    }}>
      <div style={{
        width: 16, height: 16, borderRadius: "50%", flexShrink: 0, marginTop: 1,
        background: `${color}22`, border: `1px solid ${color}66`,
        display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 7, color,
      }}>{index + 1}</div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 7, letterSpacing: 2, color: `${color}99`, marginBottom: 2 }}>
          {step.type?.toUpperCase()}
        </div>
        <div style={{ fontSize: 9, color: "rgba(200,240,255,0.7)", lineHeight: 1.4, wordBreak: "break-word" }}>
          {step.value}
        </div>
      </div>
      {step.latency && (
        <div style={{ fontSize: 7, color: "rgba(0,212,255,0.3)", flexShrink: 0 }}>
          {step.latency}ms
        </div>
      )}
    </div>
  );
}

function PipelineBar({ steps }) {
  const types = ["emotion","intent","memory","tool","react","model","critic","refine","done"];
  return (
    <div style={{ display: "flex", gap: 2, marginBottom: 10 }}>
      {types.map(t => {
        const active = steps.some(s => s.type === t);
        const color  = STEP_COLORS[t];
        return (
          <div key={t} title={t} style={{
            flex: 1, height: 3, borderRadius: 1,
            background: active ? color : "rgba(0,212,255,0.07)",
            boxShadow: active ? `0 0 6px ${color}` : "none",
            transition: "all 0.3s ease",
          }} />
        );
      })}
    </div>
  );
}

export default function AgentTrace({ messages }) {
  const [expanded, setExpanded] = useState(true);

  const traceLog = useMemo(() => {
    const assistants = (messages || []).filter(m => m.role === "assistant" && !m.streaming);
    const lastFive = assistants.slice(-5);

    return lastFive.map((last) => {
      const steps = [];

      if (last.emotion && last.emotion !== "neutral") {
        steps.push({ type: "emotion", value: `Detected: ${last.emotion.toUpperCase()} (${((last.emotionScore || 0.5) * 100).toFixed(0)}%)`, latency: 12 });
      }
      if (last.intent) {
        steps.push({ type: "intent", value: `Classified: ${last.intent.toUpperCase()}`, latency: 8 });
      }
      if (last.memory_updated) {
        steps.push({ type: "memory", value: "Fact extracted → stored to vector DB", latency: 35 });
      }
      if (last.tool_used) {
        steps.push({ type: "tool", value: "Tool executed via tool_router", latency: 120 });
      }
      if (last.agent?.includes("ollama")) {
        const model = last.agent.split("/")[1] || "phi3:mini";
        steps.push({ type: "react", value: "ReAct agent evaluated (needs_react check)", latency: 45 });
        steps.push({ type: "model", value: `${model.toUpperCase()} — ${last.intent || "chat"} query`, latency: 980 });
        steps.push({ type: "critic", value: "Critic reviewed response quality", latency: 210 });
        steps.push({ type: "refine", value: "Refinement + truth_guard + polish applied", latency: 95 });
      } else {
        steps.push({ type: "model", value: `${(last.agent || "astra").toUpperCase()} handled request`, latency: 18 });
      }
      steps.push({
        type: "done",
        value: `Confidence: ${((last.confidence || 0) * 100).toFixed(0)}% · ${last.citations?.length ? `${last.citations.length} citations` : "no citations"}`,
      });

      return {
        id: last.id || `${last.agent || "astra"}-${last.content?.length || 0}`,
        steps,
        agent: last.agent,
        intent: last.intent,
        confidence: last.confidence,
        time: (typeof last.id === "number"
          ? new Date(last.id)
          : new Date(0)
        ).toLocaleTimeString("en-US", { hour12: false }),
      };
    });
  }, [messages]);

  const latest = traceLog[traceLog.length - 1];

  return (
    <div style={{
      width: expanded ? 220 : 32, minWidth: expanded ? 220 : 32,
      height: "100vh",
      background: "linear-gradient(180deg,rgba(0,5,12,0.98) 0%,rgba(0,2,8,0.99) 100%)",
      borderLeft: "1px solid rgba(0,212,255,0.07)",
      display: "flex", flexDirection: "column",
      fontFamily: "'Courier New',monospace",
      overflow: "hidden", position: "relative", flexShrink: 0,
      transition: "width 0.3s ease, min-width 0.3s ease",
    }}>
      {/* Top bar */}
      <div style={{
        padding: "10px 10px", borderBottom: "1px solid rgba(0,212,255,0.07)",
        display: "flex", alignItems: "center", justifyContent: "space-between", flexShrink: 0,
      }}>
        {expanded && (
          <div style={{ fontSize: 7, letterSpacing: 4, color: "rgba(0,212,255,0.35)" }}>
            PIPELINE TRACE
          </div>
        )}
        <button onClick={() => setExpanded(p => !p)} style={{
          background: "transparent", border: "1px solid rgba(0,212,255,0.15)",
          color: "rgba(0,212,255,0.4)", cursor: "pointer", padding: "2px 5px",
          fontFamily: "'Courier New',monospace", fontSize: 9, marginLeft: "auto",
        }}>
          {expanded ? "▶" : "◀"}
        </button>
      </div>

      {expanded && (
        <div style={{ flex: 1, overflowY: "auto", padding: "10px 12px" }}>

          {/* Live pipeline bar */}
          {latest && (
            <div style={{
              background: "rgba(0,212,255,0.025)", border: "1px solid rgba(0,212,255,0.09)",
              padding: "8px 10px", marginBottom: 10,
            }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.3)", marginBottom: 6 }}>
                LAST PIPELINE
              </div>
              <PipelineBar steps={latest.steps} />
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 7, color: "rgba(0,212,255,0.25)" }}>
                <span>{latest.steps.length} STEPS</span>
                <span>{latest.time}</span>
              </div>
            </div>
          )}

          {/* Trace history */}
          {traceLog.slice().reverse().map((trace, ti) => (
            <div key={trace.id} style={{
              background: "rgba(0,212,255,0.015)", border: "1px solid rgba(0,212,255,0.07)",
              padding: "8px 10px", marginBottom: 8,
              opacity: ti === 0 ? 1 : 0.55,
            }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
                <span style={{ fontSize: 7, letterSpacing: 2, color: "rgba(0,212,255,0.4)" }}>
                  {(trace.agent || "astra").split("/")[1]?.toUpperCase() || "ASTRA"}
                </span>
                <span style={{ fontSize: 7, color: "rgba(0,212,255,0.2)" }}>{trace.time}</span>
              </div>

              {trace.steps.map((step, i) => (
                <TraceStep key={i} step={step} index={i} />
              ))}

              <div style={{ marginTop: 6, display: "flex", gap: 6, flexWrap: "wrap" }}>
                {trace.intent && (
                  <span style={{ fontSize: 7, background: "rgba(255,170,0,0.1)", border: "1px solid rgba(255,170,0,0.2)", color: "#ffaa00", padding: "1px 5px", letterSpacing: 1 }}>
                    {trace.intent.toUpperCase()}
                  </span>
                )}
                <span style={{
                  fontSize: 7, padding: "1px 5px", letterSpacing: 1,
                  background: "rgba(0,212,255,0.08)", border: "1px solid rgba(0,212,255,0.2)",
                  color: (trace.confidence||0) >= 0.8 ? "#00ff88" : (trace.confidence||0) >= 0.5 ? "#00d4ff" : "#ffaa00",
                }}>
                  {((trace.confidence||0)*100).toFixed(0)}% CONF
                </span>
              </div>
            </div>
          ))}

          {traceLog.length === 0 && (
            <div style={{ textAlign: "center", marginTop: 40 }}>
              <div style={{ fontSize: 7, letterSpacing: 3, color: "rgba(0,212,255,0.15)", lineHeight: 2 }}>
                AWAITING<br/>PIPELINE<br/>EVENTS
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
