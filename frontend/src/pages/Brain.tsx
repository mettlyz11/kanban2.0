import { useState, useEffect } from 'react'

export function Brain() {
  const [stats, setStats] = useState<any>(null)
  const [entities, setEntities] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedType, setSelectedType] = useState('')
  const [showAllEntities, setShowAllEntities] = useState(false)
  const [showAllRelations, setShowAllRelations] = useState(false)

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

      {/* 统计卡片 - 紧凑尺寸 */}
      {stats && (
        <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
          <div 
            className="stat-card purple" 
            style={{ padding: '10px 16px', cursor: 'pointer', flex: 1, maxWidth: '200px' }}
            onClick={() => setShowAllEntities(true)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '1.5rem' }}>🧩</span>
              <div>
                <div style={{ fontSize: '1.4rem', fontWeight: 600, lineHeight: 1 }}>{stats.entities?.toLocaleString()}</div>
                <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '2px' }}>实体总数</div>
              </div>
            </div>
          </div>
          <div 
            className="stat-card blue" 
            style={{ padding: '10px 16px', cursor: 'pointer', flex: 1, maxWidth: '200px' }}
            onClick={() => setShowAllRelations(true)}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <span style={{ fontSize: '1.5rem' }}>🔗</span>
              <div>
                <div style={{ fontSize: '1.4rem', fontWeight: 600, lineHeight: 1 }}>{stats.relationships?.toLocaleString()}</div>
                <div style={{ fontSize: '0.7rem', color: '#666', marginTop: '2px' }}>关系总数</div>
              </div>
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

      {/* 所有实体弹窗 */}
      {showAllEntities && (
        <div className="modal-overlay" onClick={() => setShowAllEntities(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>🧩 所有实体 ({entities.length})</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setShowAllEntities(false)}>✕</button>
            </div>
            <div style={{ maxHeight: '60vh', overflow: 'auto' }}>
              <table className="data-table">
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>名称</th>
                    <th>描述</th>
                  </tr>
                </thead>
                <tbody>
                  {entities.map(e => (
                    <tr key={e.id}>
                      <td>
                        <span className="badge" style={{ background: typeColors[e.entity_type] || '#667eea', color: 'white' }}>
                          {typeLabels[e.entity_type] || e.entity_type}
                        </span>
                      </td>
                      <td>{e.name}</td>
                      <td>{e.description?.slice(0, 50) || '-'}{e.description?.length > 50 ? '...' : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* 所有关系弹窗 */}
      {showAllRelations && (
        <div className="modal-overlay" onClick={() => setShowAllRelations(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '800px', maxHeight: '80vh', overflow: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>🔗 所有关系 ({stats?.relationships || 0})</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setShowAllRelations(false)}>✕</button>
            </div>
            <div style={{ padding: '40px', textAlign: 'center' }}>
              <div className="empty-state-icon">🔗</div>
              <p>关系详情功能开发中</p>
              <p style={{ fontSize: '0.85rem', color: '#999', marginTop: '8px' }}>
                将展示所有实体间的关联关系网络
              </p>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
