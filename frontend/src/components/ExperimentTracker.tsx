import React, { useState } from 'react'
export default function ExperimentTracker({leaves}:{leaves:any[]}){
  const exps=leaves.filter(l=>l.id?.includes('exp')||l.name?.includes('实验'))
  const [filter,setFilter]=useState('all')
  return <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:12,padding:16}}>
    <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:12}}>
      <h3 style={{margin:0}}>🧪 实验记录</h3>
      <select value={filter} onChange={e=>setFilter(e.target.value)} style={{background:'#0f172a',border:'1px solid #334155',borderRadius:6,color:'#e2e8f0',padding:'4px 8px'}}>
        <option value="all">全部</option><option value="running">进行中</option><option value="done">已完成</option>
      </select>
    </div>
    <div style={{display:'grid',gap:8}}>
      {exps.length===0?<div style={{color:'#64748b',padding:20,textAlign:'center'}}>暂无实验记录。添加第一个实验。</div>:exps.map((e,i)=><div key={i} style={{padding:12,background:'#0f172a',borderRadius:8,borderLeft:'4px solid #22c55e'}}>
        <div style={{display:'flex',justifyContent:'space-between'}}><b>{e.name}</b><span style={{color:'#64748b',fontSize:11}}>{e.status||'draft'}</span></div>
        <div style={{fontSize:12,color:'#94a3b8',marginTop:4}}>{e.description}</div>
      </div>)}
    </div>
  </div>
}
