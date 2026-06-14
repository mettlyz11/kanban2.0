/**
 * Mac mini 同步数据 WebSocket Hook
 * 监听来自 Mac mini 统一同步服务的实时推送
 * 
 * 使用方式：
 * const { syncData, lastUpdate, isConnected } = useMacMiniSync('cron_sync')
 */
import { useState, useEffect, useRef, useCallback } from 'react'
import { socketIO } from '../utils/socket'

interface SyncData {
  type: string
  data: any
  timestamp: string
}

const SYNC_EVENT_MAP: Record<string, string> = {
  'cron_sync': 'cron_updated',
  'heartbeat_sync': 'heartbeat_updated',
  'model_config_sync': 'model_config_updated',
  'skills_tools_sync': 'skills_tools_updated'
}

export function useMacMiniSync(syncType?: string) {
  const [syncData, setSyncData] = useState<Record<string, any>>({})
  const [lastUpdate, setLastUpdate] = useState<string | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const isConnectedRef = useRef(false)

  useEffect(() => {
    // 关键修复：主动连接 socketIO（如果还没连接）
    if (!isConnectedRef.current) {
      socketIO.connect({
        userId: 'macmini-sync-viewer',
        username: 'Mac mini 同步',
        onConnect: () => {
          setIsConnected(true)
          isConnectedRef.current = true
        },
        onDisconnect: () => {
          setIsConnected(false)
          isConnectedRef.current = false
        },
      }).catch(() => {
        // 连接失败也不阻塞页面
      })
    }

    // 立即检查当前连接状态
    if (socketIO.isConnected()) {
      setIsConnected(true)
      isConnectedRef.current = true
    }

    // 监听所有同步事件
    const handlers: Record<string, (data: any) => void> = {}

    Object.entries(SYNC_EVENT_MAP).forEach(([type, event]) => {
      handlers[event] = (data: SyncData) => {
        setSyncData(prev => ({
          ...prev,
          [data.type || type]: data.data
        }))
        setLastUpdate(data.timestamp || new Date().toISOString())
      }
      socketIO.on(event, handlers[event])
    })

    // 监听连接状态变化
    const checkConn = setInterval(() => {
      const nowConnected = socketIO.isConnected()
      if (nowConnected !== isConnectedRef.current) {
        setIsConnected(nowConnected)
        isConnectedRef.current = nowConnected
      }
    }, 2000)

    return () => {
      clearInterval(checkConn)
      Object.entries(handlers).forEach(([event, handler]) => {
        socketIO.off(event, handler)
      })
    }
  }, [])

  return {
    syncData,
    lastUpdate,
    isConnected,
    getData: (type: string) => syncData[type]
  }
}

/**
 * 专用 Hook：获取 Mac mini 同步的 Cron 数据
 */
export function useMacMiniCron() {
  const { syncData, lastUpdate, isConnected } = useMacMiniSync('cron_sync')
  return {
    jobs: syncData['cron_sync']?.jobs || [],
    count: syncData['cron_sync']?.count || 0,
    lastUpdate,
    isConnected
  }
}

/**
 * 专用 Hook：获取 Mac mini 同步的心跳数据
 */
export function useMacMiniHeartbeat() {
  const { syncData, lastUpdate, isConnected } = useMacMiniSync('heartbeat_sync')
  return {
    data: syncData['heartbeat_sync'] || null,
    lastUpdate,
    isConnected
  }
}

/**
 * 专用 Hook：获取 Mac mini 同步的大模型配置
 */
export function useMacMiniLLM() {
  const { syncData, lastUpdate, isConnected } = useMacMiniSync('model_config_sync')
  return {
    providers: syncData['model_config_sync']?.providers || [],
    defaultModel: syncData['model_config_sync']?.default_model || '',
    fallbackChain: syncData['model_config_sync']?.fallback_chain || [],
    lastUpdate,
    isConnected
  }
}

/**
 * 专用 Hook：获取 Mac mini 同步的 Skills 和 Tools
 */
export function useMacMiniSkillsTools() {
  const { syncData, lastUpdate, isConnected } = useMacMiniSync('skills_tools_sync')
  return {
    skills: syncData['skills_tools_sync']?.skills || null,
    tools: syncData['skills_tools_sync']?.tools || null,
    lastUpdate,
    isConnected
  }
}
