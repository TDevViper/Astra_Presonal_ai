import { useState, useEffect, useRef } from "react";
import { WS_URL } from "../config";

export default function ProactiveAlerts() {
  const [alerts, setAlerts] = useState([]);
  const wsRef = useRef(null);

  useEffect(() => {
    function connect() {
      const ws = new WebSocket(WS_URL);
      wsRef.current = ws;
      ws.onmessage = (e) => {
        try {
          const msg = JSON.parse(e.data);
          if (msg.type === "proactive" && msg.data) {
            const id = Date.now();
            setAlerts(prev => [...prev.slice(-4), { id, text: msg.data }]);
            setTimeout(() => {
              setAlerts(prev => prev.filter(a => a.id !== id));
            }, 6000);
          }
        } catch {}
      };
      ws.onclose = () => setTimeout(connect, 3000);
      ws.onerror = () => ws.close();
    }
    connect();
    return () => wsRef.current?.close();
  }, []);

  if (!alerts.length) return null;

  return (
    <div style={{ position:"fixed", bottom:"24px", right:"24px", zIndex:9999, display:"flex", flexDirection:"column", gap:"10px", maxWidth:"360px" }}>
      {alerts.map(alert => (
        <div key={alert.id}
          onClick={() => setAlerts(prev => prev.filter(a => a.id !== alert.id))}
          style={{ background:"rgba(0,0,0,0.85)", border:"1px solid rgba(0,255,200,0.3)", borderRadius:"12px", padding:"14px 18px", color:"#00ffc8", fontSize:"14px", fontFamily:"monospace", backdropFilter:"blur(10px)", boxShadow:"0 0 20px rgba(0,255,200,0.15)", animation:"slideIn 0.3s ease", cursor:"pointer" }}>
          {alert.text}
        </div>
      ))}
      <style>{`@keyframes slideIn { from{opacity:0;transform:translateX(40px)} to{opacity:1;transform:translateX(0)} }`}</style>
    </div>
  );
}
