import { useState, useEffect } from 'react'

// 图标组件
const SyncIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M21.5 2v6h-6M2.5 22v-6h6M2 11.5a10 10 0 0 1 18.8-4.3M22 12.5a10 10 0 0 1-18.8 4.3"/>
  </svg>
)

const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <line x1="12" y1="5" x2="12" y2="19"/>
    <line x1="5" y1="12" x2="19" y2="12"/>
  </svg>
)

const TrashIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <polyline points="3 6 5 6 21 6"/>
    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
  </svg>
)

export function CalendarSettings() {
  const [accounts, setAccounts] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [syncing, setSyncing] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [formData, setFormData] = useState({
    name: '',
    account_type: 'caldav',
    server_url: '',
    username: '',
    password: '',
    calendar_name: ''
  })

  useEffect(() => {
    loadAccounts()
  }, [])

  const loadAccounts = async () => {
    try {
      const res = await fetch('/api/calendar/accounts')
      const data = await res.json()
      if (data.success) setAccounts(data.accounts || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSync = async () => {
    setSyncing(true)
    try {
      const res = await fetch('/api/calendar/sync', { method: 'POST' })
      const data = await res.json()
      if (data.success) {
        alert(`同步完成！共同步 ${data.results?.reduce((acc: number, r: any) => acc + (r.synced_events || 0), 0)} 个事件`)
        loadAccounts()
      } else {
        alert('同步失败: ' + data.error)
      }
    } catch (e) {
      alert('同步出错')
    } finally {
      setSyncing(false)
    }
  }

  const handleAddAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      const res = await fetch('/api/calendar/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      const data = await res.json()
      if (data.success) {
        setShowAddModal(false)
        setFormData({ name: '', account_type: 'caldav', server_url: '', username: '', password: '', calendar_name: '' })
        loadAccounts()
      }
    } catch (e) {
      console.error(e)
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📅 日历同步设置</h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
            <PlusIcon /> 添加账户
          </button>
          <button className="btn btn-success" onClick={handleSync} disabled={syncing}>
            <SyncIcon /> {syncing ? '同步中...' : '立即同步'}
          </button>
        </div>
      </div>

      {/* 账户列表 */}
      <div className="card">
        <div className="card-header">
          <h5>CalDAV账户 ({accounts.length})</h5>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>类型</th>
                <th>服务器</th>
                <th>用户名</th>
                <th>状态</th>
                <th>最后同步</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {accounts.length === 0 ? (
                <tr>
                  <td colSpan={7} className="empty-state">
                    <div>暂无CalDAV账户</div>
                    <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '8px' }}>
                      点击"添加账户"配置iCloud/Google/Outlook日历同步
                    </div>
                  </td>
                </tr>
              ) : (
                accounts.map((account: any) => (
                  <tr key={account.id}>
                    <td><strong>{account.name}</strong></td>
                    <td>
                      <span className="badge badge-blue">{account.account_type?.toUpperCase()}</span>
                    </td>
                    <td style={{ fontSize: '0.85rem', maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {account.server_url}
                    </td>
                    <td>{account.username}</td>
                    <td>
                      <span className={`badge ${account.sync_enabled ? 'badge-green' : 'badge-gray'}`}>
                        {account.sync_enabled ? '已启用' : '已禁用'}
                      </span>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>
                      {account.last_sync_at ? new Date(account.last_sync_at).toLocaleString('zh-CN') : '从未'}
                    </td>
                    <td>
                      <button className="btn btn-sm btn-danger">
                        <TrashIcon />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 配置说明 */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <h5>📖 配置指南</h5>
        </div>
        <div style={{ padding: '20px' }}>
          <h6 style={{ marginBottom: '12px' }}>支持的日历服务：</h6>
          <ul style={{ lineHeight: '2', paddingLeft: '20px', marginBottom: '20px' }}>
            <li><strong>iCloud日历</strong> - 使用App专用密码</li>
            <li><strong>Google日历</strong> - 启用CalDAV API</li>
            <li><strong>Outlook.com</strong> - 支持CalDAV协议</li>
            <li><strong>自建CalDAV服务器</strong> - 如Nextcloud、Radicale</li>
          </ul>
          
          <h6 style={{ marginBottom: '12px' }}>iCloud配置示例：</h6>
          <div style={{ background: '#f8f9fa', padding: '16px', borderRadius: '8px', fontFamily: 'monospace', fontSize: '0.85rem' }}>
            <div>服务器: https://caldav.icloud.com</div>
            <div>用户名: your@icloud.com</div>
            <div>密码: [App专用密码]</div>
          </div>
        </div>
      </div>

      {/* 添加账户弹窗 */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h3><PlusIcon /> 添加CalDAV账户</h3>
            <form onSubmit={handleAddAccount} style={{ marginTop: '16px' }}>
              <div style={{ marginBottom: '16px' }}>
                <label>账户名称 *</label>
                <input
                  type="text"
                  value={formData.name}
                  onChange={e => setFormData({...formData, name: e.target.value})}
                  placeholder="例如：我的iCloud"
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>账户类型</label>
                <select
                  value={formData.account_type}
                  onChange={e => setFormData({...formData, account_type: e.target.value})}
                >
                  <option value="caldav">CalDAV (通用)</option>
                  <option value="icloud">iCloud</option>
                  <option value="google">Google</option>
                  <option value="outlook">Outlook</option>
                </select>
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>服务器地址 *</label>
                <input
                  type="url"
                  value={formData.server_url}
                  onChange={e => setFormData({...formData, server_url: e.target.value})}
                  placeholder="https://caldav.icloud.com"
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>用户名 *</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={e => setFormData({...formData, username: e.target.value})}
                  placeholder="your@email.com"
                  required
                />
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label>密码 *</label>
                <input
                  type="password"
                  value={formData.password}
                  onChange={e => setFormData({...formData, password: e.target.value})}
                  placeholder="密码或App专用密码"
                  required
                />
              </div>
              <div style={{ marginBottom: '24px' }}>
                <label>日历名称（可选）</label>
                <input
                  type="text"
                  value={formData.calendar_name}
                  onChange={e => setFormData({...formData, calendar_name: e.target.value})}
                  placeholder="工作 / 个人 / 家庭"
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>取消</button>
                <button type="submit" className="btn btn-success">添加账户</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

export default CalendarSettings
