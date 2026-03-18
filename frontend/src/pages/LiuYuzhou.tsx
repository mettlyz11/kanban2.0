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
  Clock,
  Award,
  BookOpen,
  FileCheck,
  Trophy
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

interface EducationItem {
  school: string
  degree: string
  major: string
  year: string
}

interface ResearchResult {
  title: string
  type: string
  date: string
  description: string
}

interface ProjectItem {
  name: string
  role: string
  period: string
  description: string
}

interface CertificateItem {
  name: string
  issuer: string
  date: string
  level: string
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
  education: EducationItem[]
  researchResults: ResearchResult[]
  projects: ProjectItem[]
  certificates: CertificateItem[]
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
    },
    {
      school: '北京大学',
      degree: '学士',
      major: '化学',
      year: '2005'
    }
  ],
  researchResults: [
    {
      title: 'AI 驱动的分子动力学模拟方法研究',
      type: '论文',
      date: '2024-03',
      description: '发表于 Nature Communications，影响因子 17.7'
    },
    {
      title: '基于机器学习的化学反应预测模型',
      type: '专利',
      date: '2023-11',
      description: '发明专利，专利号：ZL202310123456.7'
    },
    {
      title: '计算化学在药物设计中的应用',
      type: '著作',
      date: '2023-06',
      description: '科学出版社，ISBN: 978-7-03-012345-6'
    }
  ],
  projects: [
    {
      name: '国家自然科学基金面上项目',
      role: '项目负责人',
      period: '2024-2027',
      description: '基于 AI 的分子模拟方法研究，经费 180 万元'
    },
    {
      name: '国家重点研发计划课题',
      role: '课题负责人',
      period: '2023-2026',
      description: '新型催化材料的计算设计，经费 320 万元'
    },
    {
      name: '北京市自然科学基金重点项目',
      role: '项目负责人',
      period: '2022-2025',
      description: '机器学习辅助的化学反应机理研究，经费 80 万元'
    }
  ],
  certificates: [
    {
      name: '高等学校教师资格证书',
      issuer: '北京市教育委员会',
      date: '2021-09',
      level: '高等学校'
    },
    {
      name: '博士生导师资格证书',
      issuer: '北京航空航天大学',
      date: '2022-03',
      level: '博士'
    },
    {
      name: '国家自然科学基金评审专家',
      issuer: '国家自然科学基金委员会',
      date: '2023-01',
      level: '会评专家'
    }
  ],
researchAreas: [
    '计算化学',
    '分子模拟',
    'AI 驱动的化学研究',
    'AI + 新材料'
  ],
  entrepreneurship: {
    company: '北京深云智合科技有限公司',
    position: '创始人',
    location: '北京市昌平区',
    product: 'DeepChem 智能合成平台',
    description: '基于人工智能、计算化学、云平台和智能合成机器人，通过设计目标分子及其合成路径，探索催化剂、溶剂和温度等反应条件对结果的影响',
    achievements: [
      '一天完成研发人员在传统模式下10天的工作量',
      '助力千亿级别新材料产业研发及提速',
      '推动"AI+绿色创新"的多场景应用'
    ],
    mediaCoverage: {
      source: '中国青年报',
      date: '2025-03-21',
      title: '"人工智能+新材料"产业升温 北京为青年铺就发展新赛道',
      url: 'https://zqb.cyol.com/pc/content/202503/21/content_408652.html'
    }
  },
  contract: {
    contractNo: '09855-01-2025-1',
    position: '蓝天青年学者（二级）',
    positionType: '专任教师岗位 - 蓝天学者岗位',
    department: '化学学院',
    startDate: '2025-09-01',
    endDate: '2030-08-31',
    duration: '5 年',
    requirements: [
      '每学年主讲不少于 1 门课程，年均教学工作量不少于 64 学时',
      '聘期内完成不少于 1 项亮点业绩Ⅰ类或 2 项亮点业绩Ⅱ类',
      '年均科研经费不低于 30 万元（理科）',
      '聘期内引育不少于 1 名国家级人才'
    ],
    fileName: '09855_刘宇宙_化学学院_聘用合同 - 蓝天青年学者（二级）.pdf'
  }
}

