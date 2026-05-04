import { useState, useEffect, useRef, useCallback } from 'react'
import { socket, connectSocket, disconnectSocket } from '../utils/socket'

interface SDSWebSocketState {
  connected: boolean
  taskCreated: any | null
  taskExecuting: { task_id: number; progress: number; status_message: string } | null
  taskCompleted: { task_id: number; result_summary: string } | null
  taskFailed: { task_id: number; error: string } | null
  systemStatus: { status: string; metrics: any } | null
  alert: { type: string; message: string; severity: string } | null
}

export function useSDSWebSocket(userId?: string) {
  const [state, setState] = useState<SDSWebSocketState>({
    connected: false,
    taskCreated: null,
    taskExecuting: null,
    taskCompleted: null,
    taskFailed: null,
    systemStatus: null,
    alert: null,
  })

  const eventBufferRef = useRef<any[]>([])
  const userIdRef = useRef(userId)

  const connect = useCallback(() => {
    connectSocket()
    socket.on('connect', () => {
      setState(prev => ({ ...prev, connected: true }))
      console.log('🔌 SDS WebSocket 已连接')
      
      if (userIdRef.current) {
        socket.emit('sds_subscribe', { user_id: userIdRef.current })
      }
    })

    socket.on('disconnect', () => {
      setState(prev => ({ ...prev, connected: false }))
      console.log('🔌 SDS WebSocket 已断开')
    })

    socket.on('sds_task_created', (data: any) => {
      setState(prev => ({ ...prev, taskCreated: data }))
      eventBufferRef.current.push({ type: 'task_created', data })
    })

    socket.on('sds_task_executing', (data: any) => {
      setState(prev => ({ ...prev, taskExecuting: data }))
      eventBufferRef.current.push({ type: 'task_executing', data })
    })

    socket.on('sds_task_completed', (data: any) => {
      setState(prev => ({ ...prev, taskCompleted: data }))
      eventBufferRef.current.push({ type: 'task_completed', data })
    })

    socket.on('sds_task_failed', (data: any) => {
      setState(prev => ({ ...prev, taskFailed: data }))
      eventBufferRef.current.push({ type: 'task_failed', data })
    })

    socket.on('sds_system_status', (data: any) => {
      setState(prev => ({ ...prev, systemStatus: data }))
      eventBufferRef.current.push({ type: 'system_status', data })
    })

    socket.on('sds_alert', (data: any) => {
      setState(prev => ({ ...prev, alert: data }))
      eventBufferRef.current.push({ type: 'alert', data })
    })
  }, [])

  const disconnect = useCallback(() => {
    socket.emit('sds_unsubscribe', { user_id: userIdRef.current })
    disconnectSocket()
    setState({
      connected: false,
      taskCreated: null,
      taskExecuting: null,
      taskCompleted: null,
      taskFailed: null,
      systemStatus: null,
      alert: null,
    })
  }, [])

  const clearEvent = useCallback((eventType: string) => {
    setState(prev => ({ ...prev, [eventType]: null }))
  }, [])

  const clearAllEvents = useCallback(() => {
    setState(prev => ({
      ...prev,
      taskCreated: null,
      taskExecuting: null,
      taskCompleted: null,
      taskFailed: null,
      systemStatus: null,
      alert: null,
    }))
  }, [])

  const getEventHistory = useCallback(() => {
    return [...eventBufferRef.current]
  }, [])

  useEffect(() => {
    connect()
    return () => {
      disconnect()
    }
  }, [connect, disconnect])

  return {
    ...state,
    clearEvent,
    clearAllEvents,
    getEventHistory,
    reconnect: connect,
  }
}
