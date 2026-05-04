import { useState, useEffect, useRef, useCallback } from 'react'

interface LocalMetrics {
  cpu: { percent: number; cores: number; freq_mhz: number | null; per_cpu: number[] }
  memory: { percent: number; total_gb: number; used_gb: number; available_gb: number }
  disk: { percent: number; total_gb: number; used_gb: number; free_gb: number }
  network: { bytes_sent_mb: number; bytes_recv_mb: number }
  processes: number
  battery: { percent: number | null; power_plugged: boolean | null; secsleft: number | null }
  uptime: number
  timestamp: string
}

interface HistoryPoint {
  timestamp: string; cpu: number; memory: number; disk: number; processes: number
}

// 通过 Nginx 反向代理连接中继服务
const WS_URL = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/monitor/`

export function useLocalSystemMonitor() {
  const [connected, setConnected] = useState(false)
  const [metrics, setMetrics] = useState<LocalMetrics | null>(null)
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 30

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    try {
      console.log('🖥️ 连接 Mac mini 监控:', WS_URL)
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('✅ 已连接 Mac mini 监控')
        setConnected(true)
        setError(null)
        reconnectAttemptsRef.current = 0
      }

      ws.onclose = () => {
        console.log('❌ Mac mini 监控断开')
        setConnected(false)
        if (reconnectAttemptsRef.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(1.5, reconnectAttemptsRef.current), 30000)
          reconnectTimerRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++
            connect()
          }, delay)
        } else {
          setError('无法连接到 Mac mini 监控服务')
        }
      }

      ws.onerror = () => setError('连接 Mac mini 失败')

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          if (data.type === 'metrics') {
            setMetrics(data.metrics)
            if (data.history) setHistory(data.history)
          }
        } catch (e) {
          console.error('解析监控数据失败:', e)
        }
      }
    } catch (e) {
      setError('无法创建连接')
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    if (wsRef.current) wsRef.current.close()
    wsRef.current = null
    setConnected(false)
  }, [])

  useEffect(() => { connect(); return () => disconnect() }, [connect, disconnect])

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}天 ${hours}小时 ${minutes}分钟`
  }

  return { connected, metrics, history, error, formatUptime, reconnect: connect, disconnect }
}
