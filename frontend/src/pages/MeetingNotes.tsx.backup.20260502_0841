import { useState, useEffect } from 'react'
import { Plus, Calendar, Users, FileText, Clock, Tag, X } from 'lucide-react'

interface Meeting {
  id: number
  title: string
  date: string
  attendees: string
  content: string
}

export function MeetingNotes() {
  const [meetings, setMeetings] = useState<Meeting[]>([])
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [title, setTitle] = useState('')
  const [date, setDate] = useState('')
  const [attendees, setAttendees] = useState('')
  const [content, setContent] = useState('')

  useEffect(() => {
    loadMeetings()
  }, [])

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
    return <div className="min-h-screen flex items-center justify-center bg-gray-50"><div className="animate-spin w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2"><FileText className="w-7 h-7 text-blue-500" />会议纪要</h2>
            <p className="text-gray-500 mt-1">共 {meetings.length} 条记录</p>
          </div>
          <button onClick={() => setShowModal(true)} className="flex items-center gap-2 px-5 py-2.5 bg-blue-500 text-white rounded-lg hover:bg-blue-600 shadow-sm">
            <Plus size={20} />新建会议
          </button>
        </div>

        <div className="bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-100 rounded-xl p-5 mb-6">
          <div className="flex gap-4 items-start">
            <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center flex-shrink-0"><Calendar className="w-5 h-5 text-blue-600" /></div>
            <div>
              <h4 className="font-semibold text-gray-800 mb-2">会议纪要说明</h4>
              <ul className="text-sm text-gray-600 space-y-1">
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-blue-400 rounded-full"></span>记录会议主题、参会人员、讨论内容</li>
                <li className="flex items-center gap-2"><span className="w-1.5 h-1.5 bg-blue-400 rounded-full"></span>明确行动项、负责人和截止日期</li>
              </ul>
            </div>
          </div>
        </div>

        <div className="space-y-4">
          {meetings.length === 0 ? (
            <div className="text-center py-16 bg-white rounded-xl border border-gray-100">
              <FileText className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <h3 className="text-lg font-medium text-gray-800 mb-2">还没有会议纪要</h3>
              <p className="text-gray-500 mb-6">记录你的第一次会议</p>
            </div>
          ) : (
            meetings.map((meeting) => (
              <div key={meeting.id} className="bg-white rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow">
                <div className="p-5 border-b border-gray-100 bg-gradient-to-r from-gray-50 to-white">
                  <h4 className="text-lg font-semibold text-gray-800">{meeting.title || '未命名会议'}</h4>
                  <div className="flex flex-wrap items-center gap-4 mt-2 text-sm text-gray-500">
                    {meeting.date && <span className="flex items-center gap-1"><Clock className="w-4 h-4" />{new Date(meeting.date).toLocaleDateString('zh-CN')}</span>}
                    {meeting.attendees && <span className="flex items-center gap-1"><Users className="w-4 h-4" />{meeting.attendees}</span>}
                  </div>
                </div>
                <div className="p-5">{formatContent(meeting.content)}</div>
              </div>
            ))
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
