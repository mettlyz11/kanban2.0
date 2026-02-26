import { Link, useLocation } from 'react-router-dom'
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
  { path: '/chat', icon: '💬', label: '聊天' },
  { path: '/emails', icon: '📧', label: '邮件' },
]

export function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)

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
          <button className="chat-btn">💬 问Dudu</button>
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
    </div>
  )
}
