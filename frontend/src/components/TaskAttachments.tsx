import { useState, useEffect } from 'react'
import { FileText, Download, Edit, Save, X, Eye, Plus, Upload } from 'lucide-react'

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
  taskId: number
}

export function TaskAttachments({ taskId }: TaskAttachmentsProps) {
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [editingFile, setEditingFile] = useState<string | null>(null)
  const [editContent, setEditContent] = useState('')
  const [viewingFile, setViewingFile] = useState<string | null>(null)
  const [viewContent, setViewContent] = useState('')

  useEffect(() => {
    loadAttachments()
  }, [taskId])

  const loadAttachments = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/tasks/${taskId}/attachments`)
      const data = await response.json()
      if (data.success) {
        setAttachments(data.attachments || [])
      }
    } catch (error) {
      console.error('Failed to load attachments:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleDownload = (url: string, filename: string) => {
    window.open(url, '_blank')
  }

  const handleEdit = async (url: string, filename: string) => {
    try {
      const response = await fetch(url)
      const content = await response.text()
      setEditContent(content)
      setEditingFile(filename)
    } catch (error) {
      console.error('Failed to load file for editing:', error)
      alert('无法加载文件进行编辑')
    }
  }

  const handleSave = async () => {
    if (!editingFile) return
    try {
      const response = await fetch(`/api/tasks/${taskId}/attachments/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ filename: editingFile, content: editContent })
      })
      if (response.ok) {
        alert('保存成功！')
        setEditingFile(null)
        loadAttachments()
      } else {
        alert('保存失败')
      }
    } catch (error) {
      console.error('Failed to save file:', error)
      alert('保存失败')
    }
  }

  const handleView = async (url: string, filename: string) => {
    try {
      const response = await fetch(url)
      const content = await response.text()
      setViewContent(content)
      setViewingFile(filename)
    } catch (error) {
      console.error('Failed to load file:', error)
      alert('无法加载文件')
    }
  }

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`/api/tasks/${taskId}/attachments/upload`, {
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
      // 清除input值允许重复上传同一个文件名
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

  if (editingFile) {
    return (
      <div className="task-attachments-editor">
        <div className="editor-header">
          <h4>编辑: {editingFile}</h4>
          <div className="editor-actions">
            <button onClick={handleSave} className="save-btn"><Save size={14} /> 保存</button>
            <button onClick={() => setEditingFile(null)} className="cancel-btn"><X size={14} /> 取消</button>
          </div>
        </div>
        <textarea className="editor-textarea" value={editContent} onChange={(e) => setEditContent(e.target.value)} rows={30} />
      </div>
    )
  }

  if (viewingFile) {
    return (
      <div className="task-attachments-viewer">
        <div className="viewer-header">
          <h4>查看: {viewingFile}</h4>
          <button onClick={() => setViewingFile(null)} className="close-btn"><X size={14} /> 关闭</button>
        </div>
        <pre className="viewer-content">{viewContent}</pre>
      </div>
    )
  }

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
    </div>
  )
}
