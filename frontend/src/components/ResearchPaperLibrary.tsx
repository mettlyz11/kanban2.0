import React, { useState } from 'react'
export default function ResearchPaperLibrary({leaves}:{leaves:any[]}){
  const [tab,setTab]=useState<'all'|'recent'|'fav'>('all')
  const papers=leaves.filter(l=>l.id?.includes('paper')||l.name?.includes('文献')||l.name?.includes('论文'))
  return <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:12,padding:16}}>
    <div style={{display:'flex',gap:8,marginBottom:12}}>
      {['all','recent','fav'].map(t=><button key={t} onClick={()=>setTab(t as any)} style={{background:tab===t?'#3b82f6':'#0f172a',border:'1px solid #334155',borderRadius:6,padding:'4px 10px',color:'#e2e8f0'}}>{t==='all'?'全部':t==='recent'?'最近':'收藏'}</button>)}
      <button style={{marginLeft:'auto',background:'#22c55e',border:0,borderRadius:6,padding:'4px 10px',color:'#020617',fontWeight:700}}>+ 导入</button>
    </div>
    <div style={{display:'grid',gap:8}}>
      {papers.length===0?<div style={{color:'#64748b',padding:20,textAlign:'center'}}>暂无文献。从 DOI/arXiv 导入或手动添加。</div>:papers.map((p,i)=><div key={i} style={{display:'flex',alignItems:'center',gap:10,padding:10,background:'#0f172a',borderRadius:8}}>
        <span>{p.emoji||'📄'}</span>
        <div style={{flex:1}}><b>{p.name}</b><div style={{fontSize:11,color:'#64748b'}}>{p.description||'No description'}</div></div>
        <button style={{background:'transparent',border:'1px solid #334155',borderRadius:6,padding:'2px 8px',color:'#64748b'}}>标签</button>
      </div>)}
    </div>
  </div>
}
