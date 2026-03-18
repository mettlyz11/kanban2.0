import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { ChevronDown, ChevronUp, Clock, Settings, FileText, CheckCircle } from 'lucide-react'

interface TaskHistory {
  id: number
  task_id: number
  action: string
  details: string
  created_at: string
  performed_by: string
}

interface GearExecution {
  id: number
  task_id: number
  gear_name: string
  status: string
  output: string
  started_at: string
  completed_at: string
}

interface Task {
  id: number
  number: string
  title: string
  description: string
  project_name: string
  priority: string
  status: string
  result_summary: string
  details?: string
  created_at: string
  updated_at: string
  history?: TaskHistory[]
  gear_executions?: GearExecution[]
  // 结论字段
  conclusion_type?: string
  conclusion_passed?: boolean
  conclusion_execute?: boolean
  conclusion_audit_content?: string
}

export function Tasks() {
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [expandedTasks, setExpandedTasks] = useState<Set<number>>(new Set())
  const [taskDetails, setTaskDetails] = useState<Record<number, { history: TaskHistory[], gears: GearExecution[] }>>({})

  useEffect(() => {
    loadTasks()
  }, [filter])

  const loadTasks = async () => {
    try {
      const data = await api.getTasks(filter ? { status: filter } : {})
      if (data.success) setTasks(data.tasks)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const loadTaskDetails = async (taskId: number) => {
    try {
      const data = await api.getTaskHistory(taskId)
      if (data.success) {
        setTaskDetails(prev => ({
          ...prev,
          [taskId]: {
            history: data.history || [],
            gears: data.gear_executions || []
          }
        }))
      }
    } catch (e) {
      console.error('Failed to load task details:', e)
    }
  }

  const toggleExpand = async (taskId: number) => {
    const newExpanded = new Set(expandedTasks)
    if (newExpanded.has(taskId)) {
      newExpanded.delete(taskId)
    } else {
      newExpanded.add(taskId)
      // 加载详情
      if (!taskDetails[taskId]) {
        await loadTaskDetails(taskId)
      }
    }
    setExpandedTasks(newExpanded)
  }

  const handleStatusChange = async (taskId: number, newStatus: string) => {
    const res = await api.updateTask(taskId, { status: newStatus })
    if (res.success) {
      loadTasks()
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <h2 className="page-title">✅ 任务管理</h2>
      
      <div className="filter-bar">
        {[
          { key: '', label: '全部' },
          { key: 'todo', label: '待办' },
          { key: 'progress', label: '进行中' },
          { key: 'done', label: '已完成' }
        ].map(item => (
          <button
            key={item.key || 'all'}
            className={`filter-btn ${filter === item.key ? 'active' : ''}`}
            onClick={() => setFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div className="card">
        <div className="table-container">
          <table className="data-table" style={{ tableLayout: 'fixed' }}>
            <thead>
              <tr>
                <th style={{ width: '40px' }}></th>
                <th>任务</th>
                <th style={{ width: '120px' }}>项目</th>
                <th style={{ width: '80px' }}>优先级</th>
                <th style={{ width: '100px' }}>状态</th>
                <th style={{ width: '120px' }}>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="empty-state">暂无任务</td>
                </tr>
              ) : (
                tasks.map(t => (
                  <>
                    <tr key={t.id} style={{ cursor: 'pointer' }} onClick={() => toggleExpand(t.id)}>
                      <td>
                        <button 
                          className="expand-btn"
                          onClick={(e) => { e.stopPropagation(); toggleExpand(t.id); }}
                          style={{ 
                            background: 'none', 
                            border: 'none', 
                            cursor: 'pointer',
                            padding: '4px'
                          }}
                        >
                          {expandedTasks.has(t.id) ? 
                            <ChevronUp size={18} color="#667eea" /> : 
                            <ChevronDown size={18} color="#999" />
                          }
                        </button>
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <span style={{ fontSize: '0.75rem', color: '#667eea', fontWeight: 600, fontFamily: 'monospace' }}>{t.number || `T-${t.id}`}</span>
                          <strong>{t.title}</strong>
                        </div>
                      </td>
                      <td>{t.project_name || '-'}</td>
                      <td>
                        <span className={`badge ${
                          t.priority === 'high' ? 'badge-red' : 
                          t.priority === 'medium' ? 'badge-orange' : 'badge-green'
                        }`}>
                          {t.priority === 'high' ? '高' : t.priority === 'medium' ? '中' : '低'}
                        </span>
                      </td>
                      <td>
                        <span className={`status-badge status-${t.status}`}>
                          {t.status === 'todo' ? '待办' : t.status === 'progress' ? '进行中' : '已完成'}
                        </span>
                      </td>
                      <td onClick={(e) => e.stopPropagation()}>
                        <select 
                          value={t.status}
                          onChange={(e) => handleStatusChange(t.id, e.target.value)}
                          style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #ddd' }}
                        >
                          <option value="todo">待办</option>
                          <option value="progress">进行中</option>
                          <option value="done">已完成</option>
                        </select>
                      </td>
                    </tr>
                    {expandedTasks.has(t.id) && (
                      <tr className="task-details-row">
                        <td colSpan={6} style={{ padding: 0, background: '#f8f9fa' }}>
                          <TaskDetailPanel 
                            task={t} 
                            details={taskDetails[t.id] || { history: [], gears: [] }}
                            loading={!taskDetails[t.id]}
                          />
                        </td>
                      </tr>
                    )}
                  </>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

// 任务详情面板组件
function TaskDetailPanel({ task, details, loading }: { 
  task: Task; 
  details: { history: TaskHistory[], gears: GearExecution[] };
  loading: boolean;
}) {
  const [activeTab, setActiveTab] = useState<'description' | 'history' | 'gears' | 'summary' | 'conclusion'>('description')
  const [editingConclusion, setEditingConclusion] = useState(false)
  const [conclusionData, setConclusionData] = useState({
    type: task.conclusion_type || '',
    passed: task.conclusion_passed ?? false,
    execute: task.conclusion_execute ?? false,
    auditContent: task.conclusion_audit_content || ''
  })

  const saveConclusion = async () => {
    try {
      await api.updateTask(task.id, {
        conclusion_type: conclusionData.type,
        conclusion_passed: conclusionData.passed,
        conclusion_execute: conclusionData.execute,
        conclusion_audit_content: conclusionData.auditContent
      })
      setEditingConclusion(false)
      alert('结论已保存')
    } catch (e) {
      alert('保存失败')
    }
  }

  if (loading) {
    return (
      <div style={{ padding: '20px', textAlign: 'center', color: '#999' }}>
        加载详情中...
      </div>
    )
  }

  return (
    <div style={{ padding: '20px' }}>
      {/* Tab 导航 */}
      <div style={{ display: 'flex', gap: '8px', marginBottom: '16px', borderBottom: '2px solid #e0e0e0' }}>
        <TabButton 
          active={activeTab === 'description'} 
          onClick={() => setActiveTab('description')}
          icon={<FileText size={16} />}
          label="任务描述"
        />
        <TabButton 
          active={activeTab === 'history'} 
          onClick={() => setActiveTab('history')}
          icon={<Clock size={16} />}
          label={`执行历史 (${details.history.length})`}
        />
        <TabButton 
          active={activeTab === 'gears'} 
          onClick={() => setActiveTab('gears')}
          icon={<Settings size={16} />}
          label={`齿轮执行 (${details.gears.length})`}
        />
        <TabButton 
          active={activeTab === 'summary'} 
          onClick={() => setActiveTab('summary')}
          icon={<CheckCircle size={16} />}
          label="结论总结"
        />
        <TabButton 
          active={activeTab === 'conclusion'} 
          onClick={() => setActiveTab('conclusion')}
          icon={<CheckCircle size={16} />}
          label="任务结论"
        />
      </div>

      {/* Tab 内容 */}
      <div style={{ minHeight: '150px' }}>
        {activeTab === 'description' && (
          <div>
            <h4 style={{ margin: '0 0 12px 0', color: '#333' }}>任务描述</h4>
            <p style={{ 
              color: '#555', 
              lineHeight: 1.6, 
              background: '#fff', 
              padding: '16px', 
              borderRadius: '8px',
              border: '1px solid #e0e0e0'
            }}>
              {task.description || '暂无描述'}
            </p>
            <div style={{ marginTop: '12px', fontSize: '0.85rem', color: '#999' }}>
              创建时间: {new Date(task.created_at).toLocaleString('zh-CN')} | 
              更新时间: {new Date(task.updated_at).toLocaleString('zh-CN')}
            </div>
          </div>
        )}

        {activeTab === 'history' && (
          <div>
            <h4 style={{ margin: '0 0 12px 0', color: '#333' }}>执行历史</h4>
            {details.history.length === 0 ? (
              <EmptyState message="暂无执行历史记录" />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {details.history.map((h, idx) => (
                  <HistoryItem key={h.id} history={h} index={idx + 1} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'gears' && (
          <div>
            <h4 style={{ margin: '0 0 12px 0', color: '#333' }}>齿轮执行详情</h4>
            {details.gears.length === 0 ? (
              <EmptyState message="暂无齿轮执行记录" />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {details.gears.map((g) => (
                  <GearItem key={g.id} gear={g} />
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'summary' && (
          <div>
            <h4 style={{ margin: '0 0 12px 0', color: '#333' }}>结论总结</h4>
            {task.result_summary ? (
              <div style={{ 
                background: '#e8f5e9', 
                padding: '16px', 
                borderRadius: '8px',
                border: '1px solid #4caf50'
              }}>
                <pre style={{ 
                  margin: 0, 
                  whiteSpace: 'pre-wrap', 
                  wordWrap: 'break-word',
                  fontFamily: 'inherit',
                  color: '#2e7d32'
                }}>
                  {task.result_summary}
                </pre>
              </div>
            ) : task.details ? (
              <div style={{ 
                background: '#f0f4ff', 
                padding: '16px', 
                borderRadius: '8px',
                border: '1px solid #667eea'
              }}>
                <div style={{ fontSize: '0.8rem', color: '#667eea', marginBottom: '8px' }}>
                  执行历史（自动生成）
                </div>
                <pre style={{ 
                  margin: 0, 
                  whiteSpace: 'pre-wrap', 
                  wordWrap: 'break-word',
                  fontFamily: 'inherit',
                  color: '#333',
                  maxHeight: '300px',
                  overflow: 'auto'
                }}>
                  {task.details}
                </pre>
              </div>
            ) : (
              <EmptyState message="暂无结论总结" />
            )}
          </div>
        )}

        {activeTab === 'conclusion' && (
          <ConclusionPanel 
            editing={editingConclusion}
            setEditing={setEditingConclusion}
            data={conclusionData}
            setData={setConclusionData}
            onSave={saveConclusion}
          />
        )}
      </div>
    </div>
  )
}

function TabButton({ active, onClick, icon, label }: { 
  active: boolean; 
  onClick: () => void; 
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        padding: '10px 16px',
        background: active ? '#667eea' : 'transparent',
        color: active ? '#fff' : '#666',
        border: 'none',
        borderRadius: active ? '6px 6px 0 0' : '6px',
        cursor: 'pointer',
        fontWeight: active ? 600 : 400,
        transition: 'all 0.2s'
      }}
    >
      {icon}
      {label}
    </button>
  )
}

function HistoryItem({ history, index }: { history: TaskHistory; index: number }) {
  return (
    <div style={{
      background: '#fff',
      padding: '12px 16px',
      borderRadius: '8px',
      border: '1px solid #e0e0e0',
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'flex-start'
    }}>
      <div>
        <div style={{ fontWeight: 600, color: '#333', marginBottom: '4px' }}>
          #{index} {history.action}
        </div>
        {history.details && (
          <div style={{ color: '#666', fontSize: '0.9rem' }}>{history.details}</div>
        )}
      </div>
      <div style={{ textAlign: 'right', fontSize: '0.85rem', color: '#999' }}>
        <div>{new Date(history.created_at).toLocaleString('zh-CN')}</div>
        <div>{history.performed_by || '系统'}</div>
      </div>
    </div>
  )
}

function GearItem({ gear }: { gear: GearExecution }) {
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'success': return '#28a745'
      case 'failed': return '#dc3545'
      case 'running': return '#007bff'
      default: return '#ffc107'
    }
  }

  return (
    <div style={{
      background: '#fff',
      padding: '12px 16px',
      borderRadius: '8px',
      border: '1px solid #e0e0e0'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
        <div style={{ fontWeight: 600, color: '#333' }}>{gear.gear_name}</div>
        <span style={{
          padding: '4px 10px',
          borderRadius: '12px',
          fontSize: '0.75rem',
          fontWeight: 600,
          background: `${getStatusColor(gear.status)}20`,
          color: getStatusColor(gear.status)
        }}>
          {gear.status === 'success' ? '成功' : gear.status === 'failed' ? '失败' : gear.status === 'running' ? '运行中' : gear.status}
        </span>
      </div>
      {gear.output && (
        <div style={{ 
          background: '#f5f5f5', 
          padding: '8px', 
          borderRadius: '4px',
          fontSize: '0.85rem',
          color: '#666',
          fontFamily: 'monospace',
          maxHeight: '100px',
          overflow: 'auto'
        }}>
          {gear.output}
        </div>
      )}
      <div style={{ marginTop: '8px', fontSize: '0.8rem', color: '#999' }}>
        开始: {new Date(gear.started_at).toLocaleString('zh-CN')}
        {gear.completed_at && ` | 完成: ${new Date(gear.completed_at).toLocaleString('zh-CN')}`}
      </div>
    </div>
  )
}

// 结论面板组件
function ConclusionPanel({ editing, setEditing, data, setData, onSave }: {
  editing: boolean;
  setEditing: (v: boolean) => void;
  data: { type: string; passed: boolean; execute: boolean; auditContent: string };
  setData: (d: any) => void;
  onSave: () => void;
}) {
  if (!editing) {
    return (
      <div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h4 style={{ margin: 0, color: '#333' }}>任务结论</h4>
          <button 
            onClick={() => setEditing(true)}
            className="btn btn-secondary"
            style={{ padding: '6px 12px', fontSize: '0.85rem' }}
          >
            编辑结论
          </button>
        </div>
        
        {data.type ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ background: '#f8f9fa', padding: '12px 16px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>结论类型</div>
              <div style={{ fontWeight: 600, color: '#333' }}>
                {data.type === 'tech_eval' ? '技术评估' : data.type}
              </div>
            </div>
            <div style={{ background: data.passed ? '#e8f5e9' : '#ffebee', padding: '12px 16px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>评估结果</div>
              <div style={{ fontWeight: 600, color: data.passed ? '#2e7d32' : '#c62828' }}>
                {data.passed ? '✅ 通过' : '❌ 未通过'}
              </div>
            </div>
            <div style={{ background: data.execute ? '#e3f2fd' : '#f5f5f5', padding: '12px 16px', borderRadius: '8px' }}>
              <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>执行决策</div>
              <div style={{ fontWeight: 600, color: data.execute ? '#1565c0' : '#666' }}>
                {data.execute ? '🚀 需要执行' : '⏸️ 暂不执行'}
              </div>
            </div>
            {data.auditContent && (
              <div style={{ background: '#fff3e0', padding: '12px 16px', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>审核要求</div>
                <div style={{ color: '#333', whiteSpace: 'pre-wrap' }}>{data.auditContent}</div>
              </div>
            )}
          </div>
        ) : (
          <EmptyState message="暂无结论，请点击编辑添加" />
        )}
      </div>
    );
  }
  
  return (
    <div>
      <h4 style={{ margin: '0 0 16px 0', color: '#333' }}>编辑任务结论</h4>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500, color: '#333' }}>结论类型</label>
          <select 
            value={data.type}
            onChange={(e) => setData({...data, type: e.target.value})}
            style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #ddd' }}
          >
            <option value="">请选择...</option>
            <option value="tech_eval">技术评估</option>
            <option value="review">审核结论</option>
            <option value="decision">决策结论</option>
            <option value="other">其他</option>
          </select>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input type="checkbox" id="passed" checked={data.passed} onChange={(e) => setData({...data, passed: e.target.checked})} style={{ width: '20px', height: '20px' }} />
          <label htmlFor="passed" style={{ fontWeight: 500, color: '#333' }}>评估通过</label>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <input type="checkbox" id="execute" checked={data.execute} onChange={(e) => setData({...data, execute: e.target.checked})} style={{ width: '20px', height: '20px' }} />
          <label htmlFor="execute" style={{ fontWeight: 500, color: '#333' }}>需要执行</label>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontWeight: 500, color: '#333' }}>审核要求/备注</label>
          <textarea 
            value={data.auditContent}
            onChange={(e) => setData({...data, auditContent: e.target.value})}
            placeholder="请输入需要审核的内容或备注..."
            rows={4}
            style={{ width: '100%', padding: '10px', borderRadius: '6px', border: '1px solid #ddd' }}
          />
        </div>
        <div style={{ display: 'flex', gap: '12px', marginTop: '8px' }}>
          <button onClick={onSave} className="btn btn-primary">保存结论</button>
          <button onClick={() => setEditing(false)} className="btn btn-secondary">取消</button>
        </div>
      </div>
    </div>
  );
}

function EmptyState({ message }: { message: string }) {
  return (
    <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999', background: '#fff', borderRadius: '8px', border: '1px dashed #ddd' }}>
      {message}
    </div>
  );
}
