import { useState, useEffect, useRef, useCallback } from 'react'
import { socketIO, SocketIOConfig } from '../utils/socket'

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

export function useLocalSystemMonitor() {
  const [connected, setConnected] = useState(socketIO?.connected ?? false)
  const [metrics, setMetrics] = useState<LocalMetrics | null>(null)
  const [history, setHistory] = useState<HistoryPoint[]>([])
  const [error, setError] = useState<string | null>(null)

  // Listen for resource_metrics events from backend Socket.IO broadcast
  useEffect(() => {
    if (!socketIO) {
      setError('Socket.IO not available')
      return
    }

    // Ensure Socket.IO is connected
    if (!socketIO.connected) {
      socketIO.connect({
        userId: 'local',
        username: 'SystemMonitor'
      })
    }

    // Subscribe to monitoring channel
    const subTimeout = setTimeout(() => {
      socketIO.emit('monitor_subscribe', { user_id: 'local' })
    }, 500)

    const handleMetrics = (data: any) => {
      if (data) {
        setMetrics({
          cpu: { percent: data.cpu ?? 0, cores: 0, freq_mhz: null, per_cpu: [] },
          memory: { percent: data.memory ?? 0, total_gb: 0, used_gb: 0, available_gb: 0 },
          disk: { percent: data.disk ?? 0, total_gb: 0, used_gb: 0, free_gb: 0 },
          network: { bytes_sent_mb: 0, bytes_recv_mb: 0 },
          processes: data.processes ?? 0,
          battery: { percent: null, power_plugged: null, secsleft: null },
          uptime: data.uptime ?? 0,
          timestamp: data.timestamp ?? new Date().toISOString()
        })
        
        // Build history point
        if (data.timestamp && data.cpu != null) {
          setHistory(prev => {
            const point: HistoryPoint = {
              timestamp: data.timestamp,
              cpu: data.cpu,
              memory: data.memory ?? 0,
              disk: data.disk ?? 0,
              processes: data.processes ?? 0
            }
            const next = [...prev, point]
            return next.length > 100 ? next.slice(-100) : next
          })
        }
      }
    }

    const handleConnect = () => {
      console.log('✅ Socket.IO 已连接 (系统监控)')
      setConnected(true)
      setError(null)
      socketIO.emit('monitor_subscribe', { user_id: 'local' })
    }

    const handleDisconnect = () => {
      console.log('❌ Socket.IO 断开 (系统监控)')
      setConnected(false)
    }

    // Register handlers
    socketIO.on('resource_metrics', handleMetrics)
    socketIO.on('connect', handleConnect)
    socketIO.on('disconnect', handleDisconnect)

    // If already connected, set state
    if (socketIO.connected) {
      setConnected(true)
    }

    return () => {
      socketIO.off('resource_metrics', handleMetrics)
      socketIO.off('connect', handleConnect)
      socketIO.off('disconnect', handleDisconnect)
      socketIO.emit('monitor_unsubscribe', { user_id: 'local' })
    }
  }, [])

  const formatUptime = (seconds: number) => {
    const days = Math.floor(seconds / 86400)
    const hours = Math.floor((seconds % 86400) / 3600)
    const minutes = Math.floor((seconds % 3600) / 60)
    return `${days}天 ${hours}小时 ${minutes}分钟`
  }

  return { connected, metrics, history, error, formatUptime }
}
