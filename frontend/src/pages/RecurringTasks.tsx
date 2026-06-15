import React, { useState, useEffect } from 'react';

export default function RecurringTasks() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editExpr, setEditExpr] = useState('');
  const [form, setForm] = useState({ title: '', description: '', cron_expr: '' });

  const fetchTasks = async () => {
    try {
      const r = await fetch('/api/tasks/recurring');
      const d = await r.json();
      if (d.success) setTasks(d.tasks || []);
    } catch(e) { console.error(e); }
    finally { setLoading(false); }
  };

  useEffect(() => { fetchTasks(); }, []);

  const addTask = async () => {
    if (!form.title || !form.cron_expr) return;
    try {
      const r = await fetch('/api/tasks/create-recurring', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form)
      });
      const d = await r.json();
      if (d.success) { setShowAdd(false); setForm({ title: '', description: '', cron_expr: '' }); fetchTasks(); }
      else alert(d.error || '');
    } catch(e) { alert('创建失败'); }
  };

  const updateCron = async (tid: number, expr: string) => {
    const aliases: Record<string,string> = {
      '每小时': '0 * * * *', '每2小时': '0 */2 * * *',
      '每天': '0 9 * * *', '每天8点': '0 8 * * *', '每天9点': '0 9 * * *',
      '每天10点': '0 10 * * *', '每天12点': '0 12 * * *',
      '每天14点': '0 14 * * *', '每天16点': '0 16 * * *',
      '每周': '0 9 * * 1', '每周一': '0 9 * * 1', '每周二': '0 9 * * 2',
      '每周三': '0 9 * * 3', '每两周': '0 9 * * 1', '每月': '0 9 1 * *',
    };
    const finalExpr = aliases[expr] || expr;
    try {
      const r = await fetch(`/api/tasks/${tid}/cron`, {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cron_expr: finalExpr })
      });
      const d = await r.json();
      if (d.success) { setEditingId(null); setEditExpr(''); fetchTasks(); }
      else alert(d.error || '更新失败');
    } catch(e) { alert('网络错误'); }
  };

  const presets = [
    { expr: '0 8 * * 1', label: '每周一 8:00' },
    { expr: '0 9 1 * *', label: '每月1号 9:00' },
    { expr: '0 */6 * * *', label: '每6小时' },
    { expr: '0 0 * * *', label: '每天午夜' },
    { expr: '每天', label: '每天9:00' },
    { expr: '每周一', label: '每周一9:00' },
    { expr: '每小时', label: '每小时' },
  ];

  const cronLabels: Record<string,string> = {
    '0 9 * * *': '每天 9:00', '0 8 * * *': '每天 8:00',
    '0 10 * * 1': '每周一 10:00', '0 11 * * 1': '每周一 11:00',
    '0 12 * * 1': '每周一 12:00', '0 13 * * 1': '每周一 13:00',
    '0 14 * * 1': '每周一 14:00', '0 15 * * 1': '每周一 15:00',
    '0 16 * * 1': '每周一 16:00',
    '0 11 * * 2': '每周二 11:00', '0 12 * * 2': '每周二 12:00',
    '0 13 * * 2': '每周二 13:00', '0 14 * * 2': '每周二 14:00',
    '0 15 * * 2': '每周二 15:00', '0 16 * * 2': '每周二 16:00',
  };

  return (
    <div style={{ padding: '24px', maxWidth: '900px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h1 style={{ fontSize: '1.3rem', fontWeight: 700, color: '#1e293b' }}>⏰ 定期任务管理</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button onClick={fetchTasks} style={{ padding: '6px 12px', borderRadius: '6px', background: '#f1f5f9', border: '1px solid #e2e8f0', cursor: 'pointer' }}>🔄 刷新</button>
          <button onClick={() => setShowAdd(!showAdd)} style={{ padding: '6px 14px', borderRadius: '6px', background: '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600, fontSize: '0.85rem' }}>{showAdd ? '取消' : '+ 新建'}</button>
        </div>
      </div>

      {showAdd && (
        <div style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '20px', marginBottom: '16px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            <input placeholder="任务标题" value={form.title} onChange={e => setForm({...form,title:e.target.value})}
              style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.9rem' }} />
            <input placeholder="描述（可选）" value={form.description} onChange={e => setForm({...form,description:e.target.value})}
              style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.9rem' }} />
            <div>
              <input placeholder="cron 表达式 或 别名（每天/每周一/每小时）" value={form.cron_expr} onChange={e => setForm({...form,cron_expr:e.target.value})}
                style={{ padding: '8px 12px', borderRadius: '6px', border: '1px solid #e2e8f0', fontSize: '0.9rem', width: '100%' }} />
              <div style={{ display: 'flex', gap: '6px', marginTop: '6px', flexWrap: 'wrap' }}>
                {presets.map(p => (
                  <span key={p.expr} onClick={() => setForm({...form,cron_expr:p.expr})}
                    style={{ cursor: 'pointer', padding: '2px 8px', background: '#f1f5f9', borderRadius: '4px', fontSize: '0.75rem', color: '#64748b' }}>
                    {p.label}
                  </span>
                ))}
              </div>
            </div>
            <button onClick={addTask} disabled={!form.title||!form.cron_expr}
              style={{ padding: '8px', borderRadius: '6px', background: !form.title||!form.cron_expr ? '#94a3b8' : '#2563eb', color: '#fff', border: 'none', cursor: 'pointer', fontWeight: 600 }}>
              创建
            </button>
          </div>
        </div>
      )}

      {loading ? <div style={{ textAlign: 'center', color: '#64748b', padding: '40px' }}>加载中...</div> : tasks.length === 0 ? (
        <div style={{ textAlign: 'center', color: '#94a3b8', padding: '40px' }}>
          <div style={{ fontSize: '3rem', marginBottom: '8px' }}>📅</div>
          <div style={{ fontSize: '1rem' }}>暂无定期任务</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {tasks.map(t => (
            <div key={t.id} style={{ background: '#fff', borderRadius: '10px', border: '1px solid #e2e8f0', padding: '14px 16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 600, color: '#1e293b', fontSize: '0.9rem' }}>
                    #{t.id} {t.title}
                    {t.project_id && <span style={{ fontSize: '0.75rem', color: '#94a3b8', marginLeft: '8px' }}>项目#{t.project_id}</span>}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#64748b', marginTop: '4px', display: 'flex', gap: '12px', alignItems: 'center' }}>
                    {editingId === t.id ? (
                      <span style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
                        <input value={editExpr} onChange={e => setEditExpr(e.target.value)}
                          placeholder="cron 或别名" style={{ width: '160px', padding: '4px 8px', borderRadius: '4px', border: '1px solid #2563eb', fontSize: '0.8rem' }}
                          onKeyDown={e => { if (e.key === 'Enter') updateCron(t.id, editExpr); }} />
                        <button onClick={() => updateCron(t.id, editExpr)} style={{ padding: '3px 8px', background: '#2563eb', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem' }}>确定</button>
                        <button onClick={() => setEditingId(null)} style={{ padding: '3px 8px', background: '#f1f5f9', border: '1px solid #e2e8f0', borderRadius: '4px', cursor: 'pointer', fontSize: '0.75rem' }}>取消</button>
                      </span>
                    ) : (
                      <span onClick={() => { setEditingId(t.id); setEditExpr(t.cron_expr || ''); }}
                        style={{ cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
                        🕐 <strong>{t.cron_expr}</strong>
                        {cronLabels[t.cron_expr] && <span style={{ color: '#94a3b8' }}>({cronLabels[t.cron_expr]})</span>}
                        <span style={{ fontSize: '0.7rem', color: '#94a3b8' }}>✏️</span>
                      </span>
                    )}
                    {t.last_run && <span>⏳ 上次: {t.last_run}</span>}
                  </div>
                  {t.description && <div style={{ fontSize: '0.78rem', color: '#94a3b8', marginTop: '4px' }}>{t.description}</div>}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span style={{ padding: '2px 8px', borderRadius: '99px', fontSize: '0.75rem', fontWeight: 600,
                    background: t.status === 'completed' ? '#dcfce7' : t.status === 'pending' ? '#fef3c7' : '#f1f5f9',
                    color: t.status === 'completed' ? '#166534' : t.status === 'pending' ? '#92400e' : '#64748b' }}>
                    {t.status === 'completed' ? '待调度' : t.status === 'pending' ? '执行中' : t.status}
                  </span>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
      <div style={{ marginTop: '16px', padding: '12px', background: '#f8fafc', borderRadius: '8px', fontSize: '0.78rem', color: '#64748b' }}>
        💡 点击 🕐 表达式可直接修改周期。支持别名：<strong>每天 / 每周一 / 每周二 / 每小时 / 每月</strong> 或原生 cron 表达式
      </div>
    </div>
  );
}
