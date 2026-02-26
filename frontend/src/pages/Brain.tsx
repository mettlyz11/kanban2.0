import { useState, useEffect } from 'react'

export function Brain() {
  const [stats, setStats] = useState<any>(null)
  const [entities, setEntities] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState('')

  useEffect(() => {
    loadData()
  }, [selectedType])

  const loadData = async () => {
    try {
      const [statsRes, entitiesRes] = await Promise.all([
        fetch('/api/brain/stats').then(r => r.json()),
        fetch(`/api/brain/entities?type=${selectedType}`).then(r => r.json())
      ])
      
      if (statsRes.success) setStats(statsRes.stats)
      if (entitiesRes.success) setEntities(entitiesRes.entities)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const filteredEntities = entities.filter(e => 
    !search || e.name?.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) return <div className="loading">加载中...</div>

  const typeColors: Record<string, string> = {
    'person': '#667eea',
    'org': '#11998e',
    'product': '#fc4a1a',
    'project': '#f7b733',
    'group': '#a855f7',
    'event': '#ec4899'
  }

  const typeLabels: Record<string, string> = {
    'person': '👤 人物',
    'org': '🏢 组织',
    'product': '📦 产品',
    'project': '📁 项目',
    'group': '👥 群组',
    'event': '📅 事件'
  }

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🧠 知识大脑</h2>
      </div>

      {/* 统计卡片 */}
      {stats && (
        <div className="stats-grid" style={{ marginBottom: '24px' }}>
          <div className="stat-card purple">
            <div className="stat-icon">🧩</div>
            <div className="stat-info">
              <h3>{stats.entities?.toLocaleString()}</h3>
              <p>实体总数</p>
            </div>
          </div>
          <div className="stat-card blue">
            <div className="stat-icon">🔗</div>
            <div className="stat-info">
              <h3>{stats.relationships?.toLocaleString()}</h3>
              <p>关系总数</p>
            </div>
          </div>
        </div>
      )}

      {/* 类型分布 */}
      {stats?.types && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <h5 style={{ marginBottom: '16px' }}>实体类型分布</h5>
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {Object.entries(stats.types).map(([type, count]) => (
              <button
                key={type}
                onClick={() => setSelectedType(selectedType === type ? '' : type)}
                style={{
                  padding: '10px 20px',
                  borderRadius: '20px',
                  border: 'none',
                  background: selectedType === type ? typeColors[type] || '#667eea' : '#f0f0f0',
                  color: selectedType === type ? 'white' : '#333',
                  cursor: 'pointer',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  fontSize: '14px'
                }}
              >
                {typeLabels[type] || type}
                <span style={{
                  background: selectedType === type ? 'rgba(255,255,255,0.3)' : '#ddd',
                  padding: '2px 8px',
                  borderRadius: '10px',
                  fontSize: '12px'
                }}>
                  {count as number}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 搜索 */}
      <div className="filter-bar" style={{ marginBottom: '16px' }}>
        <input
          type="text"
          placeholder="搜索实体..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ 
            padding: '10px 16px', 
            borderRadius: '8px', 
            border: '1px solid #ddd',
            minWidth: '300px'
          }}
        />
      </div>

      {/* 实体网格 */}
      <div className="grid-4">
        {filteredEntities.map(entity => (
          <div key={entity.id} className="card" style={{ 
            borderTop: `4px solid ${typeColors[entity.entity_type] || '#667eea'}`
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <span 
                className="badge" 
                style={{ 
                  background: typeColors[entity.entity_type] || '#667eea',
                  color: 'white'
                }}
              >
                {typeLabels[entity.entity_type] || entity.entity_type}
              </span>
            </div>
            <h4 style={{ marginBottom: '8px', fontSize: '1.1rem' }}>{entity.name}</h4>
            <p style={{ 
              color: '#666', 
              fontSize: '0.85rem', 
              marginBottom: '12px',
              display: '-webkit-box',
              WebkitLineClamp: 2,
              WebkitBoxOrient: 'vertical',
              overflow: 'hidden'
            }}>
              {entity.description || '暂无描述'}
            </p>
            {entity.metadata && (
              <div style={{ 
                padding: '8px', 
                background: '#f8f9fa', 
                borderRadius: '4px',
                fontSize: '0.75rem',
                color: '#666'
              }}>
                {(() => {
                  try {
                    const meta = JSON.parse(entity.metadata)
                    return Object.entries(meta).slice(0, 2).map(([k, v]) => (
                      <div key={k}><strong>{k}:</strong> {String(v).slice(0, 30)}</div>
                    ))
                  } catch {
                    return <div>元数据</div>
                  }
                })()}
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredEntities.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🧠</div>
          <p>{search ? '未找到匹配的实体' : '暂无实体数据'}</p>
        </div>
      )}
    </div>
  )
}
