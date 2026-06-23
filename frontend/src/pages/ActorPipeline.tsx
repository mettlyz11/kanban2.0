import { MODES, MODE_CATEGORIES, SCENE_MODES } from './modes_config';
import React, { useState, useRef, useEffect, useCallback } from "react"
const A = "/api/actor"
const C = "/api/crews"
const PRESETS = [
  { label: "AI催化化学调研", task: "调研AI催化化学三个前沿方向（Diffusion逆向设计、GNN过渡态搜索、主动学习高通量），做商业化分析，给出All-in决策" },
  { label: "竞争对手分析", task: "调研深势科技、深度原理、Matlantis等AI+材料公司的产品线、融资、团队，分析和光智成差异化竞争力，给出应对策略" },
  { label: "融资策略建议", task: "分析当前AI+材料赛道融资环境，基于和光智成现状给出融资策略、BP打磨方向、目标投资人清单" },
]
const R6: Record<string,{n:string,e:string,d:string}> = {
  researcher: { n:"子墨", e:"🔬", d:"技术文献调研" },
  analyst:    { n:"计然", e:"📊", d:"商业化分析" },
  strategist: { n:"卧龙", e:"🧠", d:"战略决策" },
  finance:    { n:"陶朱", e:"💰", d:"财务顾问" },
  risk:       { n:"韩非", e:"⚠️", d:"风险排查" },
  investor:   { n:"白圭", e:"👀", d:"投资人视角" },
}
const MODERATOR = { n:"孔子", e:"👴", d:"圆桌主持人" }
const RK = Object.keys(R6)
interface Hist { id:string; task:string; status:string; created_at:string; duration_s:number }
interface RTHist { timestamp:string; question:string; participants:string[]; round_count:number; consensus:boolean }


// 渲染 Markdown 文本，将 ![alt](url) 转为可点击的图片
function renderMarkdownWithImages(text: string) {
  if (!text) return null;
  // 把 Markdown 图片 ![alt](url) 转为 HTML <img>
  const html = text.replace(/!\[([^\]]*)\]\(([^\)]+)\)/g, '<br/><a href="$2" target="_blank" rel="noopener noreferrer"><img src="$2" alt="$1" style="max-width:100%;max-height:300px;border-radius:8px;box-shadow:0 1px 4px rgba(0,0,0,0.15);margin:8px 0"/></a><br/>');
  return <div dangerouslySetInnerHTML={{__html: html}} />;
}

export default function ActorPipeline() {
  const [tab,setTab]=useState<"run"|"crew"|"history"|"chat"|"brainstorm">("run")
  const [chatMode,setChatMode]=useState<"single"|"roundtable">("single")
  const [task,setTask]=useState(PRESETS[0].task)
  const [running,setRunning]=useState(false); const [stage,setStage]=useState("")
  const [rawOut,setRawOut]=useState(""); const [result,setResult]=useState<any>(null); const [error,setError]=useState("")
  const [history,setHistory]=useState<Hist[]>([]); const [showId,setShowId]=useState<string|null>(null); const [det,setDet]=useState<any>(null); const [histFilter,setHistFilter]=useState<string|null>(null)
  const [chatRole,setChatRole]=useState("researcher"); const [chatMsgs,setChatMsgs]=useState<{r:string;c:string;image?:any}[]>([])
  const [chatModeType,setChatModeType]=useState<string>("auto")
  const [rtMode,setRtMode]=useState<string>("auto")
  const [chatInput,setChatInput]=useState(""); const [chatLoading,setChatLoading]=useState(false)
  const [rtRoles,setRtRoles]=useState(["researcher","analyst","strategist"]); const [rtQ,setRtQ]=useState("")
  const [rtRes,setRtRes]=useState<any>(null); const [rtLoad,setRtLoad]=useState(false); const [rtSettings,setRtSettings]=useState({max_rounds:3,max_tokens:800,timeout_s:300,depth:"normal",focus:"",keyword_block:"",knowledge_scope:"auto",image_mode:false}); const [rtShowSettings,setRtShowSettings]=useState(false)
  const [rtHist,setRtHist]=useState<RTHist[]>([]); const [rtHistTab,setRtHistTab]=useState(false)
  const [crewData,setCrewData]=useState<any>(null); const [crewLoading,setCrewLoading]=useState(false); const [crewMsg,setCrewMsg]=useState("")
  const loadCrew=useCallback(async()=>{setCrewLoading(true);try{const r=await fetch(C+"/status");const d=await r.json();setCrewData(d);setCrewMsg(d.ok?"":"⚠️ "+(d.error||"加载失败"))}catch(e:any){setCrewMsg("⚠️ 网络错误: "+(e.message||""))}finally{setCrewLoading(false)}},[])
  const triggerCrew=async(name:string)=>{setCrewMsg("启动中: "+name);try{const r=await fetch(C+"/trigger",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({crew:name})});const d=await r.json();setCrewMsg(d.ok?"✅ 已启动 "+name+" pid="+d.pid:"⚠️ "+(d.error||"启动失败"));setTimeout(loadCrew,1200)}catch(e:any){setCrewMsg("⚠️ 网络错误: "+(e.message||""))}}
  const resolveEsc=async(id:number,action="resolved_by_actor")=>{try{await fetch(C+"/resolve",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({id,action})});loadCrew()}catch(e:any){setCrewMsg("⚠️ 网络错误: "+(e.message||""))}}
