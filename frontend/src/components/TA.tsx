import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2, CheckCircle, XCircle, MessageSquare, History } from 'lucide-react'
import { TaskAttachments } from "../components/TaskAttachments"
import { TaskExecutionLog } from "../components/TaskExecutionLog"

interface Task {
  project_name?: string;
  project_number?: string;
  task_type?: string;
  id: number
  number: string
  title: string
  status: string
  priority: string
  description?: string
  execution_log?: string
  result_summary?: string
  task_summary?: string
  remaining_issues?: string
  improvement_suggestions?: string
  created_at: string
  review_round?: number
  review_feedback?: string
}

interface TaskAccordionProps {
  tasks: Task[]
  onDeleteTask: (id: number) => void
  onReviewTask?: (id: number, action: 'approve' | 'reject' | 'skip') => void
  showReviewActions?: boolean
}

export function TaskAccordion({ tasks, onDeleteTask, onReviewTask, showReviewActions = false }: TaskAccordionProps) {
  const [expandedTask, setExpandedTask] = useState<number | null>(null)
  const [taskData, setTaskData] = useState<Task[]>(tasks)
  const [feedbackTaskId, setFeedbackTaskId] = useState<number | null>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [reviewHistory, setReviewHistory] = useState<{[key: number]: any[]}>({})

  const handleSubmitFeedback = async (taskId: number) => {
    if (!feedbackText.trim()) return
    if (onReviewTask) {
      onReviewTask(taskId, 'feedback', feedbackText)
      setFeedbackTaskId(null)
      setFeedbackText('')
    }
  }

  const fetchReviewHistory = async (taskId: number) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}/review-history`)
      const data = await response.json()
      if (data.success) {
        setReviewHistory(prev => ({ ...prev, [taskId]: data.history }))
      }
    } catch (error) {
      console.error('Failed to fetch review history:', error)
    }
  }

  const toggleTaskWithHistory = (taskId: number) => {
    const isExpanding = expandedTask !== taskId
    setExpandedTask(expandedTask === taskId ? null : taskId)
    if (isExpanding) {
      fetchReviewHistory(taskId)
    }
  }

  const toggleTask = (taskId: number) => {
    setExpandedTask(expandedTask === taskId ? null : taskId)
  }

  const handleUpdateLog = async (taskId: number, data: {
    execution_log?: string
    result_summary?: string
    task_summary?: string
    remaining_issues?: string
    improvement_suggestions?: string
  }) => {
    try {
      const response = await fetch('/api/tasks/' + taskId + '/execution-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (response.ok) {
        setTaskData(prev => prev.map(t => 
          t.id === taskId ? { ...t, ...data } : t
        ))
      }
    } catch (error) {
      console.error('Failed to update execution log:', error)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {taskData.map(task => (
        <div 
          key={task.id}
          style={{
            background: '#fff',
            borderRadius: '8px',
            border: '1px solid #e0e0e0',
            overflow: 'hidden'
          }}
        >
          <div 
            onClick={() => toggleTaskWithHistory(task.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              cursor: 'pointer',
              background: expandedTask === task.id ? '#f8f9fa' : '#fff',
              borderBottom: expandedTask === task.id ? '1px solid #e0e0e0' : 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
              <span style={{ color: '#667eea' }}>
                {expandedTask === task.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </span>
              <span style={{ 
                fontSize: '0.75rem', 
                color: '#667eea', 
                fontWeight: 600, 
                fontFamily: 'monospace',
                background: '#f0f4ff',
                padding: '2px 8px',
                borderRadius: '4px'
              }}>
                {task.number}
              </span>
              {task.project_name && (
                <span style={{
                  fontSize: '0.75rem',
                  color: '#666',
                  background: '#f0f4ff',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  marginRight: '8px'
                }}>
                  [{task.project_number || 'N/A'}] {task.project_name}
                </span>
              )}
              <span style={{ fontSize: '0.95rem', color: '#333', fontWeight: 500 }}>
                {task.title}
              </span>
              {task.review_round > 0 && (
                <span style={{
                  fontSize: '0.7rem',
                  color: '#ff9800',
                  background: '#fff3e0',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  marginLeft: '8px',
                  border: '1px solid #ffcc80'
                }}>
                  第{task.review_round}轮
                </span>
              )}
              <span style={{ 
                fontSize: '0.7rem', 
                color: '#999', 
                fontFamily: 'monospace',
                background: '#f5f5f5',
                padding: '2px 6px',
                borderRadius: '4px',
                marginLeft: '8px'
              }}>
                #{task.id}
              </span>
              <span style={{ 
                fontSize: '0.7rem', 
                color: task.task_type === 'guide' ? '#ff6b6b' : '#51cf66', 
                fontWeight: 600,
                background: task.task_type === 'guide' ? '#fff5f5' : '#f0fff4',
                padding: '2px 8px',
                borderRadius: '4px',
                marginLeft: '8px',
                border: '1px solid ' + (task.task_type === 'guide' ? '#ffc9c9' : '#b2f2bb')
              }}>
                {task.task_type === 'guide' ? '【指导性】' : '【普通】'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={'badge ' + (
                task.priority === 'high' ? 'badge-red' : 
                task.priority === 'medium' ? 'badge-orange' : 'badge-green'
              )} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
              </span>
              <span className={'status-badge status-' + task.status} style={{
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                  background:
                    task.status === 'failed' || task.status === 'cancelled' ? '#f8d7da' :
                    task.status === 'failed_retryable' ? '#ffeeba' :
                    task.status === 'redundant' ? '#e2e3e5' :
                    task.status === 'todo' || task.status === 'pending' ? '#fff3cd' :
                    task.status === 'progress' || task.status === 'in_progress' ? '#cce5ff' :
                    '#d4edda',
                  color:
                    task.status === 'failed' || task.status === 'cancelled' ? '#721c24' :
                    task.status === 'failed_retryable' ? '#856404' :
                    task.status === 'redundant' ? '#383d41' :
                    task.status === 'todo' || task.status === 'pending' ? '#856404' :
                    task.status === 'progress' || task.status === 'in_progress' ? '#004085' :
                    '#155724'
                }}>
                {task.status === 'failed' ? '失败' : task.status === 'failed_retryable' ? '重试中' : task.status === 'redundant' ? '冗余' : task.status === 'cancelled' ? '已取消' : task.status === 'todo' || task.status === 'pending' ? '待办' : task.status === 'progress' || task.status === 'in_progress' ? '进行中' : '已完成'}
              </span>
              {showReviewActions && task.status === 'pending_review' && onReviewTask && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onReviewTask(task.id, 'approve')
                    }}
                    style={{
                      background: '#e8f5e9',
                      border: '1px solid #4caf50',
                      color: '#2e7d32',
                      cursor: 'pointer',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      fontWeight: 500
                    }}
                    title="通过"
                  >
                    <CheckCircle size={14} />
                    通过
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setFeedbackTaskId(task.id)
                    }}
                    style={{
                      background: '#fff3e0',
                      border: '1px solid #ff9800',
                      color: '#e65100',
                      cursor: 'pointer',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      fontWeight: 500
                    }}
                    title="要求修改"
                  >
                    <MessageSquare size={14} />
                    要求修改
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onReviewTask(task.id, 'reject')
                    }}
                    style={{
                      background: '#ffebee',
                      border: '1px solid #ef5350',
                      color: '#c62828',
                      cursor: 'pointer',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      fontWeight: 500
                    }}
                    title="驳回"
                  >
                    <XCircle size={14} />
                    驳回
                  </button>
                </div>
              )}
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteTask(task.id)
                }}
                style={{
                  background: '#ffebee',
                  border: 'none',
                  color: '#c62828',
                  cursor: 'pointer',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="删除任务"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>

          {expandedTask === task.id && (
            <div style={{ padding: '16px', background: '#fafbfc' }}>
              {/* ✅ 完成按钮 */}
              <div style={{ display:'flex', justifyContent:'flex-end', marginBottom:'12px' }}>
                {task.status !== 'completed' && (
                  <span onClick={() => {
                    if (!confirm('确定标记为已完成？')) return;
                    fetch('/api/tasks/' + task.id + '/status', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({status:'completed'}) })
                      .then(r => r.json())
                      .then(d => { if(d.success) window.location.reload(); else alert('操作失败'); })
                      .catch(() => alert('网络错误'));
                  }}
                  style={{ fontSize:'0.75rem', color:'#10b981', cursor:'pointer', padding:'4px 14px', borderRadius:'6px', background:'#d1fae5', border:'1px solid #6ee7b7', fontWeight:600, letterSpacing:'0.5px' }}
                  >✅ 标记完成</span>
                )}
              </div>
              {task.description && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ display:'flex',alignItems:'center',gap:'8px',marginBottom:'8px' }}>
                    <span style={{ fontSize:'0.8rem',fontWeight:600,color:'#666' }}>📋 描述</span>
                    {task.description.startsWith('{') && (
                      <span onClick={() => {
                        try { const p = JSON.parse(task.description); const e = prompt('编辑 JSON:', JSON.stringify(p, null, 2)); if (e && e.trim()) { JSON.parse(e); fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:e}) }); } }
                        catch(ex) { alert('JSON 格式错误: ' + ex); }
                      }}
                      style={{ fontSize:'0.7rem', color:'#0075de', cursor:'pointer', padding:'2px 8px', borderRadius:'4px', background:'#e3f2fd', border:'1px solid #bbdefb' }}
                      >✏️ 编辑JSON</span>
                    )}
                  </div>
                  {task.description.startsWith('{') ? (() => {
                    try {
                      const d = JSON.parse(task.description);
                      const cm = { goal:'#3b82f6', input:'#8b5cf6', output:'#22c55e', steps:'#f59e0b', acceptance:'#ef4444', depends_on:'#06b6d4', background:'#64748b', summary:'#14b8a6', context_summary:'#f97316', tools:'#6366f1', refs:'#a855f7' };
                      const lm = { goal:'目标', input:'输入', output:'产出', steps:'步骤', acceptance:'验收', depends_on:'前置任务', background:'背景', summary:'摘要', context_summary:'上下文', tools:'工具', refs:'参考' };
                      const order = ['background','context_summary','goal','input','output','steps','acceptance','depends_on','summary','tools','refs'];
                      return (
                        <div style={{ display:'flex', flexDirection:'column', gap:'6px' }}>
                          {order.filter(k => d[k] !== undefined && d[k] !== null && d[k] !== '' && !(Array.isArray(d[k]) && d[k].length === 0)).map(k => {
                            const label = lm[k] || k; const color = cm[k] || '#666';
                            const val = Array.isArray(d[k]) ? d[k].map((s,i) => { const p = String(i+1)+'. '; const t = String(s); return (t.startsWith(p) ? t : p + t).length > 200 ? t.substring(0,200)+'...' : t; }).join('\n') : String(d[k]).length > 500 ? String(d[k]).substring(0,500)+'...' : String(d[k]);
                            return (
                              <div key={k} style={{ display:'flex', gap:'6px', alignItems:'flex-start' }}>
                                <span style={{ fontSize:'0.7rem', fontWeight:600, color:color, background:color+'18', padding:'2px 8px', borderRadius:'4px', whiteSpace:'nowrap', flexShrink:0, minWidth:'40px', textAlign:'center' }}>{label}</span>
                                <div style={{ fontSize:'0.75rem', color:'#444', lineHeight:1.6, whiteSpace:'pre-wrap', flex:1 }}>{val}</div>
                              </div>
                            );
                          })}
                        </div>
                      );
                    } catch(e) { return <div style={{ color:'#ef4444', fontSize:'0.75rem' }}>JSON 解析失败: {e.message}</div>; }
                  })() : (
                    <div style={{ fontSize:'0.9rem', color:'#333', lineHeight:'1.6', whiteSpace:'pre-wrap' }}>{task.description}</div>
                  )}
                </div>
              )}

              {/* 任务背景 */}
              <div style={{ marginBottom: '12px' }}>
                <div style={{ display:'flex',alignItems:'center',gap:'8px',marginBottom:'6px' }}>
                  <span style={{ fontSize:'0.8rem',fontWeight:600,color:'#64748b' }}>📋 任务背景</span>
                  <span onClick={() => {
                    try {
                      const d = JSON.parse(task.description || '{}');
                      const cur = d.background || d.context_summary || d.summary || '';
                      const e = prompt('编辑任务背景:', cur);
                      if (e !== null) {
                        const nd = JSON.parse(task.description || '{}');
                        nd.background = e;
                        fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:JSON.stringify(nd,null,2)}) }).then(() => { window.location.reload(); });
                      }
                    } catch(ex) { alert('操作失败: ' + ex.message); }
                  }}
                  style={{ fontSize:'0.7rem',color:'#64748b',cursor:'pointer',padding:'2px 8px',borderRadius:'4px',background:'#e2e8f0',border:'1px solid #cbd5e1' }}
                  >✏️ 编辑</span>
                </div>
                {(() => {
                  if (!task.description || !task.description.startsWith('{')) return <div style={{ fontSize:'0.75rem',color:'#999',fontStyle:'italic' }}>暂无背景信息</div>;
                  try {
                    const d = JSON.parse(task.description);
                    const bg = d.background || d.context_summary || d.summary || '';
                    return bg ? <div style={{ fontSize:'0.8rem',color:'#555',lineHeight:1.6,whiteSpace:'pre-wrap' }}>{bg.length > 300 ? bg.substring(0,300)+'...' : bg}</div> : <div style={{ fontSize:'0.75rem',color:'#999',fontStyle:'italic' }}>暂无背景信息</div>;
                  } catch(e) { return <div style={{ fontSize:'0.75rem',color:'#999',fontStyle:'italic' }}>暂无背景信息</div>; }
                })()}
              </div>

              {/* 参考文件 */}
              <div style={{ marginBottom: '12px' }}
                tabIndex={0}
                onPaste={(e) => {
                  const files = e.clipboardData.files;
                  const text = e.clipboardData.getData('text');
                  
                  if (files.length > 0) {
                    e.preventDefault();
                    Array.from(files).forEach(file => {
                      const fd = new FormData();
                      fd.append('file', file);
                      fetch('/api/tasks/' + task.id + '/attachments/upload', { method:'POST', body:fd })
                        .then(r => r.json())
                        .then(d => { if(d.success) { try {
                          const nd = JSON.parse(task.description || '{}');
                          nd.refs = [...(nd.refs || []), file.name];
                          return fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:JSON.stringify(nd,null,2)}) });
                        } catch(ex) {} } })
                        .then(() => { window.location.reload(); })
                        .catch(() => alert('上传失败: ' + file.name));
                    });
                  } else if (text) {
                    e.preventDefault();
                    const lines = text.trim().split('\n').map(s => s.trim()).filter(s => s);
                    if (lines.length > 0) {
                      try {
                        const nd = JSON.parse(task.description || '{}');
                        nd.refs = [...(nd.refs || []), ...lines];
                        fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:JSON.stringify(nd,null,2)}) })
                          .then(() => { window.location.reload(); });
                      } catch(ex) { alert('操作失败: ' + ex.message); }
                    }
                  }
                }}
                onFocus={(e) => { e.target.style.outline = '2px dashed #06b6d4'; e.target.style.outlineOffset = '4px'; e.target.style.borderRadius = '8px'; }}
                onBlur={(e) => { e.target.style.outline = 'none'; }}>
                <div style={{ display:'flex',alignItems:'center',gap:'8px',marginBottom:'6px' }}>
                  <span style={{ fontSize:'0.8rem',fontWeight:600,color:'#06b6d4' }}>📎 参考文件</span>
                  <span onClick={() => {
                    const e = prompt('粘贴参考文件路径或URL（每行一个）:', '');
                    if (e && e.trim()) {
                      try {
                        const nd = JSON.parse(task.description || '{}');
                        const newRefs = e.trim().split('\n').map(s => s.trim()).filter(s => s);
                        nd.refs = [...(nd.refs || []), ...newRefs];
                        fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:JSON.stringify(nd,null,2)}) }).then(() => { window.location.reload(); });
                      } catch(ex) { alert('操作失败: ' + ex.message); }
                    }
                  }}
                  style={{ fontSize:'0.7rem',color:'#06b6d4',cursor:'pointer',padding:'2px 8px',borderRadius:'4px',background:'#cffafe',border:'1px solid #67e8f9' }}
                  >📋 粘贴</span>
                  <span onClick={() => {
                    try {
                      const nd = JSON.parse(task.description || '{}');
                      nd.refs = [];
                      fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:JSON.stringify(nd,null,2)}) }).then(() => { window.location.reload(); });
                    } catch(ex) { alert('操作失败: ' + ex.message); }
                  }}
                  style={{ fontSize:'0.7rem',color:'#ef4444',cursor:'pointer',padding:'2px 8px',borderRadius:'4px',background:'#fee2e2',border:'1px solid #fca5a5' }}
                  >🗑️ 清空</span>
                </div>
                {(() => {
                  if (!task.description || !task.description.startsWith('{')) return <div style={{ fontSize:'0.75rem',color:'#999',fontStyle:'italic' }}>暂无参考文件</div>;
                  try {
                    const d = JSON.parse(task.description);
                    const refs = d.refs || [];
                    return Array.isArray(refs) && refs.length > 0
                      ? <div style={{ display:'flex', flexDirection:'column', gap:'4px' }}>
                          {refs.map((r,i) => <div key={i} style={{ display:'flex',alignItems:'center',gap:'8px',fontSize:'0.75rem',color:'#06b6d4',padding:'4px 8px',background:'#ecfeff',borderRadius:'4px',border:'1px solid #cffafe' }}>
                            <span style={{ flex:1,overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap' }}>📄 {r}</span>
                            <span onClick={() => {
                              const nd = JSON.parse(task.description || '{}');
                              nd.refs = (nd.refs || []).filter((_,j) => j !== i);
                              fetch('/api/admin/tasks/' + task.id + '/description', { method:'PUT', headers:{'Content-Type':'application/json'}, body:JSON.stringify({description:JSON.stringify(nd,null,2)}) }).then(() => { window.location.reload(); });
                            }}
                            style={{ color:'#ef4444',cursor:'pointer',fontSize:'0.7rem',flexShrink:0 }}>✕</span>
                          </div>)}
                        </div>
                      : <div style={{ fontSize:'0.75rem',color:'#999',fontStyle:'italic' }}>暂无参考文件</div>;
                  } catch(e) { return <div style={{ fontSize:'0.75rem',color:'#999',fontStyle:'italic' }}>暂无参考文件</div>; }
                })()}
              </div>

              <div style={{ fontSize: '0.75rem', color: '#999', marginBottom: '16px' }}>
                创建时间：{new Date(task.created_at).toLocaleString('zh-CN')}
              </div>

              {/* 任务结果 */}
              {(task.result_summary || task.task_summary) && (
                <div style={{ marginTop:'12px',padding:'12px',background:'#f0fdf4',borderRadius:'8px',border:'1px solid #bbf7d0' }}>
                  <div style={{ fontSize:'0.85rem',fontWeight:600,color:'#16a34a',marginBottom:'8px' }}>📋 任务结果</div>
                  {task.task_summary && (
                    <div style={{ marginBottom:'8px' }}>
                      <div style={{ fontSize:'0.75rem',fontWeight:600,color:'#555',marginBottom:'4px' }}>摘要</div>
                      <div style={{ fontSize:'0.8rem',color:'#333',lineHeight:1.5,whiteSpace:'pre-wrap',background:'white',padding:'8px',borderRadius:'6px',border:'1px solid #e8f5e9' }}>
                        {task.task_summary}
                      </div>
                    </div>
                  )}
                  {task.result_summary && (
                    <div>
                      <div style={{ fontSize:'0.75rem',fontWeight:600,color:'#555',marginBottom:'4px' }}>产出</div>
                      <div style={{ fontSize:'0.8rem',color:'#333',lineHeight:1.5,whiteSpace:'pre-wrap',background:'white',padding:'8px',borderRadius:'6px',border:'1px solid #e8f5e9' }}>
                        {task.result_summary}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <TaskAttachments taskId={task.id} />
              
              <TaskExecutionLog
                taskId={task.id}
                executionLog={task.execution_log}
                remainingIssues={task.remaining_issues}
                improvementSuggestions={task.improvement_suggestions}
                onUpdate={(data) => handleUpdateLog(task.id, data)}
              />

              {/* Phase R — 横向排列 */}
              <div style={{ marginTop:'12px',padding:'12px',background:'#faf5ff',borderRadius:'8px',border:'1px solid #e9d5ff' }}>
                <div style={{ fontSize:'0.85rem',fontWeight:600,color:'#8b5cf6',marginBottom:'8px' }}>🧠 Phase R 思考过程</div>
                <div style={{ display:'flex',flexDirection:'row',gap:'6px',overflowX:'auto',paddingBottom:'4px' }}>
                  {['现状审查','目标对齐','Brainstorming','方案评估','子任务'].map((l,i) => {
                    const colors = ['#3b82f6','#8b5cf6','#f59e0b','#22c55e','#06b6d4'];
                    const log = (task.execution_log || '');
                    const has = log.includes('Phase R');
                    const kw = ['现状','目标','方案','选中','完成'];
                    let val = '';
                    if (has) {
                      const lines = (log || '').split('\n');
                      const found = lines.filter(ln => ln.includes(kw[i]));
                      val = found.length > 0 ? found[0].replace(kw[i]+':','').replace(kw[i]+'：','').trim().substring(0,150) : '';
                      if (!val && i === 4) val = '已生成';
                    }
                    return (
                      <div key={i} style={{ display:'flex',flexDirection:'column',alignItems:'center',gap:'4px',flex:'1',minWidth:'120px',padding:'8px',background:'white',borderRadius:'8px',border:'1px solid #e9d5ff' }}>
                        <div style={{ width:'24px',height:'24px',borderRadius:'50%',background:colors[i],display:'flex',alignItems:'center',justifyContent:'center',flexShrink:0,fontSize:'10px',color:'#fff',fontWeight:700 }}>{i + 1}</div>
                        <div style={{ fontSize:'0.7rem',fontWeight:600,color:colors[i],textAlign:'center' }}>{l}</div>
                        {val
                          ? <div style={{ fontSize:'0.65rem',color:'#555',lineHeight:1.4,textAlign:'center',wordBreak:'break-all' }}>{val.length > 60 ? val.substring(0,60) + '...' : val}</div>
                          : <div style={{ fontSize:'0.65rem',color:'#8b5cf6',textAlign:'center' }}>⏳</div>
                        }
                        {i < 4 && <div style={{ color:'#d1d5db',fontSize:'14px',marginTop:'2px' }}>→</div>}
                      </div>
                    );
                  })}
                </div>
              </div>

              {/* 反馈输入框 */}
              {feedbackTaskId === task.id && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px',
                  background: '#fff8e1',
                  borderRadius: '8px',
                  border: '1px solid #ffcc80'
                }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e65100', marginBottom: '8px' }}>
                    提供修改反馈
                  </div>
                  <textarea
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    placeholder="请描述需要修改的内容..."
                    style={{
                      width: '100%',
                      minHeight: '80px',
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem',
                      resize: 'vertical'
                    }}
                  />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px', justifyContent: 'flex-end' }}>
                    <button
                      onClick={() => {
                        setFeedbackTaskId(null)
                        setFeedbackText('')
                      }}
                      style={{
                        padding: '6px 12px',
                        border: '1px solid #ddd',
                        background: '#fff',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      取消
                    </button>
                    <button
                      onClick={() => handleSubmitFeedback(task.id)}
                      style={{
                        padding: '6px 12px',
                        border: 'none',
                        background: '#ff9800',
                        color: '#fff',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      提交反馈
                    </button>
                  </div>
                </div>
              )}

              {/* 审核历史记录 */}
              {reviewHistory[task.id] && reviewHistory[task.id].length > 0 && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px',
                  background: '#f5f5f5',
                  borderRadius: '8px'
                }}>
                  <div style={{ 
                    fontSize: '0.85rem', 
                    fontWeight: 600, 
                    color: '#666', 
                    marginBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <History size={14} />
                    审核历史
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {reviewHistory[task.id].map((item: any) => (
                      <div key={item.id} style={{
                        padding: '8px',
                        background: '#fff',
                        borderRadius: '4px',
                        borderLeft: `3px solid ${
                          item.action === 'approve' ? '#4caf50' :
                          item.action === 'reject' ? '#ef5350' :
                          item.action === 'feedback' ? '#ff9800' : '#999'
                        }`
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                            {item.action === 'approve' ? '✓ 通过' :
                             item.action === 'reject' ? '✗ 驳回' :
                             item.action === 'feedback' ? '💬 要求修改' : item.action}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#999' }}>
                            第{item.round_number}轮
                          </span>
                        </div>
                        {item.feedback && (
                          <div style={{ fontSize: '0.8rem', color: '#333', marginTop: '4px' }}>
                            {item.feedback}
                          </div>
                        )}
                        <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '4px' }}>
                          {new Date(item.created_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
