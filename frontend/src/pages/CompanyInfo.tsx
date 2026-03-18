import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { Building2, Users, FileText, ChevronRight } from 'lucide-react'

interface Company {
  id: string
  name: string
  shortName: string
  legalRepresentative: string
  industry: string
  createDate: string
  lastUpdated: string
}

const sampleCompanies: Company[] = [
  {
    id: 'helight',
    name: '和光智成（北京）科技有限公司',
    shortName: '和光智成',
    legalRepresentative: '刘宇宙',
    industry: '人工智能/化学计算',
    createDate: '2020-01-15',
    lastUpdated: '2026-03-02'
  }
]

export function CompanyInfo() {
  const [companies, setCompanies] = useState<Company[]>([])
  const [loading, setLoading] = useState(true)
  const navigate = useNavigate()

  useEffect(() => {
    fetchCompanies()
  }, [])

  const fetchCompanies = async () => {
    try {
      const res = await fetch('/api/company-info/companies')
      const data = await res.json()
      if (data.success) {
        setCompanies(data.companies)
      } else {
        setCompanies(sampleCompanies)
      }
    } catch (e) {
      setCompanies(sampleCompanies)
    } finally {
      setLoading(false)
    }
  }

  const handleCompanyClick = (companyId: string) => {
    // 使用公司ID作为路由参数
    navigate(`/company/${companyId}`)
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
        <h2 className="page-title">🏢 公司信息管理</h2>
        <p style={{ color: '#666', marginTop: '8px' }}>
          管理公司档案、合同、资质等企业信息
        </p>
      </div>

      {/* 公司列表 */}
      <div className="card">
        <h3 style={{ marginBottom: '20px' }}>公司列表</h3>
        <div style={{ display: 'grid', gap: '16px' }}>
          {companies.map(company => (
            <div
              key={company.id}
              onClick={() => handleCompanyClick(company.id)}
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
                borderRadius: '12px',
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: '28px'
              }}>
                🏢
              </div>
              <div style={{ flex: 1 }}>
                <h4 style={{ margin: '0 0 4px 0', fontSize: '1.2rem' }}>{company.name}</h4>
                <p style={{ margin: 0, color: '#666', fontSize: '0.9rem' }}>
                  行业: {company.industry}
                </p>
                <p style={{ margin: '4px 0 0 0', color: '#888', fontSize: '0.85rem' }}>
                  法定代表人: {company.legalRepresentative}
                </p>
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
          <Building2 size={32} color="#667eea" />
          <div className="stat-value">{companies.length}</div>
          <div className="stat-label">公司总数</div>
        </div>
        <div className="stat-card">
          <FileText size={32} color="#4CAF50" />
          <div className="stat-value">0</div>
          <div className="stat-label">合同档案</div>
        </div>
        <div className="stat-card">
          <Users size={32} color="#FF9800" />
          <div className="stat-value">1</div>
          <div className="stat-label">核心团队</div>
        </div>
      </div>
    </div>
  )
}