// 脑风暴状态
  const [brainstormQ,setBrainstormQ]=useState("")
  const [brainstormAgentA,setBrainstormAgentA]=useState("researcher")
  const [brainstormAgentB,setBrainstormAgentB]=useState("analyst")
  const [brainstormRes,setBrainstormRes]=useState<any>(null)
  const [brainstormLoad,setBrainstormLoad]=useState(false)
  // 使用 ref 跟踪最新消息，避免闭包过期
  const chatMsgsRef=useRef(chatMsgs)
  useEffect(()=>{chatMsgsRef.current=chatMsgs},[chatMsgs])
  const pr=useRef<ReturnType<typeof setInterval>>(); const st=useRef(0); const ld=useRef(false)
  const lh=useCallback(async()=>{try{const r=await fetch(A+"/crew-history");const d=await r.json();if(d.ok)setHistory(d.history||[])}catch{}},[])
  const lrt=useCallback(async()=>{try{const r=await fetch(A+"/roundtable-history");const d=await r.json();if(d.ok)setRtHist(d.history||[])}catch{}},[])
  useEffect(()=>{if(!ld.current){ld.current=true;lh();lrt();loadCrew()}},[])
  useEffect(()=>()=>clearInterval(pr.current),[])
  const sr=async()=>{setRunning(true);setStage("启动中");setRawOut("");setResult(null);setError("");st.current=Date.now()
    const ac=new AbortController()
    const tt=setTimeout(()=>ac.abort(),3600000)
    try{const r=await fetch(A+"/crew-run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task}),signal:ac.signal});clearTimeout(tt);const d=await r.json();if(d.error){setStage("启动失败");setError(d.error);setRunning(false);return}
    pr.current=setInterval(async()=>{try{const sr=await fetch(A+"/crew-status");const sd=await sr.json();setStage(sd.stage||"运行中");if(sd.output)setRawOut(sd.output);if(["completed","failed","timeout","cancelled","error"].includes(sd.status)){clearInterval(pr.current);const fs=sd.status==="completed"?"完成":sd.status==="cancelled"?"已取消":sd.status;setStage(fs);setRawOut(sd.output||(sd.error||""));setResult(sd);setRunning(false);try{await fetch(A+"/crew-save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task,status:sd.status,output:(sd.output||"")?.slice(0,2000),duration_s:Math.round((Date.now()-st.current)/1000)})});lh()}catch{}}}catch{}},3000)}catch(e:any){
      const errorMsg = e.message || '';
      const friendlyError = errorMsg.includes('signal is aborted') 
        ? '请求超时，请重试' 
        : errorMsg.includes('timeout') 
        ? '请求超时，请稍后重试'
        : '网络错误: ' + errorMsg;
      setStage(friendlyError); 
      setError(friendlyError);
      setRunning(false)
    }}
  const cr=async()=>{clearInterval(pr.current);try{await fetch(A+"/crew-cancel",{method:"POST"})}catch{};setRunning(false);setStage("已取消")}
  const ldDet=async(id:string)=>{setShowId(id);setDet(null);try{const r=await fetch(A+"/crew-history/"+id);const d=await r.json();if(d.ok)setDet(d.entry)}catch{}}
  const sc=async()=>{
    if(!chatInput.trim()||chatLoading)return
    const m=chatInput;setChatInput("")
    // ✅ 用 ref 获取最新消息列表，避免闭包过期导致消息丢失
    const msgs=[...chatMsgsRef.current,{r:"user",c:m}]
    setChatMsgs(msgs)
    setChatLoading(true)
    const acChat=new AbortController()
    const ttChat=setTimeout(()=>acChat.abort(),3000000)
    try{
      const r=await fetch(A+"/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          messages:msgs.map(({r,c})=>({role:r,content:c})),
          role:chatRole,
          mode:chatModeType,
          knowledge_scope:chatRole==="researcher"?"academic":chatRole==="analyst"||chatRole==="finance"||chatRole==="investor"?"business":"full",
          max_tokens:2000
        }),
        signal:acChat.signal
      })
      const d=await r.json()
      if(d.ok){
        // 有图片时嵌入回复文字中，不单独加图片消息
        const replyText = d.image?.url ? d.reply + "\n\n![配图](" + d.image.url + ")" : d.reply
        setChatMsgs(p=>[...p,{r:"assistant",c:replyText}])
      }else{
        setChatMsgs(p=>[...p,{r:"error",c:"⚠️ "+(d.error||"请求失败")}])
      }
    }catch(e:any){
      setChatMsgs(p=>[...p,{r:"error",c:"⚠️ 网络错误: "+(e.message||"")}])
    }
    clearTimeout(ttChat)
    setChatLoading(false)
  }
  const rr=async()=>{
    if(!rtQ.trim()||rtLoad)return
    setRtRes(null)
    setRtLoad(true)
    const ac=new AbortController()
    const tt=setTimeout(()=>ac.abort(),3000000)
    try{
      const r=await fetch(A+"/roundtable",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({question:rtQ,roles:rtRoles,mode:rtMode,...rtSettings}),
        signal:ac.signal
      })
      clearTimeout(tt)
      const d=await r.json()
      if(d.ok){setRtRes(d);lrt()}else{setRtRes({error:d.error||"请求失败"})}
    }catch(e:any){
      setRtRes({error:e.name==="AbortError"?"请求超时(>10分钟)，请重试":"网络错误: "+(e.message||"未知错误")})
    }finally{
      clearTimeout(tt)
      setTimeout(()=>setRtLoad(false),1500)
    }
  }
  const pct=running?Math.min(100,[stage.includes("研究")?1:0,stage.includes("分析")?1:0,stage.includes("扮演")||stage==="完成"?1:0].reduce((a,b)=>a+b,0)/3*100):result?100:0
  const hc=history.length
  return <div style={{maxWidth:960,margin:"0 auto",padding:"4px 6px"}}>
    <div style={{display:"flex",gap:0,marginBottom:5,borderBottom:"1px solid #999",width:"100%"}}>
      {[{k:"run",l:"🤖 管道"},{k:"crew",l:"🧑‍✈️ Crew"},{k:"brainstorm",l:"🧠 脑风暴"},{k:"chat",l:"💬 对话"},{k:"history",l:"📜 历史"}].map(t=><button key={t.k} onClick={()=>setTab(t.k as any)} style={{flex:1,padding:"10px 24px",border:"none",background:tab===t.k?"#fff":"transparent",borderBottom:tab===t.k?"3px solid #1677ff":"2px solid transparent",cursor:"pointer",fontSize:14,color:tab===t.k?"#1677ff":"#444",fontWeight:tab===t.k?500:400,whiteSpace:"nowrap"}}>{t.l}</button>)}
    </div>
    {tab==="run"&&<RunTab task={task} setTask={setTask} running={running} stage={stage} rawOut={rawOut} result={result} error={error} pct={pct} onStart={sr} onCancel={cr}/>}
    {tab==="crew"&&<CrewTab data={crewData} loading={crewLoading} msg={crewMsg} onRefresh={loadCrew} onTrigger={triggerCrew} onResolve={resolveEsc}/>}
    {tab==="history"&&<div>
      <div style={{display:"flex",gap:2,marginBottom:4}}>
        <button onClick={()=>setRtHistTab(false)} style={{padding:"3px 8px",borderRadius:10,border:"none",background:!rtHistTab?"#1677ff":"#d9d9d9",color:!rtHistTab?"#fff":"#555",cursor:"pointer",fontSize:13}}>管道历史</button>
        <button onClick={()=>{setRtHistTab(true);lrt()}} style={{padding:"3px 8px",borderRadius:10,border:"none",background:rtHistTab?"#1677ff":"#d9d9d9",color:rtHistTab?"#fff":"#555",cursor:"pointer",fontSize:13}}>圆桌历史({rtHist.length})</button>
      </div>
      {rtHistTab?<RtHisTab history={rtHist}/>:<HisTab history={history} showId={showId} detail={det} onLoad={ldDet} typeFilter={histFilter} setTypeFilter={setHistFilter}/>}
    </div>}
{tab==="brainstorm"&&<BrainstormTab q={brainstormQ} setQ={setBrainstormQ} agentA={brainstormAgentA} setAgentA={setBrainstormAgentA} agentB={brainstormAgentB} setAgentB={setBrainstormAgentB}/>}
    {tab==="chat"&&<div>
      <div style={{display:"flex",gap:2,marginBottom:4}}>
        <button onClick={()=>setChatMode("single")} style={{padding:"3px 8px",borderRadius:10,border:"none",background:chatMode==="single"?"#1677ff":"#d9d9d9",color:chatMode==="single"?"#fff":"#555",cursor:"pointer",fontSize:13}}>单聊</button>
        <button onClick={()=>setChatMode("roundtable")} style={{padding:"3px 8px",borderRadius:10,border:"none",background:chatMode==="roundtable"?"#1677ff":"#d9d9d9",color:chatMode==="roundtable"?"#fff":"#555",cursor:"pointer",fontSize:13}}>圆桌讨论</button>
      </div>
      {chatMode==="single"&&<ChatSingle role={chatRole} setRole={setChatRole} msgs={chatMsgs} setMsgs={setChatMsgs} input={chatInput} setInput={setChatInput} loading={chatLoading} send={sc} chatModeType={chatModeType} setChatModeType={setChatModeType}/>}
      {chatMode==="roundtable"&&<RtTab rtRoles={rtRoles} setRtRoles={setRtRoles} rtQ={rtQ} setRtQ={setRtQ} rtRes={rtRes} rtLoad={rtLoad} onRun={rr} rtMode={rtMode} setRtMode={setRtMode} rtSettings={rtSettings} setRtSettings={setRtSettings} rtShowSettings={rtShowSettings} setRtShowSettings={setRtShowSettings}/>}
    </div>}
  </div>
}


function CrewTab({data,loading,msg,onRefresh,onTrigger,onResolve}:any){
  const crews=data?.crews||[]
  const esc=data?.escalations||[]
  const runs=data?.recent_runs||[]
  const pending=esc.filter((e:any)=>e.status==='pending')
  const statusColor=(s:string)=>s==='completed'?'#52c41a':s==='failed'?'#ff4d4f':s==='pending'?'#faad14':'#888'
  return <div>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:3}}>
      <div>
        <div style={{fontSize:14,fontWeight:700}}>🧑‍✈️ Crew 控制台</div>
        <div style={{fontSize:11,color:'#555'}}>查看 Crew 状态、手动触发任务、处理人工介入项</div>
      </div>
      <button onClick={onRefresh} disabled={loading} style={{padding:'8px 16px',borderRadius:20,border:'1px solid #1677ff',background:'#fff',color:'#1677ff',cursor:'pointer'}}>{loading?'刷新中...':'刷新'}</button>
    </div>
    {msg&&<div style={{marginBottom:2,padding:'6px 10px',borderRadius:10,background:msg.startsWith('✅')?'#d9f7be':'#fffbe6',border:'1px solid '+(msg.startsWith('✅')?'#52c41a':'#ffe58f'),fontSize:13}}>{msg}</div>}
    <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(190px,1fr))',gap:3,marginBottom:5}}>
      {crews.map((c:any)=><div key={c.name} style={{padding:12,border:'1px solid #777',borderRadius:14,background:'#fff'}}>
        <div style={{fontWeight:700,fontSize:14,marginBottom:4}}>{c.name}</div>
        <div style={{fontSize:11,color:'#555',minHeight:34}}>{c.desc}</div>
        <button onClick={()=>onTrigger(c.name)} style={{marginTop:2,width:'100%',padding:'7px 10px',borderRadius:18,border:'none',background:'#1677ff',color:'#fff',cursor:'pointer'}}>立即运行</button>
      </div>)}
      {crews.length===0&&<div style={{padding:20,color:'#444'}}>暂无 Crew 数据</div>}
    </div>
    <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:2}}>
      <div style={{border:'1px solid #555',borderRadius:14,overflow:'hidden'}}>
        <div style={{padding:'6px 10px',background:'#fff7e6',fontWeight:700}}>📣 人工介入项 <span style={{color:'#fa8c16'}}>pending {pending.length}</span></div>
        <div style={{maxHeight:360,overflow:'auto'}}>
          {esc.length===0?<div style={{padding:18,color:'#444'}}>暂无介入项</div>:esc.map((e:any)=><div key={e.id} style={{padding:'6px 10px',borderTop:'1px solid #888'}}>
            <div style={{display:'flex',justifyContent:'space-between',gap:2}}><b style={{fontSize:13}}>#{e.task_id} · {e.crew_name}</b><span style={{fontSize:11,color:e.status==='pending'?'#fa8c16':'#999'}}>{e.status}</span></div>
            <div style={{fontSize:12,color:'#333',marginTop:2,whiteSpace:'pre-wrap'}}>{e.reason}</div>
            <div style={{fontSize:11,color:'#333',marginTop:2}}>{String(e.created_at||'')}</div>
            {e.status==='pending'&&<div style={{display:'flex',gap:3,marginTop:2}}>
              <button onClick={()=>onResolve(e.id,'resolved_by_actor')} style={{padding:'4px 10px',borderRadius:12,border:'none',background:'#52c41a',color:'#fff',fontSize:12,cursor:'pointer'}}>已处理</button>
              <button onClick={()=>onResolve(e.id,'ignored_by_actor')} style={{padding:'4px 10px',borderRadius:12,border:'1px solid #777',background:'#fff',fontSize:12,cursor:'pointer'}}>忽略</button>
            </div>}
          </div>)}
        </div>
      </div>
      <div style={{border:'1px solid #555',borderRadius:14,overflow:'hidden'}}>
        <div style={{padding:'6px 10px',background:'#d9f7be',fontWeight:700}}>🧾 最近 Crew 执行</div>
        <div style={{maxHeight:360,overflow:'auto'}}>
          {runs.length===0?<div style={{padding:18,color:'#444'}}>暂无执行记录</div>:runs.map((r:any)=><div key={r.id} style={{padding:'6px 10px',borderTop:'1px solid #888'}}>
            <div style={{display:'flex',justifyContent:'space-between',gap:2}}><b style={{fontSize:13}}>{r.title}</b><span style={{fontSize:11,color:statusColor(r.status)}}>{r.status}</span></div>
            <div style={{fontSize:12,color:'#333',marginTop:2,whiteSpace:'pre-wrap'}}>{(r.result_summary||'').slice(0,260)}</div>
            <div style={{fontSize:11,color:'#333',marginTop:2}}>{String(r.created_at||'')}</div>
          </div>)}
        </div>
      </div>
    </div>
  </div>
}

