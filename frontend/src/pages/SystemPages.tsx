import { useState, useEffect } from 'react'

export function SystemMonitor() {
  const [metrics, setMetrics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadMetrics()
    const interval = setInterval(loadMetrics, 30000) // 30秒刷新
    return () => clearInterval(interval)
  }, [])

  const loadMetrics = async () => {
    try {
      const res = await fetch('/api/system/status')
      const data = await res.json()
      if (data.success) {
        setMetrics(data.metrics)
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
        <h2 className="page-title">📈 系统监控</h2>
      </div>

      {/* 实时指标 */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card blue">
          <div className="stat-icon">💻</div>
          <div className="stat-info">
            <h3>{metrics?.cpu || 0}%</h3>
            <p>CPU使用率</p>
          </div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon">🧠</div>
          <div className="stat-info">
            <h3>{metrics?.memory || 0}%</h3>
            <p>内存使用率</p>
          </div>
        </div>
        <div className="stat-card orange">
          <div className="stat-icon">💾</div>
          <div className="stat-info">
            <h3>{metrics?.disk || 0}%</h3>
            <p>磁盘使用率</p>
          </div>
        </div>
        <div className="stat-card purple">
          <div className="stat-icon">🌐</div>
          <div className="stat-info">
            <h3>{metrics?.gateway_status || '正常'}</h3>
            <p>Gateway状态</p>
          </div>
        </div>
      </div>

      {/* 服务状态 */}
      <div className="card">
        <h5 style={{ marginBottom: '16px' }}>服务状态</h5>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '16px' }}>
          {[
            { name: '看板系统', status: 'running', icon: '📊' },
            { name: 'Gateway', status: 'running', icon: '🌐' },
            { name: '数据库', status: 'running', icon: '🗄️' },
            { name: '定时任务', status: 'running', icon: '⏰' }
          ].map(service => (
            <div key={service.name} style={{
              padding: '16px',
              background: '#f8f9fa',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px'
            }}>
              <span style={{ fontSize: '1.5rem' }}>{service.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{service.name}</div>
                <span className={`badge ${service.status === 'running' ? 'badge-green' : 'badge-red'}`}>
                  {service.status === 'running' ? '运行中' : '异常'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export function AccessStats() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const res = await fetch('/api/access/stats')
      const data = await res.json()
      if (data.success) {
        setStats(data.stats)
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
        <h2 className="page-title">🌐 访问统计</h2>
      </div>

      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card blue">
          <div className="stat-icon">👁️</div>
          <div className="stat-info">
            <h3>{stats?.total_views?.toLocaleString() || 0}</h3>
            <p>总访问量</p>
          </div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon">👤</div>
          <div className="stat-info">
            <h3>{stats?.unique_visitors?.toLocaleString() || 0}</h3>
            <p>独立访客</p>
          </div>
        </div>
        <div className="stat-card orange">
          <div className="stat-icon">📅</div>
          <div className="stat-info">
            <h3>{stats?.today_views?.toLocaleString() || 0}</h3>
            <p>今日访问</p>
          </div>
        </div>
        <div className="stat-card purple">
          <div className="stat-icon">⏱️</div>
          <div className="stat-info">
            <h3>{stats?.avg_duration || '2:30'}</h3>
            <p>平均停留</p>
          </div>
        </div>
      </div>

      <div className="card">
        <h5 style={{ marginBottom: '16px' }}>热门页面</h5>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>页面</th>
                <th>访问量</th>
                <th>占比</th>
              </tr>
            </thead>
            <tbody>
              {(stats?.top_pages || []).map((page: any, i: number) => (
                <tr key={i}>
                  <td>{page.path}</td>
                  <td>{page.views.toLocaleString()}</td>
                  <td>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div style={{
                        width: '100px',
                        height: '8px',
                        background: '#e9ecef',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${page.percentage}%`,
                          height: '100%',
                          background: '#667eea'
                        }}/>
                      </div>
                      <span>{page.percentage}%</span>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export function VersionLogs() {
  const [logs, setLogs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadLogs()
  }, [])

  const loadLogs = async () => {
    try {
      const res = await fetch('/api/version-logs')
      const data = await res.json()
      if (data.success) {
        setLogs(data.logs || [])
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
        <h2 className="page-title">📝 版本记录</h2>
      </div>

      <div className="card">
        {logs.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📝</div>
            <p>暂无版本记录</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {logs.map((log, i) => (
              <div key={i} style={{
                padding: '20px',
                background: '#f8f9fa',
                borderRadius: '8px',
                borderLeft: '4px solid #667eea'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <h4 style={{ margin: 0 }}>v{log.version}</h4>
                  <span style={{ color: '#999', fontSize: '0.85rem' }}>
                    {new Date(log.release_date).toLocaleDateString('zh-CN')}
                  </span>
                </div>
                <p style={{ margin: 0, color: '#666' }}>{log.description}</p>
                {log.changes && (
                  <ul style={{ marginTop: '12px', paddingLeft: '20px', color: '#666' }}>
                    {log.changes.map((change: string, j: number) => (
                      <li key={j}>{change}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
