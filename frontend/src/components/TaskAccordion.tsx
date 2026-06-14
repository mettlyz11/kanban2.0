import { useState, useEffect } from 'react'
import { Maximize2, ChevronDown, ChevronUp, Trash2, CheckCircle, XCircle, MessageSquare, History, Sparkles, GitBranch, FileText } from 'lucide-react'
import { TaskAttachments } from "../components/TaskAttachments"

interface Task {
  project_name?: string; project_number?: string; task_type?: string;
  strategic_goal?: string; blocked_reason?: string; depends_on?: number;
  priority_score?: number; task_summary?: string; result_summary?: string;
  execution_log?: string; remaining_issues?: string; improvement_suggestions?: string;
  notes?: string; overall_status?: string; sds_verified?: number;
  ripple_upstream_ids?: any;
  id: number; number: string; title: string; status: string;
  priority: string; description?: string; created_at: string;
  review_round?: number; review_feedback?: string; goal_id?: number;
}

// Execution record interface
interface ExecutionRecord {
  id: number; version: number; status: string; duration_sec: number;
  trigger_type: string; result_summary: string; task_summary: string;
  files: any; started_at: string; completed_at: string; created_at: string;
  ripple_context?: string;
}

const statusColors: Record<string, {bg:string,text:string,dot:string}> = {
  'todo': {bg:'#fef2f2',text:'#991b1b',dot:'#ef4444'},
  'pending': {bg:'#fef2f2',text:'#991b1b',dot:'#ef4444'},
  'in_progress': {bg:'#eff6ff',text:'#1e40af',dot:'#3b82f6'},
  'pending_review': {bg:'#fefce8',text:'#854d0e',dot:'#f59e0b'},
  'completed': {bg:'#f0fdf4',text:'#166534',dot:'#10b981'},
  'failed_retryable': {bg:'#fff7ed',text:'#9a3412',dot:'#f97316'},
  'blocked': {bg:'#fef2f2',text:'#dc2626',dot:'#dc2626'},
};
const statusLabel: Record<string,string> = {
  'todo':'待办','pending':'待处理','in_progress':'进行中',
  'pending_review':'待审阅','completed':'已完成','failed_retryable':'可重试',
  'blocked':'已阻塞','cancelled':'已取消','failed':'失败',
};
const priorityMap: Record<string,{l:string,c:string,bg:string}> = {
  '1':{l:'高',c:'#991b1b',bg:'#fef2f2'},'high':{l:'高',c:'#991b1b',bg:'#fef2f2'},
  '2':{l:'中',c:'#854d0e',bg:'#fefce8'},'medium':{l:'中',c:'#854d0e',bg:'#fefce8'},
  '3':{l:'低',c:'#166534',bg:'#f0fdf4'},'low':{l:'低',c:'#166534',bg:'#f0fdf4'},
};
function getPrio(p:string) { return priorityMap[p] || {l:p||'-',c:'#666',bg:'#f5f5f5'}; }

// Format JSON descriptions - collapse long raw JSON
function smartDescription(desc: string | undefined, maxLen: number = 200): {display: string, isLong: boolean} {
  if (!desc) return {display: '', isLong: false};
  // Check if it's a big JSON block from SDS
  const isJsonSDS = desc.startsWith('{"') || desc.includes('── 涟漪');
  const display = isJsonSDS && desc.length > maxLen ? desc.slice(0, maxLen) + '...' : desc;
  return {display, isLong: desc.length > maxLen || isJsonSDS};
}

// Parse goal ID to label
const goalLabels: Record<number, string> = {
  1:'AI助手',2:'商业化',3:'学术',4:'财富',5:'家庭',6:'社会',7:'健康',8:'极光',
};

