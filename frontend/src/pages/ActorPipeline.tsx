import React, { useState, useRef, useEffect, useCallback } from "react"
const A = "/api/actor"
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

export default function ActorPipeline() {
  const [tab,setTab]=useState<"run"|"history"|"chat"|"brainstorm">("run")
  const [chatMode,setChatMode]=useState<"single"|"roundtable">("single")
  const [task,setTask]=useState(PRESETS[0].task)
  const [running,setRunning]=useState(false); const [stage,setStage]=useState("")
  const [rawOut,setRawOut]=useState(""); const [result,setResult]=useState<any>(null); const [error,setError]=useState("")
  const [history,setHistory]=useState<Hist[]>([]); const [showId,setShowId]=useState<string|null>(null); const [det,setDet]=useState<any>(null); const [histFilter,setHistFilter]=useState<string|null>(null)
  const [chatRole,setChatRole]=useState("researcher"); const [chatMsgs,setChatMsgs]=useState<{r:string;c:string}[]>([])
  const [chatInput,setChatInput]=useState(""); const [chatLoading,setChatLoading]=useState(false)
  const [rtRoles,setRtRoles]=useState(["researcher","analyst","strategist"]); const [rtQ,setRtQ]=useState("")
  const [rtRes,setRtRes]=useState<any>(null); const [rtLoad,setRtLoad]=useState(false)
  const [rtHist,setRtHist]=useState<RTHist[]>([]); const [rtHistTab,setRtHistTab]=useState(false)
// 脑风暴状态
  const [brainstormQ,setBrainstormQ]=useState("")
  const [brainstormAgentA,setBrainstormAgentA]=useState("")
  const [brainstormAgentB,setBrainstormAgentB]=useState("")
  const [brainstormRes,setBrainstormRes]=useState<any>(null)
  const [brainstormLoad,setBrainstormLoad]=useState(false)
  // 使用 ref 跟踪最新消息，避免闭包过期
  const chatMsgsRef=useRef(chatMsgs)
  useEffect(()=>{chatMsgsRef.current=chatMsgs},[chatMsgs])
  const pr=useRef<ReturnType<typeof setInterval>>(); const st=useRef(0); const ld=useRef(false)
  const lh=useCallback(async()=>{try{const r=await fetch(A+"/crew-history");const d=await r.json();if(d.ok)setHistory(d.history||[])}catch{}},[])
  const lrt=useCallback(async()=>{try{const r=await fetch(A+"/roundtable-history");const d=await r.json();if(d.ok)setRtHist(d.history||[])}catch{}},[])
  useEffect(()=>{if(!ld.current){ld.current=true;lh();lrt()}},[])
  useEffect(()=>()=>clearInterval(pr.current),[])
  const sr=async()=>{setRunning(true);setStage("启动中");setRawOut("");setResult(null);setError("");st.current=Date.now()
    try{const r=await fetch(A+"/crew-run",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task})});const d=await r.json();if(d.error){setStage("启动失败");setError(d.error);setRunning(false);return}
    pr.current=setInterval(async()=>{try{const sr=await fetch(A+"/crew-status");const sd=await sr.json();setStage(sd.stage||"运行中");if(sd.output)setRawOut(sd.output);if(["completed","failed","timeout","cancelled","error"].includes(sd.status)){clearInterval(pr.current);const fs=sd.status==="completed"?"完成":sd.status==="cancelled"?"已取消":sd.status;setStage(fs);setRawOut(sd.output||(sd.error||""));setResult(sd);setRunning(false);try{await fetch(A+"/crew-save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({task,status:sd.status,output:(sd.output||"")?.slice(0,2000),duration_s:Math.round((Date.now()-st.current)/1000)})});lh()}catch{}}}catch{}},3000)}catch(e:any){setStage("网络错误");setError(e.message);setRunning(false)}}
  const cr=async()=>{clearInterval(pr.current);try{await fetch(A+"/crew-cancel",{method:"POST"})}catch{};setRunning(false);setStage("已取消")}
  const ldDet=async(id:string)=>{setShowId(id);setDet(null);try{const r=await fetch(A+"/crew-history/"+id);const d=await r.json();if(d.ok)setDet(d.entry)}catch{}}
  const sc=async()=>{
    if(!chatInput.trim()||chatLoading)return
    const m=chatInput;setChatInput("")
    // ✅ 用 ref 获取最新消息列表，避免闭包过期导致消息丢失
    const msgs=[...chatMsgsRef.current,{r:"user",c:m}]
    setChatMsgs(msgs)
    setChatLoading(true)
    try{
      const r=await fetch(A+"/chat",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          messages:msgs.map(({r,c})=>({role:r,content:c})),
          role:chatRole,
          knowledge_scope:chatRole==="researcher"?"academic":chatRole==="analyst"||chatRole==="finance"||chatRole==="investor"?"business":"full",
          max_tokens:2000
        })
      })
      const d=await r.json()
      if(d.ok){
        setChatMsgs(p=>[...p,{r:"assistant",c:d.reply}])
      }else{
        setChatMsgs(p=>[...p,{r:"error",c:"⚠️ "+(d.error||"请求失败")}])
      }
    }catch(e:any){
      setChatMsgs(p=>[...p,{r:"error",c:"⚠️ 网络错误: "+(e.message||"")}])
    }
    setChatLoading(false)
  }
  const runBrainstorm=async()=>{
    if(!brainstormQ.trim()||brainstormLoad)return
    setBrainstormRes(null)
    setBrainstormLoad(true)
    const ac=new AbortController()
    const tt=setTimeout(()=>ac.abort(),600000)
    try{
      const r=await fetch(A+"/brainstorm",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({
          question:brainstormQ,
          max_rounds:2,
          agent_a:brainstormAgentA,
          agent_b:brainstormAgentB
        }),
        signal:ac.signal
      })
      clearTimeout(tt)
      const d=await r.json()
      if(d.ok){setBrainstormRes(d)}else{setBrainstormRes({error:d.error||"请求失败"})}
    }catch(e:any){
      setBrainstormRes({error:e.name==="AbortError"?"请求超时(>10分钟)，请重试":"网络错误: "+(e.message||"未知错误")})
    }finally{
      clearTimeout(tt)
      setBrainstormLoad(false)
    }
  }
  const rr=async()=>{
    if(!rtQ.trim()||rtLoad)return
    setRtRes(null)
    setRtLoad(true)
    const ac=new AbortController()
    const tt=setTimeout(()=>ac.abort(),600000)
    try{
      const r=await fetch(A+"/roundtable",{
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body:JSON.stringify({question:rtQ,roles:rtRoles,max_rounds:3}),
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
  return <div style={{maxWidth:960,margin:"0 auto",padding:"16px 24px"}}>
    <div style={{display:"flex",gap:0,marginBottom:16,borderBottom:"1px solid #e8e8e8"}}>
      {[{k:"run",l:"🤖 管道"},{k:"brainstorm",l:"🧠 脑风暴"},{k:"chat",l:"💬 对话"},{k:"history",l:"📜 历史"}].map(t=><button key={t.k} onClick={()=>setTab(t.k as any)} style={{padding:"8px 20px",border:"none",background:tab===t.k?"#fff":"transparent",borderBottom:tab===t.k?"2px solid #1677ff":"2px solid transparent",cursor:"pointer",fontSize:14,color:tab===t.k?"#1677ff":"#888",fontWeight:tab===t.k?500:400}}>{t.l}</button>)}
    </div>
    {tab==="run"&&<RunTab task={task} setTask={setTask} running={running} stage={stage} rawOut={rawOut} result={result} error={error} pct={pct} onStart={sr} onCancel={cr}/>}
    {tab==="history"&&<div>
      <div style={{display:"flex",gap:12,marginBottom:12}}>
        <button onClick={()=>setRtHistTab(false)} style={{padding:"6px 18px",borderRadius:20,border:"none",background:!rtHistTab?"#1677ff":"#f0f0f0",color:!rtHistTab?"#fff":"#555",cursor:"pointer",fontSize:13}}>管道历史</button>
        <button onClick={()=>{setRtHistTab(true);lrt()}} style={{padding:"6px 18px",borderRadius:20,border:"none",background:rtHistTab?"#1677ff":"#f0f0f0",color:rtHistTab?"#fff":"#555",cursor:"pointer",fontSize:13}}>圆桌历史({rtHist.length})</button>
      </div>
      {rtHistTab?<RtHisTab history={rtHist}/>:<HisTab history={history} showId={showId} detail={det} onLoad={ldDet}/>}
    </div>}
{tab==="brainstorm"&&<BrainstormTab q={brainstormQ} setQ={setBrainstormQ} agentA={brainstormAgentA} setAgentA={setBrainstormAgentA} agentB={brainstormAgentB} setAgentB={setBrainstormAgentB}/>}
    {tab==="chat"&&<div>
      <div style={{display:"flex",gap:12,marginBottom:12}}>
        <button onClick={()=>setChatMode("single")} style={{padding:"6px 18px",borderRadius:20,border:"none",background:chatMode==="single"?"#1677ff":"#f0f0f0",color:chatMode==="single"?"#fff":"#555",cursor:"pointer",fontSize:13}}>单聊</button>
        <button onClick={()=>setChatMode("roundtable")} style={{padding:"6px 18px",borderRadius:20,border:"none",background:chatMode==="roundtable"?"#1677ff":"#f0f0f0",color:chatMode==="roundtable"?"#fff":"#555",cursor:"pointer",fontSize:13}}>圆桌讨论</button>
      </div>
      {chatMode==="single"&&<ChatSingle role={chatRole} setRole={setChatRole} msgs={chatMsgs} setMsgs={setChatMsgs} input={chatInput} setInput={setChatInput} loading={chatLoading} send={sc}/>}
      {chatMode==="roundtable"&&<RtTab rtRoles={rtRoles} setRtRoles={setRtRoles} rtQ={rtQ} setRtQ={setRtQ} rtRes={rtRes} rtLoad={rtLoad} onRun={rr}/>}
    </div>}
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
  const col:any={r:["#e6f4ff","#1677ff"],d:["#f6ffed","#52c41a"],p:["#fafafa","#d9d9d9"],i:["#fafafa","#f0f0f0"]}
  return <div>
    <div><span style={{fontSize:12,color:"#aaa"}}>快速开始：</span>
      {PRESETS.map((p,i)=><button key={i} onClick={()=>setTask(p.task)} style={{margin:"2px 4px",padding:"4px 12px",borderRadius:14,border:task===p.task?"2px solid #1677ff":"1px solid #d9d9d9",background:task===p.task?"#e6f4ff":"#fff",fontSize:12,cursor:"pointer",color:task===p.task?"#1677ff":"#555"}}>{p.label}</button>)}
    </div>
    {m.length>0&&!running&&<div style={{marginBottom:8,padding:"6px 12px",background:"#fffbe6",borderRadius:8,border:"1px solid #ffe58f",fontSize:12,color:"#ad8b00"}}>找到{m.length}条相似历史</div>}
    <textarea style={{width:"100%",minHeight:60,padding:"10px 12px",borderRadius:10,border:"1px solid #d9d9d9",fontSize:14,resize:"vertical",boxSizing:"border-box"}} value={task} onChange={e=>setTask(e.target.value)} placeholder="描述任务..." />
    <div style={{display:"flex",gap:8}}>
      <button onClick={onStart} disabled={running||!task.trim()} style={{padding:"10px 28px",fontSize:15,borderRadius:24,border:"none",background:running?"#bbb":"#1677ff",color:"#fff",cursor:running?"not-allowed":"pointer",fontWeight:500}}>
        {running?"运行中":"开始分析"}</button>
      {running&&<button onClick={onCancel} style={{padding:"10px 18px",fontSize:14,borderRadius:24,border:"1px solid #ff4d4f",color:"#ff4d4f",cursor:"pointer",background:"#fff"}}>取消</button>}
    </div>
    {(running||result)&&<div style={{background:"#f8f9fb",borderRadius:14,padding:"12px 16px",marginTop:4}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:8,fontSize:13}}>
        <span style={{color:running?"#1677ff":"#52c41a",fontWeight:500}}>{running?""+stage:result?.status==="completed"?"完成":""+stage}</span>
        <span style={{color:"#aaa"}}>~3-6分钟</span>
      </div>
      <div style={{height:5,background:"#e8e8e8",borderRadius:3,marginBottom:12,overflow:"hidden"}}>
        <div style={{height:"100%",width:pct+"%",background:"linear-gradient(90deg,#1677ff,#52c41a)",borderRadius:3,transition:"width 0.8s ease"}}/></div>
      <div style={{display:"flex",gap:8}}>{steps.map((s,i)=>{const[bg,c]=col[s.s]||["#fafafa","#d9d9d9"];return <div key={i} style={{flex:1,padding:"8px 10px",borderRadius:10,background:bg,border:"1px solid "+(s.s==="r"?"#1677ff":"#e8e8e8")}}><div style={{fontSize:18}}>{s.e}</div><div style={{fontSize:11,fontWeight:500,color:c}}>{s.l}</div><div style={{fontSize:10,color:s.s==="r"?"#1677ff":s.s==="d"?"#52c41a":"#ccc"}}>{s.s==="r"?"工作中":s.s==="d"?"完成":"—"}</div></div>})}</div>
      {rawOut&&<pre style={{marginTop:10,padding:10,background:"#1e1e1e",color:"#d4d4d4",borderRadius:8,fontSize:11,maxHeight:200,overflow:"auto",whiteSpace:"pre-wrap"}}>{rawOut.slice(-3000)}</pre>}
    </div>}
    {error&&<div style={{marginTop:8,padding:8,background:"#fff2f0",borderRadius:8,color:"#ff4d4f",fontSize:12}}>错误: {error}</div>}
  </div>
}

function HisTab({history,showId,detail,onLoad,typeFilter,setTypeFilter}:any){
  const typeLabels: Record<string,string> = {crew: '🤖 管道', brainstorm: '🧠 脑风暴', chat: '💬 单聊', roundtable: '🏯 圆桌'}
  const filtered = typeFilter ? history.filter((x:any)=>x.type===typeFilter) : history
  return <div>
    <div style={{display:'flex',gap:8,marginBottom:12,padding:'8px 0',borderBottom:'1px solid #e8e8e8'}}>
      <button onClick={()=>setTypeFilter(null)} style={{padding:'4px 12px',borderRadius:12,border:'1px solid',borderColor:typeFilter?'#d9d9d9':'#1677ff',background:typeFilter?'#fff':'#e6f4ff',color:typeFilter?'#555':'#1677ff',fontSize:12,cursor:'pointer'}}>全部</button>
      {['crew','brainstorm','chat','roundtable'].map(t=><button key={t} onClick={()=>setTypeFilter(t)} style={{padding:'4px 12px',borderRadius:12,border:'1px solid',borderColor:typeFilter===t?'#1677ff':'#d9d9d9',background:typeFilter===t?'#e6f4ff':'#fff',color:typeFilter===t?'#1677ff':'#555',fontSize:12,cursor:'pointer'}}>{typeLabels[t]}</button>)}
    </div>
    {filtered.length===0?<div style={{padding:20,textAlign:"center",color:"#bbb"}}>还没有运行记录</div>:
      <div style={{display:"flex",flexDirection:"column",gap:6}}>{filtered.map((x:any)=><div key={x.id} style={{padding:"8px 12px",borderRadius:8,background:"#f8f9fb",border:"1px solid #f0f0f0",cursor:"pointer"}} onClick={()=>onLoad(x.id)}>
        <div style={{fontSize:12,color:'#888',marginBottom:2}}>{typeLabels[x.type] || x.type}</div>
        <div style={{fontSize:13}}>{x.task?.slice(0,60)}</div>
        <div style={{fontSize:11,color:"#aaa",marginTop:2}}>{x.created_at} - {x.status} - {x.duration_s}s</div>
      </div>)}</div>}
    {showId&&<div style={{marginTop:12,padding:"10px 14px",background:"#f6f8fa",borderRadius:10}}>
      <div style={{display:"flex",justifyContent:"space-between",marginBottom:8}}><b>{detail?.task||""}</b><span style={{fontSize:12,color:"#aaa"}}>{detail?.created_at}</span></div>
      <pre style={{fontSize:11,maxHeight:400,overflow:"auto",whiteSpace:"pre-wrap",background:"#1e1e1e",color:"#d4d4d4",padding:10,borderRadius:8}}>{detail?.output||"无详细输出"}</pre>
    </div>}
  </div>
}

function RtHisTab({history}:{history:RTHist[]}){
  return <div>
    {history.length===0?<div style={{padding:20,textAlign:"center",color:"#bbb"}}>还没有圆桌讨论记录</div>:
      <div style={{display:"flex",flexDirection:"column",gap:6}}>{history.map((x,i)=><div key={i} style={{padding:"8px 12px",borderRadius:8,background:"#f8f9fb",border:"1px solid #f0f0f0"}}>
        <div style={{display:"flex",alignItems:"center",gap:6}}>
          <span>{x.consensus?"✅":"❌"}</span>
          <span style={{fontSize:13}}>{x.question.slice(0,80)}</span>
        </div>
        <div style={{fontSize:11,color:"#aaa",marginTop:2}}>
          {x.timestamp} | {x.participants.join("、")} | {x.round_count}轮讨论
        </div>
      </div>)}</div>}
  </div>
}

function ChatSingle({role,setRole,msgs,setMsgs,input,setInput,loading,send}:any){
  const endRef=useRef<HTMLDivElement>(null)
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:"smooth"})},[msgs])
  return <div>
    <div style={{marginBottom:12}}><b style={{fontSize:14}}>选择专家：</b>
      <div style={{display:"flex",flexWrap:"wrap",gap:4,marginTop:6}}>{RK.map(k=>{const r=R6[k];return<button key={k} onClick={()=>{setRole(k);setMsgs([])}} style={{padding:"5px 14px",borderRadius:20,border:"1px solid",borderColor:role===k?"#1677ff":"#d9d9d9",background:role===k?"#e6f4ff":"#fff",color:role===k?"#1677ff":"#555",fontSize:12,cursor:"pointer"}}>{r.e} {r.n}</button>})}
    </div></div>
    <div style={{border:"1px solid #e8e8e8",borderRadius:12,overflow:"hidden",marginBottom:8}}>
      <div style={{padding:"8px 14px",background:"#f5f7fa",fontSize:12,color:"#888",borderBottom:"1px solid #e8e8e8"}}>{R6[role]?.e} {R6[role]?.n} - {R6[role]?.d}</div>
      <div style={{minHeight:200,maxHeight:400,overflow:"auto",padding:12}}>
        {msgs.length===0&&<div style={{color:"#bbb",textAlign:"center",padding:20,fontSize:13}}>开始对话...</div>}
        {msgs.map((m:any,i:number)=><div key={i} style={{display:"flex",marginBottom:8,justifyContent:m.r==="user"?"flex-end":"flex-start"}}>
          <div style={{maxWidth:"80%",padding:"6px 12px",borderRadius:m.r==="user"?"12px 12px 4px 12px":"12px 12px 12px 4px",background:m.r==="user"?"#1677ff":"#f0f0f0",color:m.r==="user"?"#fff":"#333",fontSize:13,whiteSpace:"pre-wrap"}}>{m.c}</div>
        </div>)}
        {loading&&<div style={{textAlign:"center",color:"#aaa",fontSize:12}}>思考中...</div>}
      </div>
      <div style={{borderTop:"1px solid #e8e8e8",display:"flex",padding:8,gap:8}}>
        <input style={{flex:1,padding:"8px 12px",borderRadius:20,border:"1px solid #d9d9d9",fontSize:13,outline:"none"}} value={input} onChange={e=>setInput(e.target.value)} onKeyDown={e=>e.key==="Enter"&&send()} placeholder="输入问题..." />
        <button onClick={send} disabled={loading||!input.trim()} style={{padding:"8px 14px",borderRadius:20,border:"none",background:loading?"#bbb":"#1677ff",color:"#fff",cursor:loading?"not-allowed":"pointer",fontSize:13}}>{loading?"...":"发送"}</button>
      </div>
    </div>
  </div>
}