export function LiuYuzhou() {
  const [detail, setDetail] = useState<PersonDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'overview' | 'education' | 'research' | 'projects' | 'certificates' | 'contract' | 'files'>('overview')
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

      {/* Tab 导航 */}
      <div style={{ 
        display: 'flex', 
        gap: '12px', 
        marginBottom: '24px',
        borderBottom: '2px solid #e0e0e0',
        paddingBottom: '12px',
        flexWrap: 'wrap'
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
          <User size={18} style={{ display: 'inline', marginRight: '4px' }} />
          基本信息
        </button>
        <button
          onClick={() => setActiveTab('education')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'education' ? '#667eea' : 'transparent',
            color: activeTab === 'education' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'education' ? '600' : '400'
          }}
        >
          <GraduationCap size={18} style={{ display: 'inline', marginRight: '4px' }} />
          教育背景
        </button>
        <button
          onClick={() => setActiveTab('research')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'research' ? '#667eea' : 'transparent',
            color: activeTab === 'research' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'research' ? '600' : '400'
          }}
        >
          <BookOpen size={18} style={{ display: 'inline', marginRight: '4px' }} />
          研究成果
        </button>
        <button
          onClick={() => setActiveTab('projects')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'projects' ? '#667eea' : 'transparent',
            color: activeTab === 'projects' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'projects' ? '600' : '400'
          }}
        >
          <Briefcase size={18} style={{ display: 'inline', marginRight: '4px' }} />
          项目经历
        </button>
        <button
          onClick={() => setActiveTab('certificates')}
          style={{
            padding: '12px 24px',
            background: activeTab === 'certificates' ? '#667eea' : 'transparent',
            color: activeTab === 'certificates' ? 'white' : '#666',
            border: 'none',
            borderRadius: '8px',
            cursor: 'pointer',
            fontWeight: activeTab === 'certificates' ? '600' : '400'
          }}
        >
          <Award size={18} style={{ display: 'inline', marginRight: '4px' }} />
          技能证书
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
          <FileText size={18} style={{ display: 'inline', marginRight: '4px' }} />
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
          <Folder size={18} style={{ display: 'inline', marginRight: '4px' }} />
          文件档案
        </button>
      </div>

      {/* Tab 内容 */}
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

      {/* 教育背景 Tab */}
      {activeTab === 'education' && (
        <div className="card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <GraduationCap size={20} />
            教育背景
          </h3>
          {detail.education.map((edu, index) => (
            <div key={index} style={{ 
              padding: '20px', 
              background: '#f8f9fa', 
              borderRadius: '8px',
              marginBottom: '16px',
              borderLeft: '4px solid #667eea'
            }}>
              <div style={{ fontWeight: '600', fontSize: '1.1rem', marginBottom: '8px' }}>{edu.school}</div>
              <div style={{ color: '#666', fontSize: '0.95rem', display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
                <span><strong>学位：</strong>{edu.degree}</span>
                <span><strong>专业：</strong>{edu.major}</span>
                <span><strong>毕业年份：</strong>{edu.year}年</span>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 研究成果 Tab */}
      {activeTab === 'research' && (
        <div className="card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <BookOpen size={20} />
            研究成果
          </h3>
          {detail.researchResults.map((result, index) => (
            <div key={index} style={{ 
              padding: '20px', 
              background: '#f8f9fa', 
              borderRadius: '8px',
              marginBottom: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                <div>
                  <span style={{
                    padding: '4px 12px',
                    background: '#667eea',
                    color: 'white',
                    borderRadius: '4px',
                    fontSize: '0.8rem',
                    marginRight: '8px'
                  }}>
                    {result.type}
                  </span>
                  <span style={{ color: '#999', fontSize: '0.9rem' }}>{result.date}</span>
                </div>
              </div>
              <div style={{ fontWeight: '600', fontSize: '1.1rem', marginBottom: '8px' }}>{result.title}</div>
              <div style={{ color: '#666' }}>{result.description}</div>
            </div>
          ))}
        </div>
      )}

      {/* 项目经历 Tab */}
      {activeTab === 'projects' && (
        <div className="card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Briefcase size={20} />
            项目经历
          </h3>
          {detail.projects.map((project, index) => (
            <div key={index} style={{ 
              padding: '20px', 
              background: '#f8f9fa', 
              borderRadius: '8px',
              marginBottom: '16px',
              borderLeft: '4px solid #764ba2'
            }}>
              <div style={{ fontWeight: '600', fontSize: '1.1rem', marginBottom: '8px' }}>{project.name}</div>
              <div style={{ display: 'flex', gap: '16px', color: '#666', fontSize: '0.95rem', marginBottom: '12px', flexWrap: 'wrap' }}>
                <span><strong>角色：</strong>{project.role}</span>
                <span><strong>周期：</strong>{project.period}</span>
              </div>
              <div style={{ color: '#888' }}>{project.description}</div>
            </div>
          ))}
        </div>
      )}

      {/* 技能证书 Tab */}
      {activeTab === 'certificates' && (
        <div className="card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Award size={20} />
            技能证书
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {detail.certificates.map((cert, index) => (
              <div key={index} style={{ 
                padding: '20px', 
                background: 'linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%)', 
                borderRadius: '12px',
                border: '1px solid #dee2e6'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '12px' }}>
                  <div style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: '50%',
                    background: '#667eea',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'white'
                  }}>
                    <Award size={20} />
                  </div>
                  <div>
                    <div style={{ fontWeight: '600', fontSize: '0.9rem' }}>{cert.level}</div>
                    <div style={{ color: '#999', fontSize: '0.85rem' }}>{cert.date}</div>
                  </div>
                </div>
                <div style={{ fontWeight: '600', fontSize: '1.05rem', marginBottom: '8px' }}>{cert.name}</div>
                <div style={{ color: '#666', fontSize: '0.9rem' }}>{cert.issuer}</div>
              </div>
            ))}
          </div>
        </div>
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
              下载合同 PDF
            </button>
            <button className="btn btn-secondary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <FileText size={18} />
              查看电子版
            </button>
          </div>
        </div>
      )}

      {activeTab === 'files' && (
        <div className="card">
          <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Folder size={20} />
            个人档案 - 刘宇宙
          </h3>
          <ProfileFromFiles type="personal" name="刘宇宙" showTabs={true} />
        </div>
      )}
    </div>
  )
}
