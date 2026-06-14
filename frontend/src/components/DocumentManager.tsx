import { useState, useEffect, useRef } from 'react'
import { api } from '../utils/api'
import { FileUp, Download, Trash2, FileText, X } from 'lucide-react'

interface Document {
  id: number
  file_name: string
  original_name: string
  file_size: number
  mime_type: string
  description: string
  uploaded_by: string
  uploaded_at: string
}

interface DocumentManagerProps {
  projectId: number
}

export function DocumentManager({ projectId }: DocumentManagerProps) {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<{[key: string]: number}>({})
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    loadDocuments()
  }, [projectId])

  const loadDocuments = async () => {
    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${projectId}/document`)
      const data = await response.json()
      if (data.success) {
        setDocuments(data.documents || [])
      }
    } catch (error) {
      console.error('Failed to load documents:', error)
    } finally {
      setLoading(false)
    }
  }

  const handleFileSelect = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = event.target.files
    if (!files || files.length === 0) return

    for (const file of files) {
      await uploadFile(file)
    }
    
    // 重置input
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  const uploadFile = async (file: File) => {
    setUploading(true)
    setUploadProgress(prev => ({ ...prev, [file.name]: 0 }))

    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`/api/projects/${projectId}/document`, {
        method: 'POST',
        body: formData
      })

      setUploadProgress(prev => ({ ...prev, [file.name]: 100 }))

      if (response.ok) {
        await loadDocuments()
        setTimeout(() => {
          setUploadProgress(prev => {
            const newProgress = { ...prev }
            delete newProgress[file.name]
            return newProgress
          })
        }, 1000)
      }
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId: number) => {
    if (!confirm('确定要删除这个文档吗？')) return

    try {
      const response = await fetch(`/api/projects/${projectId}/document/${docId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        await loadDocuments()
      }
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const handleDownload = (docId: number, fileName: string) => {
    window.open(`/api/projects/${projectId}/document/${docId}/download`, '_blank')
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  const getFileIcon = (mimeType: string) => {
    if (mimeType.includes('pdf')) return '📄'
    if (mimeType.includes('word') || mimeType.includes('doc')) return '📝'
    if (mimeType.includes('text') || mimeType.includes('md')) return '📃'
    if (mimeType.includes('code') || mimeType.includes('javascript') || mimeType.includes('typescript')) return '💻'
    return '📎'
  }

  return (
    <div className="document-manager">
      {/* 上传区域 */}
      <div className="upload-section">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          accept=".pdf,.doc,.docx,.md,.txt,.js,.ts,.tsx,.vue,.py,.java,.json,.yaml,.yml"
        />
        <button 
          className="upload-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={uploading}
        >
          <FileUp size={16} />
          {uploading ? '上传中...' : '上传文档'}
        </button>
        <span className="upload-hint">支持 PDF, Word, Markdown, 代码文件</span>
      </div>

      {/* 上传进度 */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="upload-progress">
          {Object.entries(uploadProgress).map(([fileName, progress]) => (
            <div key={fileName} className="progress-item">
              <span className="file-name">{fileName}</span>
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${progress}%` }}></div>
              </div>
              <span className="progress-text">{progress}%</span>
            </div>
          ))}
        </div>
      )}

      {/* 文档列表 */}
      <div className="documents-list">
        {loading ? (
          <div className="loading">加载中...</div>
        ) : documents.length === 0 ? (
          <div className="empty-state">暂无文档</div>
        ) : (
          documents.map(doc => (
            <div key={doc.id} className="document-item">
              <span className="file-icon">{getFileIcon(doc.mime_type)}</span>
              <div className="file-info">
                <div className="file-name" title={doc.original_name}>
                  {doc.original_name}
                </div>
                <div className="file-meta">
                  {formatFileSize(doc.file_size)} · {new Date(doc.uploaded_at).toLocaleDateString()}
                </div>
              </div>
              <div className="file-actions">
                <button 
                  className="action-btn download"
                  onClick={() => handleDownload(doc.id, doc.original_name)}
                  title="下载"
                >
                  <Download size={14} />
                </button>
                <button 
                  className="action-btn delete"
                  onClick={() => handleDelete(doc.id)}
                  title="删除"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}

export default DocumentManager;
