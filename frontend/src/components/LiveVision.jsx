// LiveVision.jsx — WebRTC + Voice + Vision combined
import { useState, useEffect, useRef, useCallback } from "react";

const API = "http://127.0.0.1:5050";

const C = {
  bg: "#080808", surface: "#0f0f0f", surface2: "#141414",
  border: "#1a1a1a", border2: "#222222",
  green: "#00ff88", blue: "#0088ff", yellow: "#ffaa00",
  red: "#ff4444", purple: "#aa44ff", cyan: "#00ddff",
  dim: "#333333", text: "#e0e0e0", muted: "#555555", faint: "#2a2a2a"
};

export default function LiveVision({ onAnalysis }) {
  const videoRef    = useRef(null);
  const canvasRef   = useRef(null);
  const streamRef   = useRef(null);
  const intervalRef = useRef(null);

  const [camActive, setCamActive]     = useState(false);
  const [talkState, setTalkState]     = useState("idle"); // idle|listening|thinking|speaking
  const [analyzing, setAnalyzing]     = useState(false);
  const [liveMode, setLiveMode]       = useState(false);
  const [analysis, setAnalysis]       = useState(null);
  const [history, setHistory]         = useState([]);
  const [question, setQuestion]       = useState("");
  const [error, setError]             = useState(null);
  const [lastReply, setLastReply]     = useState("");

  // ── Camera ────────────────────────────────────────────────
  const startCamera = async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 1280, height: 720 }, audio: false
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setCamActive(true);
    } catch (e) {
      setError("Camera access denied — allow camera in browser settings.");
    }
  };

  const stopCamera = () => {
    streamRef.current?.getTracks().forEach(t => t.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    setCamActive(false);
    setLiveMode(false);
    clearInterval(intervalRef.current);
  };

  useEffect(() => () => { stopCamera(); clearInterval(intervalRef.current); }, []);

  // ── Capture frame ─────────────────────────────────────────
  const captureFrame = useCallback(() => {
    const video = videoRef.current, canvas = canvasRef.current;
    if (!video || !canvas) return null;
    canvas.width = video.videoWidth || 640;
    canvas.height = video.videoHeight || 480;
    canvas.getContext("2d").drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg", 0.65).split(",")[1];
  }, []);

  // ── MAIN: Talk to ASTRA ───────────────────────────────────
  // This is the killer feature: voice + vision together
  const talkToAstra = async () => {
    if (talkState !== "idle") return;
    if (!camActive) { await startCamera(); return; }

    try {
      const frame = captureFrame();
      setTalkState("listening");

      const res = await fetch(`${API}/realtime/talk`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ duration: 5, image: frame })
      });

      const data = await res.json();

      if (data.silent || !data.text) {
        setTalkState("idle");
        return;
      }

      setTalkState("speaking");
      setLastReply(data.reply || "");
      setAnalysis({
        jarvis_response: data.reply,
        objects_detected: [],
        suggestions: [],
        visual_context: data.reply
      });

      const entry = {
        id:        Date.now(),
        question:  data.text,
        jarvis:    data.reply,
        objects:   [],
        timestamp: new Date().toLocaleTimeString(),
        source:    data.vision ? "vision+talk" : "talk"
      };
      setHistory(prev => [entry, ...prev].slice(0, 15));
      if (onAnalysis) onAnalysis(entry);

      const speakMs = Math.min((data.reply?.length || 0) * 55, 9000);
      setTimeout(() => setTalkState("idle"), speakMs);

    } catch (e) {
      console.error("Realtime talk error:", e);
      setTalkState("idle");
    }
  };

  // ── Silent analyze (no voice) ─────────────────────────────
  const analyzeFrame = useCallback(async (ctx = "") => {
    if (analyzing) return;
    const b64 = captureFrame();
    if (!b64) return;
    setAnalyzing(true);
    try {
      const res = await fetch(`${API}/vision/analyze_b64`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: b64, mode: "camera", context: ctx })
      });
      const data = await res.json();
      setAnalysis(data);
      const entry = {
        id: Date.now(), question: ctx || null,
        jarvis: data.jarvis_response || data.summary,
        objects: data.objects_detected || [],
        suggestions: data.suggestions || [],
        timestamp: new Date().toLocaleTimeString(), source: "camera"
      };
      setHistory(prev => [entry, ...prev].slice(0, 15));
      if (onAnalysis) onAnalysis(entry);
    } catch (e) { console.error(e); }
    finally { setAnalyzing(false); }
  }, [analyzing, captureFrame, onAnalysis]);

  // ── Screen ────────────────────────────────────────────────
  const analyzeScreen = async () => {
    setAnalyzing(true);
    try {
      const res = await fetch(`${API}/vision/screen`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ context: question })
      });
      const data = await res.json();
      setAnalysis(data);
      setHistory(prev => [{
        id: Date.now(), question: question || null,
        jarvis: data.jarvis_response || data.summary,
        objects: [], suggestions: data.suggestions || [],
        timestamp: new Date().toLocaleTimeString(), source: "screen"
      }, ...prev].slice(0, 15));
    } catch (e) { console.error(e); }
    finally { setAnalyzing(false); }
  };

  // ── Live mode ─────────────────────────────────────────────
  const toggleLive = () => {
    if (liveMode) {
      clearInterval(intervalRef.current);
      setLiveMode(false);
    } else {
      if (!camActive) startCamera();
      setLiveMode(true);
      intervalRef.current = setInterval(() => analyzeFrame(), 8000);
    }
  };

  // ── Type + send ───────────────────────────────────────────
  const sendTyped = () => {
    if (!question.trim()) return;
    const q = question.trim();
    setQuestion("");
    if (camActive) {
      const frame = captureFrame();
      fetch(`${API}/talk`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: frame, text: q, speak: true })
      }).then(r => r.json()).then(data => {
        setLastReply(data.reply);
        setAnalysis({ jarvis_response: data.reply, objects_detected: [], suggestions: [] });
        setHistory(prev => [{
          id: Date.now(), question: q, jarvis: data.reply,
          objects: [], timestamp: new Date().toLocaleTimeString(), source: "talk"
        }, ...prev].slice(0, 15));
      });
    } else analyzeScreen();
  };

  // ── Talk button color/label ───────────────────────────────
  const talkColor = talkState === "listening" ? C.red
                  : talkState === "thinking"  ? C.yellow
                  : talkState === "speaking"  ? C.purple
                  : C.green;

  const talkLabel = talkState === "listening" ? "● LISTENING..."
                  : talkState === "thinking"  ? "◈ THINKING..."
                  : talkState === "speaking"  ? "◈ SPEAKING..."
                  : "🎤 TALK TO ASTRA";

  return (
    <div style={{ display: "flex", height: "100%", background: C.bg, fontFamily: "monospace" }}>

      {/* Left: Camera feed */}
      <div style={{ width: "55%", borderRight: `1px solid ${C.border}`, display: "flex", flexDirection: "column" }}>

        {/* Header */}
        <div style={{
          padding: "8px 12px", borderBottom: `1px solid ${C.border}`,
          display: "flex", alignItems: "center", gap: 8, background: C.surface
        }}>
          <span style={{ color: C.cyan, fontSize: 11, letterSpacing: 2 }}>◎ VISION</span>
          <StatusPill camActive={camActive} talkState={talkState} analyzing={analyzing} liveMode={liveMode} />
        </div>

        {/* Video */}
        <div style={{ flex: 1, position: "relative", background: "#030303", display: "flex", alignItems: "center", justifyContent: "center" }}>
          <video ref={videoRef} autoPlay playsInline muted
            style={{ width: "100%", height: "100%", objectFit: "cover", display: camActive ? "block" : "none" }} />
          <canvas ref={canvasRef} style={{ display: "none" }} />

          {!camActive && (
            <div style={{ textAlign: "center", color: C.dim }}>
              <div style={{ fontSize: 40, marginBottom: 10 }}>◎</div>
              <div style={{ fontSize: 11, letterSpacing: 2, marginBottom: 20 }}>NO FEED</div>
              <button onClick={startCamera} style={{
                background: `${C.green}15`, border: `1px solid ${C.green}`,
                borderRadius: 3, color: C.green, fontFamily: "monospace",
                fontSize: 11, padding: "8px 20px", cursor: "pointer", letterSpacing: 1
              }}>START CAMERA</button>
              {error && <div style={{ color: C.red, fontSize: 10, marginTop: 10, maxWidth: 200 }}>{error}</div>}
            </div>
          )}

          {/* Scan line when analyzing/talking */}
          {(analyzing || talkState !== "idle") && (
            <div style={{
              position: "absolute", inset: 0, pointerEvents: "none",
              background: `linear-gradient(transparent 48%, ${talkColor}08 50%, transparent 52%)`,
              backgroundSize: "100% 8px", animation: "scanline 1.5s linear infinite"
            }} />
          )}

          {/* Corner brackets */}
          {camActive && ["tl","tr","bl","br"].map(p => (
            <div key={p} style={{
              position: "absolute",
              top: p[0]==="t" ? 10 : "auto", bottom: p[0]==="b" ? 10 : "auto",
              left: p[1]==="l" ? 10 : "auto", right: p[1]==="r" ? 10 : "auto",
              width: 18, height: 18,
              borderTop:    p[0]==="t" ? `1px solid ${talkColor}66` : "none",
              borderBottom: p[0]==="b" ? `1px solid ${talkColor}66` : "none",
              borderLeft:   p[1]==="l" ? `1px solid ${talkColor}66` : "none",
              borderRight:  p[1]==="r" ? `1px solid ${talkColor}66` : "none",
              transition: "border-color 0.3s"
            }} />
          ))}

          {/* State badge */}
          {talkState !== "idle" && (
            <div style={{
              position: "absolute", top: 14, left: "50%", transform: "translateX(-50%)",
              fontSize: 10, color: talkColor, letterSpacing: 2,
              padding: "3px 12px", border: `1px solid ${talkColor}44`,
              background: `${talkColor}11`, borderRadius: 2,
              animation: "pulse 0.6s infinite"
            }}>{talkLabel}</div>
          )}
        </div>

        {/* ── MAIN TALK BUTTON ── */}
        <div style={{
          padding: "14px 12px", borderTop: `1px solid ${C.border}`,
          background: C.surface, display: "flex", flexDirection: "column", gap: 10
        }}>
          {/* Big talk button */}
          <button
            onClick={talkToAstra}
            disabled={talkState !== "idle"}
            style={{
              background: talkState !== "idle" ? `${talkColor}15` : `${C.green}10`,
              border: `1px solid ${talkState !== "idle" ? talkColor : C.green}`,
              borderRadius: 4, color: talkState !== "idle" ? talkColor : C.green,
              fontFamily: "monospace", fontSize: 13, fontWeight: "bold",
              padding: "12px", cursor: talkState !== "idle" ? "default" : "pointer",
              letterSpacing: 2, transition: "all 0.2s", width: "100%",
              animation: talkState === "listening" ? "pulse 0.8s infinite" : "none"
            }}>
            {talkLabel}
          </button>

          {/* Secondary controls */}
          <div style={{ display: "flex", gap: 6 }}>
            {camActive
              ? <Btn color={C.red} onClick={stopCamera}>⏹</Btn>
              : <Btn color={C.green} onClick={startCamera}>📷</Btn>
            }
            <Btn color={C.blue} onClick={() => analyzeFrame()} disabled={!camActive || analyzing}>👁 Look</Btn>
            <Btn color={C.cyan} onClick={analyzeScreen} disabled={analyzing}>🖥 Screen</Btn>
            <Btn color={liveMode ? C.red : C.purple} onClick={toggleLive}>
              {liveMode ? "⏹ Live" : "▶ Live"}
            </Btn>
          </div>
        </div>
      </div>

      {/* Right: Analysis */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", overflow: "hidden" }}>

        {/* Current reply */}
        <div style={{
          padding: "12px 14px", borderBottom: `1px solid ${C.border}`,
          background: C.surface2, flexShrink: 0, minHeight: 150
        }}>
          <div style={{ color: C.cyan, fontSize: 9, letterSpacing: 2, marginBottom: 10 }}>ASTRA SAYS</div>

          {analysis ? (
            <>
              <div style={{ color: C.green, fontSize: 12, lineHeight: 1.7, marginBottom: 10 }}>
                "{analysis.jarvis_response || analysis.summary}"
              </div>
              {analysis.objects_detected?.filter(Boolean).length > 0 && (
                <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 8 }}>
                  {analysis.objects_detected.filter(Boolean).map((o, i) => (
                    <span key={i} style={{ fontSize: 10, color: C.text, padding: "1px 6px", border: `1px solid ${C.border2}`, borderRadius: 2 }}>{o}</span>
                  ))}
                </div>
              )}
              {analysis.suggestions && (
                <div>
                  {(Array.isArray(analysis.suggestions) ? analysis.suggestions : [analysis.suggestions])
                    .filter(Boolean).slice(0, 2).map((s, i) => (
                    <div key={i} style={{ color: C.yellow, fontSize: 10, marginBottom: 3 }}>→ {s}</div>
                  ))}
                </div>
              )}
            </>
          ) : (
            <div style={{ color: C.dim, fontSize: 11 }}>
              Press 🎤 TALK TO ASTRA — speak + show camera<br/>
              <span style={{ fontSize: 10, color: C.dim, marginTop: 6, display: "block" }}>
                ASTRA will see what you're showing and respond out loud
              </span>
            </div>
          )}
        </div>

        {/* Type input */}
        <div style={{ padding: "8px 12px", borderBottom: `1px solid ${C.border}`, background: C.surface, flexShrink: 0 }}>
          <div style={{
            display: "flex", gap: 8, alignItems: "center",
            border: `1px solid ${C.border2}`, borderRadius: 3, padding: "5px 10px"
          }}>
            <span style={{ color: C.muted, fontSize: 11 }}>›</span>
            <input value={question} onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => e.key === "Enter" && sendTyped()}
              placeholder="or type a question while showing camera..."
              style={{
                flex: 1, background: "transparent", border: "none",
                outline: "none", color: C.text, fontFamily: "monospace",
                fontSize: 11, caretColor: C.green
              }}
            />
            <span onClick={sendTyped} style={{ color: C.cyan, cursor: "pointer", fontSize: 10 }}>↵</span>
          </div>
        </div>

        {/* History */}
        <div style={{ flex: 1, overflowY: "auto", padding: "8px 12px" }}>
          {history.length === 0 && (
            <div style={{ color: C.dim, fontSize: 10, textAlign: "center", marginTop: 24, letterSpacing: 1 }}>
              conversation history will appear here
            </div>
          )}
          {history.map(entry => (
            <div key={entry.id} style={{ marginBottom: 14, paddingBottom: 12, borderBottom: `1px solid ${C.faint}` }}>
              <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 4, fontSize: 9, color: C.muted }}>
                <span style={{ color: entry.source === "screen" ? C.blue : entry.source === "talk" ? C.green : C.purple }}>
                  {entry.source === "screen" ? "🖥 screen" : entry.source === "talk" ? "🎤 talk" : "📷 camera"}
                </span>
                <span>{entry.timestamp}</span>
              </div>
              {entry.question && (
                <div style={{ color: C.blue, fontSize: 10, marginBottom: 4 }}>
                  YOU: {entry.question}
                </div>
              )}
              <div style={{ color: C.text, fontSize: 11, lineHeight: 1.6 }}>
                ASTRA: {entry.jarvis}
              </div>
            </div>
          ))}
        </div>
      </div>

      <style>{`
        @keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.2} }
        @keyframes scanline { 0%{background-position:0 0} 100%{background-position:0 200px} }
        input::placeholder { color: ${C.dim}; }
      `}</style>
    </div>
  );
}

