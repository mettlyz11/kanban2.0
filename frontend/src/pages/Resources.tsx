import { useState, useEffect } from 'react'
import { Search, ExternalLink, Database, ChevronRight } from 'lucide-react'

// 资源类型配置
const typeConfig: Record<string, { icon: string; color: string; bg: string }> = {
  'chemistry': { icon: '🧪', color: 'text-purple-600', bg: 'bg-purple-50' },
  'search': { icon: '🔍', color: 'text-blue-600', bg: 'bg-blue-50' },
  'github': { icon: '🐙', color: 'text-gray-800', bg: 'bg-gray-100' },
  'website': { icon: '🌐', color: 'text-green-600', bg: 'bg-green-50' },
  'tool': { icon: '🛠️', color: 'text-orange-600', bg: 'bg-orange-50' },
  'document': { icon: '📚', color: 'text-red-600', bg: 'bg-red-50' },
  'database': { icon: '🗄️', color: 'text-indigo-600', bg: 'bg-indigo-50' },
  'file': { icon: '📄', color: 'text-gray-600', bg: 'bg-gray-50' },
  'link': { icon: '🔗', color: 'text-cyan-600', bg: 'bg-cyan-50' },
}

// 预设资源
const defaultResources = [
  // 计算化学
  { name: 'T109计算平台', type: 'chemistry', url: 'https://t109.mettlyz.com', desc: '过渡态计算平台', category: '计算化学' },
  { name: 'Sobereva', type: 'chemistry', url: 'http://sobereva.com', desc: '量子化学博客', category: '计算化学' },
  { name: 'PubChem', type: 'chemistry', url: 'https://pubchem.ncbi.nlm.nih.gov', desc: '化学分子数据库', category: '计算化学' },
  { name: 'NIST Chemistry', type: 'chemistry', url: 'https://webbook.nist.gov/chemistry', desc: 'NIST化学数据库', category: '计算化学' },
  
  // 搜索工具
  { name: 'Google Scholar', type: 'search', url: 'https://scholar.google.com', desc: '学术搜索', category: '搜索工具' },
  { name: 'Google', type: 'search', url: 'https://google.com', desc: '通用搜索', category: '搜索工具' },
  { name: 'Bing', type: 'search', url: 'https://bing.com', desc: '微软搜索', category: '搜索工具' },
  { name: 'Semantic Scholar', type: 'search', url: 'https://semanticscholar.org', desc: 'AI学术搜索', category: '搜索工具' },
  { name: 'arXiv', type: 'search', url: 'https://arxiv.org', desc: '预印本论文', category: '搜索工具' },
  
  // GitHub
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
  { name: 'DeepSeek', type: 'website', url: 'https://deepseek.com', desc: '深度求索', category: 'AI工具' },
]

