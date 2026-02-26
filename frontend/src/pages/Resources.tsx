import { useState, useEffect } from 'react'

export function Resources() {
  const [resources, setResources] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadResources()
  }, [])

  const loadResources = async () => {
    try {
      const res = await fetch('/api/resources')
      const data = await res.json()
      if (data.success) setResources(data.resources || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📚 资源库 (T021)</h2>
      </div>

      <div className="card">
        {resources.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📚</div>
            <p>暂无资源</p>
          </div>
        ) : (
          <div className="grid-3">
            {resources.map((resource: any, i: number) => (
              <div key={i} className="card" style={{ marginBottom: 0, borderLeft: '4px solid #667eea' }}>
                <h4>{resource.name || '未命名资源'}</h4>
                <p style={{ color: '#666', marginTop: '8px', fontSize: '0.9rem' }}>
                  {resource.content || resource.description || '暂无描述'}
                </p>
                <div style={{ marginTop: '12px', display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  <span className="badge badge-blue">{resource.resource_type || '文档'}</span>
                  {resource.url && (
                    <a href={resource.url} target="_blank" rel="noopener noreferrer" className="badge badge-green">
                      访问链接
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
