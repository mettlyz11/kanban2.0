import { useState, useEffect } from 'react'

export function LLMConfigs() {
  const [configs, setConfigs] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [configsRes, statsRes] = await Promise.all([
        fetch('/api/llm/configs').then(r => r.json()),
        fetch('/api/llm/stats').then(r => r.json())
      ])
      if (configsRes.success) setConfigs(configsRes.configs || [])
      if (statsRes.success) setStats(statsRes.stats)
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
        <h2 className="page-title">🤖 大模型配置 (T009)</h2>
      </div>

      {stats && (
        <div className="stats-grid" style={{ marginBottom: '24px' }}>
          <div className="stat-card blue">
            <div className="stat-icon">🔧</div>
            <div className="stat-info">
              <h3>{stats.total || 0}</h3>
              <p>配置总数</p>
            </div>
          </div>
          <div className="stat-card green">
            <div className="stat-icon">✅</div>
            <div className="stat-info">
              <h3>{stats.active || 0}</h3>
              <p>活跃配置</p>
            </div>
          </div>
          <div className="stat-card purple">
            <div className="stat-icon">📊</div>
            <div className="stat-info">
              <h3>{stats.usage || 0}</h3>
              <p>使用次数</p>
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="card-header">
          <h5>模型配置列表</h5>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>提供商</th>
                <th>模型</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {configs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="empty-state">暂无模型配置</td>
                </tr>
              ) : (
                configs.map((config: any) => (
                  <tr key={config.id}>
                    <td><strong>{config.name}</strong></td>
                    <td>{config.provider}</td>
                    <td>{config.model}</td>
                    <td>
                      <span className={`badge ${config.is_active ? 'badge-green' : 'badge-gray'}`}>
                        {config.is_active ? '活跃' : '停用'}
                      </span>
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
