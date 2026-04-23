import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { User, FileText, Award, Folder, ChevronRight } from 'lucide-react'

interface PersonInfo {
  id: string
  name: string
  birthDate: string
  gender: string
  currentPosition: string
  department: string
  photo?: string
  lastUpdated: string
}

const samplePeople: PersonInfo[] = [
  {
    id: 'liuyuzhou',
    name: '刘宇宙',
    birthDate: '1982-09-16',
    gender: '男',
    currentPosition: '蓝天青年学者（二级）',
    department: '北京航空航天大学 化学学院',
    lastUpdated: '2026-03-02'
  }
]

export function PersonalInfo() {
  const [people, setPeople] = useState<PersonInfo[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    // 从API获取人员列表
    fetchPeople()
  }, [])

  const fetchPeople = async () => {
    try {
      const res = await fetch('/api/personal-info/people')
      const data = await res.json()
      if (data.success) {
        setPeople(data.people)
      } else {
        // 使用示例数据
        setPeople(samplePeople)
      }
    } catch (e) {
      setPeople(samplePeople)
    } finally {
      setLoading(false)
    }
  }

  const handlePersonClick = (personId: string) => {
    navigate(`/personal/${personId}`)
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">加载中...</div>
      </div>
    )
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h2 className="page-title">👤 个人信息管理</h2>
        <p style={{ color: '#666', marginTop: '8px' }}>
          管理人员档案、合同、证书等个人信息
        </p>
      </div>

      {/* 人员列表 */}
      <div className="card">
        <h3 style={{ marginBottom: '20px' }}>人员列表</h3>
        <div style={{ display: 'grid', gap: '16px' }}>
          {people.map(person => (
            <div
              key={person.id}
              onClick={() => handlePersonClick(person.id)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                padding: '20px',
                background: '#f8f9fa',
                borderRadius: '12px',
                cursor: 'pointer',
                transition: 'all 0.2s',
                border: '2px solid transparent'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.borderColor = '#667eea'
                e.currentTarget.style.background = '#f0f4ff'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.borderColor = 'transparent'
                e.currentTarget.style.background = '#f8f9fa'
              }}
            >
              <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '28px'
              }}>
                {person.photo ? (
                  <img src={person.photo} alt={person.name} style={{ width: '100%', height: '100%', borderRadius: '50%' }} />
                ) : (
                  '👤'
                )}
              </div>
              <div style={{ flex: 1 }}>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '1.2rem' }}>{person.name}</h4>
                <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>{person.currentPosition}</p>
                <p style={{ margin: '4px 0 0 0', color: '#888', fontSize: '0.85rem' }}>{person.department}</p>
              </div>
              <div style={{ textAlign: 'right' }}>
                <ChevronRight size={24} color="#667eea" />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 统计信息 */}
      <div className="stats-grid" style={{ marginTop: '24px' }}>
        <div className="stat-card">
          <User size={32} color="#667eea" />
          <div className="stat-value">{people.length}</div>
          <div className="stat-label">人员总数</div>
        </div>
        <div className="stat-card">
          <FileText size={32} color="#4CAF50" />
          <div className="stat-value">1</div>
          <div className="stat-label">合同档案</div>
        </div>
        <div className="stat-card">
          <Award size={32} color="#FF9800" />
          <div className="stat-value">0</div>
          <div className="stat-label">证书资质</div>
        </div>
        <div className="stat-card">
          <Folder size={32} color="#9C27B0" />
          <div className="stat-value">6</div>
          <div className="stat-label">文件分类</div>
        </div>
      </div>
    </div>
  )
}

export default PersonalInfo
