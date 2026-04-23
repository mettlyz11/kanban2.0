import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { User, FileText, Plus, X, Edit2, Trash2, Star, Save, ChevronLeft, Calendar, Upload, Link as LinkIcon } from 'lucide-react'
import MdEditor from 'react-markdown-editor-lite'
import 'react-markdown-editor-lite/lib/index.css'
import MarkdownIt from 'markdown-it'

const mdParser = new MarkdownIt()

interface PersonInfo {
  id: number
  name: string
  email: string
  department: string
  phone: string
  company: string
  is_favorite: boolean
  created_at: string
  tabs?: PersonTab[]
}

interface PersonTab {
  id: number
  name: string
  type: string
  items: TabItem[]
}

interface TabItem {
  id: number
  title: string
  content: string
  item_date: string | null
  attachments?: Attachment[]
}

interface Attachment {
  id: number
  filename: string
  url: string
  size: number
  type: string
}

export function PersonalInfo() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [person, setPerson] = useState<PersonInfo | null>(null)
  const [tabs, setTabs] = useState<PersonTab[]>([])
  const [activeTabId, setActiveTabId] = useState<number | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeFilter, setActiveFilter] = useState<'favorite' | 'other'>('favorite')
  const [showAddTab, setShowAddTab] = useState(false)
  const [newTabName, setNewTabName] = useState('')
  const [editingItem, setEditingItem] = useState<TabItem | null>(null)
  const [showEditModal, setShowEditModal] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editContent, setEditContent] = useState('')
  const [editDate, setEditDate] = useState('')
  const [editAttachments, setEditAttachments] = useState<Attachment[]>([])
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (id) {
      setLoading(true)
      fetchPersonDetail(parseInt(id)).finally(() => {
        setLoading(false)
      })
    } else {
      setLoading(false)
    }
  }, [id])

  const fetchPersonDetail = async (personId: number) => {
    try {
      const res = await fetch(`/api/personal-info/people/${personId}`)
      const data = await res.json()
      if (data.success) { 
        setPerson(data.person); 
        fetchPersonTabs(personId);
      }
    } catch (e) {
      console.error('获取人员详情失败:', e)
    }
  }

  const fetchPersonTabs = async (personId: number) => {
    try {
      const res = await fetch(`/api/persons/${personId}/tabs`)
      const data = await res.json()
      if (data.success) {
        setTabs(data.tabs)
        if (data.tabs.length > 0) setActiveTabId(data.tabs[0].id)
      }
    } catch (e) {
      console.error('获取标签页失败:', e)
    } finally {
      setLoading(false)
    }
  }

  const toggleFavorite = async () => {
    if (!person) return
    try {
      await fetch(`/api/persons/${person.id}/favorite`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ is_favorite: !person.is_favorite })
      })
      setPerson({ ...person, is_favorite: !person.is_favorite })
    } catch (e) {
      console.error('切换收藏失败:', e)
    }
  }

  const createTab = async () => {
    if (!newTabName.trim() || !person) return
    try {
      await fetch(`/api/persons/${person.id}/tabs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newTabName, type: 'custom' })
      })
      setNewTabName('')
      setShowAddTab(false)
      fetchPersonTabs(person.id)
    } catch (e) {
      console.error('创建标签页失败:', e)
    }
  }

  const deleteTab = async (tabId: number) => {
    if (!person || !confirm('确定要删除这个标签页吗？')) return
    try {
      await fetch(`/api/persons/${person.id}/tabs/${tabId}`, { method: 'DELETE' })
      fetchPersonTabs(person.id)
      if (activeTabId === tabId) setActiveTabId(null)
    } catch (e) {
      console.error('删除标签页失败:', e)
    }
  }

  const createItem = async (tabId: number) => {
    if (!person) return
    try {
      await fetch(`/api/persons/${person.id}/tabs/${tabId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: '新项目', content: '', item_date: new Date().toISOString().split('T')[0] })
      })
      fetchPersonTabs(person.id)
    } catch (e) {
      console.error('创建项目失败:', e)
    }
  }

  const openEditModal = (item: TabItem) => {
    setEditingItem(item)
    setEditTitle(item.title)
    setEditContent(item.content || '')
    setEditDate(item.item_date || '')
    setEditAttachments(item.attachments || [])
    setShowEditModal(true)
  }

  const saveItem = async () => {
    if (!person || !activeTabId || !editingItem) return
    try {
      await fetch(`/api/persons/${person.id}/tabs/${activeTabId}/items/${editingItem.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: editTitle, content: editContent, item_date: editDate, attachments: editAttachments })
      })
      setShowEditModal(false)
      fetchPersonTabs(person.id)
    } catch (e) {
      console.error('保存项目失败:', e)
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !person) return
    
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('entity_type', 'person')
      formData.append('entity_id', person.id.toString())
      
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      })
      const data = await res.json()
      if (data.success) {
        setEditAttachments([...editAttachments, {
          id: data.attachment_id,
          filename: data.filename,
          url: data.url,
          size: data.size,
          type: data.type
        }])
      }
    } catch (e) {
      console.error('上传失败:', e)
    } finally {
      setUploading(false)
    }
  }

  const removeAttachment = (index: number) => {
    setEditAttachments(editAttachments.filter((_, i) => i !== index))
  }

  const deleteItem = async (tabId: number, itemId: number) => {
    if (!person || !confirm('确定要删除这个项目吗？')) return
    try {
      await fetch(`/api/persons/${person.id}/tabs/${tabId}/items/${itemId}`, { method: 'DELETE' })
      fetchPersonTabs(person.id)
    } catch (e) {
      console.error('删除项目失败:', e)
    }
  }

  if (loading) return <div className="p-8 text-center">加载中...</div>
  if (!person) return <div className="p-8 text-center">未找到人员信息</div>

  const activeTab = tabs.find(t => t.id === activeTabId)

  return (
    <div className="max-w-6xl mx-auto p-6">
      {/* 头部 */}
      <div className="bg-[#f5f5f7] rounded-xl shadow p-6 mb-6">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-4">
            <div className="w-16 h-16 bg-blue-100 rounded-full flex items-center justify-center text-2xl font-bold text-[#0071e3]">
              {person.name.charAt(0)}
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold">{person.name}</h1>
                <button onClick={toggleFavorite} className="p-1 hover:bg-white rounded">
                  <Star className={`w-6 h-6 ${person.is_favorite ? 'fill-yellow-400 text-yellow-400' : 'text-gray-300'}`} />
                </button>
              </div>
              <p className="text-[rgba(0,0,0,0.8)]">{person.department}</p>
              <p className="text-sm text-[rgba(0,0,0,0.48)]">{person.email} {person.phone && `· ${person.phone}`}</p>
            </div>
          </div>
          <button onClick={() => navigate("/personal")} className="flex items-center gap-1 px-4 py-2 text-[rgba(0,0,0,0.8)] hover:bg-white rounded">
            <ChevronLeft className="w-5 h-5" /> 返回
          </button>
        </div>
      </div>

      {/* 常用/其他切换 */}
      <div className="bg-[#f5f5f7] rounded-xl shadow mb-6">
        <div className="flex border-b">
          <button onClick={() => setActiveFilter('favorite')} className={`flex-1 px-6 py-3 font-medium ${activeFilter === 'favorite' ? 'text-[#0071e3] border-b-2 border-blue-600 bg-blue-50' : 'text-[rgba(0,0,0,0.48)]'}`}>
            <Star className="w-4 h-4 inline mr-2" /> 常用
          </button>
          <button onClick={() => setActiveFilter('other')} className={`flex-1 px-6 py-3 font-medium ${activeFilter === 'other' ? 'text-[#0071e3] border-b-2 border-blue-600 bg-blue-50' : 'text-[rgba(0,0,0,0.48)]'}`}>
            <User className="w-4 h-4 inline mr-2" /> 其他
          </button>
        </div>
      </div>

      {/* 标签页 */}
      <div className="bg-[#f5f5f7] rounded-xl shadow mb-6">
        <div className="flex items-center gap-2 p-4 border-b overflow-x-auto">
          {tabs.map(tab => (
            <button key={tab.id} onClick={() => setActiveTabId(tab.id)} className={`flex items-center gap-2 px-4 py-2 rounded-lg ${activeTabId === tab.id ? 'bg-blue-100 text-blue-700' : 'text-[rgba(0,0,0,0.8)] hover:bg-white'}`}>
              <FileText className="w-4 h-4" /> {tab.name}
              <button onClick={(e) => { e.stopPropagation(); deleteTab(tab.id); }} className="ml-1 text-[rgba(0,0,0,0.48)] hover:text-red-500"><X className="w-3 h-3" /></button>
            </button>
          ))}
          <button onClick={() => setShowAddTab(true)} className="flex items-center gap-1 px-4 py-2 text-[#0071e3] hover:bg-blue-50 rounded-lg">
              <Plus className="w-4 h-4" /> 添加标签
            </button>
        </div>

        <div className="p-4">
          {activeTab ? (
            <div>
              <div className="flex justify-between items-center mb-4">
                <h3 className="text-lg font-semibold">{activeTab.name}</h3>
                <button onClick={() => createItem(activeTab.id)} className="flex items-center gap-1 px-4 py-2 bg-[#0071e3] text-white rounded-lg hover:bg-[#0077ed]">
                  <Plus className="w-4 h-4" /> 添加项目
                </button>
              </div>
              
              <div className="space-y-4">
                {activeTab.items?.map(item => (
                  <div key={item.id} className="border rounded-lg p-4 hover:shadow-[0_4px_16px_rgba(0,0,0,0.12)]">
                    <div className="flex justify-between items-start mb-2">
                      <h4 className="font-semibold text-lg">{item.title}</h4>
                      <div className="flex gap-2">
                        <button onClick={() => openEditModal(item)} className="p-1 text-[rgba(0,0,0,0.48)] hover:text-[#0071e3]"><Edit2 className="w-4 h-4" /></button>
                        <button onClick={() => deleteItem(activeTab.id, item.id)} className="p-1 text-[rgba(0,0,0,0.48)] hover:text-[#ff3b30]"><Trash2 className="w-4 h-4" /></button>
                      </div>
                    </div>
                    {item.item_date && <div className="flex items-center gap-1 text-sm text-[rgba(0,0,0,0.48)] mb-2"><Calendar className="w-4 h-4" /> {item.item_date}</div>}
                    {item.content && (
                      <div 
                        className="prose prose-sm max-w-none text-[rgba(0,0,0,0.8)] mt-2"
                        dangerouslySetInnerHTML={{ __html: mdParser.render(item.content) }}
                      />
                    )}
                    {item.attachments && item.attachments.length > 0 && (
                      <div className="mt-3 flex flex-wrap gap-2">
                        {item.attachments.map((att, idx) => (
                          <a
                            key={idx}
                            href={att.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="flex items-center gap-1 px-3 py-1 bg-white rounded-full text-sm text-[rgba(0,0,0,0.8)] hover:bg-gray-200"
                          >
                            <LinkIcon className="w-3 h-3" />
                            {att.filename}
                          </a>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          ) : <div className="text-center text-[rgba(0,0,0,0.48)] py-12">请选择或创建一个标签页</div>}
        </div>
      </div>

      {/* 添加标签对话框 */}
      {showAddTab && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-[#f5f5f7] rounded-xl p-6 w-96">
            <h3 className="text-lg font-semibold mb-4">添加新标签</h3>
            <input type="text" value={newTabName} onChange={(e) => setNewTabName(e.target.value)} placeholder="标签名称" className="w-full px-4 py-2 border rounded-lg mb-4" />
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowAddTab(false)} className="px-4 py-2 text-[rgba(0,0,0,0.8)] hover:bg-white rounded-lg">取消</button>
              <button onClick={createTab} className="px-4 py-2 bg-[#0071e3] text-white rounded-lg hover:bg-[#0077ed]">创建</button>
            </div>
          </div>
        </div>
      )}

      {/* 编辑对话框 */}
      {showEditModal && (
        <div className="absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-[#f5f5f7] rounded-xl p-6 mx-auto w-[95vw] max-w-4xl max-h-[90vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">编辑项目</h3>
            <input type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} placeholder="标题" className="w-full px-4 py-2 border rounded-lg mb-4" />
            <input type="date" value={editDate} onChange={(e) => setEditDate(e.target.value)} className="w-full px-4 py-2 border rounded-lg mb-4" />
            <div className="mb-4 border rounded-lg">
              <MdEditor
                value={editContent}
                style={{ height: '300px' }}
                renderHTML={(text) => mdParser.render(text)}
                onChange={({ text }) => setEditContent(text)}
              />
            </div>
            
            {/* 附件上传 */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-[rgba(0,0,0,0.8)] mb-2">附件</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {editAttachments.map((att, idx) => (
                  <div key={idx} className="flex items-center gap-1 px-3 py-1 bg-white rounded-full text-sm">
                    <LinkIcon className="w-3 h-3" />
                    {att.filename}
                    <button onClick={() => removeAttachment(idx)} className="ml-1 text-[rgba(0,0,0,0.48)] hover:text-red-500">
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
              <label className="flex items-center gap-2 px-4 py-2 border border-dashed border-[rgba(0,0,0,0.1)] rounded-lg cursor-pointer hover:bg-[#f5f5f7]">
                <Upload className="w-4 h-4" />
                <span>{uploading ? '上传中...' : '上传附件'}</span>
                <input type="file" onChange={handleFileUpload} disabled={uploading} className="hidden" />
              </label>
            </div>
            <div className="flex justify-end gap-2">
              <button onClick={() => setShowEditModal(false)} className="px-4 py-2 text-[rgba(0,0,0,0.8)] hover:bg-white rounded-lg">取消</button>
              <button onClick={saveItem} className="flex items-center gap-1 px-4 py-2 bg-[#0071e3] text-white rounded-lg hover:bg-[#0077ed]"><Save className="w-4 h-4" /> 保存</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
export default PersonalInfo;
