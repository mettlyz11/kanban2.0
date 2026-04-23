import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { 
  Building2, 
  Calendar, 
  User, 
  Award,
  ChevronLeft,
  Folder,
  Clock,
  Briefcase,
  Users,
  FileText,
  Camera
} from 'lucide-react'

interface TabData {
  tab_key: string
  tab_label: string
  tab_icon: string
  is_system: number
  is_custom: number
  sort_order: number
  data: any
}

interface Company {
  id: number
  name: string
  short_name: string
  industry: string
  sub_industry: string
  address: string
  legal_representative: string
  registered_capital: string
  create_date: string
  employee_count: number
  description: string
  business_license: string
  email: string
  phone: string
  website: string
  logo: string
  tax_id: string
  tabs: TabData[]
}

const iconMap: Record<string, any> = {
  Building2,
  Camera,
  Users,
  FileText,
  Folder,
  Calendar,
  User,
  Award,
  Clock,
  Briefcase
}

export function Helight() {
  const companyId = 1
  const navigate = useNavigate()
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<string>('basic')

  useEffect(() => {
    fetchCompany()
  }, [companyId])

  const fetchCompany = async () => {
    try {
      setLoading(true)
      const res = await fetch(`/api/companies/${companyId}`)
      const data = await res.json()
      if (data.success && data.company) {
        setCompany(data.company)
        // 设置第一个 Tab 为活跃 Tab
        if (data.company.tabs && data.company.tabs.length > 0) {
          setActiveTab(data.company.tabs[0].tab_key)
        }
      }
    } catch (e) {
      console.error('Failed to fetch company:', e)
    } finally {
      setLoading(false)
    }
  }

  const renderTabContent = (tab: TabData) => {
    switch (tab.tab_key) {
      case 'basic':
        return renderBasicInfo(tab.data)
      case 'logo':
        return renderLogo(tab.data)
      case 'team':
        return renderTeam(tab.data)
      case 'news':
        return renderNews(tab.data)
      case 'local_files':
        return renderLocalFiles(tab.data)
      default:
        return (
          <div style={{ padding: '40px', textAlign: 'center', color: '#888' }}>
            Tab 内容开发中...
          </div>
        )
    }
  }

  const renderBasicInfo = (data: any) => (
    <div className="card" style={{ marginBottom: '24px' }}>
      <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Building2 size={20} />
        基本信息
      </h3>
      <div style={{ display: 'grid', gap: '16px' }}>
        <InfoRow label="公司名称" value={data.name} />
        <InfoRow label="简称" value={data.short_name} />
        <InfoRow label="行业" value={`${data.industry} ${data.sub_industry || ''}`.trim()} />
        <InfoRow label="地址" value={data.address} />
        <InfoRow label="法定代表人" value={data.legal_representative} />
        <InfoRow label="注册资本" value={data.registered_capital} />
        <InfoRow label="成立日期" value={data.create_date} />
        <InfoRow label="员工人数" value={data.employee_count?.toString()} />
        <InfoRow label="公司简介" value={data.description} />
      </div>
    </div>
  )

  const renderLogo = (data: any) => (
    <div className="card">
      <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Camera size={20} />
        Logo 设置
      </h3>
      {data.logo_url ? (
        <img src={data.logo_url} alt="Company Logo" style={{ maxWidth: '200px' }} />
      ) : (
        <p style={{ color: '#888' }}>暂无 Logo</p>
      )}
    </div>
  )

  const renderTeam = (data: any) => (
    <div className="card">
      <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Users size={20} />
        团队成员
      </h3>
      {data.members && data.members.length > 0 ? (
        <div style={{ display: 'grid', gap: '12px' }}>
          {data.members.map((member: any, index: number) => (
            <div key={index} style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontWeight: '600' }}>{member.name}</div>
              <div style={{ color: '#888', fontSize: '0.9rem' }}>{member.position}</div>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: '#888' }}>暂无团队成员</p>
      )}
    </div>
  )

  const renderNews = (data: any) => (
    <div className="card">
      <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <FileText size={20} />
        公司动态
      </h3>
      {data.items && data.items.length > 0 ? (
        <div style={{ display: 'grid', gap: '12px' }}>
          {data.items.map((item: any, index: number) => (
            <div key={index} style={{ padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>
              <div style={{ fontWeight: '600' }}>{item.title}</div>
              <div style={{ color: '#888', fontSize: '0.9rem' }}>{item.date}</div>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: '#888' }}>暂无动态</p>
      )}
    </div>
  )

  const renderLocalFiles = (data: any) => (
    <div className="card">
      <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <Folder size={20} />
        本地文件
      </h3>
      
      {data.files && data.files.length > 0 ? (
        <div style={{ display: 'grid', gap: '16px' }}>
          {data.files.map((file: any, index: number) => (
            <div
              key={index}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '16px',
                padding: '16px',
                background: '#f8f9fa',
                borderRadius: '8px',
                cursor: 'pointer',
                transition: 'all 0.2s'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = '#e8f4ff'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = '#f8f9fa'
              }}
            >
              <span style={{ fontSize: '32px' }}>📄</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: '600', marginBottom: '4px' }}>{file.name}</div>
                <div style={{ color: '#888', fontSize: '0.85rem' }}>
                  {file.path}
                </div>
                {file.category && (
                  <div style={{ color: '#667eea', fontSize: '0.8rem', marginTop: '4px' }}>
                    📁 {file.category}
                  </div>
                )}
              </div>
              <div style={{ color: '#667eea' }}>›</div>
            </div>
          ))}
        </div>
      ) : (
        <p style={{ color: '#888', padding: '40px', textAlign: 'center' }}>暂无文件</p>
      )}

      <div style={{ 
        marginTop: '24px', 
        padding: '16px', 
        background: '#f0f4ff', 
        borderRadius: '8px',
        display: 'flex',
        alignItems: 'center',
        gap: '8px'
      }}>
        <Clock size={18} color="#667eea" />
        <span style={{ color: '#667eea', fontSize: '0.9rem' }}>
          本地文件夹同步状态：✅ 已同步
        </span>
      </div>
    </div>
  )

  const InfoRow = ({ label, value }: { label: string; value?: string }) => {
    if (!value) return null
    return (
      <div style={{ display: 'flex', padding: '12px', background: '#f8f9fa', borderRadius: '8px' }}>
        <span style={{ width: '150px', color: '#666' }}>{label}</span>
        <span style={{ flex: 1, fontWeight: '500' }}>{value}</span>
      </div>
    )
  }

  if (loading) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '24px', marginBottom: '16px' }}>⏳</div>
        <div>加载中...</div>
      </div>
    )
  }

  if (!company) {
    return (
      <div style={{ padding: '40px', textAlign: 'center' }}>
        <div style={{ fontSize: '24px', marginBottom: '16px' }}>❌</div>
        <div>公司不存在</div>
      </div>
    )
  }

  const getIconComponent = (iconName: string) => {
    const IconComponent = iconMap[iconName] || Folder
    return IconComponent
  }

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      {/* 返回按钮 */}
      <button
        onClick={() => navigate('/company')}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          marginBottom: '24px',
          padding: '8px 16px',
          background: 'transparent',
          border: 'none',
          cursor: 'pointer',
          color: '#667eea',
          fontSize: '16px'
        }}
      >
        <ChevronLeft size={20} />
        返回公司列表
      </button>

      {/* 公司标题 */}
      <div style={{ marginBottom: '32px' }}>
        <h1 style={{ fontSize: '32px', marginBottom: '8px' }}>{company.name}</h1>
        {company.short_name && (
          <p style={{ color: '#888', fontSize: '18px' }}>{company.short_name}</p>
        )}
      </div>

      {/* Tab 导航 */}
      <div style={{ 
        display: 'flex', 
        gap: '12px', 
        marginBottom: '24px',
        borderBottom: '2px solid #e0e0e0',
        paddingBottom: '12px',
        flexWrap: 'wrap'
      }}>
        {company.tabs.map((tab) => {
          const IconComponent = getIconComponent(tab.tab_icon)
          return (
            <button
              key={tab.tab_key}
              onClick={() => setActiveTab(tab.tab_key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '12px 24px',
                background: activeTab === tab.tab_key ? '#667eea' : 'transparent',
                color: activeTab === tab.tab_key ? 'white' : '#666',
                border: 'none',
                borderRadius: '8px',
                cursor: 'pointer',
                fontWeight: activeTab === tab.tab_key ? '600' : '400',
                transition: 'all 0.2s'
              }}
              onMouseEnter={e => {
                if (activeTab !== tab.tab_key) {
                  e.currentTarget.style.background = '#f0f0f0'
                }
              }}
              onMouseLeave={e => {
                if (activeTab !== tab.tab_key) {
                  e.currentTarget.style.background = 'transparent'
                }
              }}
            >
              <IconComponent size={18} />
              {tab.tab_label}
            </button>
          )
        })}
      </div>

      {/* Tab 内容 */}
      {company.tabs.map(tab => {
        if (tab.tab_key === activeTab) {
          return <div key={tab.tab_key}>{renderTabContent(tab)}</div>
        }
        return null
      })}
    </div>
  )
}

export default Helight
