import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

const menuItems = [
  { path: '/', icon: '📊', label: '总览' },
  { path: '/projects', icon: '📁', label: '项目' },
  { path: '/tasks', icon: '✅', label: '任务' },
  { path: '/brain', icon: '🧠', label: '知识大脑' },
  { path: '/cron', icon: '⏰', label: '定时任务' },
  { path: '/stocks', icon: '📈', label: '资产' },
  { path: '/review', icon: '👁️', label: '审核' },
  { path: '/skills', icon: '🛠️', label: '技能' },
  { path: '/llm-configs', icon: '🤖', label: '大模型配置' },
  { path: '/daily-reviews', icon: '🔄', label: '每日复盘' },
  { path: '/meetings', icon: '📝', label: '会议纪要' },
  { path: '/research', icon: '📚', label: '调研记录' },
  { path: '/architecture', icon: '🏗️', label: '架构图' },
  { path: '/resources', icon: '📦', label: '资源库' },
  { path: '/calc-tasks', icon: '🔢', label: '计算' },
  { path: '/molecules', icon: '🧪', label: '分子' },
  { path: '/reactions', icon: '⚗️', label: '反应' },
  { path: '/emails', icon: '📧', label: '邮件' },
]

// 更新记录
const updateRecords = [
  { date: '2026-02-26', version: 'v2.1.0', changes: ['新增系统监控历史数据', '新增访问统计详情', '优化移动端适配', '修复计算任务页面'] },
  { date: '2026-02-26', version: 'v2.0.5', changes: ['修复邮件API错误', '修复localhost:8086硬编码问题', '新增邮件回复和抄送功能'] },
  { date: '2026-02-26', version: 'v2.0.4', changes: ['新增架构图页面', '新增资源库、调研记录、会议纪要页面', '新增大模型配置页面'] },
  { date: '2026-02-26', version: 'v2.0.3', changes: ['新增Pepi数字员工页面', '新增系统监控、访问统计、版本记录页面', '修复聊天功能'] },
  { date: '2026-02-26', version: 'v2.0.2', changes: ['新增登录保护', '修复知识大脑API', '新增技能库页面'] },
  { date: '2026-02-26', version: 'v2.0.1', changes: ['修复Cron任务统计', '新增资产、审核页面', '修复React路由'] },
  { date: '2026-02-26', version: 'v2.0.0', changes: ['看板2.0正式发布', 'React + Flask架构', 'Cloudflare部署', '所有功能迁移完成'] },
]

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const navigate = useNavigate()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showUpdates, setShowUpdates] = useState(false)

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <button className="menu-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <h1>📊 看板系统 v2.0</h1>
        </div>
        <nav className="header-nav">
          <Link to="/" className="nav-link">看板</Link>
          <a href="https://kanban.mettlyz.com" className="nav-link" target="_blank">v1.0系统</a>
          <button className="nav-link" onClick={() => setShowUpdates(true)}>📝 更新记录</button>
          <button className="chat-btn" onClick={() => navigate('/chat')}>💬 问Dudu</button>
        </nav>
      </header>
      <div className="app-body">
        <aside className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
          <nav className="sidebar-nav">
            {menuItems.map(item => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-item ${location.pathname === item.path ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                {sidebarOpen && <span className="nav-label">{item.label}</span>}
              </Link>
            ))}
          </nav>
        </aside>
        <main className="main-content">{children}</main>
      </div>

      {/* 更新记录弹窗 */}
      {showUpdates && (
        <div className="modal-overlay" onClick={() => setShowUpdates(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px', maxHeight: '80vh', overflow: 'auto' }}>
            <h3>📝 更新记录</h3>
            <div style={{ marginTop: '16px' }}>
              {updateRecords.map((record, i) => (
                <div key={i} style={{ 
                  marginBottom: '16px', 
                  padding: '12px', 
                  background: '#f8f9fa', 
                  borderRadius: '8px',
                  borderLeft: '4px solid #667eea'
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                    <strong>{record.version}</strong>
                    <span style={{ color: '#999', fontSize: '0.85rem' }}>{record.date}</span>
                  </div>
                  <ul style={{ margin: 0, paddingLeft: '20px', fontSize: '0.9rem' }}>
                    {record.changes.map((change, j) => (
                      <li key={j} style={{ marginBottom: '4px' }}>{change}</li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowUpdates(false)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
