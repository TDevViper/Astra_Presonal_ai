import React, { useState, useEffect } from "react";
import API from "../config";

function StatBar({ label, value = 0 }) {
  const color = value > 85 ? "bg-red-500 shadow-[0_0_8px_#ef4444]" : value > 65 ? "bg-amber-400 shadow-[0_0_8px_#fbbf24]" : "bg-emerald-400 shadow-[0_0_8px_#34d399]";
  const textColor = value > 85 ? "text-red-400" : value > 65 ? "text-amber-400" : "text-emerald-400";
  return (
    <div className="mb-3 group">
      <div className="flex justify-between text-[10px] font-mono mb-1.5">
        <span className="text-slate-500 drop-shadow-sm">{label}</span>
        <span className={`${textColor} drop-shadow`}>{value.toFixed(0)}%</span>
      </div>
      <div className="h-1.5 bg-black/80 rounded-full overflow-hidden border border-white/5 shadow-[inset_0_2px_4px_rgba(0,0,0,0.8)]">
        <div className={`h-full ${color} rounded-full transition-all duration-1000 relative`}
          style={{ width: `${value}%` }}>
          <div className="absolute top-0 left-0 right-0 h-0.5 bg-white/30" />
        </div>
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
        <div className="text-[8px] font-mono tracking-widest text-slate-600 mb-3 drop-shadow">SERVICES</div>
        {services.map(({ name, ok }) => (
          <div key={name} className="flex justify-between items-center mb-2 px-2.5 py-2 rounded-lg bg-gradient-to-b from-black/20 to-black/40 border-t border-t-white/5 border-b border-b-black shadow-[inset_0_1px_3px_rgba(0,0,0,0.6),0_2px_4px_rgba(0,0,0,0.2)]">
            <span className="text-[10px] font-mono text-slate-400">{name}</span>
            <div className={`w-2 h-2 rounded-full transition-all duration-300
              ${ok ? "bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] border border-emerald-200" : "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.8)] border border-red-300"}`} />
          </div>
        ))}
      </div>

      <div className="mb-4 pb-4 border-b border-white/5">
        <div className="text-[8px] font-mono tracking-widest text-slate-600 mb-3 drop-shadow">MODELS</div>
        {(models || ["phi3:mini"]).map(m => {
          const active = m === currentModel;
          return (
            <div key={m} onClick={() => onSwitchModel?.(m)}
              className={`px-3 py-2 mb-2 rounded-lg text-[9px] font-mono font-bold tracking-wider cursor-pointer
                transition-all duration-300 transform active:scale-95 relative overflow-hidden
                ${active
                  ? "bg-gradient-to-b from-sky-500/20 to-sky-900/40 text-sky-400 border-t border-t-sky-400/40 border-b border-b-black/80 shadow-[0_4px_12px_rgba(14,165,233,0.3),inset_0_1px_2px_rgba(255,255,255,0.2),inset_0_-1px_2px_rgba(0,0,0,0.4)]"
                  : "bg-gradient-to-b from-slate-800/50 to-slate-900/60 text-slate-500 hover:text-slate-300 border-t border-t-white/10 border-b border-b-black/80 shadow-[0_2px_6px_rgba(0,0,0,0.4),inset_0_1px_1px_rgba(255,255,255,0.05),inset_0_-1px_1px_rgba(0,0,0,0.6)] hover:shadow-[0_4px_10px_rgba(0,0,0,0.5),inset_0_1px_2px_rgba(255,255,255,0.1)]"}`}>
              <div className="relative z-10 flex items-center justify-between">
                <span>{m.toUpperCase()}</span>
                {active && <div className="w-1.5 h-1.5 rounded-full bg-sky-400 shadow-[0_0_6px_#38bdf8]" />}
              </div>
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
