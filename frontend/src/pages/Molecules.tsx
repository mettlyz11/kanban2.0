import { useState, useEffect } from 'react'

export function Molecules() {
  const [molecules, setMolecules] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadMolecules()
  }, [])

  const loadMolecules = async () => {
    try {
      const res = await fetch('/api/chemistry/molecules')
      const data = await res.json()
      if (data.success) {
        setMolecules(data.molecules || [])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const filteredMolecules = molecules.filter(m => 
    !search || 
    m.name?.toLowerCase().includes(search.toLowerCase()) ||
    m.formula?.toLowerCase().includes(search.toLowerCase())
  )

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🧪 分子管理</h2>
      </div>

      {/* 搜索 */}
      <div className="filter-bar">
        <input
          type="text"
          placeholder="搜索分子名称或化学式..."
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

      {/* 分子网格 */}
      <div className="grid-4">
        {filteredMolecules.map(mol => (
          <div key={mol.id} className="card" style={{ textAlign: 'center' }}>
            <div style={{ 
              fontSize: '3rem', 
              marginBottom: '12px',
              padding: '20px',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              borderRadius: '12px',
              color: 'white'
            }}>
              🧪
            </div>
            <h4 style={{ marginBottom: '8px' }}>{mol.name || 'Unknown'}</h4>
            <code style={{ 
              display: 'inline-block',
              padding: '4px 12px', 
              background: '#f8f9fa', 
              borderRadius: '4px',
              marginBottom: '8px'
            }}>
              {mol.formula || 'C?H?'}
            </code>
            <p style={{ color: '#666', fontSize: '0.85rem' }}>
              {mol.description || '暂无描述'}
            </p>
            <div style={{ marginTop: '12px', display: 'flex', gap: '8px', justifyContent: 'center' }}>
              <span className="badge badge-blue">MW: {mol.molecular_weight?.toFixed(2) || '?'}</span>
              <span className="badge badge-green">{mol.charge || 0}电荷</span>
            </div>
          </div>
        ))}
      </div>

      {filteredMolecules.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">🧪</div>
          <p>{search ? '未找到匹配的分子' : '暂无分子数据'}</p>
        </div>
      )}
    </div>
  )
}
