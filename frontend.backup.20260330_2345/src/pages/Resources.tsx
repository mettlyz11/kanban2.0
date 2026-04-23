import { useState, useEffect } from 'react'

// 资源类型图标
const resourceIcons: Record<string, string> = {
  'file': '📄',
  'link': '🔗',
  'website': '🌐',
  'github': '🐙',
  'chemistry': '🧪',
  'search': '🔍',
  'note': '📝',
  'database': '🗄️',
  'tool': '🛠️',
  'document': '📚',
  'code': '💻',
  'config': '⚙️',
  'web': '🌍',
  'style': '🎨',
  'script': '📜',
  'text': '📃'
}

// Chevron 图标组件
const ChevronDown = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="6 9 12 15 18 9"></polyline>
  </svg>
)

const ChevronUp = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="18 15 12 9 6 15"></polyline>
  </svg>
)

const ExternalLink = () => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
    <polyline points="15 3 21 3 21 9"></polyline>
    <line x1="10" y1="14" x2="21" y2="3"></line>
  </svg>
)

// 预设资源
const defaultResources = [
  // 计算化学网站
  { name: 'T109计算平台', type: 'chemistry', url: 'https://t109.mettlyz.com', desc: '过渡态计算平台', category: '计算化学' },
  { name: 'Sobereva', type: 'chemistry', url: 'http://sobereva.com', desc: '量子化学博客', category: '计算化学' },
  { name: 'PubChem', type: 'chemistry', url: 'https://pubchem.ncbi.nlm.nih.gov', desc: '化学分子数据库', category: '计算化学' },
  { name: 'NIST Chemistry', type: 'chemistry', url: 'https://webbook.nist.gov/chemistry', desc: 'NIST化学数据库', category: '计算化学' },
  
  // 搜索网站
  { name: 'Google Scholar', type: 'search', url: 'https://scholar.google.com', desc: '学术搜索', category: '搜索工具' },
  { name: 'Google', type: 'search', url: 'https://google.com', desc: '通用搜索', category: '搜索工具' },
  { name: 'Bing', type: 'search', url: 'https://bing.com', desc: '微软搜索', category: '搜索工具' },
  { name: 'Semantic Scholar', type: 'search', url: 'https://semanticscholar.org', desc: 'AI学术搜索', category: '搜索工具' },
  { name: 'arXiv', type: 'search', url: 'https://arxiv.org', desc: '预印本论文', category: '搜索工具' },
  
  // GitHub资源
  { name: '看板系统 v2.0', type: 'github', url: 'https://github.com/mettlyz11/kanban2.0', desc: 'React看板系统', category: 'GitHub' },
  { name: '看板系统 v1.0', type: 'github', url: 'https://github.com/mettlyz11/kanban-system', desc: 'Flask看板系统', category: 'GitHub' },
  { name: 'GitHub主页', type: 'github', url: 'https://github.com/mettlyz11', desc: '我的GitHub主页', category: 'GitHub' },
  
  // 开发工具
  { name: 'React文档', type: 'website', url: 'https://react.dev', desc: 'React官方文档', category: '开发工具' },
  { name: 'Flask文档', type: 'website', url: 'https://flask.palletsprojects.com', desc: 'Flask官方文档', category: '开发工具' },
  { name: 'MDN Web Docs', type: 'website', url: 'https://developer.mozilla.org', desc: 'Web技术文档', category: '开发工具' },
  { name: 'Stack Overflow', type: 'website', url: 'https://stackoverflow.com', desc: '开发者问答', category: '开发工具' },
  
  // AI工具
  { name: 'OpenAI', type: 'website', url: 'https://openai.com', desc: 'OpenAI官网', category: 'AI工具' },
  { name: 'Claude', type: 'website', url: 'https://claude.ai', desc: 'Anthropic Claude', category: 'AI工具' },
  { name: 'Moonshot AI', type: 'website', url: 'https://moonshot.cn', desc: '月之暗面', category: 'AI工具' },
]

