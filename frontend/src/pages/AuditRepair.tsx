import React, { useState, useEffect } from 'react';

export default function AuditRepair() {
  const [history, setHistory] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<any>(null);
  const [tab, setTab] = useState<'history' | 'detail'>('history');

  const fetchHistory = async () => {
    try {
      const [h, s] = await Promise.all([
        fetch('/api/audit-repair/history?limit=50').then(r => r.json()),
        fetch('/api/audit-repair/stats').then(r => r.json()),
      ]);
      if (h.success) setHistory(h.history || []);
      if (s.success) setStats(s);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchHistory(); }, []);

  const loadDetail = async (id: number) => {
    try {
      const r = await fetch(`/api/audit-repair/history/${id}`);
      const d = await r.json();
      if (d.success) { setSelected(d.record); setTab('detail'); }
    } catch(e) { console.error(e); }
  };

  const actionColor = (a: string) => {
    if (a === 'proceed') return '#166534';
    if (a === 'steer') return '#92400e';
    if (a === 'escalate') return '#991b1b';
    return '#64748b';
  };

  const actionBg = (a: string) => {
    if (a === 'proceed') return '#dcfce7';
    if (a === 'steer') return '#fef3c7';
    if (a === 'escalate') return '#fee2e2';
    return '#f1f5f9';
  };

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#1e293b', display: 'flex', alignItems: 'center', gap: '8px' }}>
          🔍 审计扮演修复
        </h1>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center', fontSize: '0.8rem', color: '#64748b' }}>
          {stats && <span>共 {stats.total} 次审计</span>}
          {stats && stats.fixed > 0 && <span style={{ color: '#166534' }}>已修复 {stats.fixed} 项</span>}
          <button onClick={() => { fetchHistory(); setTab('history'); setSelected(null); }}
            style={{ padding: '4px 12px', borderRadius: '6px', background: '#f1f5f9', border: '1px solid #e2e8f0', cursor: 'pointer', fontSize: '0.8rem' }}>
            🔄 刷新
          </button>
        </div>
      </div>

      {stats?.actions && (
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px', flexWrap: 'wrap' }}>
          {Object.entries(stats.actions).map(([k, v]: any) => (
            <div key={k} style={{
              padding: '6px 14px', borderRadius: '8px', background: actionBg(k),
              border: `1px solid ${actionColor(k)}20`, fontSize: '0.85rem',
              display: 'flex', alignItems: 'center', gap: '6px'
            }}>
              <span style={{ fontWeight: 600, color: actionColor(k) }}>{k}</span>
              <span style={{ color: '#64748b', fontWeight: 600 }}>{v}</span>
              <span style={{ color: '#94a3b8', fontSize: '0.75rem' }}>次</span>
            </div>
          ))}
        </div>
      )}

      {tab === 'detail' && selected ? (
        <div>
          <a href="#" onClick={(e) => { e.preventDefault(); setTab('history'); setSelected(null); }}
            style={{ color: '#2563eb', fontSize: '0.85rem', textDecoration: 'none', marginBottom: '12px', display: 'inline-block' }}>
            ← 返回列表
          </a>
          <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
              <h2 style={{ fontSize: '1.1rem', fontWeight: 700, color: '#1e293b' }}>
                审计 #{selected.id}
                <span style={{ marginLeft: '10px', padding: '2px 8px', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 600,
                  background: actionBg(selected.actor_action), color: actionColor(selected.actor_action) }}>
                  {selected.actor_action}
                </span>
                <span style={{ marginLeft: '8px', padding: '2px 8px', borderRadius: '99px', fontSize: '0.75rem',
                  background: selected.repair_status === 'fixed' ? '#dcfce7' : '#fef3c7',
                  color: selected.repair_status === 'fixed' ? '#166534' : '#92400e' }}>
                  {selected.repair_status === 'pending' ? '待修复' : '已修复'}
                </span>
              </h2>
              <span style={{ fontSize: '0.8rem', color: '#94a3b8' }}>{selected.run_at}</span>
            </div>
            <div style={{ marginBottom: '12px' }}>
              <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '4px', fontWeight: 600 }}>🤖 扮演者诊断</div>
              <div style={{ fontSize: '0.9rem', color: '#334155', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>{selected.actor_reason}</div>
            </div>
            {selected.actor_guidance && (
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '4px', fontWeight: 600 }}>🛠 修复方案</div>
                <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f8fafc', padding: '12px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  {selected.actor_guidance}
                </div>
              </div>
            )}
            {selected.feedback && (
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '4px', fontWeight: 600 }}>📎 修复反馈</div>
                <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: 1.6, whiteSpace: 'pre-wrap', background: '#f0fdf4', padding: '12px', borderRadius: '8px', border: '1px solid #bbf7d0' }}>
                  {selected.feedback}
                </div>
              </div>
            )}
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {loading ? <div style={{ textAlign: 'center', color: '#64748b', padding: '40px' }}>加载中...</div> : history.length === 0 ? (
            <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px' }}>
              <div style={{ fontSize: '3rem', marginBottom: '8px' }}>📋</div>
              <div style={{ fontSize: '1rem' }}>暂无审计记录</div>
            </div>
          ) : (
            history.map((h: any) => (
              <div key={h.id} onClick={() => loadDetail(h.id)}
                style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '14px 16px', cursor: 'pointer', transition: 'box-shadow 0.15s' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ flex: 1 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>#{h.id}</span>
                      <span style={{ padding: '2px 8px', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 600,
                        background: actionBg(h.action), color: actionColor(h.action) }}>
                        {h.action}
                      </span>
                      <span style={{ padding: '2px 8px', borderRadius: '99px', fontSize: '0.75rem',
                        background: h.status === 'fixed' ? '#dcfce7' : '#fef3c7',
                        color: h.status === 'fixed' ? '#166534' : '#92400e' }}>
                        {h.status === 'fixed' ? '已修复' : '待修复'}
                      </span>
                      {h.feedback && <span style={{ fontSize: '0.75rem', color: '#16a34a' }}>📎 有反馈</span>}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#334155', lineHeight: 1.5 }}>{h.reason}</div>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: '#94a3b8', whiteSpace: 'nowrap', marginLeft: '12px' }}>{h.run_at}</div>
                </div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
