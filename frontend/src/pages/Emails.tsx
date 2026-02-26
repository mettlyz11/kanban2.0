import { useState, useEffect } from 'react'

export function Emails() {
  const [emails, setEmails] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('inbox')
  const [selectedEmail, setSelectedEmail] = useState<any>(null)
  const [showReplyModal, setShowReplyModal] = useState(false)
  const [showContacts, setShowContacts] = useState(false)
  const [contacts, setContacts] = useState<any[]>([])
  const [replyContent, setReplyContent] = useState('')
  const [selectedIds, setSelectedIds] = useState<number[]>([])

  useEffect(() => {
    loadEmails()
    loadContacts()
  }, [filter])

  const loadEmails = async () => {
    try {
      const [emailsRes, statsRes] = await Promise.all([
        fetch('/api/emails'),
        fetch('/api/emails/stats')
      ])
      
      const emailsData = await emailsRes.json()
      const statsData = await statsRes.json()
      
      if (emailsData.success) {
        let filtered = emailsData.emails || []
        if (filter === 'important') {
          filtered = filtered.filter((e: any) => e.is_important)
        } else if (filter === 'sent') {
          filtered = filtered.filter((e: any) => e.folder === 'sent')
        } else {
          filtered = filtered.filter((e: any) => e.folder === 'inbox')
        }
        setEmails(filtered)
      }
      
      if (statsData.success) {
        setStats(statsData.stats)
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const loadContacts = async () => {
    try {
      const res = await fetch('/api/contacts')
      const data = await res.json()
      if (data.success) setContacts(data.contacts || [])
    } catch (e) {
      console.error(e)
    }
  }

  const markAsRead = async (emailId: number) => {
    try {
      await fetch(`/api/emails/${emailId}/read`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      })
      loadEmails()
    } catch (e) {
      console.error(e)
    }
  }

  const deleteEmail = async (emailId: number) => {
    if (!confirm('确定要删除这封邮件吗？')) return
    try {
      await fetch(`/api/emails/${emailId}`, {
        method: 'DELETE'
      })
      setSelectedEmail(null)
      loadEmails()
    } catch (e) {
      console.error(e)
    }
  }

  const sendReply = async () => {
    if (!replyContent.trim() || !selectedEmail) return
    try {
      await fetch('/api/emails/reply', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email_id: selectedEmail.id,
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

  const navigateEmail = (direction: 'prev' | 'next') => {
    if (!selectedEmail) return
    const currentIndex = emails.findIndex(e => e.id === selectedEmail.id)
    const newIndex = direction === 'prev' ? currentIndex - 1 : currentIndex + 1
    if (newIndex >= 0 && newIndex < emails.length) {
      setSelectedEmail(emails[newIndex])
      markAsRead(emails[newIndex].id)
    }
  }

  const toggleSelection = (id: number) => {
    setSelectedIds(prev => 
      prev.includes(id) ? prev.filter(i => i !== id) : [...prev, id]
    )
  }

  const markSelectedAsRead = async () => {
    for (const id of selectedIds) {
      await markAsRead(id)
    }
    setSelectedIds([])
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📧 邮件管理</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-secondary" onClick={() => setShowContacts(true)}>
            📇 通讯录
          </button>
          {selectedIds.length > 0 && (
            <button className="btn btn-primary" onClick={markSelectedAsRead}>
              标记已读 ({selectedIds.length})
            </button>
          )}
        </div>
      </div>

      {/* 统计 */}
      {stats && (
        <div className="stats-grid" style={{ marginBottom: '24px' }}>
          <div className="stat-card blue">
            <div className="stat-icon">📥</div>
            <div className="stat-info">
              <h3>{stats.total || 0}</h3>
              <p>总邮件</p>
            </div>
          </div>
          <div className="stat-card orange">
            <div className="stat-icon">📩</div>
            <div className="stat-info">
              <h3>{stats.unread || 0}</h3>
              <p>未读</p>
            </div>
          </div>
          <div className="stat-card red">
            <div className="stat-icon">⭐</div>
            <div className="stat-info">
              <h3>{stats.important || 0}</h3>
              <p>重要</p>
            </div>
          </div>
        </div>
      )}

      {/* 筛选标签 */}
      <div className="filter-bar">
        {[
          { key: 'inbox', label: '📥 收件箱' },
          { key: 'sent', label: '📤 已发送' },
          { key: 'important', label: '⭐ 重要' }
        ].map(item => (
          <button
            key={item.key}
            className={`filter-btn ${filter === item.key ? 'active' : ''}`}
            onClick={() => setFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* 邮件列表 */}
        <div style={{ flex: selectedEmail ? '0 0 40%' : '1' }}>
          <div className="card" style={{ padding: 0, maxHeight: '600px', overflow: 'auto' }}>
            {emails.length === 0 ? (
              <div className="empty-state">
                <div className="empty-state-icon">📧</div>
                <p>暂无邮件</p>
              </div>
            ) : (
              emails.map(email => (
                <div 
                  key={email.id}
                  onClick={() => { setSelectedEmail(email); markAsRead(email.id); }}
                  style={{
                    padding: '16px 20px',
                    borderBottom: '1px solid #e9ecef',
                    background: selectedEmail?.id === email.id ? '#e3f2fd' : (email.is_read ? 'white' : '#f0f7ff'),
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '12px'
                  }}
                >
                  <input 
                    type="checkbox"
                    checked={selectedIds.includes(email.id)}
                    onClick={e => e.stopPropagation()}
                    onChange={() => toggleSelection(email.id)}
                  />
                  {!email.is_read && <span style={{ width: '8px', height: '8px', background: '#667eea', borderRadius: '50%' }} />}
                  {email.is_important && <span>⭐</span>}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: email.is_read ? 'normal' : '600', marginBottom: '4px' }}>
                      {email.subject || '(无主题)'}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#666' }}>
                      {email.sender_name || email.sender}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#999' }}>
                    {email.received_at && new Date(email.received_at).toLocaleDateString('zh-CN')}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* 邮件详情 */}
        {selectedEmail && (
          <div style={{ flex: '1' }}>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '16px' }}>
                <div>
                  <h4>{selectedEmail.subject || '(无主题)'}</h4>
                  <div style={{ color: '#666', fontSize: '0.9rem', marginTop: '8px' }}>
                    <strong>发件人:</strong> {selectedEmail.sender_name || selectedEmail.sender} &lt;{selectedEmail.sender}&gt;
                  </div>
                  <div style={{ color: '#999', fontSize: '0.85rem', marginTop: '4px' }}>
                    {selectedEmail.received_at && new Date(selectedEmail.received_at).toLocaleString('zh-CN')}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn btn-secondary" onClick={() => navigateEmail('prev')}>← 上一封</button>
                  <button className="btn btn-secondary" onClick={() => navigateEmail('next')}>下一封 →</button>
                </div>
              </div>

              <div style={{ 
                padding: '20px', 
                background: '#f8f9fa', 
                borderRadius: '8px',
                minHeight: '200px',
                whiteSpace: 'pre-wrap',
                marginBottom: '16px'
              }}>
                {selectedEmail.body || selectedEmail.preview || '暂无内容'}
              </div>

              <div style={{ display: 'flex', gap: '8px' }}>
                <button className="btn btn-primary" onClick={() => setShowReplyModal(true)}>↩️ 回复</button>
                <button className="btn btn-danger" onClick={() => deleteEmail(selectedEmail.id)}>🗑️ 删除</button>
                <button className="btn btn-secondary" onClick={() => setSelectedEmail(null)}>关闭</button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 回复弹窗 */}
      {showReplyModal && selectedEmail && (
        <div className="modal-overlay" onClick={() => setShowReplyModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>↩️ 回复邮件</h3>
            <div style={{ marginBottom: '16px' }}>
              <strong>收件人:</strong> {selectedEmail.sender}
            </div>
            <textarea
              value={replyContent}
              onChange={e => setReplyContent(e.target.value)}
              placeholder="输入回复内容..."
              style={{ width: '100%', minHeight: '200px', padding: '12px', borderRadius: '8px', border: '1px solid #ddd' }}
            />
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowReplyModal(false)}>取消</button>
              <button className="btn btn-primary" onClick={sendReply} disabled={!replyContent.trim()}>发送</button>
            </div>
          </div>
        </div>
      )}

      {/* 通讯录弹窗 */}
      {showContacts && (
        <div className="modal-overlay" onClick={() => setShowContacts(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h3>📇 通讯录</h3>
            <div style={{ maxHeight: '400px', overflow: 'auto' }}>
              {contacts.length === 0 ? (
                <p style={{ textAlign: 'center', color: '#666' }}>暂无联系人</p>
              ) : (
                contacts.map((contact: any, i: number) => (
                  <div key={i} style={{ 
                    padding: '12px', 
                    borderBottom: '1px solid #e9ecef',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <div>
                      <div style={{ fontWeight: 600 }}>{contact.sender_name || contact.sender}</div>
                      <div style={{ fontSize: '0.85rem', color: '#666' }}>{contact.sender}</div>
                    </div>
                    <button className="btn btn-sm btn-outline-primary" onClick={() => { setShowContacts(false); alert(`发送邮件给: ${contact.sender}`); }}>
                      发邮件
                    </button>
                  </div>
                ))
              )}
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowContacts(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
