import { useState, useEffect } from 'react'
import ProfileFromFiles from '@/components/ProfileFromFiles'
import { useNavigate } from 'react-router-dom'
import { 
  User, 
  Calendar, 
  Briefcase, 
  Building, 
  FileText, 
  GraduationCap,
  Phone,
  Mail,
  Download,
  ChevronLeft,
  Folder,
  Clock
} from 'lucide-react'

interface ContractInfo {
  contractNo: string
  position: string
  positionType: string
  department: string
  startDate: string
  endDate: string
  duration: string
  requirements: string[]
  fileName: string
}

interface PersonDetail {
  id: string
  name: string
  birthDate: string
  gender: string
  currentPosition: string
  department: string
  contact: {
    phone: string
    email: string
  }
  education: {
    school: string
    degree: string
    major: string
    year: string
  }[]
  researchAreas: string[]
  contract: ContractInfo
}

const sampleDetail: PersonDetail = {
  id: 'liuyuzhou',
  name: '刘宇宙',
  birthDate: '1982-09-16',
  gender: '男',
  currentPosition: '蓝天青年学者（二级）',
  department: '北京航空航天大学 化学学院',
  contact: {
    phone: '+86-10-xxxxxxxx',
    email: 'liuyuzhou@buaa.edu.cn'
  },
  education: [
    {
      school: '北京大学',
      degree: '博士',
      major: '物理化学',
      year: '2010'
    }
  ],
  researchAreas: [
    '计算化学',
    '分子模拟',
    'AI驱动的化学研究'
  ],
  contract: {
    contractNo: '09855-01-2025-1',
    position: '蓝天青年学者（二级）',
    positionType: '专任教师岗位 - 蓝天学者岗位',
    department: '化学学院',
    startDate: '2025-09-01',
    endDate: '2030-08-31',
    duration: '5年',
    requirements: [
      '每学年主讲不少于1门课程，年均教学工作量不少于64学时',
      '聘期内完成不少于1项亮点业绩Ⅰ类或2项亮点业绩Ⅱ类',
      '年均科研经费不低于30万元（理科）',
      '聘期内引育不少于1名国家级人才'
    ],
    fileName: '09855_刘宇宙_化学学院_聘用合同-蓝天青年学者（二级）.pdf'
  }
}

