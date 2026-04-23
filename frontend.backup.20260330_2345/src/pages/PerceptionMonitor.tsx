import { useEffect, useState } from 'react'
import { perceptionApi } from '../utils/api'

interface PerceptionStatus {
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
  severity: string
  source: string
  message: string
  timestamp: string
  hash: string
}

export function PerceptionMonitor() {
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [status, setStatus] = useState<PerceptionStatus | null>(null)
  const [events, setEvents] = useState<PerceptionEvent[]>([])
  const [refreshInterval, setRefreshInterval] = useState<number>(5000)
  const [autoRefresh, setAutoRefresh] = useState(true)

  const fetchData = async () => {
    try {
      // 获取状态
      const statusRes = await perceptionApi.getStatus()
      if (statusRes.success) {
        setStatus(statusRes.status)
        setError(null)
      } else {
        setError(statusRes.error || '获取感知Agent状态失败')
      }

      // 获取事件
      const eventsRes = await perceptionApi.getEvents()
      if (eventsRes.success) {
        setEvents(eventsRes.events || [])
      }
    } catch (e: any) {
      setError(e.message || '连接失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
    
    if (!autoRefresh) return
    
    const interval = setInterval(fetchData, refreshInterval)
    return () => clearInterval(interval)
  }, [refreshInterval, autoRefresh])

  const handleTestEvent = async (type: string) => {
    try {
      await perceptionApi.testEvent(type)
      // 刷新数据
      setTimeout(fetchData, 500)
    } catch (e: any) {
      alert('发送测试事件失败: ' + e.message)
    }
  }

  const getSeverityColor = (severity: string) => {
    switch (severity) {
      case 'critical': return '#dc2626'
      case 'high': return '#ea580c'
      case 'medium': return '#ca8a04'
      case 'low': return '#16a34a'
      default: return '#6b7280'
    }
  }

  const getSeverityBg = (severity: string) => {
    switch (severity) {
      case 'critical': return '#fef2f2'
      case 'high': return '#fff7ed'
      case 'medium': return '#fefce8'
      case 'low': return '#f0fdf4'
      default: return '#f9fafb'
    }
  }

  const formatDuration = (seconds: number | undefined) => {
    if (!seconds || seconds < 0) return "-"
    if (seconds < 60) return `${seconds}秒`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}分钟`
    return `${Math.floor(seconds / 3600)}小时 ${Math.floor((seconds % 3600) / 60)}分钟`
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1400px', margin: '0 auto' }}>
      <div className="page-header" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              🧠 感知监控中心
              {status?.running && (
                <span style={{
                  fontSize: '12px',
                  padding: '4px 8px',
                  background: '#dcfce7',
                  color: '#166534',
                  borderRadius: '4px',
                  fontWeight: 500
                }}>
                  运行中
                </span>
              )}
              {!status?.running && status && (
                <span style={{
                  fontSize: '12px',
                  padding: '4px 8px',
                  background: '#fee2e2',
                  color: '#991b1b',
                  borderRadius: '4px',
                  fontWeight: 500
                }}>
                  已停止
                </span>
              )}
            </h2>
            <p style={{ color: '#666', marginTop: '8px', fontSize: '14px' }}>
              实时监控系统状态、异常检测和认知架构运行状态
            </p>
          </div>
          
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', color: '#666' }}>
              <input
                type="checkbox"
                checked={autoRefresh}
                onChange={(e) => setAutoRefresh(e.target.checked)}
              />
              自动刷新
            </label>
            <select
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(Number(e.target.value))}
              style={{
                padding: '6px 12px',
                borderRadius: '6px',
                border: '1px solid #d1d5db',
                fontSize: '14px'
              }}
            >
              <option value={3000}>3秒</option>
              <option value={5000}>5秒</option>
              <option value={10000}>10秒</option>
              <option value={30000}>30秒</option>
            </select>
            <button
              onClick={fetchData}
              className="btn btn-secondary"
              style={{ fontSize: '14px' }}
            >
              🔄 刷新
            </button>
            <div style={{ position: 'relative' }}>
              <button
                className="btn btn-primary"
                style={{ fontSize: '14px' }}
                onClick={() => document.getElementById('test-menu')?.classList.toggle('show')}
              >
                🧪 测试
              </button>
              <div
                id="test-menu"
                style={{
                  display: 'none',
                  position: 'absolute',
                  right: 0,
                  top: '100%',
                  marginTop: '8px',
                  background: 'white',
                  border: '1px solid #e5e7eb',
                  borderRadius: '8px',
                  boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)',
                  zIndex: 100,
                  minWidth: '180px'
                }}
              >
                <div
                  style={{
                    padding: '8px 16px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f3f4f6',
                    fontSize: '14px'
                  }}
                  onClick={() => { handleTestEvent('test'); document.getElementById('test-menu')?.classList.remove('show') }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                >
                  📝 通用测试事件
                </div>
                <div
                  style={{
                    padding: '8px 16px',
                    cursor: 'pointer',
                    borderBottom: '1px solid #f3f4f6',
                    fontSize: '14px'
                  }}
                  onClick={() => { handleTestEvent('api_error'); document.getElementById('test-menu')?.classList.remove('show') }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                >
                  ⚠️ API错误事件
                </div>
                <div
                  style={{
                    padding: '8px 16px',
                    cursor: 'pointer',
                    fontSize: '14px'
                  }}
                  onClick={() => { handleTestEvent('action'); document.getElementById('test-menu')?.classList.remove('show') }}
                  onMouseEnter={(e) => e.currentTarget.style.background = '#f9fafb'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'white'}
                >
                  👤 用户行为事件
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: '48px' }}>
          <div className="loading">正在加载感知监控数据...</div>
        </div>
      )}

      {error && !loading && (
        <div style={{
          padding: '16px 20px',
          background: '#fee2e2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
          color: '#991b1b',
          marginBottom: '24px'
        }}>
          <strong>⚠️ 错误：</strong>{error}
        </div>
      )}

      {!loading && status && (
        <>
          {/* 状态概览卡片 */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
            gap: '16px',
            marginBottom: '24px'
          }}>
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>运行状态</div>
              <div style={{ fontSize: '24px', fontWeight: 600, color: status.running ? '#16a34a' : '#dc2626' }}>
                {status.running ? '🟢 运行中' : '🔴 已停止'}
              </div>
            </div>
            
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>运行时间</div>
              <div style={{ fontSize: '24px', fontWeight: 600, color: '#1f2937' }}>
                {formatDuration(status.uptime_seconds)}
              </div>
            </div>
            
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>事件总数</div>
              <div style={{ fontSize: '24px', fontWeight: 600, color: '#1f2937' }}>
                {(status.event_count || 0).toLocaleString()}
              </div>
            </div>
            
            <div style={{
              background: 'white',
              borderRadius: '12px',
              padding: '20px',
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}>
              <div style={{ fontSize: '13px', color: '#6b7280', marginBottom: '4px' }}>监听器数量</div>
              <div style={{ fontSize: '24px', fontWeight: 600, color: '#1f2937' }}>
                {(status.listeners ? Object.keys(status.listeners).length : 0)}
              </div>
            </div>
          </div>

          {/* 监听器状态 */}
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
            marginBottom: '24px'
          }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: '#1f2937' }}>
              📡 监听器状态
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
              {(status.listeners ? Object.entries(status.listeners) : []).map(([name, listener]) => (
                <div
                  key={name}
                  style={{
                    padding: '10px 16px',
                    borderRadius: '8px',
                    background: listener.running ? '#f0fdf4' : '#fef2f2',
                    border: `1px solid ${listener.running ? '#bbf7d0' : '#fecaca'}`,
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                >
                  <span style={{ fontSize: '16px' }}>
                    {listener.running ? '🟢' : '🔴'}
                  </span>
                  <span style={{ fontSize: '14px', fontWeight: 500, color: '#374151' }}>
                    {name}
                  </span>
                  <span style={{
                    fontSize: '12px',
                    padding: '2px 6px',
                    borderRadius: '4px',
                    background: listener.enabled ? '#dcfce7' : '#fee2e2',
                    color: listener.enabled ? '#166534' : '#991b1b'
                  }}>
                    {listener.enabled ? '启用' : '禁用'}
                  </span>
                </div>
              ))}
            </div>
          </div>

          {/* 事件日志 */}
          <div style={{
            background: 'white',
            borderRadius: '12px',
            padding: '20px',
            boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
          }}>
            <h3 style={{ fontSize: '16px', fontWeight: 600, marginBottom: '16px', color: '#1f2937' }}>
              📋 最近事件 ({events.length}条)
            </h3>
            
            {events.length === 0 ? (
              <div style={{
                padding: '48px',
                textAlign: 'center',
                color: '#6b7280',
                background: '#f9fafb',
                borderRadius: '8px'
              }}>
                <div style={{ fontSize: '48px', marginBottom: '12px' }}>📭</div>
                <div>暂无事件记录</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {events.map((event) => (
                  <div
                    key={event.id}
                    style={{
                      padding: '16px',
                      borderRadius: '8px',
                      background: getSeverityBg(event.severity),
                      border: `1px solid ${getSeverityColor(event.severity)}20`,
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '8px' }}>
                      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
                        <span style={{
                          fontSize: '11px',
                          padding: '2px 8px',
                          borderRadius: '4px',
                          background: getSeverityColor(event.severity),
                          color: 'white',
                          fontWeight: 600,
                          textTransform: 'uppercase'
                        }}>
                          {event.severity}
                        </span>
                        <span style={{ fontSize: '13px', color: '#6b7280' }}>
                          {event.type}
                        </span>
                      </div>
                      <span style={{ fontSize: '12px', color: '#9ca3af' }}>
                        {new Date(event.timestamp).toLocaleString('zh-CN')}
                      </span>
                    </div>
                    <div style={{ fontSize: '14px', color: '#1f2937', marginBottom: '4px' }}>
                      {event.message}
                    </div>
                    <div style={{ fontSize: '12px', color: '#6b7280' }}>
                      来源: {event.source} | ID: {event.id}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}

      <style>{`
        .show {
          display: block !important;
        }
      `}</style>
    </div>
  )
}

export default PerceptionMonitor
