import { useState, useEffect } from 'react'
import { RefreshCw, Mail, Trash2, Reply, Send, Users } from 'lucide-react'

export function Emails() {
  const [emails, setEmails] = useState<any[]>([])
  const [folders, setFolders] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [filter, setFilter] = useState('inbox')
  const [selectedEmail, setSelectedEmail] = useState<any>(null)
  const [showReplyModal, setShowReplyModal] = useState(false)
  const [replyContent, setReplyContent] = useState('')
  const [activeTab, setActiveTab] = useState('inbox')

  // 邮件API基础URL
  const EMAIL_API_URL = 'http://47.93.184.128:8089'

  useEffect(() => {
    loadFolders()
    loadEmails()
  }, [filter])

  // 加载文件夹
  const loadFolders = async () => {
    try {
      const res = await fetch(`${EMAIL_API_URL}/api/emails/folders`)
      const data = await res.json()
      if (data.success) {
        setFolders(data.folders || [])
      }
    } catch (e) {
      console.error('加载文件夹失败:', e)
    }
  }

  // 加载邮件
  const loadEmails = async () => {
    try {
      setLoading(true)
      const res = await fetch(`${EMAIL_API_URL}/api/emails?folder=${filter}`)
      const data = await res.json()
      if (data.success) {
        setEmails(data.emails || [])
      }
    } catch (e) {
      console.error('加载邮件失败:', e)
    } finally {
      setLoading(false)
    }
  }

  // 同步邮件
  const syncEmails = async () => {
    try {
      setSyncing(true)
      const res = await fetch(`${EMAIL_API_URL}/api/emails/sync`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: filter })
      })
      const data = await res.json()
      if (data.success) {
        alert(`同步完成！共 ${data.count} 封邮件`)
        loadEmails()
        loadFolders()
      }
    } catch (e) {
      console.error('同步邮件失败:', e)
      alert('同步失败，请稍后重试')
    } finally {
      setSyncing(false)
    }
  }

  // 标记已读
  const markAsRead = async (emailId: string) => {
    try {
      await fetch(`${EMAIL_API_URL}/api/emails/${emailId}/read`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ read: true })
      })
      loadEmails()
    } catch (e) {
      console.error(e)
    }
  }

  // 删除邮件
  const deleteEmail = async (emailId: string) => {
    if (!confirm('确定要删除这封邮件吗？')) return
    try {
      await fetch(`${EMAIL_API_URL}/api/emails/${emailId}`, {
        method: 'DELETE'
      })
      setSelectedEmail(null)
      loadEmails()
    } catch (e) {
      console.error(e)
    }
  }

  // 移动邮件
  const moveEmail = async (emailId: string, targetFolder: string) => {
    try {
      await fetch(`${EMAIL_API_URL}/api/emails/${emailId}/move`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ folder: targetFolder })
      })
      loadEmails()
      if (selectedEmail?.id === emailId) {
        setSelectedEmail(null)
      }
    } catch (e) {
      console.error(e)
    }
  }

  // 发送回复
  const sendReply = async () => {
    if (!replyContent.trim() || !selectedEmail) return
    try {
      await fetch(`${EMAIL_API_URL}/api/emails/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          to: selectedEmail.sender,
          subject: `Re: ${selectedEmail.subject}`,
          content: replyContent
        })
      })
      setReplyContent('')
      setShowReplyModal(false)
      alert('回复已发送')
    } catch (e) {
      console.error(e)
    }
  }

  // 格式化日期
  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <a href="/" className="p-2 bg-white rounded-lg shadow hover:shadow-md transition">
              <span className="text-gray-600">←</span>
            </a>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
              <Mail className="h-6 w-6 text-blue-600" />
              邮件管理
            </h1>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={syncEmails}
              disabled={syncing}
              className="flex items-center space-x-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition"
            >
              <RefreshCw className={`h-4 w-4 ${syncing ? 'animate-spin' : ''}`} />
              <span>{syncing ? '同步中...' : '同步邮件'}</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-12 gap-6">
          {/* 侧边栏 - 文件夹 */}
          <div className="col-span-3">
            <div className="bg-white rounded-xl shadow-sm border p-4">
              <h2 className="text-lg font-semibold text-gray-900 mb-4">文件夹</h2>
              <div className="space-y-2">
                {folders.map((folder: any) => (
                  <button
                    key={folder.id}
                    onClick={() => { setFilter(folder.id); setActiveTab(folder.id) }}
                    className={`w-full flex items-center justify-between p-3 rounded-lg text-left transition ${
                      activeTab === folder.id
                        ? 'bg-blue-50 text-blue-700 border-l-4 border-blue-600'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    <span className="font-medium">{folder.name}</span>
                    {folder.unread > 0 && (
                      <span className="bg-red-500 text-white text-xs px-2 py-1 rounded-full">
                        {folder.unread}
                      </span>
                    )}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* 邮件列表 */}
          <div className="col-span-4">
            <div className="bg-white rounded-xl shadow-sm border">
              <div className="p-4 border-b">
                <h2 className="text-lg font-semibold text-gray-900">
                  {folders.find((f: any) => f.id === filter)?.name || '收件箱'}
                  <span className="ml-2 text-sm text-gray-500">({emails.length})</span>
                </h2>
              </div>
              <div className="divide-y max-h-[calc(100vh-250px)] overflow-y-auto">
                {loading ? (
                  <div className="p-8 text-center text-gray-500">加载中...</div>
                ) : emails.length === 0 ? (
                  <div className="p-8 text-center text-gray-500">
                    <Mail className="h-12 w-12 mx-auto mb-3 text-gray-300" />
                    <p>暂无邮件</p>
                    <p className="text-sm mt-2">点击"同步邮件"获取最新邮件</p>
                  </div>
                ) : (
                  emails.map((email: any) => (
                    <div
                      key={email.id}
                      onClick={() => { setSelectedEmail(email); markAsRead(email.id) }}
                      className={`p-4 cursor-pointer hover:bg-gray-50 transition ${
                        selectedEmail?.id === email.id ? 'bg-blue-50 border-l-4 border-blue-600' : ''
                      } ${!email.read ? 'font-semibold bg-gray-50' : ''}`}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <p className={`text-sm truncate ${!email.read ? 'text-gray-900' : 'text-gray-600'}`}>
                            {email.sender_name || email.sender}
                          </p>
                          <p className="text-sm text-gray-800 truncate mt-1">{email.subject}</p>
                          <p className="text-xs text-gray-500 mt-1 truncate">{email.content?.substring(0, 50)}...</p>
                        </div>
                        <span className="text-xs text-gray-400 whitespace-nowrap ml-2">
                          {formatDate(email.date)}
                        </span>
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>

          {/* 邮件详情 */}
          <div className="col-span-5">
            {selectedEmail ? (
              <div className="bg-white rounded-xl shadow-sm border">
                <div className="p-4 border-b flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">{selectedEmail.subject}</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      来自: {selectedEmail.sender_name || selectedEmail.sender}
                    </p>
                    <p className="text-xs text-gray-400">{formatDate(selectedEmail.date)}</p>
                  </div>
                  <div className="flex space-x-2">
                    <button
                      onClick={() => setShowReplyModal(true)}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                      title="回复"
                    >
                      <Reply className="h-5 w-5" />
                    </button>
                    <button
                      onClick={() => deleteEmail(selectedEmail.id)}
                      className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                      title="删除"
                    >
                      <Trash2 className="h-5 w-5" />
                    </button>
                  </div>
                </div>
                <div className="p-4 max-h-[calc(100vh-350px)] overflow-y-auto">
                  <div className="prose max-w-none whitespace-pre-wrap">
                    {selectedEmail.content}
                  </div>
                  {selectedEmail.attachments && selectedEmail.attachments.length > 0 && (
                    <div className="mt-6 pt-4 border-t">
                      <h3 className="text-sm font-semibold text-gray-700 mb-3">附件</h3>
                      <div className="space-y-2">
                        {selectedEmail.attachments.map((att: any, idx: number) => (
                          <div key={idx} className="flex items-center p-2 bg-gray-50 rounded-lg">
                            <span className="text-sm text-gray-600">{att.name}</span>
                            <span className="text-xs text-gray-400 ml-2">({Math.round(att.size / 1024)} KB)</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            ) : (
              <div className="bg-white rounded-xl shadow-sm border p-8 text-center">
                <Mail className="h-16 w-16 mx-auto text-gray-300 mb-4" />
                <p className="text-gray-500">选择一封邮件查看详情</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 回复弹窗 */}
      {showReplyModal && selectedEmail && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl mx-4">
            <div className="p-4 border-b">
              <h3 className="text-lg font-semibold">回复: {selectedEmail.subject}</h3>
              <p className="text-sm text-gray-500">收件人: {selectedEmail.sender}</p>
            </div>
            <div className="p-4">
              <textarea
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                className="w-full h-48 p-3 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="输入回复内容..."
              />
            </div>
            <div className="p-4 border-t flex justify-end space-x-3">
              <button
                onClick={() => setShowReplyModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={sendReply}
                disabled={!replyContent.trim()}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 flex items-center gap-2"
              >
                <Send className="h-4 w-4" />
                发送
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}