import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Skills() {
  const [skills, setSkills] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')

  useEffect(() => {
    loadSkills()
  }, [])

  const loadSkills = async () => {
    try {
      const res = await api.getSkills()
      if (res.success) {
        setSkills(res.skills || [])
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const filteredSkills = skills.filter(skill => 
    !filter || skill.category === filter
  )

  const categories = Array.from(new Set(skills.map(s => s.category)))

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div className="w-full">
      {/* 标题栏 - 全宽 */}
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-gray-800 flex items-center gap-2">
          <span className="text-2xl">🛠️</span>
          技能库
        </h2>
        <p className="text-gray-500 mt-1">共 {skills.length} 个技能</p>
      </div>

      {/* 分类筛选 - 全宽 */}
      <div className="flex flex-wrap gap-2 mb-6">
        <button
          className={`px-4 py-2 rounded-lg transition-all ${filter === '' ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
          onClick={() => setFilter('')}
        >
          全部
        </button>
        {categories.map(cat => (
          <button
            key={cat}
            className={`px-4 py-2 rounded-lg transition-all ${filter === cat ? 'bg-blue-500 text-white' : 'bg-gray-100 text-gray-700 hover:bg-gray-200'}`}
            onClick={() => setFilter(cat)}
          >
            {cat}
          </button>
        ))}
      </div>

      {/* 技能网格 - 全宽多列布局 */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
        {filteredSkills.map(skill => (
          <div key={skill.id} className="bg-white rounded-xl p-5 shadow-sm hover:shadow-md transition-shadow border border-gray-100">
            <div className="flex justify-between items-start mb-3">
              <div className="text-3xl">{skill.icon || '🛠️'}</div>
              <span className="px-2 py-1 bg-blue-100 text-blue-700 text-xs rounded-full font-medium">
                {skill.category}
              </span>
            </div>
            <h4 className="font-semibold text-gray-800 mb-2">{skill.name}</h4>
            <p className="text-gray-500 text-sm mb-3 line-clamp-2">
              {skill.description || '暂无描述'}
            </p>
            <div className="flex justify-between items-center text-sm">
              <span className="text-gray-400">
                版本: {skill.version || '1.0'}
              </span>
              <span className={`px-2 py-1 rounded text-xs ${skill.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                {skill.status === 'active' ? '可用' : '开发中'}
              </span>
            </div>
            {skill.command && (
              <div className="mt-3 p-2 bg-gray-50 rounded-lg font-mono text-xs text-gray-600 overflow-x-auto">
                {skill.command}
              </div>
            )}
          </div>
        ))}
      </div>

      {filteredSkills.length === 0 && (
        <div className="text-center py-16">
          <div className="text-6xl mb-4">🛠️</div>
          <p className="text-gray-500">暂无技能</p>
        </div>
      )}
    </div>
  )
}

export default Skills
