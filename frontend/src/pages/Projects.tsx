import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Projects() {
  const [projects, setProjects] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [formData, setFormData] = useState({ 
    name: '', 
    description: '', 
    goal: '', 
    priority: 'medium' 
  })

  useEffect(() => {
    loadProjects()
  }, [])

  const loadProjects = async () => {
    try {
      const data = await api.getProjects()
      if (data.success) setProjects(data.projects)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const res = await api.createProject(formData)
    if (res.success) {
      setShowModal(false)
      setFormData({ name: '', description: '', goal: '', priority: 'medium' })
      loadProjects()
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📁 项目管理</h2>
        <button className="btn btn-primary" onClick={() => setShowModal(true)}>+ 新建项目</button>
      </div>
      
      <div className="grid-3">
        {projects.map(p => (
          <div key={p.id} className="card" style={{ borderLeft: `4px solid ${
            p.status === 'todo' ? '#ffc107' : 
            p.status === 'progress' ? '#667eea' : '#28a745'
          }`}}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
              <span style={{ fontSize: '0.85rem', color: '#667eea', fontWeight: 600 }}>{p.number}</span>
              <span className={`badge ${
                p.priority === 'high' ? 'badge-red' : 
                p.priority === 'medium' ? 'badge-orange' : 'badge-green'
              }`}>
                {p.priority === 'high' ? '高' : p.priority === 'medium' ? '中' : '低'}
              </span>
            </div>
            <h4 style={{ marginBottom: '8px' }}>{p.name}</h4>
            <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '12px' }}>
              {p.description || '暂无描述'}
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span className={`status-badge status-${p.status}`}>
                {p.status === 'todo' ? '待办' : p.status === 'progress' ? '进行中' : '已完成'}
              </span>
              <span style={{ fontSize: '0.8rem', color: '#999' }}>
                {new Date(p.created_at).toLocaleDateString('zh-CN')}
              </span>
            </div>
          </div>
        ))}
      </div>

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>新建项目</h3>
            <form onSubmit={handleSubmit}>
              <div className="form-group">
                <label>项目名称</label>
                <input 
                  value={formData.name} 
                  onChange={e => setFormData({...formData, name: e.target.value})} 
                  required 
                />
              </div>
              <div className="form-group">
                <label>项目目标</label>
                <input 
                  value={formData.goal} 
                  onChange={e => setFormData({...formData, goal: e.target.value})} 
                />
              </div>
              <div className="form-group">
                <label>项目描述</label>
                <textarea 
                  value={formData.description} 
                  onChange={e => setFormData({...formData, description: e.target.value})} 
                  rows={3} 
                />
              </div>
              <div className="form-group">
                <label>优先级</label>
                <select 
                  value={formData.priority} 
                  onChange={e => setFormData({...formData, priority: e.target.value})}
                >
                  <option value="high">高</option>
                  <option value="medium">中</option>
                  <option value="low">低</option>
                </select>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>取消</button>
                <button type="submit" className="btn btn-primary">创建</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
