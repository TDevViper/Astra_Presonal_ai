import React from "react";

function StreamCursor() {
  return (
    <span className="inline-block w-0.5 h-[1em] bg-sky-400 ml-0.5 align-middle
      animate-[blink_0.65s_steps(1)_infinite] rounded-sm" />
  );
}

export function Message({ msg, isStreaming, accent, theme }) {
  const isUser = msg.role === "user";

  return (
    <div className={`flex gap-3 mb-5 items-start animate-[fadeSlideUp_0.25s_ease_forwards]
      ${isUser ? "flex-row-reverse" : "flex-row"}`}>

      {isUser ? (
        <div className="w-8 h-8 rounded-full shrink-0 bg-slate-900
          border border-white/10 flex items-center justify-center
          text-xs text-slate-500 font-mono">U</div>
      ) : (
        <div className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center
          text-sm font-mono font-medium border border-white/10
          bg-gradient-to-br from-sky-500/20 to-violet-500/10"
          style={{ color: accent, borderColor: `${accent}33`,
            boxShadow: isStreaming ? `0 0 16px ${accent}30` : "none" }}>
          A
        </div>
      )}

      <div className="max-w-[68%] min-w-[60px]">
        <div className={`px-4 py-3 backdrop-blur-xl text-sm leading-relaxed
          text-slate-200/90 whitespace-pre-wrap break-words relative overflow-hidden
          ${isUser
            ? "rounded-[18px_18px_4px_18px] bg-slate-800/60 border border-white/10 shadow-lg"
            : "rounded-[18px_18px_18px_4px] bg-black/30 border border-white/5 shadow-2xl"}`}>
          <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r
            from-transparent via-white/5 to-transparent pointer-events-none" />
          {msg.content}
          {isStreaming && <StreamCursor />}
        </div>

        {!isUser && (msg.agent || msg.intent) && (
          <div className="flex gap-2 mt-1.5 pl-1 items-center">
            {msg.agent && (
              <span className="text-[9px] font-mono text-slate-700 tracking-wider">
                {msg.agent.toUpperCase().slice(0, 10)}
              </span>
            )}
            {msg.confidence && (
              <span className="text-[9px] font-mono text-slate-700">
                {Math.round(msg.confidence * 100)}%
              </span>
            )}
            {msg.intent && (
              <span className="text-[9px] font-mono text-slate-600 tracking-wide">
                {msg.intent.toUpperCase()}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
