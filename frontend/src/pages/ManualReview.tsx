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
        
        // 筛选逻辑
        if (filter === 'long_think') {
          filtered = filtered.filter((t: any) => t.is_from_long_think)
        } else if (filter !== 'all') {
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
      'review': '👁️ 审核',
      'long_think': '🧠 长思考'
    }
    return labels[type] || type
  }

  if (loading) return <div className="loading">加载中...</div>

  // 统计长思考任务（基于所有任务，不只是筛选后的）
  const allTasks = tasks
  const longThinkTasks = allTasks.filter(t => t.is_from_long_think)
  const pendingLongThink = longThinkTasks.filter(t => t.status === 'pending')

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">👁️ 手动审核</h2>
      </div>

      {/* 统计信息 */}
      {longThinkTasks.length > 0 && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', 
          gap: '16px', 
          marginBottom: '20px' 
        }}>
          <div className="stat-card purple" style={{ padding: '16px' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{longThinkTasks.length}</div>
            <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>长思考任务总数</div>
          </div>
          <div className="stat-card orange" style={{ padding: '16px' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{pendingLongThink.length}</div>
            <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>待执行长思考</div>
          </div>
          <div className="stat-card green" style={{ padding: '16px' }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>
              {longThinkTasks.length - pendingLongThink.length}
            </div>
            <div style={{ fontSize: '0.85rem', opacity: 0.8 }}>已执行长思考</div>
          </div>
        </div>
      )}

      {/* 防重复提示 */}
      {pendingLongThink.length > 0 && (
        <div style={{
          padding: '16px 20px',
          background: '#fff3e0',
          borderLeft: '4px solid #ff9800',
          borderRadius: '8px',
          marginBottom: '20px'
        }}>
          <strong>⚠️ 防重复机制提示：</strong>
          <p style={{ margin: '8px 0 0 0', color: '#666' }}>
            存在 {pendingLongThink.length} 个未执行的长思考任务。
            在这些任务被执行之前，系统不会再为同一任务生成新的长思考结果。
          </p>
        </div>
      )}

      {/* 筛选 */}
      <div className="filter-bar">
        {[
          { key: 'pending', label: '待审核' },
          { key: 'completed', label: '已完成' },
          { key: 'all', label: '全部' },
          { key: 'long_think', label: '🧠 长思考' }
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
                  <tr key={task.id} style={task.is_from_long_think ? { background: '#faf5ff' } : {}}>
                    <td>
                      <span className={`badge ${task.is_from_long_think ? 'badge-purple' : 'badge-blue'}`}>
                        {getTaskTypeLabel(task.task_type)}
                        {task.is_from_long_think && ' 🧠'}
                      </span>
                    </td>
                    <td>
                      <strong>{task.title}</strong>
                      {task.is_from_long_think && task.status === 'pending' && (
                        <span style={{ 
                          display: 'inline-block',
                          marginLeft: '8px',
                          padding: '2px 8px',
                          background: '#ff9800',
                          color: 'white',
                          borderRadius: '4px',
                          fontSize: '11px'
                        }}>
                          防重复保护中
                        </span>
                      )}
                    </td>
                    <td style={{ maxWidth: '500px', minWidth: '300px', whiteSpace: 'normal', wordWrap: 'break-word', lineHeight: '1.5' }}>
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

export default ManualReview
