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

// 自动检测协议：HTTPS 用 wss://，HTTP 用 ws://
const PROTOCOL = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
const WS_URL = `${PROTOCOL}://${window.location.host}/monitor/`

export function useLocalSystemMonitor() {
  const [connected, setConnected] = useState(false)
  const [metrics, setMetrics] = useState<LocalMetrics | null>(null)
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const reconnectAttemptsRef = useRef(0)
  const maxReconnectAttempts = 30
  const errorTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    if (wsRef.current?.readyState === WebSocket.CONNECTING) return

    try {
      console.log('🖥️ 连接 Mac mini 监控:', WS_URL)
      setError(null)
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      // 5秒超时检测
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
      errorTimerRef.current = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          setError('连接超时')
          ws.close()
        }
      }, 5000)

      ws.onopen = () => {
        console.log('✅ 已连接 Mac mini 监控')
        setConnected(true)
        setError(null)  // 确保清除错误
        reconnectAttemptsRef.current = 0
        if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
      }

      ws.onclose = () => {
        console.log('❌ Mac mini 监控断开')
        setConnected(false)
        if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
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

      ws.onerror = () => {
        // 关键修复：忽略握手阶段的 error 事件
        // 浏览器在 WebSocket 握手期间会触发 error，但后续 onopen 仍会成功
        // 只有 CLOSED 状态才认为是真正的失败
        if (ws.readyState === WebSocket.CLOSED) {
          setError('无法创建连接')
        }
      }

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
      if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
      setError('无法创建连接')
    }
  }, [])

  const disconnect = useCallback(() => {
    if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current)
    if (errorTimerRef.current) clearTimeout(errorTimerRef.current)
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
