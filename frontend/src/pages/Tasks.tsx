import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Tasks() {
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

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

  const handleStatusChange = async (taskId: number, newStatus: string) => {
    const res = await api.updateTaskStatus(taskId, newStatus)
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
          <table className="data-table">
            <thead>
              <tr>
                <th>任务</th>
                <th>项目</th>
                <th>优先级</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">暂无任务</td>
                </tr>
              ) : (
                tasks.map(t => (
                  <tr key={t.id}>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span style={{ fontSize: '0.75rem', color: '#667eea', fontWeight: 600, fontFamily: 'monospace' }}>{t.number || `T-${t.id}`}</span>
                        <strong>{t.title}</strong>
                      </div>
                      {t.description && (
                        <div style={{ fontSize: '0.85rem', color: '#666', marginTop: '4px', paddingLeft: '45px' }}>
                          {t.description}
                        </div>
                      )}
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
                    <td>
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
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
