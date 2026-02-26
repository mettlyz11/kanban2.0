import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function ManualReview() {
  const [tasks, setTasks] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('pending') // pending, completed, all

  useEffect(() => {
    loadTasks()
  }, [filter])

  const loadTasks = async () => {
    try {
      const res = await api.getManualReviewTasks()
      if (res.success) {
        let filtered = res.tasks || []
        if (filter !== 'all') {
          filtered = filtered.filter((t: any) => t.status === filter)
        }
        setTasks(filtered)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleComplete = async (taskId: number, approved: boolean) => {
    const notes = prompt(approved ? '请输入批准备注（可选）:' : '请输入拒绝原因:')
    if (notes === null) return

    const res = await api.completeManualReviewTask(taskId, {
      approved,
      notes: notes || (approved ? '已批准' : '已拒绝')
    })

    if (res.success) {
      loadTasks()
    } else {
      alert('操作失败: ' + (res.error || '未知错误'))
    }
  }

  const getTaskTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'email': '📧 邮件',
      'task': '✅ 任务',
      'calculation': '🔢 计算',
      'deploy': '🚀 部署',
      'review': '👁️ 审核'
    }
    return labels[type] || type
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">👁️ 手动审核</h2>
      </div>

      {/* 筛选 */}
      <div className="filter-bar">
        {[
          { key: 'pending', label: '待审核' },
          { key: 'completed', label: '已完成' },
          { key: 'all', label: '全部' }
        ].map(item => (
          <button
            key={item.key}
            className={`filter-btn ${filter === item.key ? 'active' : ''}`}
            onClick={() => setFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* 任务列表 */}
      <div className="card">
        <div className="card-header">
          <h5>审核任务列表</h5>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>类型</th>
                <th>标题</th>
                <th>描述</th>
                <th>来源</th>
                <th>创建时间</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {tasks.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">
                    {filter === 'pending' ? '暂无待审核任务 🎉' : '暂无任务'}
                  </td>
                </tr>
              ) : (
                tasks.map(task => (
                  <tr key={task.id}>
                    <td>
                      <span className="badge badge-blue">{getTaskTypeLabel(task.task_type)}</span>
                    </td>
                    <td><strong>{task.title}</strong></td>
                    <td style={{ maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {task.description || '-'}
                    </td>
                    <td>{task.source || '系统'}</td>
                    <td>{new Date(task.created_at).toLocaleString('zh-CN')}</td>
                    <td>
                      <span className={`status-badge ${task.status === 'pending' ? 'status-todo' : task.status === 'approved' ? 'status-done' : 'status-inactive'}`}>
                        {task.status === 'pending' ? '待审核' : task.status === 'approved' ? '已批准' : '已拒绝'}
                      </span>
                    </td>
                    <td>
                      {task.status === 'pending' && (
                        <div style={{ display: 'flex', gap: '8px' }}>
                          <button 
                            className="btn btn-success" 
                            style={{ padding: '6px 12px', fontSize: '12px' }}
                            onClick={() => handleComplete(task.id, true)}
                          >
                            批准
                          </button>
                          <button 
                            className="btn btn-danger" 
                            style={{ padding: '6px 12px', fontSize: '12px' }}
                            onClick={() => handleComplete(task.id, false)}
                          >
                            拒绝
                          </button>
                        </div>
                      )}
                      {task.status !== 'pending' && (
                        <span style={{ color: '#666', fontSize: '0.85rem' }}>
                          {task.notes || '-'}
                        </span>
                      )}
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
