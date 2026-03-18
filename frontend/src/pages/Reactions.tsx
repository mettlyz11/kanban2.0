import { useState, useEffect } from 'react'

export function Reactions() {
  const [reactions, setReactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadReactions()
  }, [])

  const loadReactions = async () => {
    try {
      const res = await fetch('/api/reactions')
      const data = await res.json()
      if (data.success) {
        setReactions(data.reactions || [])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">⚗️ 反应管理</h2>
      </div>

      {/* 反应列表 */}
      <div className="grid-2">
        {reactions.map(reaction => (
          <div key={reaction.id} className="card">
            <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
              <div style={{ fontSize: '2.5rem' }}>⚗️</div>
              <div>
                <h4 style={{ marginBottom: '4px' }}>{reaction.name || '未命名反应'}</h4>
                <span className="badge badge-blue">{reaction.type || '反应'}</span>
              </div>
            </div>
            
            {/* 反应方程式 */}
            <div style={{ 
              padding: '16px', 
              background: '#f8f9fa', 
              borderRadius: '8px',
              marginBottom: '16px',
              textAlign: 'center',
              fontFamily: 'monospace',
              fontSize: '1.1rem'
            }}>
              {reaction.reactants?.map((r: any, i: number) => (
                <span key={i}>
                  {r.name}{i < reaction.reactants.length - 1 ? ' + ' : ''}
                </span>
              ))}
              <span style={{ margin: '0 12px', color: '#667eea' }}>→</span>
              {reaction.products?.map((p: any, i: number) => (
                <span key={i}>
                  {p.name}{i < reaction.products.length - 1 ? ' + ' : ''}
                </span>
              ))}
            </div>

            {/* 能量信息 */}
            {reaction.energy && (
              <div style={{ display: 'flex', gap: '16px', marginBottom: '12px' }}>
                <div>
                  <span style={{ color: '#666', fontSize: '0.85rem' }}>活化能: </span>
                  <strong>{reaction.energy.activation?.toFixed(2)} kcal/mol</strong>
                </div>
                <div>
                  <span style={{ color: '#666', fontSize: '0.85rem' }}>反应热: </span>
                  <strong style={{ color: reaction.energy.delta_h > 0 ? '#dc3545' : '#28a745' }}>
                    {reaction.energy.delta_h > 0 ? '+' : ''}{reaction.energy.delta_h?.toFixed(2)} kcal/mol
                  </strong>
                </div>
              </div>
            )}

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <span style={{ fontSize: '0.85rem', color: '#999' }}>
                {reaction.created_at && new Date(reaction.created_at).toLocaleDateString('zh-CN')}
              </span>
              <button className="btn btn-primary" style={{ padding: '6px 16px', fontSize: '13px' }}>
                查看详情
              </button>
            </div>
          </div>
        ))}
      </div>

      {reactions.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">⚗️</div>
          <p>暂无反应数据</p>
        </div>
      )}
    </div>
  )
}
