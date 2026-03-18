import { useState, useEffect } from 'react'

export function MeetingNotes() {
  const [meetings, setMeetings] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  useEffect(() => {
    loadMeetings()
  }, [])

  const loadMeetings = async () => {
    try {
      const res = await fetch('/api/meetings')
      const data = await res.json()
      if (data.success) setMeetings(data.meetings || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const toggleExpand = (id: string) => {
    setExpandedId(expandedId === id ? null : id)
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">📝 会议纪要 (T020)</h2>
      </div>

      <div className="card">
        {meetings.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📝</div>
            <p>暂无会议纪要</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {meetings.map((meeting: any, i: number) => (
              <div key={i} style={{
                padding: '24px',
                background: '#f8f9fa',
                borderRadius: '12px',
                border: '1px solid #e0e0e0'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
                  <div style={{ flex: 1 }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '1.2rem', color: '#333' }}>
                      {meeting.title || '未命名会议'}
                    </h4>
                    <div style={{ display: 'flex', gap: '16px', color: '#888', fontSize: '0.9rem', flexWrap: 'wrap' }}>
                      {meeting.meeting_date && (
                        <span>📅 {new Date(meeting.meeting_date).toLocaleDateString('zh-CN')}</span>
                      )}
                      {meeting.attendees && (
                        <span>👥 {meeting.attendees}</span>
                      )}
                      {meeting.location && (
                        <span>📍 {meeting.location}</span>
                      )}
                    </div>
                  </div>
                  <button
                    onClick={() => toggleExpand(meeting.id || String(i))}
                    style={{
                      padding: '8px 16px',
                      background: expandedId === (meeting.id || String(i)) ? '#667eea' : 'white',
                      color: expandedId === (meeting.id || String(i)) ? 'white' : '#667eea',
                      border: '1px solid #667eea',
                      borderRadius: '8px',
                      cursor: 'pointer',
                      fontWeight: '500',
                      fontSize: '0.9rem',
                      marginLeft: '16px',
                      flexShrink: 0
                    }}
                  >
                    {expandedId === (meeting.id || String(i)) ? '收起' : '展开'}
                  </button>
                </div>
                
                {/* 摘要预览 */}
                <div style={{ 
                  padding: '16px', 
                  background: 'white', 
                  borderRadius: '8px',
                  marginBottom: '16px',
                  borderLeft: '4px solid #667eea'
                }}>
                  <div style={{ fontWeight: '600', marginBottom: '8px', color: '#667eea' }}>📋 会议摘要</div>
                  <p style={{ margin: 0, color: '#555', lineHeight: '1.6' }}>
                    {meeting.summary || meeting.content || '无摘要'}
                  </p>
                </div>

                {/* 完整内容 */}
                {expandedId === (meeting.id || String(i)) && (
                  <div style={{ 
                    padding: '20px', 
                    background: 'white', 
                    borderRadius: '8px',
                    border: '1px solid #e0e0e0'
                  }}>
                    <div style={{ fontWeight: '600', marginBottom: '12px', color: '#667eea', fontSize: '1.1rem' }}>
                      📄 完整会议纪要
                    </div>
                    <div style={{ 
                      whiteSpace: 'pre-wrap', 
                      lineHeight: '1.8', 
                      color: '#333',
                      fontSize: '0.95rem'
                    }}>
                      {meeting.content || meeting.full_content || '无详细内容'}
                    </div>
                    
                    {/* 会议决议 */}
                    {meeting.decisions && meeting.decisions.length > 0 && (
                      <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '2px solid #e0e0e0' }}>
                        <div style={{ fontWeight: '600', marginBottom: '12px', color: '#764ba2' }}>
                          ✅ 会议决议
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '20px', color: '#555' }}>
                          {meeting.decisions.map((decision: string, idx: number) => (
                            <li key={idx} style={{ marginBottom: '8px', lineHeight: '1.6' }}>{decision}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                    
                    {/* 待办事项 */}
                    {meeting.action_items && meeting.action_items.length > 0 && (
                      <div style={{ marginTop: '24px', paddingTop: '20px', borderTop: '2px solid #e0e0e0' }}>
                        <div style={{ fontWeight: '600', marginBottom: '12px', color: '#f59e0b' }}>
                          📌 待办事项
                        </div>
                        <ul style={{ margin: 0, paddingLeft: '20px', color: '#555' }}>
                          {meeting.action_items.map((item: any, idx: number) => (
                            <li key={idx} style={{ marginBottom: '8px', lineHeight: '1.6' }}>
                              <strong>{item.task || item}</strong>
                              {item.assignee && <span> - 👤 {item.assignee}</span>}
                              {item.due_date && <span> - 📅 {new Date(item.due_date).toLocaleDateString('zh-CN')}</span>}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
