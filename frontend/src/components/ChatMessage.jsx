function escHtml(str) {
  return str.replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");
}

function renderMarkdown(text) {
  if (!text) return "";
  return text
    .replace(/```(\w+)?\n?([\s\S]*?)```/g, (_,lang,code) =>
      `<pre class="md-pre" data-lang="${lang||''}"><code>${escHtml(code.trim())}</code></pre>`)
    .replace(/`([^`]+)`/g, (_,c) => `<code class="md-ic">${escHtml(c)}</code>`)
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/^### (.+)$/gm, "<h3>$1</h3>")
    .replace(/^## (.+)$/gm,  "<h2>$1</h2>")
    .replace(/^# (.+)$/gm,   "<h1>$1</h1>")
    .replace(/^[-•*] (.+)$/gm, "<li>$1</li>")
    .replace(/^\d+\. (.+)$/gm, "<li>$1</li>")
    .replace(/(<li>[\s\S]*?<\/li>\n?)+/g, m => `<ul>${m}</ul>`)
    .replace(/\n\n/g, "</p><p>")
    .replace(/\n/g, "<br/>");
}

const CSS = `
.md { font-size:13px; line-height:1.65; color:inherit; }
.md h1{font-size:15px;font-weight:600;margin:8px 0 4px}
.md h2{font-size:14px;font-weight:600;margin:6px 0 3px}
.md h3{font-size:13px;font-weight:600;margin:5px 0 2px}
.md ul{margin:4px 0 4px 16px;list-style:disc}
.md li{margin:2px 0}
.md-pre{background:rgba(0,0,0,0.35);border:1px solid rgba(148,163,184,0.12);border-radius:6px;padding:10px 12px;margin:6px 0;overflow-x:auto;font-family:'JetBrains Mono',monospace;font-size:11.5px;line-height:1.5;color:#c9d1d9}
.md-pre[data-lang]:not([data-lang=""])::before{content:attr(data-lang);display:block;font-size:9px;color:#4a6fa5;letter-spacing:.1em;text-transform:uppercase;margin-bottom:6px}
.md-ic{background:rgba(0,0,0,0.25);border:1px solid rgba(148,163,184,0.1);border-radius:3px;padding:1px 5px;font-family:'JetBrains Mono',monospace;font-size:11px;color:#7dd3fc}
`;

const EMOTION = {joy:"😊",sad:"😢",angry:"😠",anxious:"😰",tired:"😴",surprised:"😲"};
const AGENT_SHORT = (a="") => {
  if (a.includes("mistral")) return "MISTRAL";
  if (a.includes("llama"))   return "LLAMA";
  if (a.includes("phi3"))    return "PHI3";
  if (a==="web_search_agent") return "WEB";
  if (a==="memory")           return "MEM";
  return a.toUpperCase().slice(0,8);
};

export default function ChatMessage({ message, isUser, onFeedback }) {
  const conf = message.confidence;
  const confColor = conf>=0.8?"#34d399":conf>=0.6?"#fbbf24":"#f87171";
  const html = isUser ? null : renderMarkdown(message.content||"");

  return (
    <>
      <style>{CSS}</style>
      <div style={{display:"flex",justifyContent:isUser?"flex-end":"flex-start",marginBottom:16,gap:10,alignItems:"flex-start"}}>
        {!isUser && (
          <div style={{width:26,height:26,borderRadius:"50%",flexShrink:0,background:"radial-gradient(circle at 35% 35%,#38bdf830,#38bdf808)",border:"1px solid #38bdf822",display:"flex",alignItems:"center",justifyContent:"center",fontSize:11,color:"#38bdf8",fontFamily:"'JetBrains Mono',monospace",marginTop:2}}>A</div>
        )}
        <div style={{maxWidth:"72%",minWidth:0}}>
          <div style={{padding:"10px 14px",borderRadius:isUser?"16px 16px 4px 16px":"4px 16px 16px 16px",background:isUser?"linear-gradient(135deg,#1e3a5f,#0d2a47)":"rgba(13,31,51,0.7)",border:isUser?"1px solid #2a5080":"1px solid rgba(148,163,184,0.07)",wordBreak:"break-word"}}>
            {isUser
              ? <p style={{fontSize:13,lineHeight:1.6,color:"#c8d8e8",margin:0}}>{message.content}</p>
              : <div className="md" dangerouslySetInnerHTML={{__html:`<p>${html}</p>`}}/>
            }
          </div>
          {!isUser && (
            <div style={{display:"flex",alignItems:"center",gap:8,marginTop:5,paddingLeft:4,fontSize:9,fontFamily:"'JetBrains Mono',monospace",color:"#2a4a6a",letterSpacing:"0.06em"}}>
              {message.agent && <span style={{color:"#1e3a5f"}}>{AGENT_SHORT(message.agent)}</span>}
              {message.intent && <span style={{color:"#1e3a5f"}}>{message.intent.toUpperCase()}</span>}
              {conf!=null && <span style={{color:confColor}}>{Math.round(conf*100)}%</span>}
              {message.emotion && message.emotion!=="neutral" && <span>{EMOTION[message.emotion]||""}</span>}
              {onFeedback && (
                <div style={{display:"flex",gap:4,marginLeft:"auto"}}>
                  <button onClick={()=>onFeedback(message.id,1)} style={{background:"none",border:"none",cursor:"pointer",fontSize:11,color:message.feedback===1?"#34d399":"#1e3a5f",padding:"0 2px"}} title="Good">▲</button>
                  <button onClick={()=>onFeedback(message.id,-1)} style={{background:"none",border:"none",cursor:"pointer",fontSize:11,color:message.feedback===-1?"#f87171":"#1e3a5f",padding:"0 2px"}} title="Bad">▼</button>
                </div>
              )}
            </div>
          )}
        </div>
        {isUser && (
          <div style={{width:26,height:26,borderRadius:"50%",flexShrink:0,background:"rgba(30,58,95,0.6)",border:"1px solid #2a5080",display:"flex",alignItems:"center",justifyContent:"center",fontSize:10,color:"#4a6fa5",fontFamily:"'JetBrains Mono',monospace",marginTop:2}}>U</div>
        )}
      </div>
    </>
  );
}
