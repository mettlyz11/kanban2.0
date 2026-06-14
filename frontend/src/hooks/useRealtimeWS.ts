/**
 * useRealtimeWS — 通过 WebSocket 接收 SDS 实时事件 + 发送遥控命令
 * 统一的 SDS WebSocket 管理
 * 
 * 用法:
 * const { events, isConnected, sendCommand } = useRealtimeWS()
 * sendCommand('restart_scheduler')
 */
import { useState, useEffect, useRef, useCallback } from 'react'

export interface WSRealtimeEvent {
  event: string
  data: any
  timestamp: string
}

const WS_URL = `wss://${window.location.host}/monitor/`
const MAX_EVENTS = 50

export function useRealtimeWS(onEvent?: (event: WSRealtimeEvent) => void) {
  const [events, setEvents] = useState<WSRealtimeEvent[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimer = useRef<number | null>(null)
  const eventCbRef = useRef(onEvent)
  eventCbRef.current = onEvent

  const connect = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return
    
    try {
      const ws = new WebSocket(WS_URL)
      wsRef.current = ws

      ws.onopen = () => {
        setIsConnected(true)
      }

      ws.onclose = () => {
        setIsConnected(false)
        wsRef.current = null
        reconnectTimer.current = window.setTimeout(connect, 5000)
      }

      ws.onerror = () => {
        ws.close()
      }

      ws.onmessage = (msg) => {
        try {
          const data = JSON.parse(msg.data)
          
          if (data.type === 'status') {
            setIsConnected(data.upstream_connected || false)
            return
          }
          
          if (data.type === 'sds_batch' && data.events) {
            for (const evt of data.events) {
              _handleEvent(evt)
            }
            return
          }
          
          if (data.type === 'sds_event' && data.event) {
            _handleEvent({
              event: data.event,
              data: data.data,
              timestamp: data.timestamp
            })
            return
          }
        } catch (e) {
          // 非 JSON 消息忽略
        }
      }
    } catch (e) {
      reconnectTimer.current = window.setTimeout(connect, 5000)
    }
  }, [])

  const _handleEvent = useCallback((evt: WSRealtimeEvent) => {
    setEvents(prev => [...prev.slice(-(MAX_EVENTS - 1)), evt])
    if (eventCbRef.current) {
      eventCbRef.current(evt)
    }
  }, [])

  /** 发送遥控命令（通过同一个 WS 连接） */
  const sendCommand = useCallback((cmdId: string, taskId?: string) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      console.warn('WS not connected, can\'t send command')
      return false
    }
    const payload: any = { type: 'kanban_command', command: cmdId }
    if (taskId) payload.task_id = taskId
    ws.send(JSON.stringify(payload))
    return true
  }, [])

  useEffect(() => {
    connect()
    return () => {
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
      }
    }
  }, [connect])

  return { events, isConnected, sendCommand }
}

/**
 * 按事件类型过滤的专用 hook
 */
export function useRealtimeEvent(eventType: string) {
  const [latest, setLatest] = useState<WSRealtimeEvent | null>(null)
  
  useRealtimeWS((evt) => {
    if (evt.event === eventType) {
      setLatest(evt)
    }
  })

  return latest
}