export function Resources() {
  const [resources, setResources] = useState<any[]>(defaultResources)
  const [localFiles, setLocalFiles] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [expandedCategories, setExpandedCategories] = useState<string[]>(['本地文件'])
  const [search, setSearch] = useState('')
  const [selectedFile, setSelectedFile] = useState<any>(null)
  const [fileContent, setFileContent] = useState('')

  useEffect(() => {
    loadResources()
  }, [])

  const loadResources = async () => {
    try {
      // 加载本地文件索引
      const filesRes = await fetch('/api/files/index')
      const filesData = await filesRes.json()
      
      if (filesData.success) {
        // 转换本地文件为资源格式
        const localResources = filesData.files.slice(0, 200).map((f: any) => ({
          name: f.name,
          type: f.type,
          url: `/api/files/content/${encodeURIComponent(f.path)}`,
          desc: f.desc || f.path,
          category: '本地文件',
          path: f.path,
          size: f.size,
          modified: f.modified
        }))
        setLocalFiles(localResources)
      }
      
      // 加载API资源
      const res = await fetch('/api/resources')
      const data = await res.json()
      
      if (data.resources) {
        setResources([...defaultResources, ...data.resources])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleFileClick = async (resource: any) => {
    if (resource.category === '本地文件' && resource.path) {
      try {
        const res = await fetch(`/api/files/content/${encodeURIComponent(resource.path)}`)
        const data = await res.json()
        if (data.success) {
          setFileContent(data.content)
          setSelectedFile(resource)
        }
      } catch (e) {
        console.error(e)
      }
    } else {
      window.open(resource.url, '_blank')
    }
  }

  // 合并所有资源
  const allResources = [...localFiles, ...resources]

  // 按分类分组
  const groupedResources = allResources.reduce((acc: any, r) => {
    const cat = r.category || '其他'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(r)
    return acc
  }, {})

  // 搜索过滤
  const filteredCategories = Object.entries(groupedResources).filter(([, items]: [string, any]) => {
    if (!search) return true
    return (items as any[]).some((r: any) => 
      r.name?.toLowerCase().includes(search.toLowerCase()) ||
      r.desc?.toLowerCase().includes(search.toLowerCase())
    )
  })

  const toggleCategory = (category: string) => {
    setExpandedCategories(prev => 
      prev.includes(category) 
        ? prev.filter(c => c !== category)
        : [...prev, category]
    )
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📚 资源库 (T021)</h2>
      </div>

      {/* 搜索 */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <input
          type="text"
          placeholder="搜索资源..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ 
            padding: '12px 16px', 
            borderRadius: '8px', 
            border: '1px solid #ddd',
            width: '100%',
            fontSize: '14px'
          }}
        />
      </div>

      {/* 资源列表 - 手风琴样式 */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
        {filteredCategories.map(([category, items]: [string, any]) => (
          <div key={category} className="card" style={{ padding: 0, overflow: 'hidden' }}>
            {/* 分类标题栏 */}
            <div 
              onClick={() => toggleCategory(category)}
              style={{ 
                padding: '16px 20px',
                background: '#f8f9fa',
                cursor: 'pointer',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                borderLeft: `4px solid ${getCategoryColor(category)}`,
                transition: 'background 0.2s'
              }}
              onMouseEnter={e => e.currentTarget.style.background = '#e9ecef'}
              onMouseLeave={e => e.currentTarget.style.background = '#f8f9fa'}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '1.25rem' }}>{getCategoryIcon(category)}</span>
                <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>{category}</span>
                <span className="badge" style={{ background: '#e9ecef', color: '#666' }}>
                  {(items as any[]).length}
                </span>
              </div>
              <span style={{ fontSize: '1.5rem', color: '#999' }}>
                {expandedCategories.includes(category) ? <ChevronUp /> : <ChevronDown />}
              </span>
            </div>

            {/* 展开的资源列表 */}
            {expandedCategories.includes(category) && (
              <div style={{ borderTop: '1px solid #e9ecef' }}>
                {(items as any[]).map((resource: any, i: number) => (
                  <div
                    key={i}
                    onClick={() => handleFileClick(resource)}
                    style={{ 
                      display: 'flex',
                      alignItems: 'center',
                      gap: '16px',
                      padding: '14px 20px',
                      textDecoration: 'none',
                      color: 'inherit',
                      borderBottom: i < (items as any[]).length - 1 ? '1px solid #f0f0f0' : 'none',
                      transition: 'background 0.2s',
                      cursor: 'pointer'
                    }}
                    onMouseEnter={e => e.currentTarget.style.background = '#f8f9fa'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <span style={{ fontSize: '1.5rem' }}>
                      {resourceIcons[resource.type] || '📄'}
                    </span>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 500, marginBottom: '2px' }}>{resource.name}</div>
                      <div style={{ fontSize: '0.85rem', color: '#666' }}>{resource.desc}</div>
                    </div>
                    {resource.modified && (
                      <span style={{ fontSize: '0.75rem', color: '#999' }}>{resource.modified}</span>
                    )}
                    <span style={{ color: '#999' }}>
                      {resource.category === '本地文件' ? '👁️' : <ExternalLink />}
                    </span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredCategories.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <p>暂无资源</p>
        </div>
      )}

      {/* 文件内容查看弹窗 */}
      {selectedFile && (
        <div className="modal-overlay" onClick={() => setSelectedFile(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '900px', maxHeight: '85vh' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <div>
                <h4>{selectedFile.name}</h4>
                <p style={{ fontSize: '0.85rem', color: '#666', margin: '4px 0 0 0' }}>{selectedFile.path}</p>
              </div>
              <button className="btn btn-sm btn-secondary" onClick={() => setSelectedFile(null)}>✕</button>
            </div>
            <div style={{ 
              maxHeight: '60vh', 
              overflow: 'auto',
              padding: '16px',
              background: '#f8f9fa',
              borderRadius: '8px',
              fontFamily: 'monospace',
              fontSize: '13px',
              lineHeight: '1.6',
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-word'
            }}>
              {fileContent}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function getCategoryColor(category: string): string {
  const colors: Record<string, string> = {
    '本地文件': '#28a745',
    '计算化学': '#17a2b8',
    '搜索工具': '#ffc107',
    'GitHub': '#6f42c1',
    '开发工具': '#fd7e14',
    'AI工具': '#dc3545',
    '其他': '#6c757d'
  }
  return colors[category] || '#667eea'
}

function getCategoryIcon(category: string): string {
  const icons: Record<string, string> = {
    '本地文件': '📁',
    '计算化学': '🧪',
    '搜索工具': '🔍',
    'GitHub': '🐙',
    '开发工具': '🛠️',
    'AI工具': '🤖',
    '其他': '📦'
  }
  return icons[category] || '📚'
}

export default Resources
