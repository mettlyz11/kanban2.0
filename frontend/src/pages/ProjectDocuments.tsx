import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { api } from '../utils/api'
import { ArrowLeft, FileUp, Download, Trash2 } from 'lucide-react'

interface Document {
  id: number
  file_name: string
  original_name: string
  file_size: number
  uploaded_at: string
}

interface Project {
  id: number
  name: string
  description: string
}

export function ProjectDocuments() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [project, setProject] = useState<Project | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    if (projectId) {
      loadProject(parseInt(projectId))
      loadDocuments(parseInt(projectId))
    }
  }, [projectId])

  const loadProject = async (id: number) => {
    try {
      const data = await api.getProjects()
      if (data.success) {
        const p = data.projects.find((p: Project) => p.id === id)
        setProject(p || null)
      }
    } catch (e) {
      console.error(e)
    }
  }

  const loadDocuments = async (id: number) => {
    setLoading(true)
    try {
      const response = await fetch(`/api/projects/${id}/document`)
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

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file || !projectId) return

    setUploading(true)
    const formData = new FormData()
    formData.append('file', file)

    try {
      const response = await fetch(`/api/projects/${projectId}/document`, {
        method: 'POST',
        body: formData
      })

      if (response.ok) {
        await loadDocuments(parseInt(projectId))
      }
    } catch (error) {
      console.error('Upload failed:', error)
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (docId: number) => {
    if (!confirm('确定要删除这个文档吗？')) return
    if (!projectId) return

    try {
      const response = await fetch(`/api/projects/${projectId}/document/${docId}`, {
        method: 'DELETE'
      })

      if (response.ok) {
        await loadDocuments(parseInt(projectId))
      }
    } catch (error) {
      console.error('Delete failed:', error)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
  }

  if (!project) {
    return <div style={{ padding: '24px' }}>加载中...</div>
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 头部 */}
      <div style={{ marginBottom: '24px' }}>
        <button 
          onClick={() => navigate('/projects')}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '8px 16px',
            background: '#f3f4f6',
            border: 'none',
            borderRadius: '6px',
            cursor: 'pointer',
            marginBottom: '16px'
          }}
        >
          <ArrowLeft size={16} />
          返回项目列表
        </button>
        
        <h1 style={{ margin: '0 0 8px 0', fontSize: '24px', fontWeight: 600 }}>
          📎 {project.name} - 文档管理
        </h1>
        <p style={{ margin: 0, color: '#6b7280' }}>{project.description}</p>
      </div>

      {/* 上传区域 */}
      <div style={{ 
        marginBottom: '24px', 
        padding: '24px', 
        background: '#f9fafb', 
        borderRadius: '8px',
        border: '2px dashed #d1d5db'
      }}>
        <input
          type="file"
          onChange={handleFileUpload}
          style={{ display: 'none' }}
          id="file-upload"
          accept=".pdf,.doc,.docx,.md,.txt"
        />
        <label 
          htmlFor="file-upload"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '8px',
            padding: '12px 24px',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            borderRadius: '6px',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          <FileUp size={16} />
          {uploading ? '上传中...' : '上传文档'}
        </label>
        <p style={{ margin: '8px 0 0 0', fontSize: '12px', color: '#6b7280', textAlign: 'center' }}>
          支持 PDF, Word, Markdown, 文本文件
        </p>
      </div>

      {/* 文档列表 */}
      <div>
        <h2 style={{ fontSize: '18px', marginBottom: '16px' }}>文档列表</h2>
        
        {loading ? (
          <div>加载中...</div>
        ) : documents.length === 0 ? (
          <div style={{ 
            padding: '48px', 
            textAlign: 'center', 
            color: '#9ca3af',
            background: '#f9fafb',
            borderRadius: '8px' 
          }}>
            暂无文档
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {documents.map(doc => (
              <div 
                key={doc.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '16px',
                  background: 'white',
                  borderRadius: '8px',
                  border: '1px solid #e5e7eb'
                }}
              >
                <span style={{ fontSize: '24px', marginRight: '12px' }}>📄</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 500, marginBottom: '4px' }}>{doc.original_name}</div>
                  <div style={{ fontSize: '12px', color: '#6b7280' }}>
                    {formatFileSize(doc.file_size)} · {new Date(doc.uploaded_at).toLocaleDateString()}
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    onClick={() => window.open(`/api/projects/${projectId}/document/${doc.id}/download`, '_blank')}
                    style={{
                      padding: '8px',
                      background: '#f3f4f6',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer'
                    }}
                    title="下载"
                  >
                    <Download size={16} />
                  </button>
                  <button
                    onClick={() => handleDelete(doc.id)}
                    style={{
                      padding: '8px',
                      background: '#fee2e2',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      color: '#ef4444'
                    }}
                    title="删除"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export default ProjectDocuments
