import React, { useState, useEffect } from 'react';

export default function KnowledgeTreeConfig() {
  const [cfg, setCfg] = useState<any>(null);
  const [win, setWin] = useState(8192);
  const [ratio, setRatio] = useState(0.8);
  const [model, setModel] = useState('');
  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState('');

  useEffect(() => {
    fetch('/api/knowledge-tree/config').then(r=>r.json()).then(d=>{
      if(d.success&&d.config){setCfg(d.config);setWin(d.config.context_window);setRatio(d.config.ratio);setModel(d.config.model)}
    }).catch(()=>{});
  },[]);

  const save = async () => {
    setSaving(true);setMsg('');
    try{
      const r=await fetch('/api/knowledge-tree/config',{method:'PUT',headers:{'Content-Type':'application/json'},body:JSON.stringify({context_window:win,ratio:ratio,model:model})});
      const d=await r.json();
      setMsg(d.success?'OK 新上限:'+d.limit_tokens+'tok':'失败:'+d.error);
    }catch(e:any){setMsg('网络错误:'+e.message)}
    setSaving(false);
  };

  const presets = [
    {label:'DS V4 Flash 8192',w:8192,r:0.8},
    {label:'DS Reasoner 16384',w:16384,r:0.8},
    {label:'Doubao 131072',w:131072,r:0.7},
  ];

  return (
    <div className="card" style={{marginTop:20}}>
      <div className="card-header"><h5>树形知识体系配置</h5></div>
      <div style={{padding:16}}>
        {cfg&&<div style={{marginBottom:12,display:'flex',gap:16,fontSize:'0.85rem',color:'var(--text-secondary)'}}>
          <span>上限: <b>{cfg.limit_tokens}</b> tok</span>
          <span>更新: {cfg.updated_at||'-'}</span>
        </div>}
        <div style={{display:'flex',flexDirection:'column',gap:12,maxWidth:500}}>
          <input type="number" value={win} onChange={e=>setWin(Number(e.target.value))} placeholder="窗口" style={{padding:8,borderRadius:6,border:'1px solid #e2e8f0'}} />
          <input type="number" step="0.01" min="0.1" max="1" value={ratio} onChange={e=>setRatio(Number(e.target.value))} placeholder="比例" style={{padding:8,borderRadius:6,border:'1px solid #e2e8f0'}} />
          <input type="text" value={model} onChange={e=>setModel(e.target.value)} placeholder="模型名" style={{padding:8,borderRadius:6,border:'1px solid #e2e8f0'}} />
          <div style={{fontSize:'0.8rem',color:'#6366f1'}}>上限 = {win} x {ratio} = {Math.round(win*ratio)} tok</div>
          <div style={{display:'flex',gap:6,flexWrap:'wrap'}}>
            {presets.map(p=>(
              <span key={p.label} onClick={()=>{setWin(p.w);setRatio(p.r)}} style={{cursor:'pointer',padding:'3px 10px',background:'#f1f5f9',borderRadius:4,fontSize:'0.75rem'}}>{p.label}</span>
            ))}
          </div>
          <button onClick={save} disabled={saving} style={{padding:'8px 20px',borderRadius:6,background:'#2563eb',color:'#fff',border:'none',cursor:'pointer',fontWeight:600,maxWidth:200}}>
            {saving?'保存中...':'保存配置'}
          </button>
          {msg&&<span style={{fontSize:'0.85rem',color:msg.startsWith('OK')?'green':'red'}}>{msg}</span>}
        </div>
      </div>
    </div>
  );
}
