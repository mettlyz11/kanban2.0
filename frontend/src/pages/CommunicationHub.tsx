import { useState, useEffect, useRef } from 'react'

interface Message {
  id: string
  type: 'dudu' | 'user' | 'system' | 'task'
  content: string
  timestamp: string
  status?: 'pending' | 'completed' | 'attention'
  priority?: 'high' | 'medium' | 'low'
}

export function CommunicationHub() {
  const [messages, setMessages] = useState<Message[]>([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<'chat' | 'tasks' | 'updates'>('chat')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // 加载历史消息
  useEffect(() => {
    loadMessages()
    // 每30秒刷新一次
    const interval = setInterval(loadMessages, 30000)
    return () => clearInterval(interval)
  }, [activeTab])

  const loadMessages = async () => {
    try {
      // 从API加载消息
      const res = await fetch('/api/communication/messages')
      if (res.ok) {
        const data = await res.json()
        if (data.success) {
          setMessages(data.messages || [])
        }
      }
    } catch (e) {
      // 使用模拟数据
      setMessages([
        {
          id: '1',
          type: 'system',
          content: '👋 欢迎来到Dudu对接中心！这里是我们的专属沟通窗口。',
          timestamp: new Date().toISOString()
        },
        {
          id: '2',
          type: 'task',
          content: '【需要您确认】体检报告已找到3份，请确认是否需要详细分析？',
          timestamp: new Date(Date.now() - 3600000).toISOString(),
          status: 'pending',
          priority: 'high'
        },
        {
          id: '3',
          type: 'dudu',
          content: '关于和光智成融资，我已经整理了投资机构清单，请问您希望优先联系哪些机构？',
          timestamp: new Date(Date.now() - 7200000).toISOString()
        }
      ])
    }
  }

  const sendMessage = async () => {
    if (!inputMessage.trim()) return

    const newMessage: Message = {
      id: Date.now().toString(),
      type: 'user',
      content: inputMessage,
      timestamp: new Date().toISOString()
    }

    setMessages(prev => [...prev, newMessage])
    setInputMessage('')
    setLoading(true)

    // 发送到后端
    try {
      await fetch('/api/communication/send', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: inputMessage })
      })
    } catch (e) {
      console.error('Failed to send message:', e)
    }

    setLoading(false)
  }

  const formatTime = (timestamp: string) => {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
  }

  const getMessageStyle = (type: string) => {
    switch (type) {
      case 'dudu':
        return { background: '#e0f2fe', borderLeft: '4px solid #0288d1', alignSelf: 'flex-start' }
      case 'user':
        return { background: '#e8f5e9', borderLeft: '4px solid #4caf50', alignSelf: 'flex-end' }
      case 'system':
        return { background: '#fff3e0', borderLeft: '4px solid #ff9800', alignSelf: 'center' }
      case 'task':
        return { background: '#fce4ec', borderLeft: '4px solid #e91e63', alignSelf: 'flex-start' }
      default:
        return { background: '#f5f5f5', borderLeft: '4px solid #9e9e9e' }
    }
  }

  const getPriorityBadge = (priority?: string) => {
    if (!priority) return null
    const colors: Record<string, string> = {
      high: '#ef4444',
      medium: '#f59e0b',
      low: '#6b7280'
    }
    const labels: Record<string, string> = {
      high: '高优先级',
      medium: '中优先级',
      low: '低优先级'
    }
    return (
      <span style={{
        display: 'inline-block',
        padding: '2px 8px',
        background: colors[priority],
        color: 'white',
        borderRadius: '4px',
        fontSize: '11px',
        marginLeft: '8px'
      }}>
        {labels[priority]}
      </span>
    )
  }

  const pendingTasks = messages.filter(m => m.type === 'task' && m.status === 'pending')
  const completedTasks = messages.filter(m => m.type === 'task' && m.status === 'completed')

  return (
    <div style={{ height: 'calc(100vh - 80px)', display: 'flex', flexDirection: 'column' }}>
      {/* 头部 */}
      <div className="page-header" style={{ marginBottom: 0, padding: '16px 24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h2 className="page-title" style={{ margin: 0 }}>💬 Dudu对接中心</h2>
            <p style={{ color: '#666', margin: '4px 0 0 0', fontSize: '14px' }}>
              专属沟通窗口 · 飞书实时 + 看板综合 · 需要您处理的任务会优先显示
            </p>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            {pendingTasks.length > 0 && (
              <div style={{
                padding: '8px 16px',
                background: '#fee2e2',
                borderRadius: '8px',
                color: '#dc2626',
                fontSize: '14px'
              }}>
                ⚠️ {pendingTasks.length} 个待处理事项
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 标签页 */}
      <div style={{
        display: 'flex',
        borderBottom: '1px solid #e0e0e0',
        background: '#fafafa'
      }}>
        {[
          { key: 'chat', label: '💬 对话', icon: '' },
          { key: 'tasks', label: `✅ 待办 (${pendingTasks.length})`, icon: '' },
          { key: 'updates', label: '📊 进展', icon: '' }
        ].map((tab: any) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '12px 24px',
              border: 'none',
              background: activeTab === tab.key ? '#fff' : 'transparent',
              borderBottom: activeTab === tab.key ? '2px solid #667eea' : 'none',
              cursor: 'pointer',
              fontSize: '14px',
              fontWeight: activeTab === tab.key ? 600 : 400,
              color: activeTab === tab.key ? '#667eea' : '#666'
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* 内容区 */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>
        {/* 消息列表 */}
        <div style={{
          flex: 1,
          overflowY: 'auto',
          padding: '20px',
          background: '#f8fafc'
        }}>
          {activeTab === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxWidth: '800px', margin: '0 auto' }}>
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  style={{
                    padding: '12px 16px',
                    borderRadius: '12px',
                    maxWidth: '80%',
                    ...getMessageStyle(msg.type)
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                    <span style={{ fontSize: '12px', color: '#666', fontWeight: 600 }}>
                      {msg.type === 'dudu' ? '🐾 Dudu' : 
                       msg.type === 'user' ? '👤 您' : 
                       msg.type === 'system' ? '🔔 系统' : 
                       msg.type === 'task' ? '📋 任务' : '💬'}
                    </span>
                    <span style={{ fontSize: '11px', color: '#999' }}>
                      {formatTime(msg.timestamp)}
                    </span>
                  </div>
                  <div style={{ fontSize: '14px', lineHeight: 1.6, color: '#333' }}>
                    {msg.content}
                  </div>
                  {msg.priority && getPriorityBadge(msg.priority)}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}

          {activeTab === 'tasks' && (
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
              <h3 style={{ marginBottom: '16px', color: '#dc2626' }}>⚠️ 需要您处理 ({pendingTasks.length})</h3>
              {pendingTasks.map(task => (
                <div key={task.id} style={{
                  padding: '16px',
                  background: '#fff',
                  borderRadius: '12px',
                  marginBottom: '12px',
                  borderLeft: '4px solid #e91e63',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.05)'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div style={{ fontSize: '15px', fontWeight: 500 }}>{task.content}</div>
                    {getPriorityBadge(task.priority)}
                  </div>
                  <div style={{ marginTop: '8px', display: 'flex', gap: '8px' }}>
                    <button className="btn btn-success" style={{ padding: '6px 12px', fontSize: '12px' }}>
                      已处理
                    </button>
                    <button className="btn btn-secondary" style={{ padding: '6px 12px', fontSize: '12px' }}>
                      稍后处理
                    </button>
                    <button className="btn btn-danger" style={{ padding: '6px 12px', fontSize: '12px' }}>
                      不需要
                    </button>
                  </div>
                </div>
              ))}

              {completedTasks.length > 0 && (
                <>
                  <h3 style={{ marginTop: '24px', marginBottom: '16px', color: '#059669' }}>✅ 已完成 ({completedTasks.length})</h3>
                  {completedTasks.map(task => (
                    <div key={task.id} style={{
                      padding: '12px 16px',
                      background: '#f0fdf4',
                      borderRadius: '8px',
                      marginBottom: '8px',
                      opacity: 0.7
                    }}>
                      <span style={{ textDecoration: 'line-through' }}>{task.content}</span>
                    </div>
                  ))}
                </>
              )}
            </div>
          )}

          {activeTab === 'updates' && (
            <div style={{ maxWidth: '800px', margin: '0 auto' }}>
              <div style={{ textAlign: 'center', padding: '40px', color: '#666' }}>
                <div style={{ fontSize: '48px', marginBottom: '16px' }}>📊</div>
                <h3>进展追踪</h3>
                <p>各目标进展统计图表将在此展示</p>
              </div>
            </div>
          )}
        </div>

        {/* 侧边栏 - 快捷操作 */}
        <div style={{
          width: '280px',
          padding: '20px',
          background: '#fff',
          borderLeft: '1px solid #e0e0e0',
          overflowY: 'auto'
        }}>
          <h4 style={{ marginBottom: '16px', fontSize: '16px' }}>🚀 快捷操作</h4>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '24px' }}>
            <button className="btn btn-primary" style={{ textAlign: 'left', justifyContent: 'flex-start' }}>
              📋 提交新任务
            </button>
            <button className="btn btn-secondary" style={{ textAlign: 'left', justifyContent: 'flex-start' }}>
              📊 查看进展报告
            </button>
            <button className="btn btn-secondary" style={{ textAlign: 'left', justifyContent: 'flex-start' }}>
              🎯 更新目标
            </button>
            <button className="btn btn-secondary" style={{ textAlign: 'left', justifyContent: 'flex-start' }}>
              📞 紧急联系
            </button>
          </div>

          <h4 style={{ marginBottom: '16px', fontSize: '16px' }}>📌 重点提醒</h4>
          <div style={{
            padding: '12px',
            background: '#fef3c7',
            borderRadius: '8px',
            fontSize: '13px',
            color: '#92400e'
          }}>
            <strong>今日重点：</strong>
            <ul style={{ paddingLeft: '16px', marginTop: '8px' }}>
              <li>和光智成BP优化</li>
              <li>体检报告确认</li>
              <li>子女教育规划</li>
            </ul>
          </div>

          <h4 style={{ marginTop: '24px', marginBottom: '16px', fontSize: '16px' }}>🤝 对接方式</h4>
          <div style={{ fontSize: '13px', color: '#666' }}>
            <p style={{ marginBottom: '8px' }}>
              <strong>飞书：</strong>实时沟通
            </p>
            <p style={{ marginBottom: '8px' }}>
              <strong>看板：</strong>综合管理和任务追踪
            </p>
            <p>
              <strong>优先级：</strong>高优先级事项会通过飞书即时通知
            </p>
          </div>
        </div>
      </div>

      {/* 输入框 */}
      {activeTab === 'chat' && (
        <div style={{
          padding: '16px 24px',
          background: '#fff',
          borderTop: '1px solid #e0e0e0',
          display: 'flex',
          gap: '12px'
        }}>
          <input
            type="text"
            value={inputMessage}
            onChange={(e) => setInputMessage(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
            placeholder="输入消息给Dudu..."
            style={{
              flex: 1,
              padding: '12px 16px',
              borderRadius: '8px',
              border: '1px solid #ddd',
              fontSize: '14px'
            }}
          />
          <button
            onClick={sendMessage}
            disabled={loading || !inputMessage.trim()}
            className="btn btn-primary"
            style={{ padding: '12px 24px' }}
          >
            {loading ? '发送中...' : '发送'}
          </button>
        </div>
      )}
    </div>
  )
}
