import { useState, useEffect } from 'react'
import { Plus, Calendar, Users, FileText } from 'lucide-react'

export function MeetingNotes() {
  const [meetings, setMeetings] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [meetingTitle, setMeetingTitle] = useState('')
  const [meetingDate, setMeetingDate] = useState('')
  const [attendees, setAttendees] = useState('')
  const [content, setContent] = useState('')

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

  const handleCreateMeeting = async () => {
    if (!meetingTitle || !meetingDate) {
      alert('请填写会议主题和日期')
      return
    }
    
    try {
      const res = await fetch('/api/meetings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          title: meetingTitle, 
          date: meetingDate,
          attendees,
          content 
        })
      })
      const data = await res.json()
      if (data.success) {
        alert('会议纪要创建成功！')
        setShowAddModal(false)
        setMeetingTitle('')
        setMeetingDate('')
        setAttendees('')
        setContent('')
        loadMeetings()
      }
    } catch (e) {
      console.error(e)
      alert('创建失败')
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">📝 会议纪要 (T020)</h2>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <Plus size={20} />
          新建会议
        </button>
      </div>

      {/* 使用说明卡片 */}
      <div className="card" style={{ marginBottom: '20px', background: '#e0f2fe', border: '1px solid #7dd3fc' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <Calendar size={24} className="text-blue-600" style={{ flexShrink: 0 }} />
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#0369a1' }}>会议纪要说明</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#0c4a6e', lineHeight: '1.6' }}>
              <li>记录会议主题、参会人员、讨论内容</li>
              <li>明确行动项、负责人和截止日期</li>
              <li>会后及时整理并分享给相关人员</li>
              <li>定期回顾会议决议的执行情况</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="card">
        {meetings.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📋</div>
            <h3 style={{ margin: '16px 0 8px', color: '#374151' }}>还没有会议纪要</h3>
            <p style={{ color: '#6b7280', marginBottom: '20px' }}>
              记录你的第一次会议，跟踪行动项和决议
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 auto' }}
            >
              <Plus size={20} />
              创建第一个会议
            </button>
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
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <h4 style={{ margin: 0 }}>{meeting.title || '未命名会议'}</h4>
                  <span style={{ color: '#666', fontSize: '0.9rem' }}>
                    {meeting.date ? new Date(meeting.date).toLocaleDateString('zh-CN') : ''}
                  </span>
                </div>
                {meeting.attendees && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '12px', color: '#666' }}>
                    <Users size={16} />
                    <span>{meeting.attendees}</span>
                  </div>
                )}
                <p style={{ color: '#666', lineHeight: '1.6' }}>{meeting.content || meeting.notes || ''}</p>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 创建会议弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <h3 className="text-lg font-bold mb-4">📝 创建会议纪要</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FileText size={16} className="inline mr-1" />
                会议主题
              </label>
              <input
                type="text"
                value={meetingTitle}
                onChange={(e) => setMeetingTitle(e.target.value)}
                placeholder="例如：周例会 - 产品评审"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar size={16} className="inline mr-1" />
                会议日期
              </label>
              <input
                type="date"
                value={meetingDate}
                onChange={(e) => setMeetingDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Users size={16} className="inline mr-1" />
                参会人员
              </label>
              <input
                type="text"
                value={attendees}
                onChange={(e) => setAttendees(e.target.value)}
                placeholder="用逗号分隔，例如：张三，李四，王五"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                会议内容
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="讨论内容、决议、行动项..."
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setMeetingTitle('')
                  setMeetingDate('')
                  setAttendees('')
                  setContent('')
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleCreateMeeting}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                保存会议
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MeetingNotes