export function Resources() {
  const [resources, setResources] = useState<any[]>(defaultResources)
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [selectedCategory, setSelectedCategory] = useState<string>('')

  useEffect(() => {
    loadResources()
  }, [])

  const loadResources = async () => {
    try {
      const filesRes = await fetch('/api/files/index')
      const filesData = await filesRes.json()
      
      if (filesData.success) {
        const localResources = filesData.files.slice(0, 100).map((f: any) => ({
          name: f.name,
          type: 'file',
          url: `/api/files/content/${encodeURIComponent(f.path)}`,
          desc: f.path,
          category: '本地文件'
        }))
        setResources([...defaultResources, ...localResources])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const filteredResources = resources.filter(r => {
    return !search || r.name.toLowerCase().includes(search.toLowerCase()) || r.desc.toLowerCase().includes(search.toLowerCase())
  })

  const groupedResources = filteredResources.reduce((acc, r) => {
    if (!acc[r.category]) acc[r.category] = []
    acc[r.category].push(r)
    return acc
  }, {} as Record<string, any[]>)

  const categories = Object.keys(groupedResources)
  
  useEffect(() => {
    if (categories.length > 0 && !selectedCategory) {
      setSelectedCategory(categories[0])
    }
  }, [categories])

  const selectedResources = selectedCategory ? groupedResources[selectedCategory] || [] : []
  const selectedConfig = typeConfig[selectedResources[0]?.type] || typeConfig['link']

  if (loading) {
    return <div className="min-h-screen flex items-center justify-center"><div className="animate-spin w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full"></div></div>
  }

  return (
    <div className="w-full">
      {/* 标题栏 */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <Database className="w-7 h-7 text-blue-500" />
          资源库
        </h2>
        <p className="text-gray-500 mt-1">共 {resources.length} 个资源</p>
      </div>

      {/* 搜索 */}
      <div className="mb-6">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 w-5 h-5" />
          <input
            type="text"
            placeholder="搜索资源..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="w-full pl-10 pr-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>
      </div>

      {/* 左右分栏布局 - 左侧窄，右侧宽 */}
      <div className="flex gap-6" style={{ minHeight: '600px' }}>
        {/* 左侧：分类列表 - 固定窄宽度 */}
        <div className="w-64 flex-shrink-0">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">资源分类</h3>
          <div className="space-y-2">
            {categories.map((category) => {
              const items = groupedResources[category]
              const config = typeConfig[items[0]?.type] || typeConfig['link']
              const isSelected = selectedCategory === category
              
              return (
                <button
                  key={category}
                  onClick={() => setSelectedCategory(category)}
                  className={`w-full px-4 py-3 flex items-center justify-between rounded-xl border transition-all ${
                    isSelected 
                      ? 'bg-blue-50 border-blue-200 shadow-sm' 
                      : 'bg-white border-gray-100 hover:bg-gray-50 hover:border-gray-200'
                  }`}
                >
                  <div className="flex items-center gap-2">
                    <span className="text-xl">{config.icon}</span>
                    <div className="text-left">
                      <span className={`font-medium text-sm ${isSelected ? 'text-blue-700' : 'text-gray-800'}`}>
                        {category}
                      </span>
                      <span className="text-xs text-gray-400 ml-1">({items.length})</span>
                    </div>
                  </div>
                  <ChevronRight className={`w-4 h-4 transition-colors ${isSelected ? 'text-blue-500' : 'text-gray-300'}`} />
                </button>
              )
            })}
          </div>
        </div>

        {/* 右侧：选中分类的资源列表 - 占满剩余空间 */}
        <div className="flex-1">
          <h3 className="text-lg font-semibold text-gray-800 mb-4">
            {selectedCategory ? `${selectedCategory} (${selectedResources.length})` : '请选择分类'}
          </h3>
          
          {selectedCategory ? (
            <div className="bg-white rounded-xl border border-gray-100 p-4">
              {/* 横向铺开的资源网格 */}
              <div className="grid grid-cols-5 gap-4">
                {selectedResources.map((resource: any, idx: number) => (
                  <a
                    key={idx}
                    href={resource.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-3 p-4 rounded-xl border border-gray-100 hover:border-blue-200 hover:shadow-md transition-all group bg-gray-50 hover:bg-white"
                  >
                    <div className={`w-12 h-12 rounded-xl ${selectedConfig.bg} flex items-center justify-center text-2xl flex-shrink-0`}>
                      {selectedConfig.icon}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-gray-800 group-hover:text-blue-600 transition-colors truncate">
                        {resource.name}
                      </h4>
                      <p className="text-sm text-gray-500 truncate mt-1">
                        {resource.desc || '暂无描述'}
                      </p>
                    </div>
                    <ExternalLink className="w-5 h-5 text-gray-300 group-hover:text-blue-500 transition-colors flex-shrink-0" />
                  </a>
                ))}
              </div>
            </div>
          ) : (
            <div className="text-center py-16 bg-gray-50 rounded-xl border border-dashed border-gray-200">
              <Database className="w-12 h-12 mx-auto mb-3 text-gray-300" />
              <p className="text-gray-500">点击左侧分类查看资源</p>
            </div>
          )}
        </div>
      </div>

      {filteredResources.length === 0 && (
        <div className="text-center py-16">
          <Database className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p className="text-gray-500">未找到匹配的资源</p>
        </div>
      )}
    </div>
  )
}

export default Resources
