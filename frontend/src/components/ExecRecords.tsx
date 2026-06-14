import React, { useState, useEffect } from 'react';

interface ExecRecord {
  id: number; task_id: number; version: number; status: string;
  started_at: string; completed_at: string; duration_seconds: number;
  execution_log: string; result_summary: string; error_message: string;
  model_used: string; task_type: string;
}

const statusIcon = (s: string) => {
  const icons: Record<string,string> = {
    'completed':'✅','failed':'❌','failed_retryable':'🔄','in_progress':'▶️',
    'pending':'⏳','pending_review':'👁️','cancelled':'🚫',
  };
  return icons[s] || '❓';
};

const ExecRecords: React.FC<{ taskId: number }> = ({ taskId }) => {
  const [records, setRecords] = useState<ExecRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`/api/tasks/${taskId}/executions`);
        const d = await r.json();
        if (d.success) setRecords(d.records || []);
        else setError(d.error || '获取失败');
      } catch(e: any) {
        setError(e.message || '网络错误');
      }
      setLoading(false);
    })();
  }, [taskId]);

  if (loading) {
    return <div style={{padding:'12px',color:'#6b7280',fontSize:'13px'}}>加载执行记录...</div>;
  }

  if (error) {
    return <div style={{padding:'12px',color:'#dc2626',fontSize:'13px'}}>⚠️ {error}</div>;
  }

  if (records.length === 0) {
    return <div style={{padding:'12px',color:'#9ca3af',fontSize:'13px'}}>暂无执行记录</div>;
  }

  const fmtDur = (sec?: number) => {
    if (!sec) return '-';
    if (sec < 60) return `${sec}s`;
    if (sec < 3600) return `${Math.floor(sec/60)}m${sec%60}s`;
    return `${Math.floor(sec/3600)}h${Math.floor((sec%3600)/60)}m`;
  };

  const fmtTime = (t?: string) => {
    if (!t) return '-';
    return t.replace('T',' ').split('.').shift() || t;
  };

  return (
    <div style={{maxHeight:'320px',overflowY:'auto',fontSize:'12px'}}>
      <table style={{width:'100%',borderCollapse:'collapse'}}>
        <thead>
          <tr style={{borderBottom:'1px solid #e5e7eb',color:'#6b7280',fontWeight:600,fontSize:'11px'}}>
            <th style={{padding:'6px 8px',textAlign:'left'}}>版本</th>
            <th style={{padding:'6px 8px',textAlign:'left'}}>状态</th>
            <th style={{padding:'6px 8px',textAlign:'left'}}>类型</th>
            <th style={{padding:'6px 8px',textAlign:'left'}}>模型</th>
            <th style={{padding:'6px 8px',textAlign:'left'}}>耗时</th>
            <th style={{padding:'6px 8px',textAlign:'left'}}>开始时间</th>
            <th style={{padding:'6px 8px',textAlign:'left'}}>执行摘要</th>
          </tr>
        </thead>
        <tbody>
          {records.map((rec) => (
            <tr key={rec.id} style={{borderBottom:'1px solid #f3f4f6'}}>
              <td style={{padding:'6px 8px',fontWeight:600,color:'#374151'}}>
                v{rec.version}
              </td>
              <td style={{padding:'6px 8px'}}>
                {statusIcon(rec.status)} {rec.status}
              </td>
              <td style={{padding:'6px 8px',color:'#6b7280',maxWidth:'80px',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                {rec.task_type || '-'}
              </td>
              <td style={{padding:'6px 8px',color:'#6b7280',fontSize:'11px',maxWidth:'80px',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                {rec.model_used || '-'}
              </td>
              <td style={{padding:'6px 8px',color:'#6b7280'}}>
                {fmtDur(rec.duration_seconds)}
              </td>
              <td style={{padding:'6px 8px',color:'#6b7280',fontSize:'11px',whiteSpace:'nowrap'}}>
                {fmtTime(rec.started_at)}
              </td>
              <td style={{padding:'6px 8px',color:'#6b7280',fontSize:'11px',maxWidth:'150px',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
                {(rec.result_summary || rec.execution_log || '').slice(0,60)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default ExecRecords;
