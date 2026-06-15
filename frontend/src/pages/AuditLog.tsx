import React, { useState, useEffect } from 'react';
import { useRealtimeWS, WSRealtimeEvent } from '../hooks/useRealtimeWS';

interface AuditEntry {
  id: number;
  task_id: number;
  decision: string;
  score: number;
  reason: string;
  created_at: string;
  reviewer: string;
}

const DECISION: Record<string, {icon: string; color: string; label: string}> = {
  approved:  { icon: '✅', color: '#22c55e', label: '通过' },
  rejected:  { icon: '⛔', color: '#ef4444', label: '驳回' },
  fast_pass: { icon: '🏃', color: '#f59e0b', label: '快速通过' },
};

const AuditLog: React.FC = () => {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [filter, setFilter] = useState<string>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/audit-logs?per_page=200')
      .then(r => r.json())
      .then(d => { if (Array.isArray(d)) setEntries(d); else if (d.data) setEntries(d.data); })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useRealtimeWS((evt) => {
    if (evt.event === 'review' && evt.data) {
      const d = evt.data;
      setEntries(p => [{
        id: d.task_id || Date.now(), task_id: d.task_id || 0,
        decision: d.decision || 'rejected', score: d.score || 0,
        reason: d.reason || '', created_at: d.timestamp || new Date().toISOString(),
        reviewer: d.reviewer || 'SDS',
      }, ...p.slice(0, 199)]);
    }
  });

  const flt = filter === 'all' ? entries : entries.filter(e => e.decision === filter);
  const fmt = (ts: string) => { try { return new Date(ts).toLocaleTimeString('zh-CN', {hour12: false}); } catch { return ts; }};

  return (
    <div style={{padding:24, maxWidth:960, margin:'0 auto'}}>
      <h1 style={{margin:'0 0 4px', fontSize:24, fontWeight:700, color:'#e2e8f0'}}>🕵️ 审核流水</h1>
      <p style={{margin:'0 0 16px', color:'#64748b', fontSize:13}}>实时 SDS 审核决策一览</p>
      <div style={{display:'flex', gap:8, marginBottom:16, flexWrap:'wrap'}}>
        {['all','approved','rejected','fast_pass'].map(f => {
          const cfg = DECISION[f as keyof typeof DECISION];
          return (
            <button key={f} onClick={() => setFilter(f)}
              style={{padding:'6px 16px', borderRadius:8, border:'1px solid #334155', cursor:'pointer',
                background: filter === f ? '#3b82f6' : '#1e293b',
                color: filter === f ? '#fff' : '#94a3b8', fontSize:13, fontWeight:600}}>
              {f === 'all' ? '📊 全部' : cfg?.icon + ' ' + cfg?.label}
            </button>
          );
        })}
        <span style={{marginLeft:'auto', color:'#64748b', fontSize:12, alignSelf:'center'}}>共 {flt.length} 条</span>
      </div>
      <div style={{background:'#0f172a', borderRadius:12, padding:8, maxHeight:600, overflowY:'auto', border:'1px solid #1e293b'}}>
        {loading && <div style={{textAlign:'center', color:'#475569', padding:40}}>加载历史记录...</div>}
        {!loading && flt.length === 0 && <div style={{textAlign:'center', color:'#475569', padding:40}}>暂无审核记录</div>}
        {flt.map((e, i) => {
          const cfg = DECISION[e.decision] || {icon:'❓', color:'#94a3b8', label:''};
          return (
            <div key={e.id || i} style={{display:'flex', gap:10, alignItems:'center', padding:'8px 10px',
              borderBottom: i < flt.length-1 ? '1px solid #1e293b' : 'none', fontSize:13, fontFamily:'ui-monospace, monospace'}}>
              <span style={{color:'#475569', minWidth:60, whiteSpace:'nowrap'}}>{fmt(e.created_at)}</span>
              <span style={{fontSize:18, width:24, textAlign:'center'}}>{cfg.icon}</span>
              <span style={{color:cfg.color, fontWeight:600, minWidth:60}}>{cfg.label}</span>
              <span style={{color:'#94a3b8', fontWeight:500, minWidth:100}}>T{e.task_id}</span>
              {e.decision === 'rejected' && <span style={{color:'#f87171', fontSize:12}}>{e.score>0 && `${e.score}分 `}{e.reason.slice(0,80)}</span>}
            </div>
          );
        })}
      </div>
    </div>
  );
};
export default AuditLog;
