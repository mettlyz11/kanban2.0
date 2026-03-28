import { useState, useEffect, useRef } from 'react'

export function Chat() {
  const [messages, setMessages] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // 加载历史消息
    loadMessages()
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadMessages = async () => {
    try {
      const res = await fetch('/api/chat/messages')
      const data = await res.json()
      if (data.success) {
        setMessages(data.messages || [])
      }
    } catch (e) {
      console.error(e)
    }
  }

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  const sendMessage = async () => {
    if (!input.trim()) return
    
    const userMsg = { id: Date.now(), role: 'user', content: input, timestamp: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/chat/ask-dudu', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: input })
      })
      const data = await res.json()
      
      if (data.success) {
        const assistantMsg = { 
          id: Date.now() + 1, 
          role: 'assistant', 
          content: data.response, 
          timestamp: new Date().toISOString() 
        }
        setMessages(prev => [...prev, assistantMsg])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 140px)' }}>
      <div className="page-header">
        <h2 className="page-title">💬 问Dudu</h2>
      </div>

      {/* 消息列表 */}
      <div style={{ 
        flex: 1, 
        overflowY: 'auto', 
        padding: '20px',
        background: '#f8f9fa',
        borderRadius: '12px',
        marginBottom: '16px'
      }}>
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">👋</div>
            <p>你好！我是Dudu，有什么可以帮你的吗？</p>
          </div>
        )}
        
        {messages.map((msg, index) => (
          <div key={msg.id || index} style={{ 
            display: 'flex', 
            justifyContent: msg.role === 'user' ? 'flex-end' : 'flex-start',
            marginBottom: '16px'
          }}>
            <div style={{ 
              maxWidth: '70%',
              padding: '12px 16px',
              borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
              background: msg.role === 'user' 
                ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' 
                : 'white',
              color: msg.role === 'user' ? 'white' : '#333',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
              whiteSpace: 'pre-wrap'
            }}>
              {msg.content}
            </div>
          </div>
        ))}
        
        {loading && (
          <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
            <div style={{ 
              padding: '12px 16px',
              borderRadius: '16px 16px 16px 4px',
              background: 'white',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}>
              <span style={{ animation: 'pulse 1s infinite' }}>思考中...</span>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 输入框 */}
      <div style={{ display: 'flex', gap: '12px' }}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="输入消息，按Enter发送..."
          style={{
            flex: 1,
            padding: '12px 16px',
            borderRadius: '12px',
            border: '1px solid #ddd',
            resize: 'none',
            minHeight: '60px',
            fontSize: '14px'
          }}
        />
        <button 
          className="btn btn-primary"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
          style={{ padding: '12px 24px' }}
        >
          {loading ? '发送中...' : '发送'}
        </button>
      </div>
    </div>
  )
}

export default Chat
