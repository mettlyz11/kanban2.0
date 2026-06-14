/**
 * RealtimeToast — SDS 实时事件 Toast 通知组件
 * 放在 Dashboard 或全局 Layout 中，接收 WS 事件后弹出通知
 */
import React, { useEffect, useState } from 'react'
import { useRealtimeWS } from '../hooks/useRealtimeWS'

interface ToastMsg {
  id: number
  text: string
  type: 'success' | 'error' | 'warning' | 'info'
}

let toastId = 0

export default function RealtimeToast() {
  const [toasts, setToasts] = useState<ToastMsg[]>([])

  useRealtimeWS((evt) => {
    const { event, data } = evt
    let text = ''
    let type: ToastMsg['type'] = 'info'

    if (event === 'review') {
      const dec = data.decision
      const tid = 'T' + data.task_id
      if (dec === 'rejected') {
        text = `⛔ ${tid} 被驳回（${(data.reason || '').slice(0, 30)}）`
        type = 'error'
      } else if (dec === 'approved') {
        text = `✅ ${tid} 审核通过`
        type = 'success'
      } else if (dec === 'steer') {
        text = `🔄 ${tid} 需调整`
        type = 'warning'
      }
    } else if (event === 'task_status') {
      const tid = 'T' + data.task_id
      if (data.status === 'in_progress') {
        text = `▶️ ${tid} 开始执行`
        type = 'info'
      } else if (data.status === 'completed') {
        text = `✅ ${tid} 执行完成`
        type = 'success'
      }
    } else if (event === 'dependency') {
      text = `🔗 依赖链异常: T${data.task_id}`
      type = 'warning'
    }

    if (text) {
      const id = ++toastId
      setToasts(prev => [...prev, { id, text, type }])
      setTimeout(() => {
        setToasts(prev => prev.filter(t => t.id !== id))
      }, 5000)
    }
  })

  if (toasts.length === 0) return null

  return (
    <div style={{
      position: 'fixed', bottom: 20, right: 20, zIndex: 9999,
      display: 'flex', flexDirection: 'column', gap: 8, maxWidth: 360
    }}>
      {toasts.map(t => (
        <div key={t.id} style={{
          padding: '10px 14px', borderRadius: 8, fontSize: 13,
          background: t.type === 'error' ? '#fef2f2' : t.type === 'warning' ? '#fffbeb' :
                      t.type === 'success' ? '#f0fdf4' : '#eff6ff',
          border: `1px solid ${
            t.type === 'error' ? '#fecaca' : t.type === 'warning' ? '#fde68a' :
            t.type === 'success' ? '#bbf7d0' : '#bfdbfe'
          }`,
          color: t.type === 'error' ? '#991b1b' : t.type === 'warning' ? '#92400e' :
                 t.type === 'success' ? '#166534' : '#1e40af',
          boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
          cursor: 'pointer'
        }} onClick={() => setToasts(prev => prev.filter(x => x.id !== t.id))}>
          {t.text}
        </div>
      ))}
    </div>
  )
}