function RunTab({task,setTask,running,stage,rawOut,result,error,pct,onStart,onCancel}:any){
  const [m,setM]=useState<any[]>([])
  const find=useCallback(async(t:string)=>{if(!t?.trim()){setM([]);return}
    try{const r=await fetch(A+"/crew-similar",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task:t})});const d=await r.json();setM(d.ok?(d.matches||[]):[])}catch{setM([])}},[setM])
  useEffect(()=>{const t=setTimeout(()=>find(task),500);return()=>clearTimeout(t)},[task,find])
  const steps=[
    {e:"🔬",l:"研究员",s:stage.includes("研究员")?"r":stage.includes("分析")||stage.includes("扮演")||stage==="完成"?"d":running?"p":"i"},
    {e:"📊",l:"分析师",s:stage.includes("分析")?"r":stage.includes("扮演")||stage==="完成"?"d":"p"},
    {e:"🧠",l:"扮演者",s:stage.includes("扮演")||stage==="完成"?"r":stage==="完成"?"d":"p"},
  ]
  const col:any={r:["#adc6ff","#1677ff"],d:["#d9f7be","#52c41a"],p:["#fafafa","#d9d9d9"],i:["#fafafa","#d9d9d9"]}
  return <div>
    <div><span style={{fontSize:12,color:"#444"}}>快速开始：</span>
      {PRESETS.map((p,i)=><button key={i} onClick={()=>setTask(p.task)} style={{margin:"2px 4px",padding:"3px 8px",borderRadius:10,border:task===p.task?"3px solid #1677ff":"1px solid #d9d9d9",background:task===p.task?"#adc6ff":"#fff",fontSize:12,cursor:"pointer",color:task===p.task?"#1677ff":"#555"}}>{p.label}</button>)}
    </div>
    {m.length>0&&!running&&<div style={{marginBottom:2,padding:"6px 12px",background:"#fffbe6",borderRadius:8,border:"1px solid #ffe58f",fontSize:12,color:"#ad8b00"}}>找到{m.length}条相似历史</div>}
    <textarea style={{width:"100%",minHeight:60,padding:"6px 10px",borderRadius:8,border:"1px solid #777",fontSize:13,resize:"vertical",boxSizing:"border-box"}} value={task} onChange={e=>setTask(e.target.value)} placeholder="描述任务..." />
    <div style={{display:"flex",gap:2}}>
      <button onClick={onStart} disabled={running||!task.trim()} style={{padding:"6px 20px",fontSize:14,borderRadius:20,border:"none",background:running?"#bbb":"#1677ff",color:"#fff",cursor:running?"not-allowed":"pointer",fontWeight:500}}>
        {running?"运行中":"开始分析"}</button>
      {running&&<button onClick={onCancel} style={{padding:"6px 14px",fontSize:13,borderRadius:20,border:"1px solid #ff4d4f",color:"#ff4d4f",cursor:"pointer",background:"#fff"}}>取消</button>}
    </div>
    {(running||result)&&<div style={{background:"#f8f9fb",borderRadius:14,padding:"12px 16px",marginTop:2}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:4,fontSize:13}}>
        <span style={{color:running?"#1677ff":"#52c41a",fontWeight:500}}>{running?""+stage:result?.status==="completed"?"完成":""+stage}</span>
        <span style={{color:"#444"}}>~3-6分钟</span>
      </div>
      <div style={{height:5,background:"#bbb",borderRadius:3,marginBottom:3,overflow:"hidden"}}>
        <div style={{height:"100%",width:pct+"%",background:"linear-gradient(90deg,#1677ff,#52c41a)",borderRadius:3,transition:"width 0.8s ease"}}/></div>
      <div style={{display:"flex",gap:2}}>{steps.map((s,i)=>{const[bg,c]=col[s.s]||["#fafafa","#d9d9d9"];return <div key={i} style={{flex:1,padding:"4px 6px",borderRadius:8,background:bg,border:"1px solid "+(s.s==="r"?"#1677ff":"#bbb")}}><div style={{fontSize:18}}>{s.e}</div><div style={{fontSize:11,fontWeight:500,color:c}}>{s.l}</div><div style={{fontSize:10,color:s.s==="r"?"#1677ff":s.s==="d"?"#52c41a":"#ccc"}}>{s.s==="r"?"工作中":s.s==="d"?"完成":"—"}</div></div>})}</div>
      {rawOut&&<>
  {/* 检测并显示图片 */}
  {(() => {
    const imageUrlMatch = rawOut.match(/https?:\/\/[^\s]+\.(?:jpeg|jpg|png)/);
    const localImageMatch = rawOut.match(/\/uploads\/brainstorm\/[^\s]+\.(?:jpeg|jpg|png)/);
    const hasImage = (imageUrlMatch || localImageMatch) && result?.status === 'completed';
    return hasImage ? (
      <div style={{marginTop:10,padding:10,background:"#f6ffed",borderRadius:8,border:"1px solid #52c41a"}}>
        <div style={{fontSize:12,color:"#52c41a",marginBottom:8}}>🎨 图片生成成功！</div>
        <img src={localImageMatch ? localImageMatch[0] : imageUrlMatch[0]} alt="生成的logo" style={{maxWidth:"100%",maxHeight:300,borderRadius:8,display:"block",margin:"0 auto"}} />
      </div>
    ) : null;
  })()}
  <pre style={{marginTop:2,padding:10,background:"#1e1e1e",color:"#d4d4d4",borderRadius:8,fontSize:11,maxHeight:200,overflow:"auto",whiteSpace:"pre-wrap"}}>{rawOut.slice(-3000)}</pre>
</>}
    </div>}
    {error&&<div style={{marginTop:2,padding:8,background:"#fff1f0",borderRadius:8,color:"#ff4d4f",fontSize:12}}>错误: {error}</div>}
  </div>
}

