import React, { useState, useEffect } from "react";
import API from "../config";

function StatBar({ label, value = 0 }) {
  const color = value > 85 ? "bg-red-400" : value > 65 ? "bg-amber-400" : "bg-emerald-400";
  const textColor = value > 85 ? "text-red-400" : value > 65 ? "text-amber-400" : "text-emerald-400";
  return (
    <div className="mb-3">
      <div className="flex justify-between text-[10px] font-mono mb-1">
        <span className="text-slate-500">{label}</span>
        <span className={textColor}>{value.toFixed(0)}%</span>
      </div>
      <div className="h-[3px] bg-slate-800 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all duration-1000`}
          style={{ width: `${value}%` }} />
      </div>
    </div>
  );
}

export function SystemSidebar({ health, memory, models, currentModel, onSwitchModel }) {
  const [sysInfo, setSysInfo] = useState(null);
  const [time, setTime] = useState(new Date());

  useEffect(() => {
    const t = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(t);
  }, []);

  useEffect(() => {
    const fetch_ = async () => {
      try {
        const r = await fetch(API.stats);
        if (r.ok) setSysInfo(await r.json());
      } catch {}
    };
    fetch_();
    const t = setInterval(fetch_, 10000);
    return () => clearInterval(t);
  }, []);

  const cpu  = sysInfo?.cpu?.percent    ?? 0;
  const ram  = sysInfo?.memory?.percent ?? 0;
  const disk = sysInfo?.disk?.percent   ?? 0;

  const services = [
    { name: "BRAIN",  ok: health?.brain  ?? false },
    { name: "MEMORY", ok: health?.memory ?? false },
    { name: "VOICE",  ok: health?.voice  ?? false },
    { name: "OLLAMA", ok: health?.ollama ?? false },
  ];

  return (
    <div className="w-48 shrink-0 flex flex-col gap-0 overflow-y-auto
      border-r border-white/5 bg-slate-950/60 backdrop-blur-xl p-4">

      <div className="text-center mb-5 pb-4 border-b border-white/5">
        <div className="text-xl font-light font-mono tracking-widest text-slate-200">
          {time.toLocaleTimeString([], { hour:"2-digit", minute:"2-digit", second:"2-digit", hour12:false })}
        </div>
        <div className="text-[9px] font-mono tracking-widest text-slate-600 mt-1">
          {time.toLocaleDateString([], { weekday:"short", day:"numeric", month:"short" }).toUpperCase()}
        </div>
      </div>

      <div className="mb-4 pb-4 border-b border-white/5">
        <div className="text-[8px] font-mono tracking-widest text-slate-600 mb-3">SYSTEM</div>
        <StatBar label="CPU"  value={cpu}  />
        <StatBar label="RAM"  value={ram}  />
        <StatBar label="DISK" value={disk} />
      </div>

      <div className="mb-4 pb-4 border-b border-white/5">
        <div className="text-[8px] font-mono tracking-widest text-slate-600 mb-3">SERVICES</div>
        {services.map(({ name, ok }) => (
          <div key={name} className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-mono text-slate-600">{name}</span>
            <div className={`w-1.5 h-1.5 rounded-full transition-all duration-300
              ${ok ? "bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.6)]" : "bg-slate-600"}`} />
          </div>
        ))}
      </div>

      <div className="mb-4 pb-4 border-b border-white/5">
        <div className="text-[8px] font-mono tracking-widest text-slate-600 mb-3">MODELS</div>
        {(models || ["phi3:mini"]).map(m => {
          const active = m === currentModel;
          return (
            <div key={m} onClick={() => onSwitchModel?.(m)}
              className={`px-2 py-1.5 mb-1 rounded-md text-[9px] font-mono tracking-wider cursor-pointer
                transition-all duration-200
                ${active
                  ? "bg-sky-400/10 text-sky-400 border border-sky-400/20"
                  : "text-slate-600 hover:text-slate-400 border border-transparent"}`}>
              {m.toUpperCase()}
            </div>
          );
        })}
      </div>

      <div>
        <div className="text-[8px] font-mono tracking-widest text-slate-600 mb-3">MEMORY CORE</div>
        {[
          { label: "FACTS",  val: memory?.user_facts?.length ?? 0,                             color: "text-sky-400"     },
          { label: "TASKS",  val: memory?.tasks?.filter(t => t.status==="todo").length ?? 0,   color: "text-amber-400"   },
          { label: "CONVOS", val: memory?.conversation_count ?? 0,                             color: "text-emerald-400" },
        ].map(({ label, val, color }) => (
          <div key={label} className="flex justify-between items-center mb-2">
            <span className="text-[10px] font-mono text-slate-600">{label}</span>
            <span className={`text-[11px] font-mono font-medium ${color}`}>{val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
