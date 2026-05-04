import { useState, useEffect, useMemo } from 'react'
import { useMeetingWebSocket } from '../hooks/useMeetingWebSocket'
import { Wifi, WifiOff, Users } from 'lucide-react'
import { Plus, Calendar, Users, FileText, Clock, Tag, X, Search } from 'lucide-react'
import './MeetingNotes.css'

interface Meeting {
  id: number
  title: string
  date: string
  attendees: string
  content: string
}

function extractKeywords(text: string): string[] {
  if (!text) return []
  const stopWords = new Set(['的', '了', '是', '在', '和', '与', '或', '就', '对', '关于', '一个', '这个', '那个', 'the', 'a', 'an', 'is', 'are', 'was', 'were'])
  const candidates = text.replace(/[^a-zA-Z一-鿿0-9]/g, ' ').split(/\s+/).filter(Boolean)
  const freq: Record<string, number> = {}
  candidates.forEach(w => {
    const lower = w.toLowerCase()
    if (!stopWords.has(lower) && lower.length > 1) freq[lower] = (freq[lower] || 0) + 1
  })
  return Object.entries(freq).sort((a, b) => b[1] - a[1]).slice(0, 5).map(([w]) => w)
}

export function MeetingNotes() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [attendees, setAttendees] = useState('')
  const [content, setContent] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  
  // User info from localStorage
  const userStr = localStorage.getItem('user')
  const user = userStr ? JSON.parse(userStr) : null
  const userId = user?.id?.toString()
  const username = user?.username || user?.name || '用户'
  
  // WebSocket for current meeting (if viewing a specific meeting)
  const [viewingMeetingId, setViewingMeetingId] = useState<number | null>(null)
  const {
    wsConnected,
    activeEditors,
    contentUpdate,
    emitContentChange,
  } = useMeetingWebSocket(
    viewingMeetingId?.toString(),
    userId,
    username
  )

  useEffect(() => {
    loadMeetings()
  }, [])
  
  // Auto-refresh when WebSocket signals changes (new comment or meeting update)
  useEffect(() => {
    if (contentUpdate) {
      loadMeetings()
    }
  }, [contentUpdate])

  const loadMeetings = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/meetings')
      const data = await res.json()
      if (data.success) setMeetings(data.meetings || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const filteredMeetings = useMemo(() => {
    let result = meetings
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(m =>
        m.title.toLowerCase().includes(q) ||
        m.content.toLowerCase().includes(q) ||
        m.attendees.toLowerCase().includes(q)
      )
    }
    if (dateFrom) {
      result = result.filter(m => m.date >= dateFrom)
    }
    if (dateTo) {
      result = result.filter(m => m.date <= dateTo)
    }
    return result
  }, [meetings, searchQuery, dateFrom, dateTo])

  const handleCreate = async () => {
    if (!title || !date) {
      alert('请填写会议主题和日期')
      return
    }
    try {
      const res = await fetch('/api/meetings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, date, attendees, content })
      })
      const data = await res.json()
      if (data.success) {
        setShowModal(false)
        setTitle('')
        setDate('')
        setAttendees('')
        setContent('')
        loadMeetings()
      }
    } catch (e) {
      alert('创建失败')
    }
  }

  const formatContent = (text: string) => {
    if (!text) return <p className="text-gray-500 italic">暂无内容</p>
    const lines = text.split('\n')
    const elements: JSX.Element[] = []
    let currentList: string[] = []
    let inList = false

    lines.forEach((line, index) => {
      const trimmed = line.trim()
      if (trimmed.startsWith('## ')) {
        if (inList && currentList.length > 0) {
          elements.push(<ul key={`ul-${index}`} className="list-disc list-inside mb-3 ml-4">{currentList.map((item, i) => <li key={i}>{item}</li>)}</ul>)
          currentList = []
          inList = false
        }
        elements.push(<h5 key={index} className="font-semibold text-gray-800 mt-4 mb-2 flex items-center gap-2"><Tag className="w-4 h-4 text-blue-500" />{trimmed.replace('## ', '')}</h5>)
      } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        inList = true
        currentList.push(trimmed.replace(/^[-*] /, ''))
      } else if (trimmed) {
        if (inList && currentList.length > 0) {
          elements.push(<ul key={`ul-${index}`} className="list-disc list-inside mb-3 ml-4">{currentList.map((item, i) => <li key={i}>{item}</li>)}</ul>)
          currentList = []
          inList = false
        }
        elements.push(<p key={index} className="text-gray-700 mb-2">{trimmed}</p>)
      }
    })

    if (inList && currentList.length > 0) {
      elements.push(<ul key="ul-final" className="list-disc list-inside mb-3 ml-4">{currentList.map((item, i) => <li key={i}>{item}</li>)}</ul>)
    }
    return <div className="mt-4">{elements}</div>
  }

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center bg-gray-50"><div className="animate-spin w-10 h-10 border-4 border-purple-500 border-t-transparent rounded-full"></div></div>
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2"><FileText className="w-7 h-7 text-purple-500" />会议纪要</h2>
            <p className="text-gray-500 mt-1">共 {meetings.length} 条记录</p>
          </div>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-5 py-2.5 bg-purple-500 text-white rounded-lg hover:bg-purple-600 shadow-sm">
            <Plus size={20} />新建会议
          </button>
        </div>

        <div className="flex flex-col sm:flex-row gap-3 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400 text-sm"
              placeholder="搜索会议标题、内容或参会人..."
            />
          </div>
          <input
            type="date"
            value={dateFrom}
            onChange={(e) => setDateFrom(e.target.value)}
            className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400 text-sm"
          />
          <input
            type="date"
            value={dateTo}
            onChange={(e) => setDateTo(e.target.value)}
            className="px-4 py-2.5 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-purple-400 text-sm"
          />
        </div>

        <div className="meeting-timeline">
          {filteredMeetings.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-xl border border-gray-100">
              <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-800 mb-2">没有找到匹配的记录</h3>
              <p className="text-gray-500 mb-6">尝试调整搜索条件或创建新会议</p>
            </div>
          ) : (
            filteredMeetings.map((meeting, index) => {
              const keywords = extractKeywords(meeting.content)
              return (
                <div key={meeting.id} className="timeline-item">
                  <div className="timeline-dot" style={index === filteredMeetings.length - 1 ? { background: '#22c55e' } : {}} />
                  <div className="meeting-card">
                    <h4 className="meeting-title">{meeting.title || '未命名会议'}</h4>
                    <div className="meeting-meta">
                      {meeting.date && <span className="flex items-center gap-1"><Calendar className="w-3.5 h-3.5" />{new Date(meeting.date).toLocaleDateString('zh-CN')}</span>}
                      {meeting.attendees && <span className="flex items-center gap-1"><Users className="w-3.5 h-3.5" />{meeting.attendees}</span>}
                    </div>
                    <div className="meeting-content">
                      {formatContent(meeting.content)}
                    </div>
                    {keywords.length > 0 && (
                      <div className="meeting-tags">
                        {keywords.map((kw, i) => (
                          <span key={i} className="meeting-tag">{kw}</span>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl w-full max-w-lg">
            <div className="p-6 border-b border-gray-100 flex items-center justify-between">
              <h3 className="text-lg font-bold">新建会议纪要</h3>
              <button onClick={() => setShowModal(false)} className="p-2 hover:bg-gray-100 rounded-lg"><X className="w-5 h-5" /></button>
            </div>
            <div className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">会议主题</label>
                <input type="text" value={title} onChange={(e) => setTitle(e.target.value)} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="输入会议主题" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">会议日期</label>
                <input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">参会人员</label>
                <input type="text" value={attendees} onChange={(e) => setAttendees(e.target.value)} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="张三、李四、王五" />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">会议内容</label>
                <textarea value={content} onChange={(e) => setContent(e.target.value)} rows={6} className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500" placeholder="输入会议内容，支持 Markdown 格式" />
              </div>
            </div>
            <div className="p-6 border-t border-gray-100 flex justify-end gap-3">
              <button onClick={() => setShowModal(false)} className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg">取消</button>
              <button onClick={handleCreate} className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600">创建</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default MeetingNotes
