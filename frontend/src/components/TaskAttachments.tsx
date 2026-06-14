import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { useState, useEffect } from 'react'
import { FileText, Download, Edit, Save, X, Eye, Plus, Upload, ChevronLeft, ChevronRight } from 'lucide-react'

interface Attachment {
  id: number
  entity_type: string
  entity_id: number
  filename: string
  url: string
  size: number
  file_type: string
  created_at: string
}

interface TaskAttachmentsProps {
  taskId?: number
  onTaskChange?: (taskId: number) => void
}

// Modal Component
const Modal = ({ isOpen, onClose, title, children, maxWidth = '900px' }: { 
  isOpen: boolean, 
  onClose: () => void, 
  title: string, 
  children: React.ReactNode,
  maxWidth?: string
}) => {
  if (!isOpen) return null
  
  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      backgroundColor: 'rgba(0, 0, 0, 0.5)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      zIndex: 1000,
      padding: 0
    }} onClick={onClose}>
      <div style={{
        backgroundColor: 'white',
        borderRadius: 0,
        width: '100vw',
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        boxShadow: 'none'
      }} onClick={e => e.stopPropagation()}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '16px 20px',
          borderBottom: '1px solid #e5e7eb',
          flexShrink: 0
        }}>
          <h4 style={{ margin: 0, fontSize: '1rem', fontWeight: 600 }}>{title}</h4>
          <button 
            onClick={onClose}
            style={{
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              padding: '4px',
              borderRadius: '4px',
              display: 'flex',
              alignItems: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>
        <div style={{
          padding: '20px',
          overflow: 'auto',
          flex: 1
        }}>
          {children}
        </div>
      </div>
    </div>
  )
}

