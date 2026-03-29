import React, { useState } from "react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';

function StreamCursor() {
  return (
    <span className="inline-block w-1 h-[1.1em] bg-sky-400 ml-1 mb-[-2px] align-baseline
      animate-[blink_0.65s_steps(1)_infinite] rounded-[1px] shadow-[0_0_8px_#38bdf8]" />
  );
}

const CodeBlock = ({ node, inline, className, children, ...props }) => {
  const match = /language-(\w+)/.exec(className || '');
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(String(children).replace(/\n$/, ''));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (!inline && match) {
    return (
      <div className="relative group mt-4 mb-4 rounded-xl overflow-hidden border border-t-white/10 border-l-white/5 border-b-black border-r-black shadow-[0_12px_30px_rgba(0,0,0,0.8),inset_0_1px_0_rgba(255,255,255,0.05)] bg-[#0d1f33]">
        <div className="flex items-center justify-between px-4 py-2 bg-gradient-to-b from-white/5 to-transparent border-b border-white/5 text-[10px] font-mono text-slate-400 tracking-wider">
          <span>{match[1].toUpperCase()}</span>
          <button 
            onClick={handleCopy} 
            className="p-1 hover:text-white hover:bg-white/10 rounded transition-all active:scale-90 flex items-center gap-1"
          >
            {copied ? <><Check size={12} className="text-emerald-400" /> COPIED</> : <><Copy size={12} /> COPY</>}
          </button>
        </div>
        <SyntaxHighlighter
          {...props}
          style={vscDarkPlus}
          language={match[1]}
          PreTag="div"
          customStyle={{ margin: 0, background: 'rgba(0,0,0,0.3)', padding: '1.25rem', fontSize: '0.85rem' }}
        >
          {String(children).replace(/\n$/, '')}
        </SyntaxHighlighter>
      </div>
    );
  }
  return (
    <code {...props} className={`${className} bg-black/40 border border-black/50 px-1.5 py-0.5 rounded text-[0.9em] font-mono text-sky-300 shadow-[inset_0_1px_4px_rgba(0,0,0,0.6)]`}>
      {children}
    </code>
  );
};

export function Message({ msg, isStreaming, accent, theme }) {
  const isUser = msg.role === "user";

  // 3D Beveled CSS classes
  const user3D = "rounded-[24px_24px_6px_24px] bg-gradient-to-br from-slate-700/80 to-slate-800/90 border border-t-white/20 border-l-white/10 border-b-black/80 border-r-black/50 shadow-[4px_12px_24px_rgba(0,0,0,0.4),inset_1px_1px_2px_rgba(255,255,255,0.15),inset_-2px_-2px_6px_rgba(0,0,0,0.4)]";
  
  const astra3D = "rounded-[24px_24px_24px_6px] bg-gradient-to-br from-black/60 to-slate-900/50 border border-t-white/10 border-l-white/5 border-b-black border-r-black/80 shadow-[6px_16px_40px_rgba(0,0,0,0.8),inset_1px_1px_1px_rgba(255,255,255,0.08),inset_-2px_-2px_4px_rgba(0,0,0,0.6)]";

  return (
    <div className={`flex gap-4 mb-8 items-end animate-[fadeSlideUp_0.35s_cubic-bezier(0.16,1,0.3,1)_forwards]
      ${isUser ? "flex-row-reverse" : "flex-row"}`}>

      {/* 3D Avatars */}
      <div className={`w-9 h-9 rounded-full shrink-0 flex items-center justify-center
        text-xs font-mono font-bold border border-t-white/20 border-l-white/10 border-b-black/80 shadow-[2px_6px_12px_rgba(0,0,0,0.5),inset_0_2px_6px_rgba(255,255,255,0.15)] z-10
        ${isUser ? "bg-gradient-to-b from-slate-700 to-slate-900 text-slate-300" : "bg-gradient-to-b from-slate-800 to-black"}
      `}
      style={!isUser ? { color: accent, borderColor: `${accent}40`, boxShadow: `0 8px 20px ${accent}25, inset 0 2px 8px rgba(255,255,255,0.1)` } : {}}>
        {isUser ? "U" : "A"}
      </div>

      <div className={`relative max-w-[75%] min-w-[60px] group`}>
        <div className={`relative px-5 py-4 backdrop-blur-2xl text-[14.5px] leading-relaxed
          break-words overflow-hidden ${isUser ? user3D : astra3D}
          ${isUser ? "text-slate-100" : "text-slate-200"}`}>
          
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{ 
              code: CodeBlock, 
              h1: ({node, ...props}) => <h1 className="text-xl font-bold mt-4 mb-2 text-white/90 drop-shadow-md tracking-tight" {...props}/>,
              h2: ({node, ...props}) => <h2 className="text-lg font-bold mt-3 mb-2 text-white/90 drop-shadow-md tracking-tight" {...props}/>,
              h3: ({node, ...props}) => <h3 className="text-base font-bold mt-2 mb-1 text-white/90 drop-shadow-md tracking-tight" {...props}/>,
              p: ({node, ...props}) => <p className="mb-3 last:mb-0 drop-shadow-sm leading-relaxed" {...props}/>,
              ul: ({node, ...props}) => <ul className="list-disc list-outside ml-4 mb-3 gap-1 flex flex-col" {...props}/>,
              ol: ({node, ...props}) => <ol className="list-decimal list-outside ml-4 mb-3 gap-1 flex flex-col" {...props}/>,
              li: ({node, ...props}) => <li className="pl-1 marker:text-sky-400 drop-shadow-sm" style={{markerColor: accent}} {...props}/>,
              a: ({node, ...props}) => <a className="text-sky-400 underline decoration-sky-400/30 hover:decoration-sky-400 transition-all drop-shadow" style={{color: accent}} {...props}/>,
              table: ({node, ...props}) => <div className="overflow-x-auto mb-4 border border-t-white/10 border-b-black rounded-lg shadow-[inset_0_2px_10px_rgba(0,0,0,0.5),0_4px_10px_rgba(0,0,0,0.3)] bg-black/20"><table className="w-full text-left border-collapse text-sm" {...props}/></div>,
              th: ({node, ...props}) => <th className="bg-black/50 p-3 font-semibold text-slate-200 border-b border-white/5" {...props}/>,
              td: ({node, ...props}) => <td className="p-3 border-b border-white/5 last:border-0" {...props}/>,
              blockquote: ({node, ...props}) => <blockquote className="border-l-4 rounded-r-lg bg-gradient-to-r from-black/40 to-transparent p-4 my-3 italic shadow-[inset_0_2px_8px_rgba(0,0,0,0.2)]" style={{borderColor: accent}} {...props}/>,
            }}
          >
            {msg.content + (isStreaming ? " \u200B" : "")}
          </ReactMarkdown>
          {isStreaming && <StreamCursor />}
        </div>

        {/* 3D Hovering Metadata Pills */}
        {!isUser && (msg.agent || msg.intent) && (
          <div className="absolute -bottom-3 left-6 flex gap-2 opacity-0 group-hover:opacity-100 transition-all duration-400 transform translate-y-2 group-hover:translate-y-0 z-20 pointer-events-none">
            {msg.agent && (
              <span className="px-2.5 py-1 rounded-full bg-gradient-to-b from-slate-800 to-slate-950 border border-t-white/20 border-l-white/10 border-b-black shadow-[0_4px_10px_rgba(0,0,0,0.6)] text-[8px] font-mono text-slate-300 tracking-widest backdrop-blur-md">
                {msg.agent.toUpperCase().slice(0, 10)}
              </span>
            )}
            {msg.intent && (
              <span className="px-2.5 py-1 rounded-full bg-gradient-to-b from-slate-800 to-slate-950 border border-t-white/20 border-l-white/10 border-b-black shadow-[0_4px_10px_rgba(0,0,0,0.6)] text-[8px] font-mono text-slate-400 tracking-wider backdrop-blur-md">
                {msg.intent.toUpperCase()}
              </span>
            )}
            {msg.confidence && (
              <span className="px-2.5 py-1 rounded-full bg-gradient-to-b from-slate-800 to-slate-950 border border-t-white/20 border-l-white/10 border-b-black shadow-[0_4px_10px_rgba(0,0,0,0.6)] text-[8px] font-mono text-slate-400 backdrop-blur-md">
                {Math.round(msg.confidence * 100)}%
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
