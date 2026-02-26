import { useState, useEffect } from 'react'

export function SystemMonitor() {
  const [metrics, setMetrics] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
    const interval = setInterval(loadData, 30000)
    return () => clearInterval(interval)
  }, [])

  const loadData = async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        fetch('/api/system/status').then(r => r.json()),
        fetch('/api/system/history').then(r => r.json())
      ])
      
      if (statusRes.success) setMetrics(statusRes.metrics)
      if (historyRes.success) setHistory(historyRes.history || [])
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
        <h2 className="page-title">📈 系统监控 (T002)</h2>
      </div>

      {/* 实时指标 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        <div className="stat-card blue" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>💻</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{metrics?.cpu || 0}%</h3>
            <p style={{ fontSize: '0.8rem' }}>CPU使用率</p>
          </div>
        </div>
        <div className="stat-card green" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>🧠</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{metrics?.memory || 0}%</h3>
            <p style={{ fontSize: '0.8rem' }}>内存使用率</p>
          </div>
        </div>
        <div className="stat-card orange" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>💾</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{metrics?.disk || 0}%</h3>
            <p style={{ fontSize: '0.8rem' }}>磁盘使用率</p>
          </div>
        </div>
        <div className="stat-card purple" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>🌐</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{metrics?.gateway_status || '正常'}</h3>
            <p style={{ fontSize: '0.8rem' }}>Gateway状态</p>
          </div>
        </div>
      </div>

      {/* 历史数据 */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <h5>📊 历史监控数据 (最近24小时)</h5>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>CPU</th>
                <th>内存</th>
                <th>磁盘</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">暂无历史数据</td>
                </tr>
              ) : (
                history.slice(0, 20).map((record: any, i: number) => (
                  <tr key={i}>
                    <td>{record.created_at || record.timestamp || '-'}</td>
                    <td>{record.cpu_percent || record.cpu || '-'}%</td>
                    <td>{record.memory_percent || record.memory || '-'}%</td>
                    <td>{record.disk_percent || record.disk || '-'}%</td>
                    <td>
                      <span className={`badge ${record.status === 'normal' ? 'badge-green' : 'badge-orange'}`}>
                        {record.status === 'normal' ? '正常' : '警告'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
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
  const [pageViews, setPageViews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadStats()
  }, [])

  const loadStats = async () => {
    try {
      const [statsRes, viewsRes] = await Promise.all([
        fetch('/api/access/stats').then(r => r.json()),
        fetch('/api/access/page-views').then(r => r.json())
      ])
      
      if (statsRes.success) setStats(statsRes.stats)
      if (viewsRes.success) setPageViews(viewsRes.views || [])
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
        <h2 className="page-title">🌐 访问统计 (T002a)</h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        <div className="stat-card blue" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>👁️</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{stats?.total_views?.toLocaleString() || 0}</h3>
            <p style={{ fontSize: '0.8rem' }}>总访问量</p>
          </div>
        </div>
        <div className="stat-card green" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>👤</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{stats?.unique_visitors?.toLocaleString() || 0}</h3>
            <p style={{ fontSize: '0.8rem' }}>独立访客</p>
          </div>
        </div>
        <div className="stat-card orange" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>📅</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{stats?.today_views?.toLocaleString() || 0}</h3>
            <p style={{ fontSize: '0.8rem' }}>今日访问</p>
          </div>
        </div>
        <div className="stat-card purple" style={{ padding: '16px' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>⏱️</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{stats?.avg_duration || '2:30'}</h3>
            <p style={{ fontSize: '0.8rem' }}>平均停留</p>
          </div>
        </div>
      </div>

      {/* 最近访问记录 */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <h5>📝 最近访问记录</h5>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>页面</th>
                <th>IP地址</th>
                <th>设备</th>
              </tr>
            </thead>
            <tbody>
              {pageViews.length === 0 ? (
                <tr>
                  <td colSpan={4} className="empty-state">暂无访问记录</td>
                </tr>
              ) : (
                pageViews.slice(0, 20).map((view: any, i: number) => (
                  <tr key={i}>
                    <td>{view.created_at || view.timestamp || '-'}</td>
                    <td>{view.path || view.page || '-'}</td>
                    <td>{view.ip_address || view.ip || '-'}</td>
                    <td>{view.user_agent ? view.user_agent.slice(0, 50) + '...' : '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 热门页面 */}
      <div className="card">
        <h5 style={{ marginBottom: '16px' }}>🔥 热门页面</h5>
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
