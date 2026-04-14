import { useState, useEffect, useCallback } from "react";
import API from "./config";

const getAuthHeader = () => ({
  "Authorization": `Bearer ${localStorage.getItem("astra_token") || ""}`,
  "X-API-Key": localStorage.getItem("astra_api_key") || ""
});

export default function useSystemStatus() {
  const [health,       setHealth]       = useState({});
  const [memory,       setMemory]       = useState({});
  const [models,       setModels]       = useState([]);
  const [currentModel, setCurrentModel] = useState("phi3:mini");
  const [currentMode,  setCurrentMode]  = useState("jarvis");
  const [modes,        setModes]        = useState([]);

  useEffect(() => {
    const poll = async () => {
      try {
        const [h, m, mdl, modeData] = await Promise.all([
          fetch(API.health,   { headers: getAuthHeader() }).then(r => r.json()).catch(() => ({})),
          fetch(API.memory,   { headers: getAuthHeader() }).then(r => r.json()).catch(() => ({})),
          fetch(API.model,    { headers: getAuthHeader() }).then(r => r.json()).catch(() => ({})),
          fetch(API.modeList, { headers: getAuthHeader() }).then(r => r.json()).catch(() => ({})),
        ]);
        setHealth(h);
        setMemory(m);
        if (mdl.available)    setModels(mdl.available);
        if (mdl.current)      setCurrentModel(mdl.current);
        if (modeData.modes)   setModes(modeData.modes);
        if (modeData.current) setCurrentMode(modeData.current);
      } catch { /* ignore */ }
    };
    poll();
    const t = setInterval(() => { if (!document.hidden) poll(); }, 60000);
    return () => clearInterval(t);
  }, []);

  const switchModel = useCallback(async (model) => {
    try {
      await fetch(API.modelSet, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ model }),
      });
      setCurrentModel(model);
    } catch { /* ignore */ }
  }, []);

  const switchMode = useCallback(async (modeId) => {
    try {
      const r = await fetch(API.modeSet, {
        method: "POST",
        headers: { "Content-Type": "application/json", ...getAuthHeader() },
        body: JSON.stringify({ mode: modeId }),
      });
      const d = await r.json();
      setCurrentMode(d.current || modeId);
    } catch { /* ignore */ }
  }, []);

  return { health, memory, models, currentModel, currentMode, modes, switchModel, switchMode };
}
