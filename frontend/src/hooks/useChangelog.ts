/**
 * useChangelog — 通过 HTTP 轮询 system_change_log
 * 替代 WebSocket/Socket.IO 的方案
 * 
 * 用法:
 * const { changes, latestId } = useChangelog()
 * // changes 是最新一批 SDS 侧的变更事件
 */
import { useState, useEffect, useRef, useCallback } from 'react'

interface ChangeEvent {
  id: number
  source: string
  entity_type: string
  entity_id: number
  action: string
  payload: any
  created_at: string
}

interface ChangelogResponse {
  success: boolean
  changes: ChangeEvent[]
  latest_id: number
}

const POLL_INTERVAL = 5000 // 5秒轮询

export function useChangelog(onChange?: (change: ChangeEvent) => void) {
  const [changes, setChanges] = useState<ChangeEvent[]>([])
  const [latestId, setLatestId] = useState(0)
  const lastIdRef = useRef(0)
  const [error, setError] = useState<string | null>(null)

  const poll = useCallback(async () => {
    try {
      const resp = await fetch(`/api/changelog/consume?source=sds&since=${lastIdRef.current}`)
      const data: ChangelogResponse = await resp.json()
      
      if (data.success && data.changes && data.changes.length > 0) {
        setChanges(prev => [...prev.slice(-50), ...data.changes])
        lastIdRef.current = data.latest_id
        setLatestId(data.latest_id)
        
        // 如果有点击回调，逐条通知
        if (onChange) {
          for (const change of data.changes) {
            onChange(change)
          }
        }
      }
      setError(null)
    } catch (e: any) {
      setError(e.message)
    }
  }, [onChange])

  useEffect(() => {
    // 初始拉取
    poll()
    const timer = setInterval(poll, POLL_INTERVAL)
    return () => clearInterval(timer)
  }, [poll])

  return { changes, latestId, error, refresh: poll }
}

/**
 * 按实体类型过滤的专用 hook
 */
export function useChangelogByType(entityType: string) {
  const [events, setEvents] = useState<ChangeEvent[]>([])
  
  useChangelog((change) => {
    if (change.entity_type === entityType) {
      setEvents(prev => [...prev.slice(-50), change])
    }
  })

  return { events }
}