function RtTab({rtRoles,setRtRoles,rtQ,setRtQ,rtRes,rtLoad,onRun}:any){
  const endRef=useRef<HTMLDivElement>(null)
  useEffect(()=>{endRef.current?.scrollIntoView({behavior:"smooth"})},[rtRes])
  const toggle=(k:string)=>setRtRoles(rtRoles.includes(k)?rtRoles.filter((x:string)=>x!==k):[...rtRoles,k])

  const renderRound = (rd:any[], ri:number) => {
    return <div key={ri} style={{marginBottom:12}}>
      <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#f0f5ff",borderRadius:"8px 8px 0 0",border:"1px solid #d6e4ff"}}>
        🏯 第{ri+1}轮讨论
      </div>
      <div style={{border:"1px solid #d6e4ff",borderTop:"none",borderRadius:"0 0 8px 8px",padding:8}}>
        {rd.map((r:any,i:number)=>{
          const roleInfo = R6[r.role]
          return <div key={i} style={{display:"flex",gap:10,padding:"6px 0",borderBottom:i<rd.length-1?"1px solid #f0f0f0":"none"}}>
            <div style={{minWidth:70,textAlign:"right",fontSize:12,color:"#888"}}>
              <span>{roleInfo?.e||r.emoji||"🤖"}</span>
              <br/><span style={{fontWeight:500,color:"#555",fontSize:13}}>{roleInfo?.n||r.name||r.role}</span>
            </div>
            <div style={{flex:1}}>
              {r.ok===false
                ? <span style={{color:"#ff4d4f",fontSize:12}}>⚠️ {r.error||"请求失败"}</span>
                : <pre style={{margin:0,fontSize:12,whiteSpace:"pre-wrap",lineHeight:1.5}}>{r.reply||"无回复"}</pre>
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
    return <div style={{marginBottom:12}}>
      <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#fff7e6",borderRadius:"8px 8px 0 0",border:"1px solid #ffd591"}}>
        🗳️ 投票结果
      </div>
      <div style={{border:"1px solid #ffd591",borderTop:"none",borderRadius:"0 0 8px 8px",padding:12}}>
        <div style={{display:"flex",gap:16,marginBottom:12}}>
          <div style={{textAlign:"center",flex:1,padding:"8px 12px",background:"#f6ffed",borderRadius:10}}>
            <div style={{fontSize:24,fontWeight:700,color:"#52c41a"}}>{summary['支持']||0}</div>
            <div style={{fontSize:11,color:"#888"}}>支持</div>
          </div>
          <div style={{textAlign:"center",flex:1,padding:"8px 12px",background:"#fff2f0",borderRadius:10}}>
            <div style={{fontSize:24,fontWeight:700,color:"#ff4d4f"}}>{summary['反对']||0}</div>
            <div style={{fontSize:11,color:"#888"}}>反对</div>
          </div>
          <div style={{textAlign:"center",flex:1,padding:"8px 12px",background:"#fafafa",borderRadius:10}}>
            <div style={{fontSize:24,fontWeight:700,color:"#aaa"}}>{summary['弃权']||0}</div>
            <div style={{fontSize:11,color:"#888"}}>弃权</div>
          </div>
        </div>
        {details?.map((v:any,i:number)=>{
          const roleInfo = R6[v.role]
          const stanceColor = v.stance==='支持'?'#52c41a':v.stance==='反对'?'#ff4d4f':'#aaa'
          return <div key={i} style={{display:"flex",gap:8,padding:"4px 0",alignItems:"center"}}>
            <span>{roleInfo?.e||v.emoji||"🤖"}</span>
            <span style={{fontSize:13,fontWeight:500,width:50}}>{roleInfo?.n||v.name||v.role}</span>
            <span style={{fontSize:12,fontWeight:600,color:stanceColor}}>{v.stance}</span>
            {v.reason&&<span style={{fontSize:11,color:"#888",overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap",maxWidth:300}}>— {v.reason.slice(0,60)}</span>}
          </div>
        })}
      </div>
    </div>
  }

  return <div>
    <div style={{marginBottom:12}}><b style={{fontSize:14}}>选择参与专家：</b>
      <div style={{display:"flex",flexWrap:"wrap",gap:4,marginTop:6,marginBottom:6}}>
        {RK.map(k=>{const r=R6[k];const sel=rtRoles.includes(k);return<button key={k} onClick={()=>toggle(k)} style={{padding:"5px 14px",borderRadius:20,border:"1px solid",borderColor:sel?"#1677ff":"#d9d9d9",background:sel?"#e6f4ff":"#fff",color:sel?"#1677ff":"#555",fontSize:12,cursor:"pointer"}}>{r.e} {r.n} {sel?"✓":"+"}</button>})}
      </div>
      <div style={{fontSize:11,color:"#888",display:"flex",alignItems:"center",gap:4}}>
        <span>👴 {MODERATOR.n}（主持人）</span>
        <span style={{color:"#d9d9d9"}}>|</span>
        <span>自动引导讨论，判断共识，组织投票</span>
      </div>
    </div>
    <textarea style={{width:"100%",minHeight:50,padding:"8px 12px",borderRadius:10,border:"1px solid #d9d9d9",fontSize:13,resize:"vertical",boxSizing:"border-box"}} value={rtQ} onChange={e=>setRtQ(e.target.value)} placeholder="输入问题..." />
    <div style={{margin:"8px 0"}}>
      <button onClick={onRun} disabled={rtLoad||!rtQ.trim()||rtRoles.length===0} style={{padding:"8px 24px",borderRadius:20,border:"none",background:rtLoad||rtRoles.length===0?"#bbb":"#1677ff",color:"#fff",cursor:rtLoad||rtRoles.length===0?"not-allowed":"pointer",fontSize:13}}>
        {rtLoad?"圆桌讨论中...":"开始圆桌讨论"}</button>
    </div>

    {rtLoad&&<div style={{textAlign:"center",color:"#aaa",fontSize:12,padding:16}}>
      <div>👴 孔子主持：各位专家请就座...</div>
      <div style={{marginTop:4}}>等待各位专家回复...（可能需要60-300秒）</div>
      <div style={{marginTop:8,display:"flex",justifyContent:"center",gap:4}}>
        {rtRoles.map((k:string)=><span key={k} style={{padding:"2px 8px",background:"#f0f0f0",borderRadius:10,fontSize:11}}>{R6[k]?.e||""} {R6[k]?.n||k}</span>)}
      </div>
    </div>}

    {rtRes?.rounds?.length>0&&<div>
      {rtRes.consensus
        ? <div style={{padding:"10px 14px",background:"#f6ffed",border:"1px solid #b7eb8f",borderRadius:10,marginBottom:12,display:"flex",alignItems:"center",gap:6}}>
            <span style={{fontSize:18}}>✅</span>
            <span style={{fontSize:14,fontWeight:500,color:"#52c41a"}}>各位已达成共识！</span>
          </div>
        : rtRes.vote_result
        ? <div style={{padding:"10px 14px",background:"#fff7e6",border:"1px solid #ffd591",borderRadius:10,marginBottom:12,display:"flex",alignItems:"center",gap:6}}>
            <span style={{fontSize:18}}>🗳️</span>
            <span style={{fontSize:14,fontWeight:500,color:"#d46b08"}}>已达{rtRes.rounds.length}轮上限，进入投票环节</span>
          </div>
        : null}

      {rtRes.moderator_reasoning&&<div style={{marginBottom:12}}>
        <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#fffbe6",borderRadius:"8px 8px 0 0",border:"1px solid #ffe58f"}}>
          👴 孔子主持点评
        </div>
        <div style={{border:"1px solid #ffe58f",borderTop:"none",borderRadius:"0 0 8px 8px",padding:"8px 12px",fontSize:12,whiteSpace:"pre-wrap",color:"#666"}}>
          {rtRes.moderator_reasoning}
        </div>
      </div>}

      {rtRes.rounds.map((rd:any,ri:number)=>renderRound(rd,ri))}

      {rtRes.vote_result&&renderVote(rtRes.vote_result)}

      {rtRes.final_report&&<div style={{marginBottom:12}}>
        <div style={{padding:"6px 12px",fontSize:13,fontWeight:600,color:"#555",background:"#f0f5ff",borderRadius:"8px 8px 0 0",border:"1px solid #adc6ff"}}>
          📋 最终报告
        </div>
        <div style={{border:"1px solid #adc6ff",borderTop:"none",borderRadius:"0 0 8px 8px",padding:"8px 12px",fontSize:12,whiteSpace:"pre-wrap",color:"#333",lineHeight:1.6}}>
          {rtRes.final_report}
        </div>
      </div>}
    </div>}

    {rtRes?.error&&<div style={{padding:12,background:"#fff2f0",borderRadius:10,color:"#ff4d4f",fontSize:13}}>
      ⚠️ {rtRes.error}
    </div>}
    <div ref={endRef}/>
  </div>
}
// ========== 脑风暴功能（完整展开版）==========
const BrainstormTab = ({q, setQ, agentA, setAgentA, agentB, setAgentB}: any) => {
  const [loading, setLoading] = React.useState(false)
  const [messages, setMessages] = React.useState<any[]>([])
  const [conclusion, setConclusion] = React.useState('')
  const [agents, setAgents] = React.useState<any>(null)
  const [error, setError] = React.useState('')
  const [rounds, setRounds] = React.useState(10)
  const abortRef = React.useRef<AbortController | null>(null)

  React.useEffect(() => {
    window.scrollTo({top: document.body.scrollHeight, behavior: 'smooth'})
  }, [messages, conclusion])

  const stopStream = () => {
    if (abortRef.current) { abortRef.current.abort(); abortRef.current = null }
    setLoading(false)
  }

  const startBrainstorm = async () => {
    if (!q.trim()) return
    setMessages([]); setConclusion(''); setAgents(null); setError('')
    setLoading(true)
    abortRef.current = new AbortController()
    try {
      const response = await fetch('/api/actor/brainstorm/stream', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({question: q, max_rounds: rounds, agent_a: agentA, agent_b: agentB}),
        signal: abortRef.current.signal
      })
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
      if (e.name !== 'AbortError') setError('请求失败: ' + e.message)
    } finally { setLoading(false); abortRef.current = null }
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
      {/* 紧凑控制栏 - 单行 */}
      <div style={{display: 'flex', gap: 8, alignItems: 'flex-start', padding: '8px 0', borderBottom: '1px solid #e8e8e8', marginBottom: 12}}>
        <select style={{width: 90, padding: '6px 8px', borderRadius: 6, border: '1px solid #d9d9d9', fontSize: 12}} value={agentA} onChange={(e: any) => setAgentA(e.target.value)}>
          <option value="">&#127922; A</option>
          {roles.map(r => <option key={r.k} value={r.k}>{r.e} {r.n}</option>)}
        </select>
        <div style={{padding: '6px 4px', color: '#d9d9d9', fontSize: 12, fontWeight: 500}}>VS</div>
        <select style={{width: 90, padding: '6px 8px', borderRadius: 6, border: '1px solid #d9d9d9', fontSize: 12}} value={agentB} onChange={(e: any) => setAgentB(e.target.value)}>
          <option value="">&#127922; B</option>
          {roles.map(r => <option key={r.k} value={r.k}>{r.e} {r.n}</option>)}
        </select>
        <input type="number" min={1} value={rounds} onChange={(e: any) => setRounds(parseInt(e.target.value) || 10)} style={{width: 70, padding: '6px 8px', borderRadius: 6, border: '1px solid #d9d9d9', fontSize: 13}} title="轮数"/>
        <textarea style={{flex: 1, minHeight: 32, padding: '6px 10px', borderRadius: 6, border: '1px solid #d9d9d9', fontSize: 13, resize: 'none'}} value={q} onChange={(e: any) => setQ(e.target.value)} placeholder="输入辩论话题..." rows={1}/>
        <button onClick={startBrainstorm} disabled={loading || !q.trim()} style={{padding: '6px 16px', borderRadius: 6, border: 'none', background: loading ? '#bbb' : '#1677ff', color: '#fff', cursor: loading ? 'not-allowed' : 'pointer', fontSize: 13, whiteSpace: 'nowrap'}}>
          {loading ? '进行中...' : '开始'}
        </button>
        {loading && <button onClick={stopStream} style={{padding: '6px 12px', borderRadius: 6, border: '1px solid #ff4d4f', background: '#fff', color: '#ff4d4f', cursor: 'pointer', fontSize: 13}}>停止</button>}
      </div>

      {/* 角色显示条 */}
      {agents && (
        <div style={{display: 'flex', gap: 16, padding: '8px 12px', background: '#f0f5ff', borderRadius: 6, fontSize: 12, marginBottom: 12}}>
          <span>{agents.agent_a.emoji} <b>{agents.agent_a.name}</b></span>
          <span style={{color: '#d9d9d9'}}>VS</span>
          <span>{agents.agent_b.emoji} <b>{agents.agent_b.name}</b></span>
        </div>
      )}

      {/* 空状态 */}
      {messages.length === 0 && !loading && !conclusion && (
        <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '60px 0', color: '#bbb'}}>
          <div style={{fontSize: 48, marginBottom: 16}}>&#129504;</div>
          <div style={{fontSize: 14, marginBottom: 8}}>选择两位Agent，开启深度辩论</div>
          <div style={{fontSize: 12, color: '#aaa'}}>支持：卧龙(战略) vs 计然(分析) 等多种组合</div>
        </div>
      )}

      {/* 消息列表 - 完整展开，无截断 */}
      {messages.map((msg: any, idx: number) => {
        const isA = msg.type === 'agent_a'
        return (
          <div key={idx} style={{marginBottom: 12}}>
            <div style={{padding: '10px 14px', fontSize: 13, fontWeight: 600, color: '#555', background: isA ? '#f6ffed' : '#e6f4ff', borderRadius: '8px 8px 0 0', border: '1px solid ' + (isA ? '#b7eb8f' : '#adc6ff')}}>
              第{msg.round}轮 &middot; {msg.data.emoji} {msg.data.name}
            </div>
            <div style={{border: '1px solid ' + (isA ? '#b7eb8f' : '#adc6ff'), borderTop: 'none', borderRadius: '0 0 8px 8px', padding: 14, background: '#fff'}}>
              {msg.data.ok ? (
                <pre style={{margin: 0, fontSize: 13, whiteSpace: 'pre-wrap', lineHeight: 1.6, color: '#333', fontFamily: 'inherit'}}>{msg.data.reply}</pre>
              ) : (
                <span style={{color: '#ff4d4f', fontSize: 13}}>&#9888;&#65039; {msg.data.error || '请求失败'}</span>
              )}
            </div>
          </div>
        )
      })}

      {/* 加载中 */}
      {loading && messages.length > 0 && <div style={{textAlign: 'center', padding: 16, color: '#aaa', fontSize: 13}}>思考中...</div>}

      {/* 综合结论 */}
      {conclusion && (
        <div style={{marginTop: 16, marginBottom: 16}}>
          <div style={{padding: '10px 14px', fontSize: 13, fontWeight: 600, color: '#555', background: '#fff7e6', borderRadius: '8px 8px 0 0', border: '1px solid #ffd591'}}>&#128221; 综合结论</div>
          <div style={{border: '1px solid #ffd591', borderTop: 'none', borderRadius: '0 0 8px 8px', padding: '14px 16px', fontSize: 13, whiteSpace: 'pre-wrap', color: '#333', lineHeight: 1.7, background: '#fff', fontFamily: 'inherit'}}>{conclusion}</div>
        </div>
      )}

      {/* 错误 */}
      {error && <div style={{padding: 12, background: '#fff2f0', borderRadius: 8, color: '#ff4d4f', fontSize: 13, marginTop: 12}}>&#9888;&#65039; {error}</div>}
    </div>
  )
}
