import { useState, useEffect } from 'react'
import { Plus, FlaskConical, ArrowRight } from 'lucide-react'

export function Reactions() {
  const [reactions, setReactions] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)

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
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <Plus size={20} />
          添加反应
        </button>
      </div>

      {/* 使用说明卡片 */}
      <div className="card" style={{ marginBottom: '20px', background: '#fce7f3', border: '1px solid #f9a8d4' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <FlaskConical size={24} className="text-pink-600" style={{ flexShrink: 0 }} />
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#9d174d' }}>化学反应管理说明</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#831843', lineHeight: '1.6' }}>
              <li>记录化学反应方程式、反应条件和产物</li>
              <li>跟踪反应的能量变化（活化能、反应热）</li>
              <li>关联分子结构和反应机理</li>
              <li>支持反应数据库查询和分析</li>
            </ul>
          </div>
        </div>
      </div>

      {reactions.length === 0 ? (
        <div className="card">
          <div className="empty-state">
            <div className="empty-state-icon">⚗️</div>
            <h3 style={{ margin: '16px 0 8px', color: '#374151' }}>还没有反应记录</h3>
            <p style={{ color: '#6b7280', marginBottom: '20px' }}>
              记录你的第一个化学反应，建立反应数据库
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 auto' }}
            >
              <Plus size={20} />
              添加第一个反应
            </button>
          </div>
        </div>
      ) : (
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
      )}

      {/* 添加反应弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-lg">
            <h3 className="text-lg font-bold mb-4">⚗️ 添加化学反应</h3>
            <p style={{ color: '#666', marginBottom: '20px' }}>
              反应数据可以通过和光智成平台自动导入，或手动添加。
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                关闭
              </button>
              <a
                href="/molecules"
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 inline-block text-center"
              >
                前往和光智成
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Reactions
