import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Cron() {
  const [tasks, setTasks] = useState<any[]>([])
  const [history, setHistory] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [activeTab, setActiveTab] = useState('tasks')
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
      // 只显示非deleted的任务
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
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
          gap: '12px',
          marginBottom: '20px' 
        }}>
          <div className="stat-card purple" style={{ padding: '16px' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>📋</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{tasks.length}</h3>
              <p style={{ fontSize: '0.8rem' }}>活跃任务</p>
            </div>
          </div>
          <div className="stat-card green" style={{ padding: '16px' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>▶️</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats.active || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>运行中</p>
            </div>
          </div>
          <div className="stat-card orange" style={{ padding: '16px' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>❌</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats.failed || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>失败次数</p>
            </div>
          </div>
          <div className="stat-card cyan" style={{ padding: '16px' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>📅</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats.today || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>今日执行</p>
            </div>
          </div>
        </div>
      )}

      {/* 标签切换 */}
      <div className="filter-bar" style={{ marginBottom: '16px' }}>
        <button 
          className={`filter-btn ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          📋 任务列表
        </button>
        <button 
          className={`filter-btn ${activeTab === 'history' ? 'active' : ''}`}
          onClick={() => setActiveTab('history')}
        >
          📜 执行历史 ({history.length})
        </button>
      </div>

      {/* 任务列表 */}
      {activeTab === 'tasks' && (
        <div className="card">
          <div className="card-header">
            <h5>活跃任务列表</h5>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>任务名称</th>
                  <th>执行频率</th>
                  <th>下次执行</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {tasks.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="empty-state">暂无定时任务</td>
                  </tr>
                ) : (
                  tasks.map(task => (
                    <tr key={task.id}>
                      <td>
                        <strong>{task.name}</strong>
                        {task.description && (
                          <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '4px' }}>
                            {task.description}
                          </div>
                        )}
                      </td>
                      <td>
                        <span className="badge badge-blue">{getScheduleLabel(task.schedule)}</span>
                      </td>
                      <td>{task.next_run || '-'}</td>
                      <td>
                        <span className={`status-badge ${task.status === 'active' ? 'status-active' : 'status-inactive'}`}>
                          {task.status === 'active' ? '运行中' : '已停用'}
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-danger" 
                          style={{ padding: '6px 12px', fontSize: '12px' }}
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
      )}

      {/* 执行历史 */}
      {activeTab === 'history' && (
        <div className="card">
          <div className="card-header">
            <h5>执行历史</h5>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>执行时间</th>
                  <th>任务名称</th>
                  <th>状态</th>
                  <th>耗时</th>
                </tr>
              </thead>
              <tbody>
                {history.length === 0 ? (
                  <tr>
                    <td colSpan={4} className="empty-state">暂无执行记录</td>
                  </tr>
                ) : (
                  history.slice(0, 20).map((record: any) => (
                    <tr key={record.id}>
                      <td>{record.started_at || record.created_at || '-'}</td>
                      <td>{record.task_name || '-'}</td>
                      <td>
                        <span className={`badge ${record.status === 'success' ? 'badge-green' : 'badge-red'}`}>
                          {record.status === 'success' ? '成功' : '失败'}
                        </span>
                      </td>
                      <td>{record.duration ? `${record.duration}s` : '-'}</td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 添加任务弹窗 */}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>➕ 添加定时任务</h3>
            {error && <div className="error-msg">{error}</div>}
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>任务名称 *</label>
                <input 
                  value={formData.name} 
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="例如：数据备份"
                  required
                />
              </div>
              <div className="form-group">
                <label>执行频率 *</label>
                <select 
                  value={formData.schedule} 
                  onChange={e => setFormData({...formData, schedule: e.target.value})}
                >
                  <option value="*/5 * * * *">每5分钟</option>
                  <option value="*/10 * * * *">每10分钟</option>
                  <option value="*/30 * * * *">每30分钟</option>
                  <option value="0 8 * * *">每天上午8点</option>
                  <option value="0 2 * * *">每天凌晨2点</option>
                  <option value="0 0 * * *">每天零点</option>
                </select>
              </div>
              <div className="form-group">
                <label>执行命令 *</label>
                <textarea 
                  value={formData.command} 
                  onChange={e => setFormData({...formData, command: e.target.value})}
                  placeholder="例如：python3 /path/to/script.py"
                  rows={3}
                  required
                />
              </div>
              <div className="form-group">
                <label>任务描述</label>
                <input 
                  value={formData.description} 
                  onChange={e => setFormData({...formData, description: e.target.value})}
                  placeholder="可选：描述任务用途"
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>
                  取消
                </button>
                <button type="submit" className="btn btn-success">
                  确认添加
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