export function TaskAttachments({ taskId: initialTaskId, onTaskChange }: TaskAttachmentsProps) {
  const [taskId, setTaskId] = useState<number>(initialTaskId || 0)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [editingFile, setEditingFile] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [currentViewIndex, setCurrentViewIndex] = useState<number>(-1)
  const [viewContent, setViewContent] = useState('')
  const [saving, setSaving] = useState(false)
  const [isEditMode, setIsEditMode] = useState(false)
  const [allTaskIds, setAllTaskIds] = useState<number[]>([])

  // Load all task IDs on mount for navigation
  useEffect(() => {
    const loadAllTasks = async () => {
      try {
        const res = await fetch("/api/tasks?page=1&limit=1000")
        const data = await res.json()
        if (data.success && data.tasks) {
          const ids = data.tasks.map((t: any) => t.id).sort((a: number, b: number) => b - a)
          setAllTaskIds(ids)
        }
      } catch (e) {
        console.error("Failed to load task list:", e)
      }
    }
    loadAllTasks()
  }, [])

  useEffect(() => {
    loadAttachments()
  }, [taskId])

  const loadAttachments = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/tasks/${taskId}/files`)
      const data = await response.json()
      if (data.success) {
        setAttachments(data.files || [])
      }
    } catch (error) {
      console.error('Failed to load attachments:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = (url: string, filename: string) => {
    const absUrl = url.startsWith('/') ? url : '/' + url
    window.open(absUrl, '_blank')
  }

  const loadFileContent = async (url: string) => {
    try {
      const absUrl = url.startsWith('/') ? url : '/' + url
      const response = await fetch(absUrl)
      return await response.text()
    } catch (error) {
      console.error('Failed to load file:', error)
      return ''
    }
  }

  const handleEdit = async (url: string, filename: string) => {
    const content = await loadFileContent(url)
    setEditContent(content)
    setEditingFile(filename)
    setIsEditMode(true)
  }

  const handleSave = async () => {
    if (!editingFile) return
    setSaving(true)
    try {
      const response = await fetch(`/api/tasks/${taskId}/files/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: editingFile, content: editContent })
      })
      if (response.ok) {
        alert('保存成功！')
        setEditingFile(null)
        setIsEditMode(false)
        setCurrentViewIndex(-1)
        loadAttachments()
      } else {
        alert('保存失败')
      }
    } catch (error) {
      console.error('Failed to save file:', error)
      alert('保存失败')
    } finally {
      setSaving(false)
    }
  }

  const handleView = async (url: string, filename: string) => {
    const index = attachments.findIndex(a => a.filename === filename)
    setCurrentViewIndex(index)
    const content = await loadFileContent(url)
    setViewContent(content)
    setIsEditMode(false)
  }

  const handlePrevDoc = async () => {
    if (currentViewIndex > 0) {
      const newIndex = currentViewIndex - 1
      const att = attachments[newIndex]
      const content = await loadFileContent(att.url)
      setCurrentViewIndex(newIndex)
      setViewContent(content)
      setEditingFile(att.filename)
      setEditContent(content)
    }
  }

  const handleNextDoc = async () => {
    if (currentViewIndex < attachments.length - 1) {
      const newIndex = currentViewIndex + 1
      const att = attachments[newIndex]
      const content = await loadFileContent(att.url)
      setCurrentViewIndex(newIndex)
      setViewContent(content)
      setEditingFile(att.filename)
      setEditContent(content)
    }
  }

  const handlePrevTask = () => {
    const currentIndex = allTaskIds.indexOf(taskId)
    if (currentIndex >= 0 && currentIndex < allTaskIds.length - 1) {
      const nextId = allTaskIds[currentIndex + 1]
      setTaskId(nextId)
      if (onTaskChange) onTaskChange(nextId)
      setCurrentViewIndex(-1)
      setIsEditMode(false)
    }
  }

  const handleNextTask = () => {
    const currentIndex = allTaskIds.indexOf(taskId)
    if (currentIndex > 0) {
      const prevId = allTaskIds[currentIndex - 1]
      setTaskId(prevId)
      if (onTaskChange) onTaskChange(prevId)
      setCurrentViewIndex(-1)
      setIsEditMode(false)
    }
  }

  const switchToEditMode = () => {
    if (currentViewIndex >= 0) {
      const att = attachments[currentViewIndex]
      setEditingFile(att.filename)
      setEditContent(viewContent)
      setIsEditMode(true)
    }
  }

  const switchToViewMode = () => {
    setViewContent(editContent)
    setIsEditMode(false)
  }

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`/api/tasks/${taskId}/files/upload`, {
        method: 'POST',
        body: formData
      })
      const data = await response.json()
      if (data.success) {
        loadAttachments()
      } else {
        alert(data.error || '上传失败')
      }
    } catch (error) {
      console.error('Failed to upload file:', error)
      alert('上传失败')
    } finally {
      setUploading(false)
      event.target.value = ''
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const isEditable = (fileType: string) => {
    return ['md', 'txt', 'js', 'ts', 'tsx', 'json', 'yaml', 'yml', 'py', 'java'].includes(fileType)
  }

  const isMarkdownFile = (filename: string) => {
    const ext = filename.split('.').pop()?.toLowerCase()
    return ['md', 'markdown', 'mdx'].includes(ext || '')
  }

  const currentFileName = currentViewIndex >= 0 && attachments[currentViewIndex] 
    ? attachments[currentViewIndex].filename 
    : ''

  const hasMultipleDocs = attachments.length > 1
  const hasPrevDoc = currentViewIndex > 0
  const hasNextDoc = currentViewIndex >= 0 && currentViewIndex < attachments.length - 1
  const currentFileIsEditable = currentViewIndex >= 0 && attachments[currentViewIndex] 
    ? isEditable(attachments[currentViewIndex].file_type)
    : false

  return (
    <div className="task-attachments">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
        <h4 style={{ margin: 0 }}>附件文档</h4>
        <label className="upload-btn" style={{ 
          display: 'inline-flex', 
          alignItems: 'center', 
          gap: '6px',
          padding: '6px 12px',
          background: '#667eea',
          color: 'white',
          borderRadius: '4px',
          cursor: 'pointer',
          fontSize: '0.85rem',
          border: 'none'
        }}>
          <Plus size={14} />
          {uploading ? '上传中...' : '上传附件'}
          <input
            type="file"
            onChange={handleUpload}
            disabled={uploading}
            style={{ display: 'none' }}
          />
        </label>
      </div>
      {loading ? <div className="loading">加载中...</div> :
       attachments.length === 0 ? <div className="empty-state">暂无附件</div> :
       <div className="attachments-list">
         {attachments.map((att) => (
           <div key={att.id} className="attachment-item">
             <span className="file-icon"><FileText size={16} /></span>
             <div className="file-info">
               <div className="file-name">{att.filename}</div>
               <div className="file-meta">{formatFileSize(att.size)} · {new Date(att.created_at).toLocaleDateString()}</div>
             </div>
             <div className="file-actions">
               <button onClick={() => handleView(att.url, att.filename)} title="查看" className="action-btn view"><Eye size={14} /></button>
               {isEditable(att.file_type) && <button onClick={() => handleEdit(att.url, att.filename)} title="编辑" className="action-btn edit"><Edit size={14} /></button>}
               <button onClick={() => handleDownload(att.url, att.filename)} title="下载" className="action-btn download"><Download size={14} /></button>
             </div>
           </div>
         ))}
       </div>
      }

      {/* View Modal */}
      <Modal
        isOpen={currentViewIndex >= 0 && !isEditMode}
        onClose={() => setCurrentViewIndex(-1)}
        title={currentFileName}
        maxWidth="900px"
      >
        {/* Combined Navigation Row */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          gap: '12px',
          marginBottom: '16px',
          padding: '12px',
          background: '#f8f9fa',
          borderRadius: '6px'
        }}>
          {/* Task Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button 
              onClick={handlePrevTask}
              disabled={taskId <= 1}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: taskId <= 1 ? '#f3f4f6' : 'white',
                cursor: taskId <= 1 ? 'not-allowed' : 'pointer',
                color: taskId <= 1 ? '#999' : '#333'
              }}
            >
              <ChevronLeft size={14} />
              上一任务 (#{taskId - 1})
            </button>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#667eea', minWidth: '100px', textAlign: 'center' }}>
              当前任务: #{taskId}
            </span>
            <button 
              onClick={handleNextTask}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: 'white',
                cursor: 'pointer'
              }}
            >
              下一任务 (#{taskId + 1})
              <ChevronRight size={14} />
            </button>
          </div>

          {/* Document Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button 
              onClick={handlePrevDoc}
              disabled={!hasPrevDoc}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: !hasPrevDoc ? '#f3f4f6' : 'white',
                cursor: !hasPrevDoc ? 'not-allowed' : 'pointer',
                color: !hasPrevDoc ? '#999' : '#333'
              }}
            >
              <ChevronLeft size={14} />
              上一文档
            </button>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#667eea', minWidth: '60px', textAlign: 'center' }}>
              {currentViewIndex + 1} / {attachments.length}
            </span>
            <button 
              onClick={handleNextDoc}
              disabled={!hasNextDoc}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: !hasNextDoc ? '#f3f4f6' : 'white',
                cursor: !hasNextDoc ? 'not-allowed' : 'pointer',
                color: !hasNextDoc ? '#999' : '#333'
              }}
            >
              下一文档
              <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* Content */}
        {isMarkdownFile(currentFileName) ? (
          <div className="markdown-body" style={{ 
            lineHeight: '1.8', 
            fontSize: '0.9rem',
            flex: 1,
            overflow: 'auto',
            padding: '24px 32px'
          }}>
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                h1: ({children}) => <h1 style={{fontSize: '1.5rem', fontWeight: 700, margin: '1.2em 0 0.6em'}}>{children}</h1>,
                h2: ({children}) => <h2 style={{fontSize: '1.25rem', fontWeight: 600, margin: '1em 0 0.5em'}}>{children}</h2>,
                h3: ({children}) => <h3 style={{fontSize: '1.1rem', fontWeight: 600, margin: '0.8em 0 0.4em'}}>{children}</h3>,
                h4: ({children}) => <h4 style={{fontSize: '1rem', fontWeight: 600, margin: '0.6em 0 0.3em'}}>{children}</h4>,
                h5: ({children}) => <h5 style={{fontSize: '0.95rem', fontWeight: 600, margin: '0.5em 0 0.3em'}}>{children}</h5>,
                h6: ({children}) => <h6 style={{fontSize: '0.9rem', fontWeight: 600, margin: '0.5em 0 0.2em'}}>{children}</h6>,
                p: ({children}) => <p style={{fontSize: '0.9rem', margin: '0.6em 0', lineHeight: '1.8'}}>{children}</p>,
                li: ({children}) => <li style={{fontSize: '0.9rem', lineHeight: '1.7'}}>{children}</li>,
                code: ({children}) => <code style={{fontSize: '0.85rem', background: '#f3f4f6', padding: '2px 6px', borderRadius: '4px'}}>{children}</code>,
                table: ({children}) => <table style={{fontSize: '0.85rem', borderCollapse: 'collapse', width: '100%', margin: '1em 0'}}>{children}</table>,
              }}
            >{viewContent}</ReactMarkdown>
          </div>
        ) : (
          <pre style={{ 
            padding: '16px', 
            overflow: 'auto', 
            maxHeight: '60vh', 
            fontSize: '0.85rem', 
            background: '#f5f5f5',
            borderRadius: '4px',
            margin: 0,
            whiteSpace: 'pre-wrap',
            wordWrap: 'break-word'
          }}>{viewContent}</pre>
        )}

        {/* Switch to Edit Mode */}
        {currentFileIsEditable && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '16px' }}>
            <button 
              onClick={switchToEditMode}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '6px',
                padding: '8px 16px',
                border: 'none',
                borderRadius: '4px',
                background: '#667eea',
                color: 'white',
                cursor: 'pointer',
                fontSize: '0.9rem'
              }}
            >
              <Edit size={14} />
              编辑文档
            </button>
          </div>
        )}
      </Modal>

      {/* Edit Modal */}
      <Modal
        isOpen={isEditMode}
        onClose={() => { setEditingFile(null); setIsEditMode(false); }}
        title={editingFile || ''}
        maxWidth="900px"
      >
        {/* Combined Navigation Row */}
        <div style={{ 
          display: 'flex', 
          justifyContent: 'space-between', 
          alignItems: 'center', 
          gap: '12px',
          marginBottom: '16px',
          padding: '12px',
          background: '#f8f9fa',
          borderRadius: '6px'
        }}>
          {/* Task Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button 
              onClick={handlePrevTask}
              disabled={taskId <= 1}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: taskId <= 1 ? '#f3f4f6' : 'white',
                cursor: taskId <= 1 ? 'not-allowed' : 'pointer',
                color: taskId <= 1 ? '#999' : '#333'
              }}
            >
              <ChevronLeft size={14} />
              上一任务 (#{taskId - 1})
            </button>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#667eea', minWidth: '100px', textAlign: 'center' }}>
              当前任务: #{taskId}
            </span>
            <button 
              onClick={handleNextTask}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: 'white',
                cursor: 'pointer'
              }}
            >
              下一任务 (#{taskId + 1})
              <ChevronRight size={14} />
            </button>
          </div>

          {/* Document Navigation */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button 
              onClick={handlePrevDoc}
              disabled={!hasPrevDoc}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: !hasPrevDoc ? '#f3f4f6' : 'white',
                cursor: !hasPrevDoc ? 'not-allowed' : 'pointer',
                color: !hasPrevDoc ? '#999' : '#333'
              }}
            >
              <ChevronLeft size={14} />
              上一文档
            </button>
            <span style={{ fontSize: '0.85rem', fontWeight: 600, color: '#667eea', minWidth: '60px', textAlign: 'center' }}>
              {currentViewIndex + 1} / {attachments.length}
            </span>
            <button 
              onClick={handleNextDoc}
              disabled={!hasNextDoc}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '4px',
                padding: '6px 12px',
                fontSize: '0.8rem',
                borderRadius: '4px',
                border: '1px solid #d1d5db',
                background: !hasNextDoc ? '#f3f4f6' : 'white',
                cursor: !hasNextDoc ? 'not-allowed' : 'pointer',
                color: !hasNextDoc ? '#999' : '#333'
              }}
            >
              下一文档
              <ChevronRight size={14} />
            </button>
          </div>
        </div>

        {/* Editor */}
        <textarea 
          value={editContent} 
          onChange={(e) => setEditContent(e.target.value)} 
          rows={20}
          style={{
            width: '100%',
            padding: '12px',
            border: '1px solid #d1d5db',
            borderRadius: '4px',
            fontSize: '0.9rem',
            fontFamily: 'monospace',
            resize: 'vertical',
            minHeight: '350px',
            marginBottom: '16px'
          }}
        />

        {/* Actions */}
        <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
          <button 
            onClick={switchToViewMode}
            style={{
              padding: '8px 16px',
              border: '1px solid #d1d5db',
              borderRadius: '4px',
              background: 'white',
              cursor: 'pointer',
              fontSize: '0.9rem'
            }}
          >
            返回查看
          </button>
          <button 
            onClick={handleSave}
            disabled={saving}
            style={{
              padding: '8px 16px',
              border: 'none',
              borderRadius: '4px',
              background: '#667eea',
              color: 'white',
              cursor: saving ? 'not-allowed' : 'pointer',
              fontSize: '0.9rem',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              opacity: saving ? 0.7 : 1
            }}
          >
            <Save size={14} />
            {saving ? '保存中...' : '保存'}
          </button>
        </div>
      </Modal>
    </div>
  )
}