function StatusPill({ camActive, talkState, analyzing, liveMode }) {
  const color = talkState !== "idle" ? C.green
              : analyzing ? C.yellow
              : camActive ? C.green : C.dim;
  const label = talkState === "listening" ? "LISTENING"
              : talkState === "thinking"  ? "THINKING"
              : talkState === "speaking"  ? "SPEAKING"
              : analyzing ? "ANALYZING"
              : liveMode  ? "LIVE"
              : camActive ? "READY" : "IDLE";
  return (
    <span style={{
      fontSize: 9, padding: "2px 8px", border: `1px solid ${color}44`,
      color, borderRadius: 2, letterSpacing: 1,
      display: "flex", alignItems: "center", gap: 4
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color, display: "inline-block", animation: camActive ? "pulse 2s infinite" : "none" }} />
      {label}
    </span>
  );
}

function Btn({ children, onClick, color, disabled }) {
  return (
    <button onClick={onClick} disabled={disabled} style={{
      background: "transparent", border: `1px solid ${disabled ? "#333" : color}`,
      borderRadius: 3, color: disabled ? "#333" : color, fontFamily: "monospace",
      fontSize: 10, padding: "5px 10px", cursor: disabled ? "default" : "pointer",
      letterSpacing: 1, transition: "all 0.15s", whiteSpace: "nowrap"
    }}>{children}</button>
  );
}