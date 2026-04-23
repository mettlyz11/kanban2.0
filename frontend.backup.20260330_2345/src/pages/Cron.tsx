import { useState, useEffect } from 'react'
import { api } from '../utils/api'

// 图标组件
const EditIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
    <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
  </svg>
)

const InfoIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"/>
    <line x1="12" y1="16" x2="12" y2="12"/>
    <line x1="12" y1="8" x2="12.01" y2="8"/>
  </svg>
)

// Cron表达式选项
const CRON_OPTIONS = [
  { value: '* * * * *', label: '每分钟' },
  { value: '*/5 * * * *', label: '每5分钟' },
  { value: '*/10 * * * *', label: '每10分钟' },
  { value: '*/15 * * * *', label: '每15分钟' },
  { value: '*/30 * * * *', label: '每30分钟' },
  { value: '0 * * * *', label: '每小时' },
  { value: '0 */2 * * *', label: '每2小时' },
  { value: '0 */6 * * *', label: '每6小时' },
  { value: '0 0 * * *', label: '每天零点' },
  { value: '0 8 * * *', label: '每天8点' },
  { value: '0 9 * * 1', label: '每周一9点' },
  { value: '0 0 1 * *', label: '每月1号' },
  { value: 'custom', label: '自定义...' }
]

// 计算下次执行时间
function getNextRun(schedule: string): string {
  try {
    const now = new Date()
    // 简化计算，实际应该用cron-parser库
    if (schedule === '* * * * *') return new Date(now.getTime() + 60000).toISOString()
    if (schedule === '*/5 * * * *') return new Date(now.getTime() + 5 * 60000).toISOString()
    if (schedule === '*/10 * * * *') return new Date(now.getTime() + 10 * 60000).toISOString()
    if (schedule === '*/30 * * * *') return new Date(now.getTime() + 30 * 60000).toISOString()
    if (schedule === '0 8 * * *') {
      const next = new Date()
      next.setHours(8, 0, 0, 0)
      if (next <= now) next.setDate(next.getDate() + 1)
      return next.toISOString()
    }
    return new Date(now.getTime() + 10 * 60000).toISOString()
  } catch (e) {
    return ''
  }
}

// 格式化时间
function formatTime(isoString: string): string {
  if (!isoString) return '-'
  try {
    const date = new Date(isoString)
    return date.toLocaleString('zh-CN', { 
      month: 'short', 
      day: 'numeric', 
      hour: '2-digit', 
      minute: '2-digit' 
    })
  } catch (e) {
    return isoString
  }
}

