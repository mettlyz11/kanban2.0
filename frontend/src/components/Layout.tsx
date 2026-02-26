import { Link, useLocation, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import { useAuth } from '../hooks/useAuth'
import './Layout.css'

interface LayoutProps {
  children: React.ReactNode
}

const menuItems = [
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
  { path: '/calendar', icon: '📅', label: '日历' },
  { path: '/calc-tasks', icon: '🔢', label: '计算' },
  { path: '/molecules', icon: '🧪', label: '和光智成' },
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
  const { user, logout, changePassword, remainingTime } = useAuth()
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [showUpdates, setShowUpdates] = useState(false)
  const [showUserMenu, setShowUserMenu] = useState(false)
  const [showPasswordModal, setShowPasswordModal] = useState(false)
  const [passwordData, setPasswordData] = useState({ oldPassword: '', newPassword: '', confirmPassword: '' })
  const [passwordError, setPasswordError] = useState('')
  const [passwordSuccess, setPasswordSuccess] = useState('')

  // 格式化剩余时间
  const formatRemainingTime = () => {
    if (!remainingTime) return ''
    const minutes = Math.floor(remainingTime / 60000)
    const seconds = Math.floor((remainingTime % 60000) / 1000)
    if (minutes > 5) return '' // 超过5分钟不显示
    return `${minutes}:${seconds.toString().padStart(2, '0')}`
  }

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPasswordError('')
    setPasswordSuccess('')

    if (passwordData.newPassword !== passwordData.confirmPassword) {
      setPasswordError('两次输入的密码不一致')
      return
    }

    if (passwordData.newPassword.length < 6) {
      setPasswordError('新密码至少需要6个字符')
      return
    }

    const success = await changePassword(passwordData.oldPassword, passwordData.newPassword)
    if (success) {
      setPasswordSuccess('密码修改成功')
      setTimeout(() => {
        setShowPasswordModal(false)
        setPasswordData({ oldPassword: '', newPassword: '', confirmPassword: '' })
      }, 1500)
    } else {
      setPasswordError('旧密码错误')
    }
  }

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-brand">
          <button className="menu-toggle" onClick={() => setSidebarOpen(!sidebarOpen)}>☰</button>
          <Link to="/" style={{ textDecoration: 'none', color: 'inherit' }}>
            <h1>📊 看板系统 v2.0</h1>
          </Link>
        </div>
        <nav className="header-nav">
          <Link to="/" className="nav-link">看板</Link>
          <a href="https://kanban.mettlyz.com" className="nav-link" target="_blank" rel="noopener noreferrer">v1.0系统</a>
          <Link to="/pepi" className="nav-link">🤖 Pepi</Link>
          <button className="nav-link" onClick={() => setShowUpdates(true)}>📝 更新记录</button>
          <button className="chat-btn" onClick={() => navigate('/chat')}>💬 问Dudu</button>
          
          {/* 用户菜单 */}
          <div style={{ position: 'relative' }}>
            <button 
              className="nav-link" 
              onClick={() => setShowUserMenu(!showUserMenu)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <span>👤 {user?.username || '用户'}</span>
              {remainingTime && remainingTime < 5 * 60 * 1000 && (
                <span style={{ 
                  fontSize: '10px', 
                  background: remainingTime < 60 * 1000 ? '#ef4444' : '#f59e0b',
                  color: 'white',
                  padding: '2px 6px',
                  borderRadius: '10px'
                }}>
                  {formatRemainingTime()}
                </span>
              )}
            </button>
            
            {showUserMenu && (
              <div style={{
                position: 'absolute',
                top: '100%',
                right: 0,
                marginTop: '8px',
                background: 'white',
                borderRadius: '8px',
                boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                minWidth: '180px',
                zIndex: 1000,
                overflow: 'hidden'
              }}>
                <div style={{ padding: '12px 16px', borderBottom: '1px solid #eee' }}>
                  <div style={{ fontWeight: 600 }}>{user?.username || '用户'}</div>
                  <div style={{ fontSize: '12px', color: '#666' }}>{user?.role || '管理员'}</div>
                </div>
                <button 
                  onClick={() => { setShowUserMenu(false); setShowPasswordModal(true); }}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    textAlign: 'left',
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#f5f5f5'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  🔒 修改密码
                </button>
                <button 
                  onClick={handleLogout}
                  style={{
                    width: '100%',
                    padding: '12px 16px',
                    textAlign: 'left',
                    border: 'none',
                    background: 'none',
                    cursor: 'pointer',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    color: '#ef4444'
                  }}
                  onMouseEnter={e => e.currentTarget.style.background = '#fef2f2'}
                  onMouseLeave={e => e.currentTarget.style.background = 'none'}
                >
                  🚪 退出登录
                </button>
              </div>
            )}
          </div>
        </nav>
      </header>
      
      {/* 点击其他地方关闭用户菜单 */}
      {showUserMenu && (
        <div 
          style={{ position: 'fixed', inset: 0, zIndex: 999 }}
          onClick={() => setShowUserMenu(false)}
        />
      )}
      
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

      {/* 修改密码弹窗 */}
      {showPasswordModal && (
        <div className="modal-overlay" onClick={() => setShowPasswordModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '400px' }}>
            <h3>🔒 修改密码</h3>
            {passwordError && (
              <div style={{ padding: '12px', background: '#ffebee', color: '#c62828', borderRadius: '8px', marginBottom: '16px' }}>
                {passwordError}
              </div>
            )}
            {passwordSuccess && (
              <div style={{ padding: '12px', background: '#e8f5e9', color: '#2e7d32', borderRadius: '8px', marginBottom: '16px' }}>
                {passwordSuccess}
              </div>
            )}
            <form onSubmit={handleChangePassword}>
              <div style={{ marginBottom: '16px' }}>
                <label>当前密码</label>
                <input
                  type="password"
                  value={passwordData.oldPassword}
                  onChange={e => setPasswordData({...passwordData, oldPassword: e.target.value})}
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>新密码</label>
                <input
                  type="password"
                  value={passwordData.newPassword}
                  onChange={e => setPasswordData({...passwordData, newPassword: e.target.value})}
                  required
                  minLength={6}
                />
              </div>
              <div style={{ marginBottom: '24px' }}>
                <label>确认新密码</label>
                <input
                  type="password"
                  value={passwordData.confirmPassword}
                  onChange={e => setPasswordData({...passwordData, confirmPassword: e.target.value})}
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowPasswordModal(false)}>取消</button>
                <button type="submit" className="btn btn-primary">确认修改</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}
