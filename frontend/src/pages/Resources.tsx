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
  'document': '📚'
}

// 预设资源
const defaultResources = [
  // 本地文件索引
  { name: '项目文档', type: 'file', url: '/docs', desc: '看板系统文档目录', category: '本地文件' },
  { name: '代码仓库', type: 'file', url: '/code', desc: '本地代码备份', category: '本地文件' },
  { name: '数据库备份', type: 'file', url: '/backups', desc: 'SQLite数据库备份', category: '本地文件' },
  { name: '配置文件', type: 'file', url: '/config', desc: '系统配置文件', category: '本地文件' },
  
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
  const [resources, setResources] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    loadResources()
  }, [])

  const loadResources = async () => {
    try {
      const res = await fetch('/api/resources')
      const data = await res.json()
      
      // 合并API数据和预设资源
      const apiResources = data.resources || []
      const allResources = [...defaultResources, ...apiResources]
      setResources(allResources)
    } catch (e) {
      console.error(e)
      // 如果API失败，使用默认资源
      setResources(defaultResources)
    } finally {
      setLoading(false)
    }
  }

  // 获取所有分类
  const categories = ['all', ...Array.from(new Set(resources.map(r => r.category || '其他')))]

  // 过滤资源
  const filteredResources = resources.filter(r => {
    const matchesCategory = filter === 'all' || r.category === filter
    const matchesSearch = !search || 
      r.name?.toLowerCase().includes(search.toLowerCase()) ||
      r.desc?.toLowerCase().includes(search.toLowerCase()) ||
      r.url?.toLowerCase().includes(search.toLowerCase())
    return matchesCategory && matchesSearch
  })

  // 按分类分组
  const groupedResources = filteredResources.reduce((acc: any, r) => {
    const cat = r.category || '其他'
    if (!acc[cat]) acc[cat] = []
    acc[cat].push(r)
    return acc
  }, {})

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📚 资源库 (T021)</h2>
      </div>

      {/* 搜索和筛选 */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div style={{ display: 'flex', gap: '16px', flexWrap: 'wrap', alignItems: 'center' }}>
          <input
            type="text"
            placeholder="搜索资源..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ 
              padding: '10px 16px', 
              borderRadius: '8px', 
              border: '1px solid #ddd',
              minWidth: '250px',
              fontSize: '14px'
            }}
          />
          <div className="filter-bar" style={{ margin: 0, flex: 1 }}>
            {categories.map(cat => (
              <button
                key={cat}
                className={`filter-btn ${filter === cat ? 'active' : ''}`}
                onClick={() => setFilter(cat)}
                style={{ fontSize: '13px', padding: '6px 14px' }}
              >
                {cat === 'all' ? '全部' : cat}
              </button>
            ))}
          </div>
        </div>
        <div style={{ marginTop: '12px', color: '#666', fontSize: '0.9rem' }}>
          共 {filteredResources.length} 个资源
        </div>
      </div>

      {/* 资源列表 - 按分类分组 */}
      {Object.entries(groupedResources).map(([category, items]: [string, any]) => (
        <div key={category} className="card" style={{ marginBottom: '20px' }}>
          <div className="card-header">
            <h5>{category}</h5>
            <span className="badge badge-blue">{(items as any[]).length} 个</span>
          </div>
          <div className="grid-4" style={{ gap: '12px' }}>
            {(items as any[]).map((resource: any, i: number) => (
              <a
                key={i}
                href={resource.url}
                target="_blank"
                rel="noopener noreferrer"
                className="card"
                style={{ 
                  marginBottom: 0, 
                  padding: '16px',
                  textDecoration: 'none',
                  color: 'inherit',
                  transition: 'transform 0.2s, box-shadow 0.2s',
                  borderLeft: `4px solid ${getCategoryColor(resource.category)}`
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <div style={{ fontSize: '2rem', marginBottom: '8px' }}>
                  {resourceIcons[resource.type] || '📄'}
                </div>
                <h6 style={{ marginBottom: '4px', fontSize: '0.95rem' }}>{resource.name}</h6>
                <p style={{ color: '#666', fontSize: '0.8rem', margin: 0, lineHeight: '1.4' }}>
                  {resource.desc}
                </p>
                {resource.url && (
                  <div style={{ 
                    marginTop: '8px', 
                    fontSize: '0.7rem', 
                    color: '#999',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap'
                  }}>
                    {resource.url}
                  </div>
                )}
              </a>
            ))}
          </div>
        </div>
      ))}

      {filteredResources.length === 0 && (
        <div className="empty-state">
          <div className="empty-state-icon">📚</div>
          <p>暂无资源</p>
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