export function LiuYuzhou() {
  const [detail, setDetail] = useState<PersonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'contract' | 'files'>('overview')
  const navigate = useNavigate()

  useEffect(() => {
    fetchDetail()
  }, [])

  const fetchDetail = async () => {
    try {
      const res = await fetch('/api/personal-info/liuyuzhou')
      const data = await res.json()
      if (data.success) {
        setDetail(data.detail)
      } else {
        setDetail(sampleDetail)
      }
    } catch (e) {
      setDetail(sampleDetail)
    } finally {
      setLoading(false)
    }
  }

  const goBack = () => {
    navigate('/personal')
  }

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    return date.toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'long',
      day: 'numeric'
    })
  }

  const calculateAge = (birthDate: string) => {
    const birth = new Date(birthDate)
    const today = new Date()
    let age = today.getFullYear() - birth.getFullYear()
    const monthDiff = today.getMonth() - birth.getMonth()
    if (monthDiff < 0 || (monthDiff === 0 && today.getDate() < birth.getDate())) {
      age--
    }
    return age
  }

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">加载中...</div>
      </div>
    )
  }

  if (!detail) {
    return (
      <div className="page-container">
        <div className="empty-state">
          <p>未找到人员信息</p>
          <button onClick={goBack} className="btn btn-primary">返回</button>
        </div>
      </div>
    )
  }

  return (
    <div className="page-container">
      {/* 返回按钮 */}
      <button 
        onClick={goBack}
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
          padding: '8px 16px',
          background: 'transparent',
          border: '1px solid #ddd',
          borderRadius: '8px',
          cursor: 'pointer',
          marginBottom: '20px'
        }}
      >
        <ChevronLeft size={20} />
        返回人员列表
      </button>

      {/* 个人信息头部 */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-start' }}>
          <div style={{
            width: '120px',
            height: '120px',
            borderRadius: '50%',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '60px',
            flexShrink: 0
          }}>
            👤
          </div>
          <div style={{ flex: 1 }}>
            <h2 style={{ margin: '0 0 8px 0', fontSize: '2rem' }}>{detail.name}</h2>
            <p style={{ margin: '0 0 16px 0', color: '#666', fontSize: '1.1rem' }}>
              {detail.currentPosition}
            </p>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '16px', color: '#888', fontSize: '0.9rem' }}>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Building size={16} />
                {detail.department}
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Calendar size={16} />
                {calculateAge(detail.birthDate)}岁 ({formatDate(detail.birthDate)})
              </span>
              <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <User size={16} />
                {detail.gender}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Tab导航 */}
      <div style={{ 
        display: 'flex', 
        gap: '12px', 
        marginBottom: '24px',
        borderBottom: '2px solid #e0e0e0',
        paddingBottom: '12px'
      }}>
        <button
          onClick={() => setActiveTab('overview')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'overview' ? '#667eea' : 'transparent',
            color: activeTab === 'overview' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'overview' ? '600' : '400'
          }}
        >
          基本信息
        </button>
        <button
          onClick={() => setActiveTab('contract')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'contract' ? '#667eea' : 'transparent',
            color: activeTab === 'contract' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'contract' ? '600' : '400'
          }}
        >
          聘用合同
        </button>
        <button
          onClick={() => setActiveTab('files')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'files' ? '#667eea' : 'transparent',
            color: activeTab === 'files' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'files' ? '600' : '400'
          }}
        >
          文件档案
        </button>
      </div>

      {/* Tab内容 */}
      {activeTab === 'overview' && (
        <>
          {/* 联系方式 */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Phone size={20} />
              联系方式
            </h3>
            <div style={{ display: 'grid', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Mail size={18} color="#667eea" />
                <span>{detail.contact.email}</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <Phone size={18} color="#667eea" />
                <span>{detail.contact.phone}</span>
              </div>
            </div>
          </div>

          {/* 教育背景 */}
          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <GraduationCap size={20} />
              教育背景
            </h3>
            {detail.education.map((edu, index) => (
              <div key={index} style={{ 
                padding: '16px', 
                background: '#f8f9fa', 
                borderRadius: '8px',
                marginBottom: '12px'
              }}>
                <div style={{ fontWeight: '600', marginBottom: '4px' }}>{edu.school}</div>
                <div style={{ color: '#666', fontSize: '0.9rem' }}>
                  {edu.degree} · {edu.major} · {edu.year}年毕业
                </div>
              </div>
            ))}
          </div>

          {/* 研究方向 */}
          <div className="card">
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Briefcase size={20} />
              研究方向
            </h3>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
              {detail.researchAreas.map((area, index) => (
                <span
                  key={index}
                  style={{
                    padding: '8px 16px',
                    background: '#e0e7ff',
                    color: '#667eea',
                    borderRadius: '20px',
                    fontSize: '0.9rem'
                  }}
                >
                  {area}
                </span>
              ))}
            </div>
          </div>
        </>
      )}

      {activeTab === 'contract' && (
        <div className="card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={20} />
            聘用合同详情
          </h3>
          
          <div style={{ 
            background: 'linear-gradient(135deg, #f0f4ff 0%, #e0e7ff 100%)',
            padding: '24px',
            borderRadius: '12px',
            marginBottom: '24px',
            border: '2px solid #667eea'
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'flex-start',
              marginBottom: '16px'
            }}>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '4px' }}>合同编号</div>
                <div style={{ fontSize: '1.3rem', fontWeight: '600', color: '#667eea' }}>
                  {detail.contract.contractNo}
                </div>
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '4px' }}>聘期时长</div>
                <div style={{ fontSize: '1.3rem', fontWeight: '600' }}>{detail.contract.duration}</div>
              </div>
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '4px' }}>岗位</div>
              <div style={{ fontSize: '1.1rem', fontWeight: '500' }}>{detail.contract.position}</div>
              <div style={{ fontSize: '0.9rem', color: '#888', marginTop: '4px' }}>{detail.contract.positionType}</div>
            </div>
            
            <div style={{ display: 'flex', gap: '24px', marginBottom: '16px' }}>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '4px' }}>开始日期</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Calendar size={16} />
                  {formatDate(detail.contract.startDate)}
                </div>
              </div>
              <div>
                <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '4px' }}>结束日期</div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Calendar size={16} />
                  {formatDate(detail.contract.endDate)}
                </div>
              </div>
            </div>
            
            <div style={{ marginBottom: '16px' }}>
              <div style={{ fontSize: '0.9rem', color: '#666', marginBottom: '8px' }}>所属部门</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <Building size={16} />
                {detail.contract.department}
              </div>
            </div>
          </div>

          <h4 style={{ marginBottom: '16px' }}>考核要求</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
            {detail.contract.requirements.map((req, index) => (
              <div
                key={index}
                style={{
                  padding: '16px',
                  background: '#f8f9fa',
                  borderRadius: '8px',
                  borderLeft: '4px solid #667eea',
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px'
                }}
              >
                <div style={{
                  width: '24px',
                  height: '24px',
                  borderRadius: '50%',
                  background: '#667eea',
                  color: 'white',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '0.8rem',
                  fontWeight: '600',
                  flexShrink: 0
                }}>
                  {index + 1}
                </div>
                <span>{req}</span>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '12px' }}>
            <button className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Download size={18} />
              下载合同PDF
            </button>
            <button className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} />
              查看电子版
            </button>
          </div>
        </div>
      )}

      {activeTab === 'files' && (
        <div>
          <div className="card" style={{ marginBottom: '24px' }}>
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Folder size={20} />
              个人档案 - 刘宇宙
            </h3>
            <ProfileFromFiles type="personal" name="刘宇宙" showTabs={true} />
          </div>
          
          <div className="card">
            <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Building size={20} />
              公司信息 - 和光智成
            </h3>
            <ProfileFromFiles type="company" name="和光智成" showTabs={true} />
          </div>
        </div>
      )}
    </div>
  )
}
