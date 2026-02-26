import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Cron() {
  const [tasks, setTasks] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [historyTab, setHistoryTab] = useState('all')
  const [formData, setFormData] = useState({
    name: '',
    command: '',
    schedule: '*/10 * * * *',
    description: ''
  })
  const [error, setError] = useState('')

  useEffect(() => {
    loadData()
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
        setTasks(activeTasks)
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
      setFormData({ name: '', command: '', schedule: '*/10 * * * *', description: '' })
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

  const getScheduleLabel = (schedule: string) => {
    const labels: Record<string, string> = {
      '* * * * *': '每分钟',
      '*/5 * * * *': '每5分钟',
      '*/10 * * * *': '每10分钟',
      '*/30 * * * *': '每30分钟',
      '0 8 * * *': '每天8点',
      '0 2 * * *': '每天2点',
      '0 0 * * *': '每天零点'
    }
    return labels[schedule] || schedule
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

      {/* 统计卡片 - 缩小尺寸 */}
      {stats && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', 
          gap: '12px',
          marginBottom: '20px' 
        }}>
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

      {/* 两列布局：任务列表 | 执行历史 */}
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
                  <th>状态</th>
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
                        <strong>{task.name}</strong>
                        {task.description && (
                          <div style={{ fontSize: '0.8rem', color: '#666', marginTop: '2px' }}>
                            {task.description}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className="badge badge-blue">{getScheduleLabel(task.schedule)}</span>
                      </td>
                      <td>
                        <span className={`status-badge ${task.status === 'active' ? 'status-active' : 'status-inactive'}`}>
                          {task.status === 'active' ? '运行中' : '已停用'}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-danger" 
                          style={{ padding: '4px 10px', fontSize: '11px' }}
                          onClick={() => handleDelete(task.id, task.name)}
                        >
                          删除
                        </button>
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
          {/* 历史汇总卡片 */}
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(3, 1fr)', 
            gap: '10px',
            marginBottom: '16px' 
          }}>
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

          {/* 任务筛选标签 */}
          <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginBottom: '12px' }}>
            <button 
              className={`filter-btn ${historyTab === 'all' ? 'active' : ''}`}
              onClick={() => setHistoryTab('all')}
              style={{ fontSize: '12px', padding: '6px 12px' }}
            >
              全部
            </button>
            {tasks.map(t => (
              <button 
                key={t.id}
                className={`filter-btn ${historyTab === t.name ? 'active' : ''}`}
                onClick={() => setHistoryTab(t.name)}
                style={{ fontSize: '12px', padding: '6px 12px' }}
              >
                {t.name}
              </button>
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
                </tr>
              </thead>
              <tbody>
                {filteredHistory.length === 0 ? (
                  <tr>
                    <td colSpan={3} className="empty-state">暂无执行记录</td>
                  </tr>
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
                <label>任务名称</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="例如：每日邮件检查"
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>执行命令</label>
                <input
                  type="text"
                  value={formData.command}
                  onChange={e => setFormData({...formData, command: e.target.value})}
                  placeholder="例如：python3 check_emails.py"
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>执行频率 (Cron表达式)</label>
                <select
                  value={formData.schedule}
                  onChange={e => setFormData({...formData, schedule: e.target.value})}
                >
                  <option value="* * * * *">每分钟</option>
                  <option value="*/5 * * * *">每5分钟</option>
                  <option value="*/10 * * * *">每10分钟</option>
                  <option value="*/30 * * * *">每30分钟</option>
                  <option value="0 8 * * *">每天8点</option>
                  <option value="0 2 * * *">每天2点</option>
                  <option value="0 0 * * *">每天零点</option>
                </select>
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>描述 (可选)</label>
                <input
                  type="text"
                  value={formData.description}
                  onChange={e => setFormData({...formData, description: e.target.value})}
                  placeholder="任务描述..."
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button type="submit" className="btn btn-success">
                  添加任务
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
