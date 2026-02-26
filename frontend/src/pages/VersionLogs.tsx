import { useState, useEffect } from 'react'

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
        <h2 className="page-title">📝 版本记录 (T008)</h2>
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