function HisTab({history,showId,detail,onLoad,typeFilter,setTypeFilter}:any){
  const typeLabels: Record<string,string> = {crew: '🤖 管道', brainstorm: '🧠 脑风暴', chat: '💬 单聊', roundtable: '🏯 圆桌'}
  const filtered = typeFilter ? history.filter((x:any)=>x.type===typeFilter) : history
  return <div>
    <div style={{display:'flex',gap:2,marginBottom:2,padding:'8px 0',borderBottom:'1px solid #bbb'}}>
      <button onClick={()=>setTypeFilter(null)} style={{padding:'4px 12px',borderRadius:12,border:'1px solid',borderColor:typeFilter?'#d9d9d9':'#1677ff',background:typeFilter?'#fff':'#597ef7',color:typeFilter?'#555':'#1677ff',fontSize:12,cursor:'pointer'}}>全部</button>
      {['crew','brainstorm','chat','roundtable'].map(t=><button key={t} onClick={()=>setTypeFilter(t)} style={{padding:'4px 12px',borderRadius:12,border:'1px solid',borderColor:typeFilter===t?'#1677ff':'#d9d9d9',background:typeFilter===t?'#597ef7':'#fff',color:typeFilter===t?'#1677ff':'#555',fontSize:12,cursor:'pointer'}}>{typeLabels[t]}</button>)}
    </div>
    {filtered.length===0?<div style={{padding:20,textAlign:"center",color:"#555"}}>还没有运行记录</div>:
      <div style={{display:"flex",flexDirection:"column",gap:3}}>{filtered.map((x:any)=><div key={x.id} style={{padding:"4px 6px",borderRadius:8,background:"#f8f9fb",border:"1px solid #d9d9d9",cursor:"pointer"}} onClick={()=>onLoad(x.id)}>
        <div style={{fontSize:11,color:'#555',marginBottom:2}}>{typeLabels[x.type] || x.type}</div>
        <div style={{fontSize:13}}>{x.task?.slice(0,60)}{x.has_image&&" 🖼️"}</div>
        <div style={{fontSize:11,color:"#444",marginTop:2}}>{x.created_at} - {x.status} - {x.duration_s}s</div>
      </div>)}</div>}
    {showId&&<div style={{marginTop:12,padding:"10px 14px",background:"#f6f8fa",borderRadius:10}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:4}}><b>{detail?.task||""}</b><span style={{fontSize:12,color:"#444"}}>{detail?.created_at}</span></div>
      {(detail?.images?.length>0)&&<div style={{marginBottom:8,display:"flex",flexWrap:"wrap",gap:4}}>
        {detail.images.map((img:any,i:number)=><a key={i} href={img.url} target="_blank" rel="noopener noreferrer" style={{display:"inline-block",border:"1px solid #d9d9d9",borderRadius:8,overflow:"hidden",width:120,height:120}}>
          <img src={img.url} alt={img.prompt||"配图"} style={{width:"100%",height:"100%",objectFit:"cover"}}/>
        </a>)}
      </div>}
      <div style={{fontSize:11,color:"#555",marginBottom:4}}>{(detail?.images?.length||0)>0?`${detail.images.length}张图片`:"无图片"}</div>
      <pre style={{fontSize:11,maxHeight:400,overflow:"auto",whiteSpace:"pre-wrap",background:"#1e1e1e",color:"#d4d4d4",padding:10,borderRadius:8}}>{detail?.output||"无详细输出"}</pre>
    </div>}
  </div>
}

function RtHisTab({history}:{history:RTHist[]}){
  return <div>
    {history.length===0?<div style={{padding:20,textAlign:"center",color:"#555"}}>还没有圆桌讨论记录</div>:
      <div style={{display:"flex",flexDirection:"column",gap:3}}>{history.map((x,i)=><div key={i} style={{padding:"4px 6px",borderRadius:8,background:"#f8f9fb",border:"1px solid #d9d9d9"}}>
        <div style={{display:"flex",alignItems:"center",gap:3}}>
          <span>{x.consensus?"✅":"❌"}</span>
          <span style={{fontSize:13}}>{x.question.slice(0,80)}</span>
        </div>
        <div style={{fontSize:11,color:"#444",marginTop:2}}>
          {x.timestamp} | {x.participants.join("、")} | {x.round_count}轮讨论
        </div>
      </div>)}</div>}
  </div>
}

function ChatSingle({role,setRole,msgs,setMsgs,input,setInput,loading,send,chatModeType,setChatModeType}:any){
  const endRef=useRef<HTMLDivElement>(null)
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:"smooth"})},[msgs])
  return <div>
    <div style={{marginBottom:3}}>
      <div style={{display:"flex",gap:2,alignItems:"center",marginBottom:4}}>
        <b style={{fontSize:14}}>选择专家：</b>
        <select value={chatModeType} onChange={(e:any)=>setChatModeType(e.target.value)}
          style={{padding:"4px 10px",borderRadius:6,border:"1px solid #777",fontSize:12,color:"#555",cursor:"pointer"}}>
          <option value="auto">🤖 自动判断</option><option value="explore">🔍 自由探索</option>
          <option value="consult">💼 咨询建议</option>
          <option value="critique">⚡ 批判评估</option>
          <option value="brainstorm">🧠 创意发散</option>
          <option value="deep">🎯 深度分析</option>
        </select>
      </div>
      <div style={{display:"flex",flexWrap:"wrap",gap:2,marginTop:3}}>{RK.map(k=>{const r=R6[k];return<button key={k} onClick={()=>{setRole(k);setMsgs([])}} style={{padding:"5px 14px",borderRadius:20,border:"1px solid",borderColor:role===k?"#1677ff":"#d9d9d9",background:role===k?"#adc6ff":"#fff",color:role===k?"#1677ff":"#555",fontSize:12,cursor:"pointer"}}>{r.e} {r.n}</button>})}
    </div></div>
    <div style={{border:"1px solid #777",borderRadius:12,overflow:"hidden",marginBottom:4}}>
      <div style={{padding:"8px 14px",background:"#f5f7fa",fontSize:11,color:"#555",borderBottom:"1px solid #999"}}>{R6[role]?.e} {R6[role]?.n} - {R6[role]?.d}</div>
      <div style={{minHeight:200,maxHeight:400,overflow:"auto",padding:12}}>
        {msgs.length===0&&<div style={{color:"#555",textAlign:"center",padding:20,fontSize:13}}>开始对话...</div>}
        {msgs.map((m:any,i:number)=>m.r==="image"?(
          <div key={i} style={{marginBottom:5,padding:10,border:"1px solid #adc6ff",borderRadius:10,background:"#d6e4ff"}}>
            {m.image?.url ? <img src={m.image.url} alt={m.image.prompt||"生图"} style={{maxWidth:"100%",maxHeight:360,borderRadius:8,display:"block",margin:"0 auto"}}/> : <div style={{color:"#ff4d4f",fontSize:13}}>⚠️ 图片生成失败</div>}
            {m.image?.prompt&&<div style={{marginTop:2,fontSize:11,color:"#555",wordBreak:"break-all"}}>Prompt: {m.image.prompt}</div>}
          </div>
        ):(
          <div key={i} style={{display:"flex",marginBottom:4,justifyContent:m.r==="user"?"flex-end":"flex-start"}}>
            <div style={{maxWidth:"80%",padding:"6px 12px",borderRadius:m.r==="user"?"12px 12px 4px 12px":"12px 12px 12px 4px",background:m.r==="user"?"#1677ff":"#d9d9d9",color:m.r==="user"?"#fff":"#333",fontSize:13,whiteSpace:"pre-wrap"}}>{renderMarkdownWithImages(m.c)}</div>
          </div>
        ))}
        {loading&&<div style={{textAlign:"center",color:"#444",fontSize:12}}>思考中...</div>}
      </div>
      <div style={{borderTop:"1px solid #bbb",display:"flex",padding:8,gap:2}}>
        <input style={{flex:1,padding:"4px 6px",borderRadius:20,border:"1px solid #777",fontSize:13,outline:"none"}} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()} placeholder="输入问题..." />
        <button onClick={send} disabled={loading||!input.trim()} style={{padding:"8px 14px",borderRadius:20,border:"none",background:loading?"#bbb":"#1677ff",color:"#fff",cursor:loading?"not-allowed":"pointer",fontSize:13}}>{loading?"...":"发送"}</button>
      </div>
    </div>
  </div>
}

