import React, { useState, useEffect } from 'react'
import VineCanvas from '../components/VineCanvas'
const SPROUT_API = '/api/sprout'
interface Garden {id:string;goal:string;scenario:string;updated_at:string;leaf_count:number}

const GardenDashboard: React.FC = () => {
  const [gardens, setGardens] = useState<Garden[]>([])
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({total:0, leaves:0, alerts:0})

  useEffect(() => {
    Promise.all([
      fetch(SPROUT_API+'/gardens').then(r=>r.json()),
      fetch(SPROUT_API+'/alerts/rules').then(r=>r.json()),
    ]).then(([g,alerts]) => {
      if(Array.isArray(g)) setGardens(g)
      const total = Array.isArray(g) ? g.length : 0
      const leaves = Array.isArray(g) ? g.reduce((a,b) => a + (b.leaf_count||0), 0) : 0
      setStats({total, leaves, alerts: Array.isArray(alerts) ? alerts.length : 0})
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [])
  // Enable manual refresh
  const refresh = () => {
    setLoading(true)
    Promise.all([
      fetch(SPROUT_API+'/gardens').then(r=>r.json()),
      fetch(SPROUT_API+'/alerts/rules').then(r=>r.json()),
    ]).then(([g,alerts]) => {
      if(Array.isArray(g)) setGardens(g)
      const total = Array.isArray(g) ? g.length : 0
      const leaves = Array.isArray(g) ? g.reduce((a,b) => a + (b.leaf_count||0), 0) : 0
      setStats({total, leaves, alerts: Array.isArray(alerts) ? alerts.length : 0})
      setLoading(false)
    }).catch(() => setLoading(false))
  }

  if (loading) return <div style={{minHeight:'100vh',background:'#0f172a',color:'#e2e8f0',display:'flex',alignItems:'center',justifyContent:'center'}}>加载中...</div>

  return (
    <div style={{minHeight:'100vh',background:'#0f172a',color:'#e2e8f0',padding:'20px max(20px, calc((100vw - 900px) / 2))'}}>
      <div style={{display:'flex',alignItems:'center',gap:12,marginBottom:24}}>
        <span style={{fontSize:32}}>🌸</span>
        <h1 style={{fontSize:24,fontWeight:700,margin:0}}>我的花园</h1>
        <button onClick={refresh} style={{padding:'6px 14px',background:'transparent',border:'1px solid #334155',borderRadius:6,color:'#64748b',fontSize:11,cursor:'pointer'}}>刷新</button><a href="/grow" style={{marginLeft:8,padding:'8px 20px',background:'#3b82f6',borderRadius:8,color:'#fff',fontSize:13,textDecoration:'none',fontWeight:600}}>🌱 新种子</a>
      </div>

      {/* Stats cards */}
      <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(150px,1fr))',gap:12,marginBottom:24}}>
        <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:10,padding:16,textAlign:'center'}}>
          <div style={{fontSize:32,fontWeight:700,color:'#22c55e'}}>{stats.total}</div>
          <div style={{fontSize:11,color:'#64748b'}}>花园</div>
        </div>
        <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:10,padding:16,textAlign:'center'}}>
          <div style={{fontSize:32,fontWeight:700,color:'#3b82f6'}}>{stats.leaves}</div>
          <div style={{fontSize:11,color:'#64748b'}}>叶子</div>
        </div>
        <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:10,padding:16,textAlign:'center'}}>
          <div style={{fontSize:32,fontWeight:700,color:'#eab308'}}>{stats.alerts}</div>
          <div style={{fontSize:11,color:'#64748b'}}>告警规则</div>
        </div>
        <div style={{background:'#1e293b',border:'1px solid #334155',borderRadius:10,padding:16,textAlign:'center'}}>
          <div style={{fontSize:32,fontWeight:700,color:'#a855f7'}}>{new Date().toLocaleTimeString('zh-CN',{hour12:false})}</div>
          <div style={{fontSize:11,color:'#64748b'}}>引擎状态</div>
        </div>
      </div>

      {/* Garden list */}
      {gardens.length === 0 ? (
        <div style={{textAlign:'center',padding:'60px 20px',color:'#475569'}}>
          <div style={{fontSize:48,marginBottom:12}}>🌱</div>
          <div style={{fontSize:18,fontWeight:600,marginBottom:8}}>还没有花园</div>
          <div style={{fontSize:12,marginBottom:20}}>去养你的第一个系统吧</div>
          <a href="/grow" style={{padding:'10px 24px',background:'#22c55e',borderRadius:8,color:'#fff',fontSize:14,textDecoration:'none',fontWeight:600}}>🌱 开始养</a>
        </div>
      ) : (
        <div style={{display:'flex',flexDirection:'column',gap:8}}>
          {gardens.map(g => (
            <div key={g.id} style={{display:'flex',alignItems:'center',background:'#1e293b',border:'1px solid #334155',borderRadius:10,padding:16,cursor:'pointer',transition:'border-color 0.15s'}}
              onClick={() => window.location.href='/grow?id='+g.id}
              onMouseEnter={e => (e.currentTarget.style.borderColor='#22c55e')}
              onMouseLeave={e => (e.currentTarget.style.borderColor='#334155')}>
              <span style={{fontSize:24,marginRight:12}}>{g.scenario==='research'?'🔬':g.scenario==='finance'?'💰':g.scenario==='company'?'🏢':'🌱'}</span>
              <div style={{flex:1}}>
                <div style={{fontSize:14,fontWeight:600}}>{g.goal.slice(0,40)}</div>
                <div style={{fontSize:10,color:'#64748b'}}>{g.scenario||'自定义'} · {g.leaf_count}片叶子 · {g.updated_at?.slice(0,10)}</div>
              </div>
              <a href={'/grow?id='+g.id} style={{padding:'4px 12px',background:'transparent',border:'1px solid #334155',borderRadius:6,color:'#94a3b8',fontSize:10,textDecoration:'none'}}>打开 →</a>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
export default GardenDashboard
