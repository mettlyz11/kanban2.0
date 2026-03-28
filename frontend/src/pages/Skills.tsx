import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Skills() {
  const [skills, setSkills] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    loadSkills()
  }, [])

  const loadSkills = async () => {
    try {
      const res = await api.getSkills()
      if (res.success) {
        setSkills(res.skills || [])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const filteredSkills = skills.filter(skill => 
    !filter || skill.category === filter
  )

  const categories = Array.from(new Set(skills.map(s => s.category)))

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🛠️ 技能库</h2>
      </div>

      {/* 分类筛选 */}
      <div className="filter-bar">
        <button
          className={`filter-btn ${filter === '' ? 'active' : ''}`}
          onClick={() => setFilter('')}
        >
          全部
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            className={`filter-btn ${filter === cat ? 'active' : ''}`}
            onClick={() => setFilter(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 技能网格 */}
      <div className="grid-3">
        {filteredSkills.map(skill => (
          <div key={skill.id} className="card" style={{ transition: 'all 0.2s' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div style={{ fontSize: '2rem' }}>{skill.icon || '🛠️'}</div>
              <span className="badge badge-blue">{skill.category}</span>
            </div>
            <h4 style={{ marginBottom: '8px', color: '#333' }}>{skill.name}</h4>
            <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '12px', lineHeight: '1.5' }}>
              {skill.description || '暂无描述'}
            </p>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: '#999' }}>
                版本: {skill.version || '1.0'}
              </span>
              <span className={`badge ${skill.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                {skill.status === 'active' ? '可用' : '开发中'}
              </span>
            </div>
            {skill.command && (
              <div style={{ 
                marginTop: '12px', 
                padding: '8px', 
                background: '#f8f9fa', 
                borderRadius: '4px',
                fontFamily: 'monospace',
                fontSize: '0.85rem',
                color: '#666'
              }}>
                {skill.command}
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredSkills.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🛠️</div>
          <p>暂无技能</p>
        </div>
      )}
    </div>
  )
}

export default Skills
