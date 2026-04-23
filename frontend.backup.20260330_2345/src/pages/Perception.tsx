import { useState, useEffect } from 'react'

interface AgentStatus {
  running: boolean
  uptime_seconds: number
  event_count: number
  listeners: Record<string, {
    enabled: boolean
    running: boolean
  }>
}

interface PerceptionEvent {
  id: string
  type: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  source: string
  message: string
  timestamp: string
  hash: string
  data?: Record<string, unknown>
}

const API_URL = ''  // 使用相对路径，自动适配当前域名

export function PerceptionAgent() {
  const [status, setStatus] = useState<AgentStatus | null>(null)
  const [events, setEvents] = useState<PerceptionEvent[]>([])
  const [config, setConfig] = useState<Record<string, unknown> | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<'overview' | 'events' | 'config'>('overview')
  const [severityFilter, setSeverityFilter] = useState<string>('all')
  const [testMessage, setTestMessage] = useState('')

  const fetchStatus = async () => {
    try {
      const response = await fetch(`${API_URL}/api/perception/status`)
      const data = await response.json()
      if (data.success) {
        setStatus(data.status)
        setError(null)
      } else {
        setError(data.error || 'Failed to fetch status')
      }
    } catch (err) {
      setError('PerceptionAgent not available')
      setStatus(null)
    }
  }

  const fetchEvents = async () => {
    try {
      const response = await fetch(`${API_URL}/api/perception/events`)
      const data = await response.json()
      if (data.success) {
        setEvents(data.events)
      }
    } catch (err) {
      console.error('Failed to fetch events:', err)
    }
  }

  const fetchConfig = async () => {
    try {
      const response = await fetch(`${API_URL}/api/perception/config`)
      const data = await response.json()
      if (data.success) {
        setConfig(data.config)
      }
    } catch (err) {
      console.error('Failed to fetch config:', err)
    }
  }

  const sendTestEvent = async () => {
    try {
      const response = await fetch(`${API_URL}/api/perception/test`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          type: 'test',
          message: testMessage || 'Test event from Perception Agent UI'
        })
      })
      const data = await response.json()
      if (data.success) {
        setTestMessage('')
        fetchEvents()
        alert('Test event sent successfully!')
      } else {
        alert('Failed: ' + data.error)
      }
    } catch (err) {
      alert('Error: ' + String(err))
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await fetchStatus()
      await fetchEvents()
      await fetchConfig()
      setLoading(false)
    }

    loadData()
    const interval = setInterval(fetchStatus, 5000)
    return () => clearInterval(interval)
  }, [])

  const formatUptime = (seconds: number) => {
    const hours = Math.floor(seconds / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    const secs = seconds % 60
    if (hours > 0) return `${hours}h ${minutes}m ${secs}s`
    if (minutes > 0) return `${minutes}m ${secs}s`
    return `${secs}s`
  }

  const formatTime = (timestamp: string) => {
    if (!timestamp) return '-'
    const date = new Date(timestamp)
    if (isNaN(date.getTime())) return '-'
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#ff4444'
      case 'high': return '#ff8800'
      case 'medium': return '#ffbb33'
      case 'low': return '#00C851'
      default: return '#888'
    }
  }

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'critical': return 'rgba(255, 68, 68, 0.1)'
      case 'high': return 'rgba(255, 136, 0, 0.1)'
      case 'medium': return 'rgba(255, 187, 51, 0.1)'
      case 'low': return 'rgba(0, 200, 81, 0.1)'
      default: return 'rgba(136, 136, 136, 0.1)'
    }
  }

  const filteredEvents = severityFilter === 'all'
    ? events
    : events.filter(e => e.severity === severityFilter)

  const criticalCount = events.filter(e => e.severity === 'critical').length
  const highCount = events.filter(e => e.severity === 'high').length
  const mediumCount = events.filter(e => e.severity === 'medium').length

  if (loading) {
    return (
      <div className="system-page">
        <div className="loading-spinner">加载中...</div>
      </div>
    )
  }

  return (
    <div className="system-page">
      <div className="page-header">
        <h1>🎯 感知Agent (Perception Agent)</h1>
        <p className="subtitle">智能监听与分析系统 - 实时监控、错误检测、性能分析</p>
      </div>

      {error && (
        <div className="error-banner">
          <span>⚠️ {error}</span>
          <button onClick={fetchStatus} className="btn btn-sm">重试</button>
        </div>
      )}

      <div className="tabs">
        <button
          className={`tab ${activeTab === 'overview' ? 'active' : ''}`}
          onClick={() => setActiveTab('overview')}
        >
          📊 概览
        </button>
        <button
          className={`tab ${activeTab === 'events' ? 'active' : ''}`}
          onClick={() => setActiveTab('events')}
        >
          📋 事件日志
        </button>
        <button
          className={`tab ${activeTab === 'config' ? 'active' : ''}`}
          onClick={() => setActiveTab('config')}
        >
          ⚙️ 配置
        </button>
      </div>

      {activeTab === 'overview' && status && (
        <div className="tab-content">
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon" style={{ color: status.running ? '#00C851' : '#ff4444' }}>
                {status.running ? '✅' : '❌'}
              </div>
              <div className="stat-value">{status.running ? '运行中' : '已停止'}</div>
              <div className="stat-label">Agent状态</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">⏱️</div>
              <div className="stat-value">{formatUptime(status.uptime_seconds)}</div>
              <div className="stat-label">运行时间</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">📊</div>
              <div className="stat-value">{status.event_count}</div>
              <div className="stat-label">事件总数</div>
            </div>
            <div className="stat-card">
              <div className="stat-icon">🔌</div>
              <div className="stat-value">{(status.listeners ? Object.keys(status.listeners).length : 0)}</div>
              <div className="stat-label">监听器数量</div>
            </div>
          </div>

          <div className="stats-grid" style={{ marginTop: '20px' }}>
            <div className="stat-card" style={{ borderLeft: `4px solid ${getSeverityColor('critical')}` }}>
              <div className="stat-value" style={{ color: getSeverityColor('critical') }}>{criticalCount}</div>
              <div className="stat-label">Critical事件</div>
            </div>
            <div className="stat-card" style={{ borderLeft: `4px solid ${getSeverityColor('high')}` }}>
              <div className="stat-value" style={{ color: getSeverityColor('high') }}>{highCount}</div>
              <div className="stat-label">High事件</div>
            </div>
            <div className="stat-card" style={{ borderLeft: `4px solid ${getSeverityColor('medium')}` }}>
              <div className="stat-value" style={{ color: getSeverityColor('medium') }}>{mediumCount}</div>
              <div className="stat-label">Medium事件</div>
            </div>
          </div>

          <div className="card" style={{ marginTop: '20px' }}>
            <h3>📡 监听器状态</h3>
            <div className="listeners-grid">
              {(status.listeners && Object.entries(status.listeners).map(([name, listenerStatus]) => (
                <div
                  key={name}
                  className="listener-item"
                  style={{
                    padding: '15px',
                    borderRadius: '8px',
                    background: listenerStatus.running ? 'rgba(0, 200, 81, 0.1)' : 'rgba(255, 68, 68, 0.1)',
                    border: `1px solid ${listenerStatus.running ? '#00C851' : '#ff4444'}`
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '20px' }}>
                      {name === 'log' && '📝'}
                      {name === 'error' && '⚠️'}
                      {name === 'metric' && '📈'}
                      {name === 'behavior' && '👤'}
                      {name === 'external' && '🌐'}
                    </span>
                    <div>
                      <div style={{ fontWeight: 'bold', textTransform: 'capitalize' }}>{name}</div>
                      <div style={{ fontSize: '12px', color: '#888' }}>
                        {listenerStatus.enabled ? '已启用' : '已禁用'} • {listenerStatus.running ? '运行中' : '已停止'}
                      </div>
                    </div>
                  </div>
                </div>
              )))}
            </div>
          </div>

          <div className="card" style={{ marginTop: '20px' }}>
            <h3>🧪 测试工具</h3>
            <div style={{ display: 'flex', gap: '10px', marginTop: '10px' }}>
              <input
                type="text"
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                placeholder="输入测试消息..."
                className="form-input"
                style={{ flex: 1 }}
              />
              <button onClick={sendTestEvent} className="btn btn-primary">
                发送测试事件
              </button>
            </div>
          </div>
        </div>
      )}

      {activeTab === 'events' && (
        <div className="tab-content">
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px' }}>
              <h3>📋 事件日志</h3>
              <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                <label>筛选:</label>
                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="form-select"
                >
                  <option value="all">全部</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
                <button onClick={fetchEvents} className="btn btn-sm">🔄 刷新</button>
              </div>
            </div>

            {filteredEvents.length === 0 ? (
              <div className="empty-state">暂无事件</div>
            ) : (
              <div className="events-list">
                {filteredEvents.map((event) => (
                  <div
                    key={event.id}
                    className="event-item"
                    style={{
                      padding: '15px',
                      marginBottom: '10px',
                      borderRadius: '8px',
                      background: getSeverityBg(event.severity),
                      borderLeft: `4px solid ${getSeverityColor(event.severity)}`
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <span
                          style={{
                            display: 'inline-block',
                            padding: '2px 8px',
                            borderRadius: '4px',
                            background: getSeverityColor(event.severity),
                            color: '#fff',
                            fontSize: '11px',
                            fontWeight: 'bold',
                            marginRight: '10px'
                          }}
                        >
                          {event.severity.toUpperCase()}
                        </span>
                        <span style={{ fontWeight: 'bold', color: '#333' }}>{event.type}</span>
                        <span style={{ color: '#888', marginLeft: '10px', fontSize: '13px' }}>
                          {event.source}
                        </span>
                      </div>
                      <span style={{ color: '#888', fontSize: '12px' }}>
                        {formatTime(event.timestamp)}
                      </span>
                    </div>
                    <div style={{ marginTop: '10px', color: '#555', fontSize: '14px' }}>
                      {event.message}
                    </div>
                    {event.data && Object.keys(event.data).length > 0 && (
                      <details style={{ marginTop: '10px' }}>
                        <summary style={{ cursor: 'pointer', color: '#666', fontSize: '12px' }}>
                          详情
                        </summary>
                        <pre style={{
                          marginTop: '10px',
                          padding: '10px',
                          background: '#f5f5f5',
                          borderRadius: '4px',
                          fontSize: '12px',
                          overflow: 'auto'
                        }}>
                          {JSON.stringify(event.data, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'config' && config && (
        <div className="tab-content">
          <div className="card">
            <h3>⚙️ 配置信息</h3>
            <pre style={{
              marginTop: '15px',
              padding: '15px',
              background: '#f8f9fa',
              borderRadius: '8px',
              fontSize: '13px',
              overflow: 'auto',
              maxHeight: '600px'
            }}>
              {JSON.stringify(config, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  )
}

export default PerceptionAgent
