import React from 'react'
const stages=['draft','submitted','under_review','revision','accepted','published']
const stageNames={'draft':'草稿','submitted':'已投稿','under_review':'审稿中','revision':'修改中','accepted':'已接收','published':'已发表'}
export default function SubmissionTracker({leaves}:{leaves:any[]}){
  const pubs=leaves.filter(l=>l.id?.includes('pub')||l.name?.includes('发表')||l.name?.includes('投稿'))
  return <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:12,padding:16}}>
    <h3 style={{margin:'0 0 12px'}}>🏆 投稿追踪</h3>
    <div style={{display:'grid',gap:10}}>
      {pubs.length===0?<div style={{color:'#64748b',padding:20,textAlign:'center'}}>暂无投稿记录。</div>:pubs.map((p,i)=><div key={i} style={{padding:12,background:'#0f172a',borderRadius:8}}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <b>{p.name}</b>
          <span style={{background:'#3b82f622',color:'#60a5fa',padding:'2px 8px',borderRadius:6,fontSize:11}}>{stageNames['draft']}</span>
        </div>
        <div style={{height:4,background:'#334155',borderRadius:2,marginTop:8}}><div style={{width:'20%',height:4,background:'#3b82f6',borderRadius:2}}/></div>
      </div>)}
    </div>
  </div>
}
