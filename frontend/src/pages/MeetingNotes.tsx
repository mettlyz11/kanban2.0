import { useState, useEffect } from 'react'

export function MeetingNotes() {
  const [meetings, setMeetings] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

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

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
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
                padding: '20px',
                background: '#f8f9fa',
                borderRadius: '8px'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <h4 style={{ margin: 0 }}>{meeting.title || '未命名会议'}</h4>
                  <span style={{ color: '#999', fontSize: '0.85rem' }}>
                    {meeting.meeting_date && new Date(meeting.meeting_date).toLocaleDateString('zh-CN')}
                  </span>
                </div>
                <p style={{ color: '#666' }}>{meeting.summary || meeting.content || ''}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
