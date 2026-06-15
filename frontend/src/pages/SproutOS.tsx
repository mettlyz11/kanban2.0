import React, { useState, useEffect } from 'react'
import VineWall from '../components/VineWall'
import ResearchPaperLibrary from '../components/ResearchPaperLibrary'
import ExperimentTracker from '../components/ExperimentTracker'
import SubmissionTracker from '../components/SubmissionTracker'
import SproutTree from '../components/SproutTree'

const SPROUT_API = '/api/sprout'
const useMobile = () => {
  const [mob, setMob] = useState(window.innerWidth < 640)
  // Check for demo mode - auto-load gardens
  useEffect(() => {
    const checkDemo = async () => {
      try {
        const r = await fetch(SPROUT_API+'/gardens')
        const data = await r.json()
        if(Array.isArray(data) && data.length > 0 && !window.location.search.includes('id=')) {
          // Gardens exist but no specific garden requested - show garden dashboard link
          setDemoMode(true)
        }
      } catch(e){}
    }
    checkDemo()
  }, [])

  useEffect(() => { const h = () => setMob(window.innerWidth < 640); window.addEventListener('resize', h); return () => window.removeEventListener('resize', h) }, [])
  return mob
}

const SproutOS: React.FC = () => {
  const [leaves, setLeaves] = useState<any[]>([])
  const [goal, setGoal] = useState('')
  const [scenarios, setScenarios] = useState<any[]>([])
  const [started, setStarted] = useState(false)
  const [demoMode, setDemoMode] = useState(false)
  const [userToken, setUserToken] = useState(localStorage.getItem('sprout_token') || '')
  const [userName, setUserName] = useState(localStorage.getItem('sprout_name') || '')
  const registerUser = async () => {
    const name = prompt('给你的花园起个主人名', userName || 'guest') || 'guest'
    const r = await fetch(SPROUT_API+'/auth/register', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({name})})
    const data = await r.json()
    if(data.token){ localStorage.setItem('sprout_token', data.token); localStorage.setItem('sprout_name', name); setUserToken(data.token); setUserName(name) }
  }
  const [tutorialStep, setTutorialStep] = useState(0)
  const TUTORIAL_STEPS = [
    {icon:'🌱',title:'说一个目标',desc:'输入你想养什么系统，比如"科研管理系统"'},
    {icon:'📋',title:'选择场景',desc:'也可以选预设场景，立即长出第一片叶子'},
    {icon:'💬',title:'说话生长',desc:'对系统说"加个预算功能"，它会从藤上长出一片新叶子'},
    {icon:'✂️',title:'修剪',desc:'不想要的叶子点一下就剪掉了'},
    {icon:'📦',title:'导出带走',desc:'养好了可以导出JSON或Docker自部署'},
    {icon:'🚀',title:'开始',desc:'准备好了就开始养你的第一个系统吧！'},
  ]
  const [currentGardenId, setCurrentGardenId] = useState('')
  // Auto-load garden from URL ?id= parameter
  // Check for demo mode - auto-load gardens
  useEffect(() => {
    const checkDemo = async () => {
      try {
        const r = await fetch(SPROUT_API+'/gardens')
        const data = await r.json()
        if(Array.isArray(data) && data.length > 0 && !window.location.search.includes('id=')) {
          // Gardens exist but no specific garden requested - show garden dashboard link
          setDemoMode(true)
        }
      } catch(e){}
    }
    checkDemo()
  }, [])

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const gid = params.get('id')
    if (gid) loadGardenById(gid)
  }, [])
  const [savedGardens, setSavedGardens] = useState<any[]>([])
  const [showGardens, setShowGardens] = useState(false)
  const [clock, setClock] = useState(new Date().toLocaleTimeString('zh-CN', {hour12: false}))

  // Auto-save on page unload
  // Check for demo mode - auto-load gardens
  useEffect(() => {
    const checkDemo = async () => {
      try {
        const r = await fetch(SPROUT_API+'/gardens')
        const data = await r.json()
        if(Array.isArray(data) && data.length > 0 && !window.location.search.includes('id=')) {
          // Gardens exist but no specific garden requested - show garden dashboard link
          setDemoMode(true)
        }
      } catch(e){}
    }
    checkDemo()
  }, [])

  useEffect(() => {
    const h = () => {
      if (leaves.length > 0 && currentGardenId) {
        navigator.sendBeacon(SPROUT_API+'/garden/save', JSON.stringify({
          id: currentGardenId, goal: goal||'my_garden',
          leaves, diary: journal, scenario: 'custom'
        }))
      }
    }
    window.addEventListener('beforeunload', h)
    return () => window.removeEventListener('beforeunload', h)
  }, [leaves, currentGardenId])

  // Check for demo mode - auto-load gardens
  useEffect(() => {
    const checkDemo = async () => {
      try {
        const r = await fetch(SPROUT_API+'/gardens')
        const data = await r.json()
        if(Array.isArray(data) && data.length > 0 && !window.location.search.includes('id=')) {
          // Gardens exist but no specific garden requested - show garden dashboard link
          setDemoMode(true)
        }
      } catch(e){}
    }
    checkDemo()
  }, [])

  useEffect(() => {
    const t = setInterval(() => setClock(new Date().toLocaleTimeString('zh-CN', {hour12: false})), 5000)
    return () => clearInterval(t)
  }, [])

  const loadScenarios = async () => {
    try {
      const r = await fetch(SPROUT_API + '/scenarios')
      const data = await r.json()
      const arr = Object.entries(data).map(([k,v]:any) => ({key:k,...v}))
      setScenarios(arr)
    } catch(e) {console.error(e)}
  }

  const loadSavedGardens = async () => {
    setShowGardens(!showGardens)
    try { const r = await fetch(SPROUT_API + '/gardens')
      const data = await r.json()
      if(Array.isArray(data)) setSavedGardens(data)
    } catch(e){}
  }

  const saveCurrentGarden = async () => {
    if (leaves.length === 0) return
    const gid = currentGardenId || 'garden_'+Date.now()
    setCurrentGardenId(gid)
    try { await fetch(SPROUT_API + '/garden/save', {
      method:'POST',headers:{'Content-Type':'application/json'},
      body: JSON.stringify({id:gid,goal:goal||'my_garden',leaves,diary:journal,scenario:'custom'})
    }) } catch(e){}
  }

  const loadGardenById = async (id: string) => {
    try { const r = await fetch(SPROUT_API+'/garden/'+id)
      const data = await r.json()
      if(data&&data.leaves){ setLeaves(JSON.parse(data.leaves))
        setGoal(data.goal||''); setCurrentGardenId(id); setStarted(true)
        if(data.diary) setJournalRaw(JSON.parse(data.diary))
      }
    } catch(e){}
  }

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.()
    else document.exitFullscreen?.()
  }

  const initScenario = async (name: string) => {
    try {
      const r = await fetch(SPROUT_API + '/scenario', {
        method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({name})
      })
      const data = await r.json()
      if(data.leaves && data.leaves.length > 0) {
        setCurrentGardenId('garden_'+Date.now())
        setCurrentGardenId('garden_'+Date.now())
        setLeaves(data.leaves.map((l:any) => ({...l,status:'growing' as const,children: []})))
        setStarted(true)
        setTimeout(() => setLeaves(p => p.map(l => ({...l,status:'alive' as const}))), 2000)
      }
    } catch(e) {console.error(e)}
  }

  const initSprout = async () => {
    if (!goal.trim()) return
    try {
      const r = await fetch(SPROUT_API + '/api/sprout/parse', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({goal: goal.trim(), existing_leaves: []})
      })
      const res = await r.json()
      if (Array.isArray(res) && res.length > 0) {
        setCurrentGardenId('garden_'+Date.now())
        setCurrentGardenId('garden_'+Date.now())
        setLeaves(res.map((l: any) => ({...l, status: 'growing' as const, children: []})))
        setStarted(true)
        setTimeout(() => setLeaves(p => p.map(l => ({...l, status: 'alive' as const}))), 2000)
      } else {
        // fallback: use templates
        setLeaves([
          {id: 'bookkeeping', name: '记账', emoji: '📝', status: 'growing' as const, deps: [], complexity: 1, children: []},
          {id: 'category', name: '分类管理', emoji: '🏷️', status: 'alive' as const, deps: ['bookkeeping'], complexity: 2, children: []},
          {id: 'report', name: '报表', emoji: '📊', status: 'alive' as const, deps: ['bookkeeping'], complexity: 3, children: []},
        ])
        setStarted(true)
      }
    } catch (e) {
      console.error('SproutOS error:', e)
      setLeaves([
        {id: 'bookkeeping', name: '记账', emoji: '📝', status: 'alive' as const, deps: [], complexity: 1, children: []},
        {id: 'report', name: '报表', emoji: '📊', status: 'alive' as const, deps: ['bookkeeping'], complexity: 3, children: []},
      ])
      setStarted(true)
    }
  }

  const growSprout = async (speech: string) => {
    try {
      const r = await fetch(SPROUT_API + '/api/sprout/grow', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({speech, current_leaves: leaves})
      })
      const res = await r.json()
      if (res.action === 'grow' && res.leaf) {
        setLeaves(p => [...p, {...res.leaf, status: 'growing', children: []}])
        setTimeout(() => setLeaves(p => p.map(l => l.id === res.leaf.id ? {...l, status: 'alive'} : l)), 2000)
      } else if (res.action === 'prune' && res.target) {
        setLeaves(p => p.map(l => l.id === res.target ? {...l, status: 'withered'} : l))
      }
    } catch (e) {
      // fallback: add a mock leaf
      const newLeaf = {id: 'leaf_' + Date.now(), name: speech.slice(0, 10), emoji: '🍃', status: 'growing' as const, deps: [], complexity: 1, children: []}
      setLeaves(p => [...p, newLeaf])
      setTimeout(() => setLeaves(p => p.map(l => l.id === newLeaf.id ? {...l, status: 'alive'} : l)), 2000)
    }
  }

  const [journal, setJournalRaw] = useState<any[]>([])
  const [alertSpeech, setAlertSpeech] = useState('')
  const [alerts, setAlerts] = useState<any[]>([])
  const [showAlerts, setShowAlerts] = useState(false)

  const createAlert = async () => {
    if (!alertSpeech.trim()) return
    try {
      const r = await fetch(SPROUT_API + '/alert/create', {
        method:'POST',headers:{'Content-Type':'application/json'},
        body: JSON.stringify({speech: alertSpeech.trim()})
      })
      const data = await r.json()
      if (data.id) {
        onSproutEvent('🚨','创建告警: '+data.metric+' '+data.operator+' '+data.threshold)
        setAlerts(p => [data,...p])
        setAlertSpeech('')
      }
    } catch(e){console.error(e)}
  }

  const loadAlerts = async () => {
    try {
      const r = await fetch(SPROUT_API + '/alerts/rules')
      const data = await r.json()
      if(Array.isArray(data)) setAlerts(data)
    } catch(e){}
  }

  const exportGarden = () => {
    if (leaves.length === 0) return;
    try {
      const pkg = {
        formatVersion: '1.0',
        exportedAt: new Date().toISOString(),
        garden: { goal: goal, leaves, diary: journal },
        deploy: { docker: 'docker compose up', port: 8080 }
      };
      const blob = new Blob([JSON.stringify(pkg, null, 2)], {type:'application/json'});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = 'sprout_'+Date.now()+'.json'; a.click();
      URL.revokeObjectURL(url);
    } catch(e){console.error(e)}
  }

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) document.documentElement.requestFullscreen?.();
    else document.exitFullscreen?.();
  }

  // Wire journal from SproutTree via callback
  const onSproutEvent = (emoji:string,desc:string) => {
    setJournalRaw(p => [{time:new Date().toLocaleTimeString('zh-CN',{hour12:false}),event:emoji+' '+desc},...p.slice(0,49)])
  }

  const pruneSprout = (leafId: string) => {
    setLeaves(p => p.map(l => l.id===leafId ? {...l, status:'withered'} : l))
    onSproutEvent('✂️','修剪了叶子')
  }
    setLeaves(p => p.map(l => l.id === leafId ? {...l, status: 'withered'} : l))
  }

  const mob = useMobile()

  if (!started) {
    return (
      <div style={{
        minHeight: '100vh',
        background: '#0f172a',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 20,
        color: '#e2e8f0'
      }}>
        {tutorialStep > 0 && tutorialStep < TUTORIAL_STEPS.length && (
        <div style={{position:'fixed',top:0,left:0,right:0,bottom:0,background:'rgba(0,0,0,0.8)',zIndex:1000,display:'flex',alignItems:'center',justifyContent:'center',padding:20}}
          onClick={() => setTutorialStep(t => Math.min(t+1, TUTORIAL_STEPS.length-1))}>
          <div style={{background:'#1e293b',border:'1px solid #22c55e',borderRadius:16,padding:'32px 40px',maxWidth:400,textAlign:'center'}}
            onClick={e => e.stopPropagation()}>
            <div style={{fontSize:48,marginBottom:12}}>{TUTORIAL_STEPS[tutorialStep-1].icon}</div>
            <div style={{fontSize:20,fontWeight:700,marginBottom:8}}>{TUTORIAL_STEPS[tutorialStep-1].title}</div>
            <div style={{color:'#94a3b8',fontSize:14,marginBottom:20}}>{TUTORIAL_STEPS[tutorialStep-1].desc}</div>
            <div style={{display:'flex',gap:8,justifyContent:'center'}}>
              {tutorialStep < TUTORIAL_STEPS.length - 1 ? (
                <button onClick={() => setTutorialStep(t => t+1)} style={{padding:'10px 24px',background:'#3b82f6',border:'none',borderRadius:8,color:'#fff',fontSize:14,fontWeight:600,cursor:'pointer'}}>
                  下一步 →
                </button>
              ) : (
                <button onClick={() => setTutorialStep(0)} style={{padding:'10px 24px',background:'#22c55e',border:'none',borderRadius:8,color:'#fff',fontSize:14,fontWeight:600,cursor:'pointer'}}>
                  🚀 开始养!
                </button>
              )}
              <button onClick={() => setTutorialStep(0)} style={{padding:'10px 24px',background:'transparent',border:'1px solid #334155',borderRadius:8,color:'#64748b',fontSize:14,cursor:'pointer'}}>
                跳过
              </button>
            </div>
            <div style={{color:'#475569',fontSize:10,marginTop:12}}>{tutorialStep}/{TUTORIAL_STEPS.length-1}</div>
          </div>
        </div>
      )}

      <span style={{fontSize: 80, marginBottom: 16, animation: 'pulse-wait 2s ease-in-out infinite'}}>🌱</span>
        <h1 style={{fontSize: 28, fontWeight: 700, margin: '0 0 8px'}}>SproutOS</h1>
        <p style={{color: '#64748b', fontSize: 14, marginBottom: 24, textAlign: 'center', maxWidth: 400}}>
          一个会自己长大的系统。<br/>说一个目标，它从 0 开始长，你只需要看着、修剪、提要求。
        </p>
        {scenarios.length===0 ? (
          <button onClick={loadScenarios} style={{padding:'8px 20px',background:'transparent',border:'1px solid #334155',borderRadius:8,color:'#64748b',fontSize:12,cursor:'pointer',marginBottom:12}}>
            📋 选择预设场景
          </button>
        ) : (
          <div style={{display:'flex',flexWrap:'wrap',gap:8,justifyContent:'center',marginBottom:16}}>
            {scenarios.map((s:any) => (
              <button key={s.key} onClick={() => initScenario(s.key)}
                style={{padding:'10px 20px',background:'#1e293b',border:'1px solid #334155',borderRadius:10,color:'#e2e8f0',fontSize:14,cursor:'pointer'}}>
                {s.emoji} {s.name} <span style={{color:'#475569',fontSize:10}}>({s.count})</span>
              </button>
            ))}
          </div>
        )}
        <input
          value={goal}
          onChange={e => setGoal(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && initSprout()}
          placeholder="或者自己说一个目标..."
          style={{
            width: '80%', maxWidth: 400,
            padding: '12px 16px',
            background: '#1e293b',
            border: '1px solid #334155',
            borderRadius: 10,
            color: '#e2e8f0',
            fontSize: 16,
            outline: 'none'
          }}
          autoFocus
        />
        <button
          onClick={initSprout}
          style={{
            marginTop: 16,
            padding: '10px 32px',
            background: '#3b82f6',
            border: 'none',
            borderRadius: 10,
            color: '#fff',
            fontSize: 16,
            fontWeight: 600,
            cursor: 'pointer'
          }}
        >
          🌱 开始养
        </button>
        <div style={{color: '#475569', fontSize: 10, marginTop: 32}}>Powered by SDS · {clock}</div>
        <style>{'@keyframes pulse-wait{0%,100%{opacity:1}50%{opacity:0.3}}'}</style>
      </div>
    )
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: '#0f172a',
      color: '#e2e8f0',
      padding: mob ? '8px' : '16px max(16px, calc((100vw - 800px) / 2))'
    }}>
      {/* Status line */}
      <div style={{display:'flex',alignItems:'center',gap:6,marginBottom:8,color:'#475569',fontSize:10}}>
        <span>已养 {leaves.length} 片叶子</span>
        <span>·</span>
        <span>生长日记 {(leaves.filter(l=>l.status==='alive').length)} 片可用</span>
        <span style={{marginLeft:'auto'}}>{clock}</span>
      </div>

      {/* Header */}
      <div style={{display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16}}>
        <span style={{fontSize: 24}}>🌱</span>
        <h1 style={{margin: 0, fontSize: 20, fontWeight: 700}}>SproutOS</h1>
        <span style={{fontSize:9,color:'#475569',background:'#0f172a',padding:'2px 8px',borderRadius:4}}>{leaves.length===0?'新种子':leaves.length+'个功能'}</span>
        <span style={{fontSize: 10, color: '#475569', marginLeft: 'auto'}}>{clock}</span>
        <button onClick={saveCurrentGarden} style={{background:'transparent',border:'1px solid #22c55e',borderRadius:6,color:'#22c55e',fontSize:10,cursor:'pointer',padding:'4px 10px',marginRight:4}}>💾 保存</button>
        <button onClick={loadSavedGardens} style={{background:'transparent',border:'1px solid #334155',borderRadius:6,color:'#64748b',fontSize:10,cursor:'pointer',padding:'4px 10px',marginRight:4}}>📂 加载</button>
        <button onClick={exportGarden} style={{background:'transparent',border:'1px solid #22c55e',borderRadius:6,color:'#22c55e',fontSize:10,cursor:'pointer',padding:'4px 10px',marginRight:4}}>📦 导出</button>
        <button onClick={toggleFullscreen} style={{background:'transparent',border:'1px solid #334155',borderRadius:6,color:'#64748b',fontSize:10,cursor:'pointer',padding:'4px 10px',marginRight:4}}>⛶ 全屏</button>
        <button onClick={() => setStarted(false)} style={{background:'transparent',border:'1px solid #334155',borderRadius:6,color:'#475569',fontSize:10,cursor:'pointer',padding:'4px 10px'}}>🌱 新种子</button>
        {showGardens && savedGardens.length>0 && (<div style={{position:'absolute',top:'100%',right:0,background:'#1e293b',border:'1px solid #334155',borderRadius:8,padding:4,zIndex:100,minWidth:200}}>
          {savedGardens.slice(0,8).map((g:any)=>(
            <div key={g.id} onClick={()=>loadGardenById(g.id)} style={{padding:'6px 10px',cursor:'pointer',fontSize:10,color:'#94a3b8',borderBottom:'1px solid #0f172a'}}>
              {g.scenario||'🌱'} {g.goal.slice(0,25)} ({g.leaf_count})
            </div>
          ))}
        </div>)}
      </div>

      {/* Tree */}
      <VineWall leaves={leaves} onGrow={growSprout} onPrune={pruneSprout} onEvent={onSproutEvent} />

      {/* Info */}
      {/* Alert panel */}
      <div style={{display:'flex',gap:8,alignItems:'center',marginBottom:12}}>
        <button onClick={() => setShowAlerts(!showAlerts)} style={{padding:'4px 12px',background:'transparent',border:'1px solid #334155',borderRadius:6,color:'#64748b',fontSize:10,cursor:'pointer',fontWeight:600}}>
          {'🚨 告警'+(alerts.length>0?' ('+alerts.length+')':'')}
        </button>
        <button onClick={loadAlerts} style={{padding:'4px 8px',background:'transparent',border:'none',color:'#475569',fontSize:9,cursor:'pointer'}}>刷新</button>
      </div>
      {showAlerts && (
        <div style={{marginBottom:12,background:'#0f172a',border:'1px solid #1e293b',borderRadius:8,padding:12}}>
          <div style={{display:'flex',gap:8,marginBottom:8}}>
            <input value={alertSpeech} onChange={e=>setAlertSpeech(e.target.value)}
              onKeyDown={e=>e.key==='Enter'&&createAlert()}
              placeholder='说一个告警规则，如：CPU超过80%持续5分钟通知我'
              style={{flex:1,padding:'8px 12px',background:'#1e293b',border:'1px solid #334155',borderRadius:6,color:'#e2e8f0',fontSize:11,outline:'none'}}/>
            <button onClick={createAlert} style={{padding:'8px 16px',background:'#eab308',border:'none',borderRadius:6,color:'#000',fontSize:11,fontWeight:600,cursor:'pointer'}}>创建</button>
          </div>
          {alerts.length>0 && <div style={{fontSize:10,color:'#64748b'}}>
            {alerts.map((a,i) => <div key={i} style={{padding:'4px 0',borderBottom:'1px solid #1e293b'}}>
              {'🚨 '+a.name+': '+a.metric+' '+a.operator+' '+a.threshold+'(持续'+a.duration_min+'分钟)'}
            </div>)}
          </div>}
        </div>
      )}

      <div style={{textAlign: 'center', color: '#475569', fontSize: 9, marginTop: 16}}>
        SDS Engine · 你的数据可以导出和自部署
      </div>
    </div>
  )
}

export default SproutOS
