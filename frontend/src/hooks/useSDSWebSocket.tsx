import { useState, useEffect } from 'react'

interface SDSWebSocketHook {
  connected: boolean
  taskCreated: any | null
  taskExecuting: any | null
  taskCompleted: any | null
  taskFailed: any | null
  systemStatus: any | null
  alert: any | null
  clearEvent: () => void
  clearAllEvents: () => void
}

export function useSDSWebSocket(): SDSWebSocketHook {
  const [connected, setConnected] = useState(false)
  const [event, setEvent] = useState<any>(null)
  
  useEffect(() => {
    const wsUrl = (window.location.protocol === 'https:' ? 'wss:' : 'ws:') + '//' + window.location.host + '/ws/sds'
    let ws: WebSocket | null = null
    let reconnectTimer: any = null

    const connect = () => {
      ws = new WebSocket(wsUrl)
      ws.onopen = () => setConnected(true)
      ws.onclose = () => {
        setConnected(false)
        reconnectTimer = setTimeout(connect, 5000)
      }
      ws.onmessage = (msg) => {
        try {
          setEvent(JSON.parse(msg.data))
        } catch {}
      }
      ws.onerror = () => ws?.close()
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      ws?.close()
    }
  }, [])

  const clearEvent = () => setEvent(null)
  const clearAllEvents = () => setEvent(null)

  return {
    connected,
    taskCreated: event?.type === 'task_created' ? event : null,
    taskExecuting: event?.type === 'task_executing' ? event : null,
    taskCompleted: event?.type === 'task_completed' ? event : null,
    taskFailed: event?.type === 'task_failed' ? event : null,
    systemStatus: event?.type === 'system_status' ? event : null,
    alert: event?.type === 'alert' ? event : null,
    clearEvent,
    clearAllEvents,
  }
}
