import { useState, useEffect } from 'react'
import { Plus, BookOpen, FileText, Search } from 'lucide-react'

export function ResearchNotes() {
  const [notes, setNotes] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')

  useEffect(() => {
    loadNotes()
  }, [])

  const loadNotes = async () => {
    try {
      const res = await fetch('/api/research')
      const data = await res.json()
      if (data.success) setNotes(data.notes || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleCreateNote = async () => {
    if (!title || !content) {
      alert('请填写标题和内容')
      return
    }
    
    try {
      const res = await fetch('/api/research', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title, content })
      })
      const data = await res.json()
      if (data.success) {
        alert('调研记录创建成功！')
        setShowAddModal(false)
        setTitle('')
        setContent('')
        loadNotes()
      }
    } catch (e) {
      console.error(e)
      alert('创建失败')
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📚 调研记录 (T018)</h2>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <Plus size={20} />
          新建调研
        </button>
      </div>

      {/* 使用说明卡片 */}
      <div className="card" style={{ marginBottom: '20px', background: '#fef3c7', border: '1px solid #fcd34d' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <BookOpen size={24} className="text-yellow-600" style={{ flexShrink: 0 }} />
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#92400e' }}>调研记录说明</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#78350f', lineHeight: '1.6' }}>
              <li>记录竞品分析、市场调研、技术调研等内容</li>
              <li>包含调研目标、方法、发现和结论</li>
              <li>支持添加相关文档和参考资料</li>
              <li>定期回顾调研结果，指导产品决策</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="card">
        {notes.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📝</div>
            <h3 style={{ margin: '16px 0 8px', color: '#374151' }}>还没有调研记录</h3>
            <p style={{ color: '#6b7280', marginBottom: '20px' }}>
              记录你的第一次调研，积累知识和洞察
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 auto' }}
            >
              <Plus size={20} />
              创建第一个调研
            </button>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {notes.map((note: any, i: number) => (
              <div key={i} style={{
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                borderLeft: '4px solid #667eea'
              }}>
                <h4>{note.title || '未命名调研'}</h4>
                <p style={{ color: '#666', marginTop: '8px' }}>{note.content || note.description || ''}</p>
                {note.created_at && (
                  <span style={{ color: '#999', fontSize: '0.85rem' }}>
                    {new Date(note.created_at).toLocaleDateString('zh-CN')}
                  </span>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* 创建调研弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <h3 className="text-lg font-bold mb-4">📚 创建调研记录</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <FileText size={16} className="inline mr-1" />
                调研标题
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="例如：竞品分析 - XXX 产品"
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Search size={16} className="inline mr-1" />
                调研内容
              </label>
              <textarea
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="调研目标、方法、发现、结论..."
                rows={8}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setTitle('')
                  setContent('')
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleCreateNote}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                保存调研
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default ResearchNotes