export function TaskAccordion({ tasks, onDeleteTask, onReviewTask, showReviewActions = false, onMaximize }: {
  tasks: Task[];
  onDeleteTask: (id: number) => void;
  onReviewTask?: (id: number, action: 'approve' | 'reject' | 'skip' | 'feedback', feedback?: string) => void;
  showReviewActions?: boolean;
}) {
  const [expandedTask, setExpandedTask] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<'overview'|'history'|'ripple'|'dep'|'ai'>('overview');
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [execLoading, setExecLoading] = useState(false);
  const [feedbackTaskId, setFeedbackTaskId] = useState<number | null>(null);
  const [feedbackText, setFeedbackText] = useState('');
  const [expandedDescs, setExpandedDescs] = useState<Set<number>>(new Set());
  const [reviewHistory, setReviewHistory] = useState<{[key: number]: any[]}>({});
  const [ripples, setRipples] = useState<any[]>([]);
  const [deps, setDeps] = useState<{prerequisites:any[],subsequents:any[],subtasks:any[]}>({prerequisites:[],subsequents:[],subtasks:[]});
  const [depsLoading, setDepsLoading] = useState(false);
  const [aiSummary, setAiSummary] = useState<string | null>(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [showFullDesc, setShowFullDesc] = useState<Set<number>>(new Set());

  // Fetch executions for a task
  const fetchExecutions = async (taskId: number) => {
    setExecLoading(true);
    try {
      const res = await fetch(`/api/tasks/${taskId}/executions`);
      const data = await res.json();
      if (data.success) setExecutions(data.records || []);
    } catch (e) { console.error(e); }
    setExecLoading(false);
  };

  // Fetch ripples for a task
  const fetchDeps = async (taskId: number) => {
    setDepsLoading(true);
    try {
      const res = await fetch('/api/tasks/' + taskId + '/dependencies');
      const data = await res.json();
      if (data.success) setDeps(data.dependencies);
    } catch (e) { console.error(e); }
    setDepsLoading(false);
  };
  const fetchRipples = async (taskId: number) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/ripples`);
      const data = await res.json();
      if (data.success) setRipples(data.ripples || []);
    } catch (e) { setRipples([]); }
  };

  const fetchReviewHistory = async (taskId: number) => {
    try {
      const res = await fetch(`/api/tasks/${taskId}/review-history`);
      const data = await res.json();
      if (data.success) setReviewHistory(p => ({...p, [taskId]: data.history}));
    } catch (e) {}
  };

  // Generate AI summary on demand
  const generateAiSummary = async (taskId: number) => {
    if (aiSummary) return;
    setAiLoading(true);
    try {
      const res = await fetch(`/api/tasks/${taskId}/ai-summary`);
      const data = await res.json();
      setAiSummary(data.summary || '无法生成摘要');
    } catch (e) { setAiSummary('AI摘要生成失败'); }
    setAiLoading(false);
  };

  const toggleExpand = (taskId: number) => {
    const expand = expandedTask !== taskId;
    setExpandedTask(expand ? taskId : null);
    setActiveTab('overview');
    setAiSummary(null);
    if (expand) {
      fetchExecutions(taskId);
      fetchRipples(taskId);
      fetchDeps(taskId);
      fetchReviewHistory(taskId);
    }
  };

  const handleSubmitFeedback = async (taskId: number) => {
    if (!feedbackText.trim()) return;
    if (onReviewTask) {
      onReviewTask(taskId, 'feedback', feedbackText);
      setFeedbackTaskId(null); setFeedbackText('');
    }
  };

  // Format duration
  const fmtDuration = (s: number) => {
    if (!s || s === 0) return '-';
    if (s < 60) return `${s}s`;
    if (s < 3600) return `${Math.floor(s/60)}m${s%60}s`;
    return `${Math.floor(s/3600)}h${Math.floor((s%3600)/60)}m`;
  };

  // Format a result_summary JSON into readable text
  const fmtResult = (rs: string | undefined): string => {
    if (!rs) return '';
    try {
      const o = JSON.parse(rs);
      if (o.files && Array.isArray(o.files)) {
        return o.files.map((f: any) => {
          const fn = f.name || f.filename || 'file';
          return '📄 ' + fn + ' (' + (f.size_bytes || f.size || '?') + 'B)';
        }).join('\n');
      }
      if (o.type) return `${o.type}: ${o.files?.length || 0} files`;
      return rs.slice(0, 200);
    } catch { return rs.slice(0, 300); }
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }} className="task-accordion">
      {tasks.map(task => {
        const prio = getPrio(task.priority);
        const sc = statusColors[task.status] || {bg:'#f5f5f5',text:'#666',dot:'#999'};
        const sd = smartDescription(task.description);
        const isExpanded = expandedTask === task.id;
        const showTaskSummary = task.status === 'completed' && task.task_summary;
        
        return (
          <div key={task.id} style={{ background:'#fff', borderRadius:'8px', border:'1px solid #e0e0e0', overflow:'hidden', position:'relative' }}>
            {/* L1+L2: STATUS-DIFFERENTIATED CARD HEADER */}
            <div onClick={() => toggleExpand(task.id)}
              style={{ display:'flex', alignItems:'center', padding:'10px 14px', cursor:'pointer',
                background: isExpanded ? '#f8f9fa' : '#fff',
                borderBottom: isExpanded ? '1px solid #e0e0e0' : 'none',
                gap: '10px', flexWrap: 'wrap' as const }}>
              <span style={{ color:'#667eea', flexShrink:0 }}>
                {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
              </span>
              
              {/* Status dot + task ID */}
              <span style={{ display:'inline-flex', alignItems:'center', gap:'4px', flexShrink:0,
                fontSize:'0.7rem', color:'#667eea', fontFamily:'monospace', fontWeight:600,
                background:'#f0f4ff', padding:'2px 8px', borderRadius:'4px' }}>
                <span style={{ width:'6px', height:'6px', borderRadius:'50%', background:sc.dot }}></span>
                #{task.id}
              </span>

              {/* Status badge */}
              <span style={{ fontSize:'0.7rem', padding:'2px 8px', borderRadius:'4px',
                background:sc.bg, color:sc.text, fontWeight:600, flexShrink:0 }}>
                {statusLabel[task.status] || task.status}
              </span>

              {/* Priority badge */}
              <span style={{ fontSize:'0.7rem', padding:'2px 8px', borderRadius:'4px',
                background:prio.bg, color:prio.c, fontWeight:600, flexShrink:0 }}>
                {prio.l}
              </span>

              {/* Goal tag */}
              {task.goal_id && (
                <span style={{ fontSize:'0.65rem', padding:'1px 6px', borderRadius:'4px',
                  background:'#e8f4fd', color:'#0369a1', border:'1px solid #bae6fd', flexShrink:0 }}>
                  {goalLabels[task.goal_id] || `#${task.goal_id}`}
                </span>
              )}

              {/* Project tag */}
              {task.project_name && (
                <span style={{ fontSize:'0.65rem', padding:'1px 6px', borderRadius:'4px',
                  background:'#f3e8ff', color:'#7c3aed', border:'1px solid #ddd6fe', flexShrink:0 }}>
                  {task.project_name.slice(0,20)}
                </span>
              )}

              {/* Strategic goal */}
              {task.strategic_goal && (
                <span style={{ fontSize:'0.65rem', padding:'1px 6px', borderRadius:'4px',
                  background:'#fef3c7', color:'#92400e', border:'1px solid #fde68a', flexShrink:0 }}>
                  {task.strategic_goal}
                </span>
              )}

              {/* Title (2 lines max) */}
              <span style={{ fontSize:'0.9rem', color:'#333', fontWeight:500,
                overflow:'hidden', textOverflow:'ellipsis', display:'-webkit-box',
                WebkitLineClamp:2, WebkitBoxOrient:'vertical', lineClamp:2,
                lineHeight:'1.3', maxHeight:'2.6em', flex:'1 1 auto' }}>
                {task.title}
              </span>

              {/* L1: Show task_summary badge for completed tasks */}
              {showTaskSummary && (
                <span style={{ fontSize:'0.7rem', color:'#166534', fontStyle:'italic',
                  background:'#f0fdf4', padding:'2px 6px', borderRadius:'4px',
                  whiteSpace:'nowrap', overflow:'hidden', textOverflow:'ellipsis', maxWidth:'200px' }}>
                  ✅ {task.task_summary?.slice(0,30)}...
                </span>
              )}

              {/* Blocked reason */}
              {task.status === 'blocked' && task.blocked_reason && (
                <span style={{ fontSize:'0.7rem', color:'#dc2626', flexShrink:0 }}
                  title={task.blocked_reason}>🔒 {task.blocked_reason.slice(0,15)}...</span>
              )}

              {/* Maximize button */}
              <button onClick={(e)=>{e.stopPropagation();if(onMaximize) onMaximize(task.id);}}
                style={{ background:'none', border:'none', color:'#667eea', cursor:'pointer',
                  padding:'4px', borderRadius:'4px', flexShrink:0, opacity:0.4 }}
                onMouseEnter={(e:any)=>{e.currentTarget.style.opacity=1}}
                onMouseLeave={(e:any)=>{e.currentTarget.style.opacity=0.4}}
                title="全屏查看"><Maximize2 size={14}/></button>
              {/* Remove button (on hover style) */}
              <button onClick={(e)=>{e.stopPropagation();onDeleteTask(task.id);}}
                style={{ background:'none', border:'none', color:'#ccc', cursor:'pointer',
                  padding:'4px', borderRadius:'4px', flexShrink:0, opacity:0.3 }}
                onMouseEnter={(e:any)=>{e.currentTarget.style.opacity=1;e.currentTarget.style.color='#c62828'}}
                onMouseLeave={(e:any)=>{e.currentTarget.style.opacity=0.3;e.currentTarget.style.color='#ccc'}}
                title="删除"><Trash2 size={14}/></button>
            </div>

            {/* EXPANDED CONTENT */}
            {isExpanded && (
              <div style={{ padding:'12px 16px', background:'#fafbfc' }}>
                {/* Tabs: Overview | Execution History | Ripple Chain | AI Summary */}
                <div style={{ display:'flex', gap:'4px', marginBottom:'12px', borderBottom:'1px solid #e0e0e0', paddingBottom:'8px' }}>
                  {[
                    {k:'overview' as const, l:'概览', icon:'📋'},
                    {k:'history' as const, l:'执行历史', icon:'📜'},
                    {k:'dep' as const, l:'依赖', icon:'🔗'},
                    {k:'ripple' as const, l:'涟漪链', icon:'🌊'},
                    {k:'ai' as const, l:'AI摘要', icon:'✨'},
                  ].map(tab => (
                    <button key={tab.k} onClick={() => { setActiveTab(tab.k); if(tab.k==='ai') generateAiSummary(task.id); }}
                      style={{ padding:'6px 12px', borderRadius:'6px', fontSize:'0.8rem', fontWeight:500,
                        border:'none', cursor:'pointer',
                        background: activeTab===tab.k ? '#e0e7ff' : 'transparent',
                        color: activeTab===tab.k ? '#4338ca' : '#666',
                        borderBottom: activeTab===tab.k ? '2px solid #4338ca' : '2px solid transparent' }}>
                      {tab.icon} {tab.l}
                    </button>
                  ))}
                </div>

                {/* ===== TAB: OVERVIEW ===== */}
                {activeTab === 'overview' && (
                  <div>
                    {/* L1: For completed tasks, show task_summary instead of raw description */}
                    {showTaskSummary ? (
                      <div style={{ marginBottom:'12px' }}>
                        <div style={{ fontSize:'0.75rem', fontWeight:600, color:'#166534', marginBottom:'4px' }}>
                          ✅ 任务摘要
                        </div>
                        <div style={{ fontSize:'0.85rem', color:'#333', lineHeight:'1.6', background:'#f0fdf4',
                          padding:'10px', borderRadius:'6px', border:'1px solid #bbf7d0', whiteSpace:'pre-wrap' }}>
                          {task.task_summary}
                        </div>
                      </div>
                    ) : (
                      /* L1: For non-completed, show description with folding */
                      task.description && (
                        <div style={{ marginBottom:'12px' }}>
                          <div style={{ fontSize:'0.75rem', fontWeight:600, color:'#666', marginBottom:'4px' }}>
                            📝 描述
                          </div>
                          <div style={{ fontSize:'0.85rem', color:'#333', lineHeight:'1.6', whiteSpace:'pre-wrap',
                            background:'#fff', padding:'8px', borderRadius:'4px', border:'1px solid #e5e7eb',
                            maxHeight: showFullDesc.has(task.id) ? 'none' : '200px',
                            overflow: showFullDesc.has(task.id) ? 'visible' : 'hidden',
                            position:'relative' as const }}>
                            {task.description}
                            {task.description.length > 500 && !showFullDesc.has(task.id) && (
                              <div style={{ position:'absolute', bottom:0, left:0, right:0,
                                height:'40px', background:'linear-gradient(transparent, #fff)', zIndex:1 }} />
                            )}
                          </div>
                          {task.description.length > 500 && (
                            <button onClick={() => setShowFullDesc(s => {const n=new Set(s); if(n.has(task.id)) n.delete(task.id); else n.add(task.id); return n;})}
                              style={{ fontSize:'0.75rem', color:'#4338ca', background:'none', border:'none',
                                cursor:'pointer', padding:'4px 0', marginTop:'4px' }}>
                              {showFullDesc.has(task.id) ? '收起 ↑' : '展开全部 ↓'}
                            </button>
                          )}
                        </div>
                      )
                    )}

                    {/* Result summary if available */}
                    {task.result_summary && (
                      <div style={{ marginBottom:'12px' }}>
                        <div style={{ fontSize:'0.75rem', fontWeight:600, color:'#666', marginBottom:'4px' }}>
                          📦 产出
                        </div>
                        <div style={{ fontSize:'0.85rem', color:'#333', background:'#f0fdf4',
                          padding:'8px', borderRadius:'4px', border:'1px solid #bbf7d0', whiteSpace:'pre-wrap' }}>
                          {(() => {
                            try {
                              const o = JSON.parse(task.result_summary!);
                              if (o.files && Array.isArray(o.files)) {
                                return o.files.map((f: any) => {
                                  const fn = f.name || f.filename || 'file';
                                  return '\ud83d\udcc4 ' + fn + ' (' + (f.size_bytes || f.size || '?') + 'B)';
                                }).join('\n');
                              }
                              return task.result_summary!.slice(0, 300);
                            } catch { return task.result_summary!.slice(0, 300); }
                          })()}
                        </div>
                      </div>
                    )}

                    {/* Execution log (collapsed by default) */}
                    {task.execution_log && (
                      <div style={{ marginBottom:'12px' }}>
                        <details style={{ fontSize:'0.8rem' }}>
                          <summary style={{ fontWeight:600, color:'#666', cursor:'pointer', padding:'4px 0' }}>
                            📋 执行日志 ({task.execution_log.length}字符)
                          </summary>
                          <pre style={{ fontSize:'0.75rem', lineHeight:'1.5', color:'#374151',
                            background:'#f9fafb', padding:'8px', borderRadius:'4px',
                            border:'1px solid #e5e7eb', marginTop:'4px',
                            maxHeight:'300px', overflow:'auto', whiteSpace:'pre-wrap' }}>
                            {task.execution_log}
                          </pre>
                        </details>
                      </div>
                    )}

                    {/* Notes if available */}
                    {task.notes && (
                      <div style={{ marginBottom:'12px' }}>
                        <div style={{ fontSize:'0.75rem', fontWeight:600, color:'#666', marginBottom:'4px' }}>
                          📌 备注
                        </div>
                        <div style={{ fontSize:'0.85rem', color:'#333', whiteSpace:'pre-wrap',
                          background:'#fffbeb', padding:'8px', borderRadius:'4px', border:'1px solid #fde68a' }}>
                          {task.notes}
                        </div>
                      </div>
                    )}

                    {/* Remaining issues */}
                    {task.remaining_issues && (
                      <div style={{ marginBottom:'12px' }}>
                        <div style={{ fontSize:'0.75rem', fontWeight:600, color:'#dc2626', marginBottom:'4px' }}>
                          ⚠️ 待解决问题
                        </div>
                        <div style={{ fontSize:'0.85rem', color:'#333', whiteSpace:'pre-wrap',
                          background:'#fef2f2', padding:'8px', borderRadius:'4px', border:'1px solid #fecaca' }}>
                          {task.remaining_issues}
                        </div>
                      </div>
                    )}

                    {/* Review actions */}
                    {showReviewActions && task.status === 'pending_review' && onReviewTask && (
                      <div style={{ display:'flex', gap:'8px', marginBottom:'12px', flexWrap:'wrap' }}>
                        <button onClick={(e)=>{e.stopPropagation();onReviewTask!(task.id,'approve');}}
                          style={{ background:'#e8f5e9', border:'1px solid #4caf50', color:'#2e7d32',
                            cursor:'pointer', padding:'6px 12px', borderRadius:'4px',
                            display:'flex', alignItems:'center', gap:'4px', fontSize:'0.8rem', fontWeight:500 }}>
                          <CheckCircle size={14}/> ✅ 通过
                        </button>
                        <button onClick={(e)=>{e.stopPropagation();setFeedbackTaskId(task.id);}}
                          style={{ background:'#fff3e0', border:'1px solid #ff9800', color:'#e65100',
                            cursor:'pointer', padding:'6px 12px', borderRadius:'4px',
                            display:'flex', alignItems:'center', gap:'4px', fontSize:'0.8rem', fontWeight:500 }}>
                          <MessageSquare size={14}/> 💬 要求修改
                        </button>
                        <button onClick={(e)=>{e.stopPropagation();onReviewTask!(task.id,'reject');}}
                          style={{ background:'#ffebee', border:'1px solid #ef5350', color:'#c62828',
                            cursor:'pointer', padding:'6px 12px', borderRadius:'4px',
                            display:'flex', alignItems:'center', gap:'4px', fontSize:'0.8rem', fontWeight:500 }}>
                          <XCircle size={14}/> ❌ 驳回
                        </button>
                      </div>
                    )}

                    {/* Feedback input */}
                    {feedbackTaskId === task.id && (
                      <div style={{ padding:'10px', background:'#fff8e1', borderRadius:'8px',
                        border:'1px solid #ffcc80', marginBottom:'12px' }}>
                        <div style={{ fontSize:'0.8rem', fontWeight:600, color:'#e65100', marginBottom:'8px' }}>
                          提供修改反馈
                        </div>
                        <textarea value={feedbackText} onChange={e=>setFeedbackText(e.target.value)}
                          placeholder="请描述需要修改的内容..."
                          style={{ width:'100%', minHeight:'60px', padding:'8px', borderRadius:'4px',
                            border:'1px solid #ddd', fontSize:'0.85rem', resize:'vertical' }} />
                        <div style={{ display:'flex', gap:'8px', marginTop:'8px', justifyContent:'flex-end' }}>
                          <button onClick={()=>{setFeedbackTaskId(null);setFeedbackText('');}}
                            style={{ padding:'6px 12px', border:'1px solid #ddd', background:'#fff',
                              borderRadius:'4px', cursor:'pointer', fontSize:'0.8rem' }}>取消</button>
                          <button onClick={()=>handleSubmitFeedback(task.id)}
                            style={{ padding:'6px 12px', border:'none', background:'#ff9800', color:'#fff',
                              borderRadius:'4px', cursor:'pointer', fontSize:'0.8rem' }}>提交反馈</button>
                        </div>
                      </div>
                    )}

                    {/* Attachments */}
                    <TaskAttachments taskId={task.id} />

                    {/* Review history */}
                    {reviewHistory[task.id]?.length > 0 && (
                      <div style={{ marginTop:'12px', padding:'8px', background:'#f5f5f5', borderRadius:'8px' }}>
                        <div style={{ fontSize:'0.85rem', fontWeight:600, color:'#666', marginBottom:'6px',
                          display:'flex', alignItems:'center', gap:'6px' }}>
                          <History size={14}/> 审核历史
                        </div>
                        {reviewHistory[task.id].map((item:any) => (
                          <div key={item.id} style={{ padding:'6px', background:'#fff', borderRadius:'4px',
                            borderLeft:`3px solid ${
                              item.action==='approve'?'#4caf50':item.action==='reject'?'#ef5350':
                              item.action==='feedback'?'#ff9800':'#999'}`, marginBottom:'4px' }}>
                            <div style={{ display:'flex', justifyContent:'space-between', marginBottom:'2px' }}>
                              <span style={{ fontSize:'0.8rem', fontWeight:600 }}>
                                {item.action==='approve'?'✓ 通过':item.action==='reject'?'✗ 驳回':
                                 item.action==='feedback'?'💬 要求修改':item.action}
                              </span>
                              <span style={{ fontSize:'0.7rem', color:'#999' }}>第{item.round_number}轮</span>
                            </div>
                            {item.feedback && <div style={{ fontSize:'0.8rem', color:'#333' }}>{item.feedback}</div>}
                          </div>
                        ))}
                      </div>
                    )}

                    <div style={{ fontSize:'0.75rem', color:'#999', marginTop:'8px' }}>
                      #{task.id} · 创建 {new Date(task.created_at).toLocaleString('zh-CN')}
                      {task.overall_status && ` · ${task.overall_status}`}
                      {task.sds_verified === 1 && ' · ✅ SDS验证通过'}
                    </div>
                  </div>
                )}

                {/* ===== TAB: EXECUTION HISTORY ===== */}
                {activeTab === 'history' && (
                  <div>
                    <div style={{ fontSize:'0.8rem', fontWeight:600, color:'#666', marginBottom:'8px',
                      display:'flex', alignItems:'center', gap:'6px' }}>
                      <History size={14}/> 执行历史（共{executions.length}次）
                    </div>
                    {execLoading ? (
                      <div style={{ textAlign:'center', padding:'20px', color:'#999' }}>加载中...</div>
                    ) : executions.length === 0 ? (
                      <div style={{ textAlign:'center', padding:'20px', color:'#999' }}>暂无执行记录</div>
                    ) : (
                      <div style={{ display:'flex', flexDirection:'column', gap:'6px' }}>
                        {executions.map((exec, idx) => {
                          const prevExec = idx < executions.length - 1 ? executions[idx + 1] : null;
                          const duration = exec.duration_sec ? fmtDuration(exec.duration_sec) : '-';
                          const hasImprovement = exec.task_summary && prevExec?.task_summary && 
                            exec.task_summary !== prevExec.task_summary;
                          return (
                            <div key={exec.id} style={{
                              padding:'10px', borderRadius:'6px',
                              background: exec.status === 'completed' ? '#f0fdf4' :
                                exec.status === 'failed_retryable' ? '#fff7ed' :
                                exec.status === 'pending_review' ? '#fefce8' :
                                exec.status === 'failed' ? '#fef2f2' : '#f9fafb',
                              border: `1px solid ${
                                exec.status === 'completed' ? '#bbf7d0' :
                                exec.status === 'failed_retryable' ? '#fed7aa' :
                                exec.status === 'pending_review' ? '#fde68a' :
                                exec.status === 'failed' ? '#fecaca' : '#e5e7eb'}`
                            }}>
                              {/* Header line: version + status + duration */}
                              <div style={{ display:'flex', alignItems:'center', gap:'8px', flexWrap:'wrap', marginBottom:'4px' }}>
                                <span style={{ fontWeight:700, fontSize:'0.85rem', fontFamily:'monospace',
                                  color:'#4338ca', background:'#e0e7ff', padding:'1px 8px', borderRadius:'4px' }}>
                                  v{exec.version}
                                </span>
                                <span style={{ fontSize:'0.75rem', fontWeight:600,
                                  color: exec.status==='completed'?'#166534':exec.status==='failed_retryable'?'#9a3412':
                                    exec.status==='pending_review'?'#854d0e':exec.status==='failed'?'#991b1b':'#666' }}>
                                  {statusLabel[exec.status] || exec.status}
                                </span>
                                <span style={{ fontSize:'0.7rem', color:'#999' }}>
                                  ⏱ {duration} · {exec.trigger_type || 'auto'}
                                </span>
                                {exec.started_at && (
                                  <span style={{ fontSize:'0.7rem', color:'#999' }}>
                                    {new Date(exec.started_at).toLocaleString('zh-CN')}
                                  </span>
                                )}
                              </div>

                              {/* v1: 干了什么 - always show task_summary */}
                              {exec.task_summary && (
                                <div style={{ marginTop:'4px' }}>
                                  <span style={{ fontSize:'0.72rem', fontWeight:600, color:'#666' }}>
                                    {exec.version === 1 ? '📌 做了：' : '📌 优化：'}
                                  </span>
                                  <span style={{ fontSize:'0.8rem', color:'#333' }}>
                                    {exec.task_summary}
                                  </span>
                                </div>
                              )}

                              {/* v2+: 改进了什么 - show diff from previous */}
                              {exec.version > 1 && (() => {
                                const rc = exec.ripple_context ? (() => { try { return JSON.parse(exec.ripple_context); } catch { return null; } })() : null;
                                const impText = rc?.improvements || '';
                                if (!impText && !hasImprovement) return null;
                                return (
                                  <div style={{ marginTop:'4px', padding:'4px 8px', background:'#e0f2fe',
                                    borderRadius:'4px', border:'1px solid #bae6fd', fontSize:'0.78rem', color:'#0369a1' }}>
                                    <span style={{ fontWeight:600 }}>🔄 相较 v{prevExec.version} 改进了：</span>
                                    <span>{impText || (exec.task_summary && prevExec?.task_summary && exec.task_summary !== prevExec.task_summary ? '执行策略调整（具体内容待完善）' : '改进点待记录')}</span>
                                  </div>
                                );
                              })()}

                              {/* Result summary - files */}
                              {exec.result_summary && (
                                <div style={{ marginTop:'4px', display:'flex', gap:'4px', flexWrap:'wrap' }}>
                                  {(() => {
                                    try {
                                      const rs = JSON.parse(exec.result_summary);
                                      if (rs.files) return rs.files.map((f:any, i:number) => (
                                        <span key={i} style={{ fontSize:'0.72rem', background:'#f0fdf4',
                                          color:'#166534', padding:'1px 6px', borderRadius:'4px',
                                          border:'1px solid #bbf7d0' }}>
                                          📄 {f.name || f.filename || `file_${i}`}
                                          {f.size_bytes ? ` (${Math.round(f.size_bytes/1024)}KB)` : ''}
                                        </span>
                                      ));
                                      return <span style={{ fontSize:'0.72rem', color:'#666' }}>{exec.result_summary.slice(0,80)}</span>;
                                    } catch {
                                      return <span style={{ fontSize:'0.72rem', color:'#666' }}>{exec.result_summary}</span>;
                                    }
                                  })()}
                                </div>
                              )}
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>
                )}

                {/* ===== TAB: RIPPLE CHAIN ===== */}
                {activeTab === 'ripple' && (
                  <div>
                    <div style={{ fontSize:'0.8rem', fontWeight:600, color:'#8b5cf6', marginBottom:'8px',
                      display:'flex', alignItems:'center', gap:'6px' }}>
                      <GitBranch size={14}/> 涟漪链
                    </div>
                    {(() => {
                      let ids = (task as any).ripple_upstream_ids;
                      if (typeof ids === 'string') { try { ids = JSON.parse(ids); } catch { ids = []; } }
                      if (!Array.isArray(ids)) ids = ripples.length > 0 ? ripples.map(r => r.task_id) : [];
                      if (ids.length > 0) {
                        return (
                          <div>
                            <div style={{ fontSize:'0.68rem', color:'#94a3b8', marginBottom:'4px' }}>
                              共 {ids.length} 个上游任务
                            </div>
                            <div style={{ display:'flex', flexWrap:'wrap', gap:'4px' }}>
                              {ids.map((rid: number) => (
                                <span key={rid} style={{ padding:'1px 8px', background:'#f5f3ff', borderRadius:'10px',
                                  border:'1px solid #e0e7ff', fontSize:'0.75rem', fontWeight:600, color:'#8b5cf6' }}>
                                  #{rid}
                                </span>
                              ))}
                            </div>
                          </div>
                        );
                      }
                      return <div style={{ textAlign:'center', padding:'20px', color:'#999' }}>暂无涟漪链数据</div>;
                    })()}
                  </div>
                )}

                {/* ===== TAB: DEPENDENCY ===== */}
                {activeTab === 'dep' && (
                  <div>
                    <div style={{ fontSize:'0.8rem', fontWeight:600, color:'#666', marginBottom:'8px',
                      display:'flex', alignItems:'center', gap:'6px' }}>
                      <GitBranch size={14}/> 依赖关系
                    </div>
                    {depsLoading ? (
                      <div style={{ textAlign:'center', padding:'20px', color:'#999' }}>加载中...</div>
                    ) : (
                      <div>
                        <div style={{ fontSize:'0.72rem', fontWeight:600, color:'#64748b', margin:'8px 0 4px' }}>
                          前置依赖 ({deps.prerequisites.length})
                        </div>
                        {deps.prerequisites.length > 0 ? deps.prerequisites.map((dep: any) => (
                          <div key={dep.id} style={{ display:'flex', alignItems:'center', gap:'6px',
                            padding:'6px 10px', margin:'3px 0', background:'#f1f5f9', borderRadius:'6px', fontSize:'0.8rem' }}>
                            <span style={{ fontWeight:600, color:'#64748b' }}>#{dep.id}</span>
                            <span style={{ flex:1 }}>{dep.title || dep.name || ''}</span>
                          </div>
                        )) : <div style={{ fontSize:'0.72rem', color:'#94a3b8', padding:'8px' }}>暂无前置依赖</div>}

                        <div style={{ fontSize:'0.72rem', fontWeight:600, color:'#64748b', margin:'12px 0 4px' }}>
                          后续依赖 ({deps.subsequents.length})
                        </div>
                        {deps.subsequents.length > 0 ? deps.subsequents.map((dep: any) => (
                          <div key={dep.id} style={{ display:'flex', alignItems:'center', gap:'6px',
                            padding:'6px 10px', margin:'3px 0', background:'#f1f5f9', borderRadius:'6px', fontSize:'0.8rem' }}>
                            <span style={{ fontWeight:600, color:'#64748b' }}>#{dep.id}</span>
                            <span style={{ flex:1 }}>{dep.title || dep.name || ''}</span>
                          </div>
                        )) : <div style={{ fontSize:'0.72rem', color:'#94a3b8', padding:'8px' }}>暂无后续依赖</div>}

                        <div style={{ fontSize:'0.72rem', fontWeight:600, color:'#64748b', margin:'12px 0 4px' }}>
                          子任务 ({deps.subtasks.length})
                        </div>
                        {deps.subtasks.length > 0 ? deps.subtasks.map((dep: any) => (
                          <div key={dep.id} style={{ display:'flex', alignItems:'center', gap:'6px',
                            padding:'6px 10px', margin:'3px 0', background:'#f1f5f9', borderRadius:'6px', fontSize:'0.8rem' }}>
                            <span style={{ fontWeight:600, color:'#64748b' }}>#{dep.id}</span>
                            <span style={{ flex:1 }}>{dep.title || dep.name || ''}</span>
                          </div>
                        )) : <div style={{ fontSize:'0.72rem', color:'#94a3b8', padding:'8px' }}>暂无子任务</div>}
                      </div>
                    )}
                  </div>
                )}

                {/* ===== TAB: AI SUMMARY ===== */}
                {activeTab === 'ai' && (
                  <div>
                    <div style={{ fontSize:'0.8rem', fontWeight:600, color:'#666', marginBottom:'8px',
                      display:'flex', alignItems:'center', gap:'6px' }}>
                      <Sparkles size={14}/> AI 实时摘要
                    </div>
                    {aiLoading ? (
                      <div style={{ textAlign:'center', padding:'20px', color:'#999' }}>
                        生成中...
                      </div>
                    ) : aiSummary ? (
                      <div style={{ padding:'12px', background:'#f0f9ff', borderRadius:'8px',
                        border:'1px solid #bae6fd', fontSize:'0.85rem', lineHeight:'1.6', color:'#333',
                        whiteSpace:'pre-wrap' }}>
                        {aiSummary}
                      </div>
                    ) : (
                      <div style={{ textAlign:'center', padding:'20px', color:'#999' }}>
                        <Sparkles size={32} style={{ margin:'0 auto 8px', display:'block', opacity:0.3 }}/>
                        <p>点击上方「AI摘要」标签生成人话摘要</p>
                      </div>
                    )}
                  </div>
                )}

              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