function RtTab({rtRoles,setRtRoles,rtQ,setRtQ,rtRes,rtLoad,onRun,rtMode,setRtMode,rtSettings,setRtSettings,rtShowSettings,setRtShowSettings}:any){
  const endRef=useRef<HTMLDivElement>(null)
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:"smooth"})},[rtRes])
  const toggle=(k:string)=>setRtRoles(rtRoles.includes(k)?rtRoles.filter((x:string)=>x!==k):[...rtRoles,k])

  const renderRound = (rd:any[], ri:number) => {
    return <div key={ri} style={{marginBottom:3}}>
      <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#d6e4ff",borderRadius:"8px 8px 0 0",border:"1px solid #d6e4ff"}}>
        🏯 第{ri+1}轮讨论
      </div>
      <div style={{border:"1px solid #d6e4ff",borderTop:"none",borderRadius:"0 0 8px 8px",padding:8}}>
        {rd.map((r:any,i:number)=>{
          const roleInfo = R6[r.role]
          return <div key={i} style={{display:"flex",gap:8,padding:"8px 0",borderBottom:i<rd.length-1?"1px solid #d9d9d9":"none"}}>
            <div style={{minWidth:70,textAlign:"right",fontSize:11,color:"#555"}}>
              <span>{roleInfo?.e||r.emoji||"🤖"}</span>
              <br/><span style={{fontWeight:500,color:"#555",fontSize:13}}>{roleInfo?.n||r.name||r.role}</span>
            </div>
            <div style={{flex:1,display:(r.image?.url||r.image_url)?"grid":"block",gridTemplateColumns:(r.image?.url||r.image_url)?"minmax(0,1fr) minmax(220px,0.8fr)":undefined,gap:12,alignItems:"start"}}>
              {r.ok===false
                ? <span style={{color:"#ff4d4f",fontSize:12}}>⚠️ {r.error||"请求失败"}</span>
                : <>
                    <div style={{margin:0,fontSize:12,lineHeight:1.5}}>{renderMarkdownWithImages(r.reply||"无回复")}</div>
                    {(r.image?.url||r.image_url)&&<a href={r.image?.url||r.image_url} target="_blank" rel="noopener noreferrer" style={{display:"block",textAlign:"center"}}>
                      <img src={r.image?.url||r.image_url} alt={r.image?.prompt||"圆桌配图"} style={{maxWidth:"100%",maxHeight:320,borderRadius:8,boxShadow:"0 1px 4px rgba(0,0,0,0.15)",objectFit:"contain",background:"#fff"}}/>
                      {r.image?.prompt&&<div style={{marginTop:4,fontSize:10,color:"#777",textAlign:"left",wordBreak:"break-all"}}>Prompt: {r.image.prompt}</div>}
                    </a>}
                  </>
              }
            </div>
          </div>
        })}
      </div>
    </div>
  }

  const renderVote = (voteResult:any) => {
    if (!voteResult) return null
    const {summary, details} = voteResult
    return <div style={{marginBottom:3}}>
      <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#fff7e6",borderRadius:"8px 8px 0 0",border:"1px solid #ffd591"}}>
        🗳️ 投票结果
      </div>
      <div style={{border:"1px solid #ffd591",borderTop:"none",borderRadius:"0 0 8px 8px",padding:12}}>
        <div style={{display:"flex",gap:3,marginBottom:3}}>
          <div style={{textAlign:"center",flex:1,padding:"4px 6px",background:"#d9f7be",borderRadius:10}}>
            <div style={{fontSize:24,fontWeight:700,color:"#52c41a"}}>{summary['支持']||0}</div>
            <div style={{fontSize:11,color:"#555"}}>支持</div>
          </div>
          <div style={{textAlign:"center",flex:1,padding:"4px 6px",background:"#fff1f0",borderRadius:10}}>
            <div style={{fontSize:24,fontWeight:700,color:"#ff4d4f"}}>{summary['反对']||0}</div>
            <div style={{fontSize:11,color:"#555"}}>反对</div>
          </div>
          <div style={{textAlign:"center",flex:1,padding:"4px 6px",background:"#fafafa",borderRadius:10}}>
            <div style={{fontSize:24,fontWeight:700,color:"#444"}}>{summary['弃权']||0}</div>
            <div style={{fontSize:11,color:"#555"}}>弃权</div>
          </div>
        </div>
        {details?.map((v:any,i:number)=>{
          const roleInfo = R6[v.role]
          const stanceColor = v.stance==='支持'?'#52c41a':v.stance==='反对'?'#ff4d4f':'#aaa'
          return <div key={i} style={{display:"flex",gap:2,padding:"4px 0",alignItems:"center"}}>
            <span>{roleInfo?.e||v.emoji||"🤖"}</span>
            <span style={{fontSize:13,fontWeight:500,width:50}}>{roleInfo?.n||v.name||v.role}</span>
            <span style={{fontSize:12,fontWeight:600,color:stanceColor}}>{v.stance}</span>
            {v.reason&&<span style={{fontSize:11,color:"#555",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:300}}>— {v.reason.slice(0,60)}</span>}
          </div>
        })}
      </div>
    </div>
  }

  return <div>
    <div style={{marginBottom:3}}>
      <div style={{display:"flex",gap:2,alignItems:"center",marginBottom:4}}>
        <b style={{fontSize:14}}>选择参与专家：</b>
        <select value={rtMode} onChange={(e:any)=>setRtMode(e.target.value)}
          style={{padding:"4px 10px",borderRadius:6,border:"1px solid #777",fontSize:12,color:"#555",cursor:"pointer"}}>
          <option value="auto">🤖 自动判断</option><option value="consensus">🤝 寻求共识</option>
          <option value="debate">⚔️ 对抗辩论</option>
          <option value="collab">💡 协作共创</option>
          <option value="review">📋 同行评审</option>
        </select>
      </div>
      <div style={{display:"flex",flexWrap:"wrap",gap:2,marginTop:3,marginBottom:3}}>
        {RK.map(k=>{const r=R6[k];const sel=rtRoles.includes(k);return<button key={k} onClick={()=>toggle(k)} style={{padding:"5px 14px",borderRadius:20,border:"1px solid",borderColor:sel?"#1677ff":"#d9d9d9",background:sel?"#adc6ff":"#fff",color:sel?"#1677ff":"#555",fontSize:12,cursor:"pointer"}}>{r.e} {r.n} {sel?"✓":"+"}</button>})}
      </div>
      <div style={{fontSize:11,color:"#555",display:"flex",alignItems:"center",gap:2}}>
        <span>👴 {MODERATOR.n}（主持人）</span>
        <span style={{color:"#d9d9d9"}}>|</span>
        <span>自动引导讨论，判断共识，组织投票</span>
      </div>
    </div>
    <div style={{marginBottom:2,fontSize:12}}>
        <button onClick={()=>setRtShowSettings(!rtShowSettings)}
          style={{width:"100%",padding:"4px 10px",borderRadius:8,border:"1px dashed #bbb",background:"#fafafa",cursor:"pointer",fontSize:12,color:"#666",textAlign:"left",marginBottom:3}}>
          {rtShowSettings?"\u25bc ":"\u25b6 "}高级设置
        </button>
        {rtShowSettings&&<div style={{padding:"6px 10px",background:"#f8f9fb",borderRadius:8,border:"1px solid #e8e8e8",display:"flex",flexWrap:"wrap",gap:6}}>
          <label style={{flex:"1 1 30%",minWidth:160,display:"flex",alignItems:"center",gap:6,fontSize:12,color:"#333",padding:"4px 6px",background:"#fff",borderRadius:6,border:"1px solid #e8e8e8"}}>
            <input type="checkbox" checked={!!rtSettings.image_mode} onChange={e=>setRtSettings({...rtSettings,image_mode:e.target.checked})}/>
            🎨 生图模式 <span style={{fontSize:11,color:"#888"}}>圆桌每位专家配图</span>
          </label>
          <div style={{flex:"1 1 30%",minWidth:120}}>
            <label style={{fontSize:11,color:"#666"}}>轮数：</label>
            <input type="number" min={1} max={10} value={rtSettings.max_rounds} onChange={e=>setRtSettings({...rtSettings,max_rounds:parseInt(e.target.value)||3})}
              style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12}}/>
          </div>
          <div style={{flex:"1 1 30%",minWidth:120}}>
            <label style={{fontSize:11,color:"#666"}}>回答长度(字)：</label>
            <input type="number" min={100} max={2000} step={100} value={rtSettings.max_tokens} onChange={e=>setRtSettings({...rtSettings,max_tokens:parseInt(e.target.value)||500})}
              style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12}}/>
          </div>
          <div style={{flex:"1 1 30%",minWidth:120}}>
            <label style={{fontSize:11,color:"#666"}}>超时(秒)：</label>
            <input type="number" min={30} max={600} step={30} value={rtSettings.timeout_s} onChange={e=>setRtSettings({...rtSettings,timeout_s:parseInt(e.target.value)||300})}
              style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12}}/>
          </div>
          <div style={{flex:"1 1 30%",minWidth:120}}>
            <label style={{fontSize:11,color:"#666"}}>深度：</label>
            <select value={rtSettings.depth} onChange={e=>setRtSettings({...rtSettings,depth:e.target.value})}
              style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12,color:"#555"}}>
              <option value="shallow">🫛 浅度</option><option value="normal">📐 中等</option><option value="deep">🎯 深度</option>
            </select>
          </div>
          <div style={{flex:"1 1 30%",minWidth:120}}>
            <label style={{fontSize:11,color:"#666"}}>知识范围：</label>
            <select value={rtSettings.knowledge_scope} onChange={e=>setRtSettings({...rtSettings,knowledge_scope:e.target.value})}
              style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12,color:"#555"}}>
              <option value="auto">🤖 自动</option><option value="academic">📚 学术</option><option value="business">💼 商业</option>
            </select>
          </div>
          <div style={{flex:"1 1 45%",minWidth:200}}>
            <label style={{fontSize:11,color:"#666"}}>聚焦：</label>
            <input type="text" value={rtSettings.focus} onChange={e=>setRtSettings({...rtSettings,focus:e.target.value})}
              placeholder="例：只讨论技术路线" style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12}}/>
          </div>
          <div style={{flex:"1 1 45%",minWidth:200}}>
            <label style={{fontSize:11,color:"#666"}}>过滤：</label>
            <input type="text" value={rtSettings.keyword_block} onChange={e=>setRtSettings({...rtSettings,keyword_block:e.target.value})}
              placeholder="股价,融资,估值" style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:12}}/>
          </div>
        </div>}
      </div>

    <textarea style={{width:"100%",minHeight:50,padding:"4px 6px",borderRadius:10,border:"1px solid #777",fontSize:13,resize:"vertical",boxSizing:"border-box"}} value={rtQ} onChange={e=>setRtQ(e.target.value)} placeholder="输入问题..." />
    <div style={{margin:"8px 0"}}>
      <button onClick={onRun} disabled={rtLoad||!rtQ.trim()||rtRoles.length===0} style={{padding:"8px 24px",borderRadius:20,border:"none",background:rtLoad||rtRoles.length===0?"#bbb":"#1677ff",color:"#fff",cursor:rtLoad||rtRoles.length===0?"not-allowed":"pointer",fontSize:13}}>
        {rtLoad?"圆桌讨论中...":"开始圆桌讨论"}</button>
    </div>

    {rtLoad&&<div style={{textAlign:"center",color:"#444",fontSize:12,padding:16}}>
      <div>👴 孔子主持：各位专家请就座...</div>
      <div style={{marginTop:2}}>等待各位专家回复...（可能需要60-300秒）</div>
      <div style={{marginTop:2,display:"flex",justifyContent:"center",gap:2}}>
        {rtRoles.map((k:string)=><span key={k} style={{padding:"2px 8px",background:"#bfbfbf",borderRadius:10,fontSize:11}}>{R6[k]?.e||""} {R6[k]?.n||k}</span>)}
      </div>
    </div>}

    {rtRes?.rounds?.length>0&&<div>
      {rtRes.consensus
        ? <div style={{padding:"10px 14px",background:"#d9f7be",border:"1px solid #52c41a",borderRadius:10,marginBottom:3,display:"flex",alignItems:"center",gap:3}}>
            <span style={{fontSize:18}}>✅</span>
            <span style={{fontSize:14,fontWeight:500,color:"#52c41a"}}>各位已达成共识！</span>
          </div>
        : rtRes.vote_result
        ? <div style={{padding:"10px 14px",background:"#fff7e6",border:"1px solid #ffd591",borderRadius:10,marginBottom:3,display:"flex",alignItems:"center",gap:3}}>
            <span style={{fontSize:18}}>🗳️</span>
            <span style={{fontSize:14,fontWeight:500,color:"#d46b08"}}>已达{rtRes.rounds.length}轮上限，进入投票环节</span>
          </div>
        : null}

      {rtRes.moderator_reasoning&&<div style={{marginBottom:3}}>
        <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#fffbe6",borderRadius:"8px 8px 0 0",border:"1px solid #ffe58f"}}>
          👴 孔子主持点评
        </div>
        <div style={{border:"1px solid #ffe58f",borderTop:"none",borderRadius:"0 0 8px 8px",padding:"4px 6px",fontSize:12,whiteSpace:"pre-wrap",color:"#333"}}>
          {rtRes.moderator_reasoning}
        </div>
      </div>}

      {rtRes.rounds.map((rd:any,ri:number)=>renderRound([rd],ri))}

      {rtRes.vote_result&&renderVote(rtRes.vote_result)}

      {rtRes.best_role&&<div style={{marginBottom:6,padding:10,background:"#f6ffed",border:"1px solid #52c41a",borderRadius:10}}>
        <div style={{fontSize:13,fontWeight:700,color:"#389e0d",marginBottom:6}}>🏆 最佳方案：{rtRes.best_role.emoji||""} {rtRes.best_role.name||rtRes.best_role.role||"专家方案"}</div>
        {(rtRes.image?.url||rtRes.best_role?.image?.url)&&<img src={rtRes.image?.url||rtRes.best_role.image.url} alt="最佳圆桌配图" style={{maxWidth:"100%",maxHeight:360,borderRadius:8,boxShadow:"0 1px 5px rgba(0,0,0,.18)",background:"#fff"}}/>}
      </div>}

      {rtRes.final_report&&<div style={{marginBottom:3}}>
        <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#d6e4ff",borderRadius:"8px 8px 0 0",border:"1px solid #adc6ff"}}>
          📋 最终报告
        </div>
        <div style={{border:"1px solid #adc6ff",borderTop:"none",borderRadius:"0 0 8px 8px",padding:"4px 6px",fontSize:12,whiteSpace:"pre-wrap",color:"#333",lineHeight:1.6}}>
          {renderMarkdownWithImages(rtRes.final_report + (rtRes.image?.url ? "\n\n![圆桌配图](" + rtRes.image.url + ")" : ""))}
        </div>
      </div>}

      {false && rtRes.image&&<div style={{marginBottom:3}}>
        <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#d6e4ff",borderRadius:"8px 8px 0 0",border:"1px solid #adc6ff"}}>🎨 圆桌生成图片</div>
        <div style={{border:"1px solid #adc6ff",borderTop:"none",borderRadius:"0 0 8px 8px",padding:12,textAlign:"center"}}>
          {rtRes.image.url ? <img src={rtRes.image.url} alt={rtRes.image.prompt||"圆桌生图"} style={{maxWidth:"100%",maxHeight:420,borderRadius:8}}/> : <span style={{color:"#ff4d4f",fontSize:13}}>⚠️ 图片生成失败</span>}
          {rtRes.image.prompt&&<div style={{marginTop:2,fontSize:11,color:"#555",textAlign:"left",wordBreak:"break-all"}}>Prompt: {rtRes.image.prompt}</div>}
        </div>
      </div>}
    </div>}

    {rtRes?.error&&<div style={{padding:12,background:"#fff1f0",borderRadius:10,color:"#ff4d4f",fontSize:13}}>
      ⚠️ {rtRes.error}
    </div>}
    <div ref={endRef}/>
  </div>
}
// ========== 脑风暴功能（完整展开版）==========
const MODES = {
  auto: { label: '自动判断', desc: '根据问题自动选择策略', icon: '🤖' },
  debate: { label: '对抗辩论', desc: '互相反驳、找漏洞', icon: '⚔️' },
  collab: { label: '协作共创', desc: '互相补充、完善', icon: '🤝' },
  mentor: { label: '导师问答', desc: '一问一答', icon: '👨‍🏫' },
  socratic: { label: '苏格拉底', desc: '连环追问', icon: '❓' },
  devil: { label: '魔鬼代言', desc: '专挑毛病', icon: '😈' },
  roleplay: { label: '角色扮演', desc: '模拟场景', icon: '🎭' },
  peer: { label: '同行评审', desc: '学术评议', icon: '📄' },
  case: { label: '案例分析', desc: '实例研讨', icon: '💼' },
  design: { label: '设计思维', desc: '创意发散', icon: '🎨' },
  redteam: { label: '红队演练', desc: '安全攻防', icon: '🛡️' },
  future: { label: '未来推演', desc: '预测趋势', icon: '🔮' },
  random: { label: '随机联想', desc: '跨界思维', icon: '🎲' },
  puzzle: { label: '拼图模式', desc: '拼合观点', icon: '🧩' },
  balance: { label: '利弊权衡', desc: '优缺点分析', icon: '⚖️' },
  global: { label: '全球视角', desc: '跨文化观点', icon: '🌐' },
}

