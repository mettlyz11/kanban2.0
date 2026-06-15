import React, { useEffect, useState } from 'react'
const SPROUT_API='/api/sprout'

type Garden={id:string;goal:string;scenario?:string;updated_at?:string;leaf_count?:number}

export default function Marketplace(){
  const [gardens,setGardens]=useState<Garden[]>([])
  const [loading,setLoading]=useState(true)
  const [q,setQ]=useState('')
  useEffect(()=>{fetch(SPROUT_API+'/gardens').then(r=>r.json()).then(d=>{setGardens(Array.isArray(d)?d:[]);setLoading(false)}).catch(()=>setLoading(false))},[])
  const featured=[
    {title:'科研管理系统',emoji:'🔬',price:'¥99',desc:'文献库、实验记录、投稿追踪、经费追踪',scenario:'research'},
    {title:'个人财务系统',emoji:'💰',price:'¥29',desc:'记账、分类、预算、报表、告警',scenario:'finance'},
    {title:'公司运营系统',emoji:'🏢',price:'¥199',desc:'客户、销售、项目、人事、财务一体化',scenario:'company'},
  ]
  const filtered=gardens.filter(g=>(g.goal||'').toLowerCase().includes(q.toLowerCase()))
  return <div style={{minHeight:'100vh',background:'#0f172a',color:'#e2e8f0',fontFamily:'system-ui',padding:24}}>
    <div style={{maxWidth:1100,margin:'0 auto'}}>
      <header style={{display:'flex',alignItems:'center',gap:12,marginBottom:32,flexWrap:'wrap'}}>
        <a href='/' style={{color:'#64748b',textDecoration:'none'}}>← 首页</a>
        <h1 style={{fontSize:28,margin:0}}>🌰 种子市场</h1>
        <span style={{color:'#64748b',fontSize:13}}>把养出来的系统卖给别人</span>
        <a href='/grow' style={{marginLeft:'auto',background:'#22c55e',color:'#020617',padding:'8px 14px',borderRadius:8,textDecoration:'none',fontWeight:700}}>养一个</a>
      </header>
      <section style={{background:'linear-gradient(135deg,#14532d,#1e3a8a)',border:'1px solid #334155',borderRadius:16,padding:28,marginBottom:24}}>
        <h2 style={{fontSize:36,margin:'0 0 8px'}}>你的藤，天生就是数字资产</h2>
        <p style={{color:'#cbd5e1',margin:0}}>目标 → 功能叶片 → 可运行系统 → 可导出/可出售种子。</p>
      </section>
      <h2 style={{fontSize:18}}>精选种子</h2>
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(240px,1fr))',gap:14,marginBottom:32}}>
        {featured.map((x,i)=><div key={i} style={{background:'#1e293b',border:'1px solid #334155',borderRadius:14,padding:18}}>
          <div style={{fontSize:36}}>{x.emoji}</div><h3>{x.title}</h3><p style={{color:'#94a3b8',minHeight:44}}>{x.desc}</p>
          <div style={{display:'flex',alignItems:'center',justifyContent:'space-between'}}><b style={{color:'#22c55e',fontSize:24}}>{x.price}</b><a href={'/grow?scenario='+x.scenario} style={{color:'#60a5fa'}}>嫁接 →</a></div>
        </div>)}
      </div>
      <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:12}}><h2 style={{fontSize:18,margin:0}}>我的可出售花园</h2><input value={q} onChange={e=>setQ(e.target.value)} placeholder='搜索花园...' style={{marginLeft:'auto',background:'#020617',border:'1px solid #334155',borderRadius:8,color:'#e2e8f0',padding:'8px 12px'}}/></div>
      {loading?<p style={{color:'#64748b'}}>加载中...</p>:filtered.length===0?<div style={{border:'1px dashed #334155',borderRadius:12,padding:30,textAlign:'center',color:'#64748b'}}>还没有花园。先去 /grow 养一个，再回来上架。</div>:<div style={{display:'grid',gap:10}}>{filtered.map(g=><div key={g.id} style={{background:'#111827',border:'1px solid #334155',borderRadius:10,padding:14,display:'flex',alignItems:'center',gap:12}}><span>🌿</span><div style={{flex:1}}><b>{g.goal}</b><div style={{fontSize:12,color:'#64748b'}}>{g.scenario||'custom'} · {g.leaf_count||0} leaves · {g.updated_at}</div></div><a href={'/grow?id='+g.id} style={{color:'#60a5fa'}}>打开</a><button style={{background:'#22c55e22',border:'1px solid #22c55e55',color:'#22c55e',borderRadius:8,padding:'6px 10px'}}>上架</button></div>)}</div>}
    </div>
  </div>
}