export function Cron() {
  const [tasks, setTasks] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [historyTab, setHistoryTab] = useState('all')
  const [editingTask, setEditingTask] = useState<number | null>(null)
  const [editingField, setEditingField] = useState<string>('')
  const [selectedHistory, setSelectedHistory] = useState<any>(null)
  const [selectedTaskDetail, setSelectedTaskDetail] = useState<any>(null)
  
  const [formData, setFormData] = useState({
    name: '',
    command: '',
    schedule: '*/10 * * * *',
    description: '',
    detailed_description: ''
  })
  const [error, setError] = useState('')

  useEffect(() => {
    loadData()
    // 每30秒刷新一次
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [tasksRes, statsRes, historyRes] = await Promise.all([
        api.getCronTasks(),
        api.getCronStats(),
        api.getCronHistory()
      ])
      if (tasksRes.success) {
        const activeTasks = (tasksRes.tasks || []).filter((t: any) => t.status !== 'deleted')
        // 计算下次执行时间
        const tasksWithNextRun = activeTasks.map((t: any) => ({
          ...t,
          next_run_calculated: getNextRun(t.schedule)
        }))
        setTasks(tasksWithNextRun)
      }
      if (statsRes.success) setStats(statsRes.stats)
      if (historyRes.success) setHistory(historyRes.history || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    
    if (!formData.name || !formData.command) {
      setError('请填写任务名称和命令')
      return
    }

    const res = await api.addCronTask(formData)
    if (res.success) {
      setShowModal(false)
      setFormData({ name: '', command: '', schedule: '*/10 * * * *', description: '', detailed_description: '' })
      loadData()
    } else {
      setError(res.error || '添加失败')
    }
  }

  const handleDelete = async (taskId: number, taskName: string) => {
    if (!confirm(`确定删除任务 "${taskName}" 吗？`)) return
    
    const res = await api.deleteCronTask(taskId)
    if (res.success) {
      loadData()
    } else {
      alert('删除失败: ' + (res.error || '未知错误'))
    }
  }

  const handleUpdateTask = async (taskId: number, updates: any) => {
    try {
      const res = await fetch(`/api/cron/tasks/${taskId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updates)
      })
      const data = await res.json()
      if (data.success) {
        loadData()
        setEditingTask(null)
        setEditingField('')
      }
    } catch (e) {
      console.error(e)
    }
  }

  const getScheduleLabel = (schedule: string) => {
    const option = CRON_OPTIONS.find(o => o.value === schedule)
    return option?.label || schedule
  }

  // 按任务过滤历史
  const filteredHistory = historyTab === 'all' 
    ? history 
    : history.filter((h: any) => h.task_name === historyTab)

  // 历史统计
  const historyStats = {
    total: history.length,
    success: history.filter((h: any) => h.status === 'success').length,
    failed: history.filter((h: any) => h.status === 'failed').length,
    recent: history.slice(0, 10)
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">⏰ 定时任务管理</h2>
        <div>
          <button className="btn btn-success" onClick={() => setShowModal(true)}>
            + 增加任务
          </button>
        </div>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div className="stat-card purple" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>📋</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{tasks.length}</h3>
              <p style={{ fontSize: '0.75rem' }}>活跃任务</p>
            </div>
          </div>
          <div className="stat-card green" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>▶️</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.active || 0}</h3>
              <p style={{ fontSize: '0.75rem' }}>运行中</p>
            </div>
          </div>
          <div className="stat-card orange" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>❌</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.failed || 0}</h3>
              <p style={{ fontSize: '0.75rem' }}>失败次数</p>
            </div>
          </div>
          <div className="stat-card cyan" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>📅</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.today || 0}</h3>
              <p style={{ fontSize: '0.75rem' }}>今日执行</p>
            </div>
          </div>
        </div>
      )}

      {/* 两列布局 */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
        {/* 左列：任务列表 */}
        <div className="card" style={{ marginBottom: 0 }}>
          <div className="card-header">
            <h5>📋 任务列表 ({tasks.length})</h5>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>任务名称</th>
                  <th>频率</th>
                  <th>下次执行</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="empty-state">暂无定时任务</td>
                  </tr>
                ) : (
                  tasks.map(task => (
                    <tr key={task.id}>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                          <strong>{task.name}</strong>
                          <button 
                            className="btn btn-sm btn-outline" 
                            onClick={() => setSelectedTaskDetail(task)}
                            title="查看详情"
                          >
                            <InfoIcon />
                          </button>
                        </div>
                        {task.description && (
                          <div style={{ fontSize: '0.8rem', color: '#666', marginTop: '2px' }}>
                            {task.description}
                          </div>
                        )}
                      </td>
                      <td>
                        {editingTask === task.id && editingField === 'schedule' ? (
                          <select
                            value={task.schedule}
                            onChange={e => handleUpdateTask(task.id, { schedule: e.target.value })}
                            onBlur={() => { setEditingTask(null); setEditingField(''); }}
                            autoFocus
                            style={{ fontSize: '12px', padding: '4px' }}
                          >
                            {CRON_OPTIONS.map(opt => (
                              <option key={opt.value} value={opt.value}>{opt.label}</option>
                            ))}
                          </select>
                        ) : (
                          <span 
                            className="badge badge-blue" 
                            style={{ cursor: 'pointer' }}
                            onClick={() => { setEditingTask(task.id); setEditingField('schedule'); }}
                            title="点击修改"
                          >
                            {getScheduleLabel(task.schedule)} <EditIcon />
                          </span>
                        )}
                      </td>
                      <td style={{ fontSize: '0.85rem' }}>
                        {formatTime(task.next_run_calculated)}
                      </td>
                      <td>
                        <div style={{ display: 'flex', gap: '4px' }}>
                          <button 
                            className="btn btn-sm btn-outline-primary"
                            onClick={() => setSelectedTaskDetail(task)}
                          >
                            详情
                          </button>
                          <button 
                            className="btn btn-sm btn-danger" 
                            onClick={() => handleDelete(task.id, task.name)}
                          >
                            删除
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* 右列：执行历史 */}
        <div>
          {/* 历史汇总 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '10px', marginBottom: '16px' }}>
            <div className="stat-card" style={{ padding: '12px', background: '#f8f9fa' }}>
              <div className="stat-info" style={{ textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.2rem', color: '#333' }}>{historyStats.total}</h3>
                <p style={{ fontSize: '0.7rem', margin: 0 }}>总记录</p>
              </div>
            </div>
            <div className="stat-card green" style={{ padding: '12px' }}>
              <div className="stat-info" style={{ textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.2rem' }}>{historyStats.success}</h3>
                <p style={{ fontSize: '0.7rem', margin: 0 }}>成功</p>
              </div>
            </div>
            <div className="stat-card orange" style={{ padding: '12px' }}>
              <div className="stat-info" style={{ textAlign: 'center' }}>
                <h3 style={{ fontSize: '1.2rem' }}>{historyStats.failed}</h3>
                <p style={{ fontSize: '0.7rem', margin: 0 }}>失败</p>
              </div>
            </div>
          </div>

          {/* 任务筛选 */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            <button className={`filter-btn ${historyTab === 'all' ? 'active' : ''}`} onClick={() => setHistoryTab('all')} style={{ fontSize: '12px' }}>全部</button>
            {tasks.map(t => (
              <button key={t.id} className={`filter-btn ${historyTab === t.name ? 'active' : ''}`} onClick={() => setHistoryTab(t.name)} style={{ fontSize: '12px' }}>{t.name}</button>
            ))}
          </div>

          {/* 历史记录表格 */}
          <div className="card" style={{ maxHeight: '500px', overflow: 'auto' }}>
            <div className="card-header">
              <h5>📜 执行历史 ({filteredHistory.length})</h5>
            </div>
            <table className="data-table" style={{ fontSize: '0.85rem' }}>
              <thead>
                <tr>
                  <th>时间</th>
                  <th>任务</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {filteredHistory.length === 0 ? (
                  <tr><td colSpan={4} className="empty-state">暂无执行记录</td></tr>
                ) : (
                  filteredHistory.slice(0, 50).map((record: any) => (
                    <tr key={record.id}>
                      <td style={{ fontSize: '0.8rem' }}>{record.started_at?.slice(5, 16) || '-'}</td>
                      <td style={{ fontSize: '0.8rem' }}>{record.task_name || '-'}</td>
                      <td>
                        <span className={`badge ${record.status === 'success' ? 'badge-green' : 'badge-red'}`} style={{ fontSize: '0.7rem' }}>
                          {record.status === 'success' ? '✓' : '✗'}
                        </span>
                      </td>
                      <td>
                        <button className="btn btn-sm btn-outline" onClick={() => setSelectedHistory(record)}>详情</button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* 添加任务弹窗 */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>➕ 添加定时任务</h3>
            {error && <div className="alert alert-error">{error}</div>}
            <form onSubmit={handleSubmit} style={{ marginTop: '16px' }}>
              <div style={{ marginBottom: '16px' }}>
                <label>任务名称 *</label>
                <input type="text" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} placeholder="例如：每日邮件检查" required />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>执行命令 *</label>
                <input type="text" value={formData.command} onChange={e => setFormData({...formData, command: e.target.value})} placeholder="例如：python3 check_emails.py" required />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>执行频率</label>
                <select value={formData.schedule} onChange={e => setFormData({...formData, schedule: e.target.value})}>
                  {CRON_OPTIONS.filter(o => o.value !== 'custom').map(opt => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>简短描述</label>
                <input type="text" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} placeholder="任务简短描述..." />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>详细说明</label>
                <textarea value={formData.detailed_description} onChange={e => setFormData({...formData, detailed_description: e.target.value})} placeholder="任务的详细说明、参数说明、注意事项..." rows={4} />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>取消</button>
                <button type="submit" className="btn btn-success">添加任务</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* 任务详情弹窗 */}
      {selectedTaskDetail && (
        <div className="modal-overlay" onClick={() => setSelectedTaskDetail(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>📋 任务详情</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setSelectedTaskDetail(null)}>✕</button>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label>任务名称</label>
              <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px', fontWeight: 600 }}>{selectedTaskDetail.name}</div>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label>执行命令</label>
              <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.9rem' }}>{selectedTaskDetail.command}</div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label>执行频率</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{getScheduleLabel(selectedTaskDetail.schedule)}</div>
              </div>
              <div>
                <label>任务状态</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>
                  <span className={`badge ${selectedTaskDetail.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                    {selectedTaskDetail.status === 'active' ? '运行中' : '已停用'}
                  </span>
                </div>
              </div>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label>下次执行时间</label>
              <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{formatTime(selectedTaskDetail.next_run_calculated)}</div>
            </div>
            {selectedTaskDetail.description && (
              <div style={{ marginBottom: '16px' }}>
                <label>任务描述</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{selectedTaskDetail.description}</div>
              </div>
            )}
            {selectedTaskDetail.detailed_description && (
              <div style={{ marginBottom: '16px' }}>
                <label>详细说明</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px', whiteSpace: 'pre-wrap' }}>{selectedTaskDetail.detailed_description}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* 执行历史详情弹窗 */}
      {selectedHistory && (
        <div className="modal-overlay" onClick={() => setSelectedHistory(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>📜 执行详情</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setSelectedHistory(null)}>✕</button>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label>任务名称</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{selectedHistory.task_name || '-'}</div>
              </div>
              <div>
                <label>执行状态</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>
                  <span className={`badge ${selectedHistory.status === 'success' ? 'badge-green' : 'badge-red'}`}>
                    {selectedHistory.status === 'success' ? '成功' : '失败'}
                  </span>
                </div>
              </div>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginBottom: '16px' }}>
              <div>
                <label>开始时间</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{formatTime(selectedHistory.started_at)}</div>
              </div>
              <div>
                <label>结束时间</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{formatTime(selectedHistory.ended_at)}</div>
              </div>
            </div>
            <div style={{ marginBottom: '16px' }}>
              <label>执行耗时</label>
              <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>{selectedHistory.duration ? `${selectedHistory.duration}秒` : '-'}</div>
            </div>
            {selectedHistory.output && (
              <div style={{ marginBottom: '16px' }}>
                <label>标准输出</label>
                <div style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.85rem', maxHeight: '200px', overflow: 'auto' }}>
                  <pre style={{ margin: 0 }}>{selectedHistory.output}</pre>
                </div>
              </div>
            )}
            {selectedHistory.error_output && (
              <div style={{ marginBottom: '16px' }}>
                <label>错误输出</label>
                <div style={{ padding: '12px', background: '#fff5f5', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.85rem', color: '#c53030', maxHeight: '200px', overflow: 'auto' }}>
                  <pre style={{ margin: 0 }}>{selectedHistory.error_output}</pre>
                </div>
              </div>
            )}
            {selectedHistory.error_message && (
              <div style={{ marginBottom: '16px' }}>
                <label>错误信息</label>
                <div style={{ padding: '12px', background: '#fff5f5', borderRadius: '8px', color: '#c53030' }}>{selectedHistory.error_message}</div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default Cron
