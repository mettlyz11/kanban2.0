import { useState } from 'react'
import { Globe, Code, Database, Server, Layout, ChevronDown, ChevronRight, Building2 } from 'lucide-react'

interface SectionProps {
  title: string
  icon: React.ReactNode
  children: React.ReactNode
  defaultOpen?: boolean
}

function Section({ title, icon, children, defaultOpen = false }: SectionProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen)
  
  return (
    <div style={{ marginBottom: '24px', background: 'white', borderRadius: '12px', boxShadow: '0 2px 8px rgba(0,0,0,0.08)' }}>
      <div 
        style={{ 
          padding: '16px 20px', 
          display: 'flex', 
          alignItems: 'center', 
          justifyContent: 'space-between',
          cursor: 'pointer',
          borderBottom: isOpen ? '1px solid #eee' : 'none'
        }}
        onClick={() => setIsOpen(!isOpen)}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          {icon}
          <h3 style={{ margin: 0, fontSize: '1.1rem', fontWeight: 600 }}>{title}</h3>
        </div>
        {isOpen ? <ChevronDown size={20} /> : <ChevronRight size={20} />}
      </div>
      {isOpen && (
        <div style={{ padding: '20px' }}>
          {children}
        </div>
      )}
    </div>
  )
}

export function ProjectDesign() {
  return (
    <div style={{ padding: '20px', maxWidth: '1200px' }}>
      <div className="page-header" style={{ marginBottom: '32px' }}>
        <h2 className="page-title">📐 项目设计</h2>
        <p style={{ color: '#666', marginTop: '8px' }}>
          T109过渡态计算平台与Helight官网架构设计文档
        </p>
      </div>

      {/* T109 架构设计 */}
      <Section title="T109 过渡态计算平台 - 架构设计" icon={<Building2 size={24} color="#00A896" />} defaultOpen={true}>
        <div style={{ display: 'grid', gap: '20px' }}>
          {/* 技术架构图 */}
          <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px' }}>
            <h4 style={{ marginBottom: '16px', color: '#333' }}>技术架构</h4>
            <pre style={{ 
              background: '#1a1a2e', 
              color: '#00ff88', 
              padding: '16px', 
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '13px',
              lineHeight: 1.6
            }}>
{`┌─────────────────────────────────────────────────────────────┐
│                      用户层 (User Layer)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │   Web界面     │  │   API接口    │  │   CLI工具    │       │
│  │  (React)     │  │ (FastAPI)   │  │  (Python)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────┐
│                   服务层 (Service Layer)                     │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              FastAPI + SQLAlchemy 2.0                │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐       │   │
│  │  │ 任务管理    │ │ 引擎调度    │ │ 结果解析    │       │   │
│  │  │  Task Queue│ │   Engine   │ │   Parser   │       │   │
│  │  └────────────┘ └────────────┘ └────────────┘       │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                  计算引擎层 (Engine Layer)                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │   PSI4   │  │ Gaussian │  │   ORCA   │  │  MACE    │   │
│  │ (主要)   │  │ (支持)   │  │ (支持)   │  │ (新增)   │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘`}
            </pre>
          </div>

          {/* 技术栈 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div style={{ background: '#e3f2fd', padding: '16px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Code size={18} color="#1976d2" />
                <strong>后端框架</strong>
              </div>
              <div style={{ fontSize: '14px', color: '#555' }}>
                FastAPI 0.110+<br/>
                SQLAlchemy 2.0<br/>
                Pydantic v2
              </div>
            </div>
            <div style={{ background: '#f3e5f5', padding: '16px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Database size={18} color="#7b1fa2" />
                <strong>数据库</strong>
              </div>
              <div style={{ fontSize: '14px', color: '#555' }}>
                PostgreSQL 15<br/>
                Redis 7<br/>
                异步连接
              </div>
            </div>
            <div style={{ background: '#e8f5e9', padding: '16px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Server size={18} color="#2e7d32" />
                <strong>计算引擎</strong>
              </div>
              <div style={{ fontSize: '14px', color: '#555' }}>
                PSI4 (主要)<br/>
                MACE-POLAR<br/>
                Gaussian/ORCA
              </div>
            </div>
            <div style={{ background: '#fff3e0', padding: '16px', borderRadius: '8px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
                <Layout size={18} color="#e65100" />
                <strong>前端</strong>
              </div>
              <div style={{ fontSize: '14px', color: '#555' }}>
                React 18<br/>
                TypeScript<br/>
                Three.js
              </div>
            </div>
          </div>

          {/* 核心功能 */}
          <div>
            <h4 style={{ marginBottom: '12px', color: '#333' }}>核心功能模块</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '12px' }}>
              {[
                { name: '分子编辑器', status: '✅ 完成', desc: 'XYZ/SMILES输入, 3D可视化' },
                { name: '计算任务管理', status: '✅ 完成', desc: '几何优化、频率、过渡态' },
                { name: '引擎管理', status: '✅ 完成', desc: 'PSI4/Gaussian/ORCA/PySCF' },
                { name: 'MACE-POLAR', status: '🚧 开发中', desc: '神经网络势函数' },
                { name: 'Committor采样', status: '🚧 开发中', desc: '增强采样方法' },
                { name: '用户系统', status: '🚧 开发中', desc: 'JWT认证、权限管理' },
              ].map((item, i) => (
                <div key={i} style={{ background: '#f5f5f5', padding: '12px', borderRadius: '8px', borderLeft: '4px solid #00A896' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <strong>{item.name}</strong>
                    <span style={{ fontSize: '12px', color: item.status.includes('✅') ? '#2e7d32' : '#f57c00' }}>{item.status}</span>
                  </div>
                  <div style={{ fontSize: '13px', color: '#666' }}>{item.desc}</div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Section>

      {/* Helight 网站设计 */}
      <Section title="Helight 官网 - 架构设计" icon={<Globe size={24} color="#FFB800" />} defaultOpen={true}>
        <div style={{ display: 'grid', gap: '20px' }}>
          {/* 网站架构 */}
          <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '8px' }}>
            <h4 style={{ marginBottom: '16px', color: '#333' }}>网站架构</h4>
            <pre style={{ 
              background: '#1a1a2e', 
              color: '#ffb800', 
              padding: '16px', 
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '13px',
              lineHeight: 1.6
            }}>
{`用户访问
    ↓
[阿里云 CDN] (全球加速 + 静态缓存)
    ↓
[阿里云 SLB] (负载均衡)
    ↓
[阿里云 ECS/ACK] (Kubernetes集群)
    - 前端: Next.js (SSR)
    - 后端: FastAPI + Python
    - 计算: PSI4/Gaussian容器
    ↓
[阿里云 RDS] (PostgreSQL)
[阿里云 OSS] (文件存储)
[阿里云 NAS] (共享存储)`}
            </pre>
          </div>

          {/* 页面规划 */}
          <div>
            <h4 style={{ marginBottom: '12px', color: '#333' }}>页面规划</h4>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
              {[
                { page: '首页', status: '✅', path: '/', desc: 'Hero区域、产品展示、统计数据' },
                { page: 'T109产品', status: '🚧', path: '/products/t109/', desc: '功能介绍、定价、演示' },
                { page: '玄基产品', status: '📝', path: '/products/xuanlab/', desc: '高通量实验机器人' },
                { page: '蕴算产品', status: '📝', path: '/products/yunsuan/', desc: 'AI分子设计' },
                { page: '案例', status: '📝', path: '/cases/', desc: '客户成功案例' },
                { page: '关于我们', status: '📝', path: '/about/', desc: '公司介绍、团队' },
              ].map((item, i) => (
                <div key={i} style={{ background: '#f5f5f5', padding: '12px', borderRadius: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '4px' }}>
                    <strong>{item.page}</strong>
                    <span>{item.status}</span>
                  </div>
                  <div style={{ fontSize: '12px', color: '#888', marginBottom: '4px' }}>{item.path}</div>
                  <div style={{ fontSize: '13px', color: '#666' }}>{item.desc}</div>
                </div>
              ))}
            </div>
          </div>

          {/* 技术栈 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            <div style={{ background: '#e3f2fd', padding: '16px', borderRadius: '8px' }}>
              <strong>前端框架</strong>
              <div style={{ fontSize: '14px', color: '#555', marginTop: '8px' }}>
                Next.js 14<br/>
                React 18 + TypeScript<br/>
                Tailwind CSS
              </div>
            </div>
            <div style={{ background: '#f3e5f5', padding: '16px', borderRadius: '8px' }}>
              <strong>部署</strong>
              <div style={{ fontSize: '14px', color: '#555', marginTop: '8px' }}>
                阿里云CDN<br/>
                阿里云OSS<br/>
                ECS/ACK
              </div>
            </div>
            <div style={{ background: '#e8f5e9', padding: '16px', borderRadius: '8px' }}>
              <strong>品牌设计</strong>
              <div style={{ fontSize: '14px', color: '#555', marginTop: '8px' }}>
                主色: #00A896 (科技青)<br/>
                强调: #FFB800 (智慧金)<br/>
                Slogan: 智算分子，光耀未来
              </div>
            </div>
          </div>
        </div>
      </Section>

      {/* 实施时间表 */}
      <Section title="实施时间表" icon={<Code size={24} color="#667eea" />}>
        <div style={{ overflow: 'auto' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f5f5f5' }}>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>时间</th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>里程碑</th>
                <th style={{ padding: '12px', textAlign: 'left', borderBottom: '2px solid #ddd' }}>交付物</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>Week 1-2</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>T109基础架构</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>FastAPI + PostgreSQL</td>
              </tr>
              <tr>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>Week 3-4</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>MACE-POLAR集成</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>神经网络计算</td>
              </tr>
              <tr>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>Week 5-7</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>用户系统/前端</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>JWT + React</td>
              </tr>
              <tr>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>并行</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>Helight网站</td>
                <td style={{ padding: '12px', borderBottom: '1px solid #eee' }}>Next.js官网</td>
              </tr>
            </tbody>
          </table>
        </div>
      </Section>

      {/* 相关文档链接 */}
      <div style={{ background: '#f0f4ff', padding: '20px', borderRadius: '12px', marginTop: '24px' }}>
        <h4 style={{ marginBottom: '12px', color: '#333' }}>📎 相关文档</h4>
        <div style={{ display: 'grid', gap: '8px' }}>
          <div>• 详细实现方案: <code>/Users/mettlyz/.openclaw/workspace/IMPLEMENTATION_PLAN.md</code></div>
          <div>• 架构框架文档: <code>/Users/mettlyz/.openclaw/workspace/T109_HELIGHT_FRAMEWORK.md</code></div>
          <div>• Helight设计文档: <code>/Users/mettlyz/.openclaw/workspace/helight-website/DESIGN.md</code></div>
          <div>• 看板项目卡片: <a href="/projects" style={{ color: '#667eea' }}>P-ARCH-001 T109 & Helight 架构设计</a></div>
        </div>
      </div>
    </div>
  )
}

export default ProjectDesign