const BrainstormTab = ({q, setQ, agentA, setAgentA, agentB, setAgentB}: any) => {
  const [loading, setLoading] = React.useState(false)
  const [messages, setMessages] = React.useState<any[]>([])
  const [conclusion, setConclusion] = React.useState('')
  const [agents, setAgents] = React.useState<any>(null)
  const [error, setError] = React.useState('')
  const [progress, setProgress] = React.useState('')
  const [rounds, setRounds] = React.useState(10)
  const [mode, setMode] = React.useState('auto')
  const [showBSSettings,setShowBSSettings]=React.useState(false)
  const [bsSettings,setBsSettings]=React.useState({max_tokens:800,timeout_s:300,depth:'normal',knowledge_scope:'full',keyword_block:'',focus:'',image_mode:false})
  const abortRef = React.useRef<AbortController | null>(null)

  React.useEffect(() => {
    window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})
  }, [messages, conclusion])

  const stopStream = () => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null }
    setLoading(false)
  }

  // 从 localStorage 恢复脑风暴状态
  React.useEffect(() => {
    const saved = localStorage.getItem('brainstorm_state')
    if (saved) {
      try {
        const state = JSON.parse(saved)
        if (state.messages) setMessages(state.messages)
        if (state.agents) setAgents(state.agents)
        if (state.conclusion) setConclusion(state.conclusion)
        if (state.q) setQ(state.q)
        if (state.rounds) setRounds(state.rounds)
        if (state.agentA) setAgentA(state.agentA)
        if (state.agentB) setAgentB(state.agentB)
        console.log('[Brainstorm] Restored from localStorage, messages:', state.messages?.length)
      } catch (e) {
        console.error('[Brainstorm] Failed to restore state:', e)
      }
    }
  }, [])

  // 保存状态到 localStorage（只在关键变化时保存，防止 startBrainstorm 中 setMessages([]) 覆盖）
  React.useEffect(() => {
    if (messages.length > 0 || conclusion) {
      const state = { messages, agents, conclusion, q, rounds, agentA, agentB }
      localStorage.setItem('brainstorm_state', JSON.stringify(state))
      console.log('[Brainstorm] Saved state, messages:', messages.length)
    }
  }, [messages, agents, conclusion, q, rounds, agentA, agentB])

  const startBrainstorm = async (isContinue = false) => {
    console.log('[Brainstorm] Starting...', {q, rounds, agentA, agentB, mode, isContinue, totalMsgs: messages.length})
    if (!q.trim()) { console.log('[Brainstorm] Empty question, returning'); return }
    
    // 如果是继续模式，使用历史消息
    const historyMessages = isContinue ? messages.filter(m => m.type === 'agent_a' || m.type === 'agent_b').map(m => ({
      type: m.type,
      data: m.data  // 只发送 data 部分
    })) : []
    console.log('[Brainstorm] History messages:', historyMessages.length, historyMessages.slice(0, 2))
    setMessages([]); setConclusion(''); setAgents(null); setError(''); setProgress('')
    setLoading(true)
    abortRef.current = new AbortController()
    try {
      console.log('[Brainstorm] Sending request...')
      console.log('[Brainstorm] Fetch initiated')
      const endpoint = isContinue ? '/api/actor/brainstorm/continue' : '/api/actor/brainstorm/stream'
      const body = isContinue 
        ? JSON.stringify({question: q, max_rounds: rounds, agent_a: agentA, agent_b: agentB, mode: mode, history: historyMessages, ...bsSettings})
        : JSON.stringify({question: q, max_rounds: rounds, agent_a: agentA, agent_b: agentB, mode: mode, ...bsSettings})
      const response = await fetch(endpoint, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: body,
        signal: abortRef.current.signal
      })
      console.log('[Brainstorm] Response received:', response.status, response.ok)
      if (!response.ok) throw new Error('HTTP ' + response.status)
      const reader = response.body!.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      while (true) {
        const {done, value} = await reader.read()
        if (done) break
        buffer += decoder.decode(value, {stream: true})
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data:')) continue
          const dataStr = line.slice(5).trim()
          if (!dataStr) continue
          try {
            const data = JSON.parse(dataStr)
            if (data.agents) setAgents(data.agents)
            else if (data.type === 'agent_a' || data.type === 'agent_b') {
              setMessages(prev => [...prev, data])
              setProgress('')
            }
            else if (data.type === 'progress') {
              setProgress(data.message || `第${data.round}/${data.max_rounds}轮思考中...`)
            }
            else if (data.type === 'image') {
              // 图片已嵌入 agent 消息的 image_url 中，此处不再重复添加
            }
            else if (data.conclusion) {
              setConclusion(data.conclusion)
              // Auto-save to history
              fetch('/api/actor/crew-save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                  type: 'brainstorm',
                  task: q,
                  status: 'completed',
                  output: conclusion,
                  metadata: {agent_a: agentA, agent_b: agentB, rounds: rounds, messages: messages},
                  duration_s: 0
                })
              }).catch(() => {})
            }
          } catch {}
        }
      }
    } catch (e: any) {
      console.error('[Brainstorm] Error:', e.name, e.message, e)
      if (e.name !== 'AbortError') setError('请求失败: ' + e.message)
    } finally { 
      console.log('[Brainstorm] Finally, loading=false')
      setLoading(false); abortRef.current = null 
    }
  }

  const roles = [
    {k: 'researcher', n: '子墨', e: '🔬'},
    {k: 'analyst', n: '计然', e: '📊'},
    {k: 'strategist', n: '卧龙', e: '🧠'},
    {k: 'finance', n: '陶朱', e: '💰'},
    {k: 'risk', n: '韩非', e: '⚠️'},
    {k: 'investor', n: '白圭', e: '👀'}
  ]

  return (
    <div style={{padding: '0 4px'}}>
      {/* 脑风暴类型选择 */}
      <div style={{display: 'flex', gap: 8, marginBottom: 2, padding: '2px 0', borderBottom: '1px solid #bbb', alignItems: 'center'}}>
        <span style={{fontSize: 13, color: '#666'}}>脑风暴类型:</span>
        <select value={mode} onChange={(e: any) => setMode(e.target.value)}
          style={{padding: '3px 8px', borderRadius: 4, border: '1px solid #bbb', background: '#fff', color: '#555', fontSize: 13, cursor: 'pointer', minWidth: 160}}>
          {Object.entries(MODES).map(([k, v]: [string, any]) => (
            <option key={k} value={k}>{v.icon} {v.label}</option>
          ))}
        </select>
        <span style={{fontSize: 12, color: '#555', marginLeft: 8}}>{MODES[mode as keyof typeof MODES]?.desc}</span>
      </div>
      {/* 紧凑控制栏 - 单行 */}
      <div style={{display: 'flex', gap: 8, alignItems: 'flex-start', padding: '2px 0', borderBottom: '1px solid #bbb', marginBottom: 8}}>
        <select style={{width: 90, padding:'4px 6px', borderRadius: 6, border: '1px solid #bbb', fontSize: 11}} value={agentA} onChange={(e: any) => setAgentA(e.target.value)}>
          <option value="">&#127922; A</option>
          {roles.map(r => <option key={r.k} value={r.k}>{r.e} {r.n}</option>)}
        </select>
        <div style={{padding: '2px 2px', color: '#bbb', fontSize: 11, fontWeight: 500}}>VS</div>
        <select style={{width: 90, padding:'4px 6px', borderRadius: 6, border: '1px solid #bbb', fontSize: 12}} value={agentB} onChange={(e: any) => setAgentB(e.target.value)}>
          <option value="">&#127922; B</option>
          {roles.map(r => <option key={r.k} value={r.k}>{r.e} {r.n}</option>)}
        </select>
        <input type="number" min={1} value={rounds} onChange={(e: any) => setRounds(parseInt(e.target.value) || 10)} style={{width: 70, padding:'4px 6px', borderRadius: 6, border: '1px solid #bbb', fontSize: 13}} title="轮数"/>
        <textarea style={{flex: 1, minHeight: 24, padding: '3px 6px', borderRadius: 4, border: '1px solid #bbb', fontSize: 12, resize: 'none'}} value={q} onChange={(e: any) => setQ(e.target.value)} placeholder="输入辩论话题..." rows={1}/>
        <button type="button" onClick={() => {
          // 检测是否有未完成的会话（有 agent 消息但没有结论）
          const agentMsgs = messages.filter(m => m.type === 'agent_a' || m.type === 'agent_b')
          const hasUnfinishedSession = agentMsgs.length > 0 && !conclusion
          console.log('[Brainstorm] Button click:', {totalMsgs: messages.length, agentMsgs: agentMsgs.length, hasUnfinishedSession, hasConclusion: !!conclusion})
          startBrainstorm(hasUnfinishedSession)
        }} disabled={loading || !q.trim()} style={{padding:'3px 8px', borderRadius: 4, border: 'none', background: loading ? '#bbb' : '#1677ff', color: '#fff', cursor: loading ? 'not-allowed' : 'pointer', fontSize: 13, whiteSpace: 'nowrap'}}>
          {loading ? '进行中...' : '开始'}
        </button>
        {loading && <button type="button" onClick={stopStream} style={{padding: '3px 8px', borderRadius: 4, border: '1px solid #ff4d4f', background: '#fff', color: '#ff4d4f', cursor: 'pointer', fontSize: 13}}>停止</button>}
      </div>

      {/* 高级设置 - 独立折叠面板，避免嵌在顶部 flex 控制栏里 */}
      <div style={{marginBottom:8}}>
        <button type="button" onClick={()=>setShowBSSettings(!showBSSettings)} style={{width:"100%",padding:"5px 8px",borderRadius:6,border:"1px dashed #bbb",background:"#fafafa",cursor:"pointer",fontSize:12,color:"#666",textAlign:"left"}}>{showBSSettings?"▼ ":"▶ "}高级设置</button>
        {showBSSettings&&<div style={{marginTop:4,padding:"8px 10px",background:"#f8f9fb",borderRadius:8,border:"1px solid #e8e8e8",display:"grid",gridTemplateColumns:"repeat(auto-fit, minmax(180px, 1fr))",gap:8}}>
          <label style={{display:"flex",alignItems:"center",gap:6,fontSize:12,color:"#333",padding:"4px 6px",background:"#fff",borderRadius:6,border:"1px solid #e8e8e8"}}>
            <input type="checkbox" checked={!!bsSettings.image_mode} onChange={e=>setBsSettings({...bsSettings,image_mode:e.target.checked})}/>
            🎨 生图模式 <span style={{fontSize:11,color:"#888"}}>默认关闭</span>
          </label>
          <div><label style={{fontSize:10,color:"#666"}}>模式：</label><select value={mode} onChange={e=>setMode(e.target.value)} style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:11,color:"#555"}}><option value="auto">🤖 自动</option><option value="debate">⚔️ 辩论</option><option value="collab">💡 协作</option><option value="critique">⚡ 批判</option><option value="research">🔬 研究</option></select></div>
          <div><label style={{fontSize:10,color:"#666"}}>回答长度(字)：</label><input type="number" min={100} max={2000} step={100} value={bsSettings.max_tokens} onChange={e=>setBsSettings({...bsSettings,max_tokens:parseInt(e.target.value)||500})} style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:11}}/></div>
          <div><label style={{fontSize:10,color:"#666"}}>超时(秒)：</label><input type="number" min={30} max={600} step={30} value={bsSettings.timeout_s} onChange={e=>setBsSettings({...bsSettings,timeout_s:parseInt(e.target.value)||300})} style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:11}}/></div>
          <div><label style={{fontSize:10,color:"#666"}}>知识范围：</label><select value={bsSettings.knowledge_scope} onChange={e=>setBsSettings({...bsSettings,knowledge_scope:e.target.value})} style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:11,color:"#555"}}><option value="full">🌐 全量</option><option value="academic">📚 学术</option><option value="business">💼 商业</option></select></div>
          <div><label style={{fontSize:10,color:"#666"}}>聚焦：</label><input type="text" value={bsSettings.focus} onChange={e=>setBsSettings({...bsSettings,focus:e.target.value})} placeholder="例：只讨论商业可行性" style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:11}}/></div>
          <div><label style={{fontSize:10,color:"#666"}}>过滤：</label><input type="text" value={bsSettings.keyword_block} onChange={e=>setBsSettings({...bsSettings,keyword_block:e.target.value})} placeholder="股价,融资,估值" style={{width:"100%",padding:"3px 6px",borderRadius:4,border:"1px solid #bbb",fontSize:11}}/></div>
        </div>}
      </div>

      {/* 角色显示条 */}
      {agents && (
        <div style={{display: 'flex', gap: 16, padding: '4px 6px', background: '#597ef7', borderRadius: 4, fontSize: 11, marginBottom: 4}}>
          <span>{agents.agent_a.emoji} <b>{agents.agent_a.name}</b></span>
          <span style={{color: '#d9d9d9'}}>VS</span>
          <span>{agents.agent_b.emoji} <b>{agents.agent_b.name}</b></span>
        </div>
      )}

      {/* 空状态 */}
      {messages.length === 0 && !loading && !conclusion && (
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '24px 0', color: '#555'}}>
          <div style={{fontSize: 32, marginBottom: 8}}>&#129504;</div>
          <div style={{fontSize: 13, marginBottom: 4}}>选择两位Agent，开启深度辩论</div>
          <div style={{fontSize: 12, color: '#444'}}>支持：卧龙(战略) vs 计然(分析) 等多种组合</div>
        </div>
      )}

      {/* 消息列表 - 完整展开，无截断 */}
      {messages.map((msg: any, idx: number) => {
        const isA = msg.type === 'agent_a'
        return (
          <div key={idx} style={{marginBottom: 8}}>
            <div style={{padding: '6px 10px', fontSize: 12, fontWeight: 600, color: '#333', background: isA ? '#d9f7be' : '#d6e4ff', borderRadius: '6px 6px 0 0', border: '1px solid ' + (isA ? '#389e0d' : '#597ef7')}}>
              第{msg.round}轮 &middot; {msg.data.emoji} {msg.data.name}
            </div>
            <div style={{border: '1px solid ' + (isA ? '#52c41a' : '#597ef7'), borderTop: 'none', borderRadius: '0 0 8px 8px', padding: 8, background: '#fafafa'}}>
              {msg.type === 'image' ? (
                <div style={{marginBottom: 8}}>
                  <div style={{padding: '5px 10px', fontSize: 12, fontWeight: 600, color: '#333', background: '#d6e4ff', borderRadius: '6px 6px 0 0', border: '1px solid #597ef7'}}>
                    🎨 生成图片
                  </div>
                  <div style={{border: '1px solid #597ef7', borderTop: 'none', borderRadius: '0 0 8px 8px', padding: 8, background: '#fafafa', textAlign: 'center'}}>
                    {msg.data.image?.url ? (
                      <img src={msg.data.image.url} alt={msg.data.image.prompt || msg.data.prompt || '生图'} style={{maxWidth: '100%', maxHeight: 400, borderRadius: 6}} />
                    ) : msg.data.error ? (
                      <div style={{padding: 12, background: '#fff2f0', borderRadius: 6}}>
                        <span style={{color: '#cf1322', fontSize: 13}}>⚠️ {msg.data.error}</span>
                        {(msg.data.image?.prompt || msg.data.prompt) && <div style={{marginTop: 6, fontSize: 11, color: '#555'}}>Prompt: {msg.data.image?.prompt || msg.data.prompt}</div>}
                      </div>
                    ) : (
                      <span style={{color: '#cf1322', fontSize: 13}}>⚠️ 生图失败</span>
                    )}
                    {(msg.data.image?.prompt || msg.data.prompt) && <div style={{marginTop: 8, fontSize: 11, color: '#555'}}>Prompt: {msg.data.image?.prompt || msg.data.prompt}</div>}
                  </div>
                </div>
              ) : msg.data.ok ? (
                <div style={{display: (msg.data.images?.length || msg.data.image_url) ? 'grid' : 'block', gridTemplateColumns: (msg.data.images?.length || msg.data.image_url) ? 'minmax(0, 1.05fr) minmax(260px, 0.95fr)' : undefined, gap: 12, alignItems: 'start'}}>
                  <div style={{margin: 0, fontSize: 12, lineHeight: 1.6, color: '#222', whiteSpace: 'normal'}}>
                    {msg.data.reply ? renderMarkdownWithImages(msg.data.reply) : <span style={{color:'#777'}}>本轮主要输出为右侧配图，文字观点为空。</span>}
                  </div>
                  {(msg.data.images?.length || msg.data.image_url) ? (
                    <div style={{display:'flex', flexDirection:'column', gap:8}}>
                      {(msg.data.images?.length ? msg.data.images : [{url: msg.data.image_url, alt: '配图'}]).map((img:any, ii:number) => (
                        <a key={ii} href={img.url} target="_blank" rel="noopener noreferrer" style={{display:'block', textAlign:'center'}}>
                          <img src={img.url} alt={img.alt || '配图'} style={{maxWidth:'100%', maxHeight:360, borderRadius:8, boxShadow:'0 1px 4px rgba(0,0,0,0.15)', objectFit:'contain', background:'#fff'}} />
                        </a>
                      ))}
                    </div>
                  ) : null}
                </div>
              ) : (
                <span style={{color: '#cf1322', fontSize: 13}}>&#9888;&#65039; {msg.data.error || '请求失败'}</span>
              )}
            </div>
          </div>
        )
      })}

      {/* 加载中 */}
      {loading && messages.length > 0 && <div style={{textAlign: 'center', padding: 16, color: '#444', fontSize: 13}}>{progress || '思考中...'}</div>}

      {/* 综合结论 */}
      {conclusion && (
        <div style={{marginTop: 16, marginBottom: 16}}>
          <div style={{padding: '6px 10px', fontSize: 12, fontWeight: 600, color: '#333', background: '#fff7e6', borderRadius: '6px 6px 0 0', border: '1px solid #fa8c16'}}>&#128221; 综合结论</div>
          <div style={{border: '1px solid #fa8c16', borderTop: 'none', borderRadius: '0 0 8px 8px', padding: '8px 12px', fontSize: 12, whiteSpace: 'pre-wrap', color: '#333', lineHeight: 1.6, background: '#fff', fontFamily: 'inherit'}}>{conclusion}</div>
        </div>
      )}

      {/* 错误 */}
      {error && <div style={{padding: 8, background: '#fff2f0', borderRadius: 6, color: '#ff4d4f', fontSize: 12, marginTop: 6}}>&#9888;&#65039; {error}</div>}
    </div>
  )
}
