import { useState, useEffect } from 'react'

export function Architecture() {
  const [, setArchitecture] = useState<any>(null)
  const [tableCounts, setTableCounts] = useState<Record<string, number>>({})
  const [loading, setLoading] = useState(true)
  const [selectedModule, setSelectedModule] = useState<string | null>(null)
  const [selectedTable, setSelectedTable] = useState<string | null>(null)
  const [zoom, setZoom] = useState(1)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const res = await fetch('/api/architecture')
      const data = await res.json()
      if (data.success) {
        setArchitecture(data.architecture)
      }
      
      // 加载表统计
      const tablesRes = await fetch('/api/table-counts')
      const tablesData = await tablesRes.json()
      if (tablesData.success) {
        setTableCounts(tablesData.counts || {})
      }
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const modules = [
    { id: 'dashboard', name: 'Dashboard', icon: '📊', desc: '项目/任务/邮件综合管理面板', color: '#667eea' },
    { id: 'stocks', name: '股票模块', icon: '📈', desc: '投资管理、交易记录、资产分析', color: '#11998e' },
    { id: 'chemistry', name: '化学模块', icon: '🧪', desc: '分子库、反应管理、计算任务', color: '#4facfe' },
    { id: 'skills', name: '技能模块', icon: '🔧', desc: '技能管理、Agent配置、调用统计', color: '#f7b733' },
    { id: 'entities', name: '实体档案', icon: '📇', desc: '人物/组织档案、联系人关联', color: '#6c757d' },
    { id: 'emails', name: '邮件系统', icon: '📧', desc: 'Mutt集成、邮件管理、自动回复', color: '#dc3545' },
    { id: 'knowledge', name: '知识大脑', icon: '🧠', desc: '知识网络、实体关联、智能推荐', color: '#9c27b0' },
    { id: 'cron', name: 'Cron任务', icon: '⏰', desc: '定时任务、调度管理、执行监控', color: '#495057' },
    { id: 'resources', name: '资源库', icon: '📚', desc: '文献资料、网站链接、学习文档', color: '#3f51b5' },
    { id: 'research', name: '调研记录', icon: '🔍', desc: '市场调研、技术调研、竞品分析', color: '#009688' },
    { id: 'llm', name: '大模型配置', icon: '🤖', desc: 'LLM管理、Token统计、模型配置', color: '#ec4899' },
    { id: 'system', name: '系统监控', icon: '💻', desc: 'CPU/内存监控、健康检查、日志管理', color: '#ff6b6b' },
    { id: 'chat', name: '聊天系统', icon: '💬', desc: '消息记录、聊天历史、多渠道集成', color: '#00bcd4' },
    { id: 'calendar', name: '日历管理', icon: '📅', desc: '日程安排、事件提醒、CalDAV同步', color: '#8bc34a' },
    { id: 'security', name: '安全管理', icon: '🛡️', desc: '访问控制、IP封锁、安全审计', color: '#795548' },
  ]

  const tables = [
    { name: 'chat_messages', desc: '聊天消息记录' },
    { name: 'chemical_elements', desc: '化学元素表' },
    { name: 'entities', desc: '实体档案表' },
    { name: 'emails', desc: '邮件数据表' },
    { name: 'projects', desc: '项目信息表' },
    { name: 'tasks', desc: '任务信息表' },
    { name: 'stocks', desc: '股票持仓表' },
    { name: 'skills', desc: '技能表' },
    { name: 'llm_configs', desc: '大模型配置表' },
    { name: 'version_logs', desc: '版本日志表' },
    { name: 'molecules', desc: '分子数据表' },
    { name: 'reactions', desc: '化学反应表' },
    { name: 'calc_tasks', desc: '计算任务表' },
    { name: 'stock_transactions', desc: '股票交易记录' },
    { name: 'system_metrics', desc: '系统监控表' },
  ]

  const files = [
    { name: 'SOUL.md', desc: '身份定义', color: '#1976d2' },
    { name: 'USER.md', desc: '用户档案', color: '#388e3c' },
    { name: 'AGENTS.md', desc: '执行准则', color: '#c2185b' },
    { name: 'standards.md', desc: '标准规范', color: '#9c27b0' },
    { name: 'MEMORY.md', desc: '长期记忆', color: '#00796b' },
    { name: 'HEARTBEAT.md', desc: '定时检查', color: '#fbc02d' },
  ]

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🏗️ 架构图 (T019)</h2>
      </div>

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card blue">
          <div className="stat-icon">📦</div>
          <div className="stat-info">
            <h3>15+</h3>
            <p>系统模块</p>
          </div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon">🗄️</div>
          <div className="stat-info">
            <h3>49</h3>
            <p>数据库表</p>
          </div>
        </div>
        <div className="stat-card orange">
          <div className="stat-icon">💻</div>
          <div className="stat-info">
            <h3>5000+</h3>
            <p>代码行数</p>
          </div>
        </div>
      </div>

      {/* 架构流程图 */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h5>🔄 Dudu工作流程架构</h5>
        </div>
        <div style={{ padding: '20px', overflow: 'auto' }}>
          <div style={{ 
            transform: `scale(${zoom})`, 
            transformOrigin: 'top left',
            transition: 'transform 0.3s',
            minWidth: '800px'
          }}>
            <svg viewBox="0 0 1000 400" style={{ width: '100%', maxWidth: '1000px' }}>
              {/* 输入与配置层 */}
              <rect x="50" y="50" width="900" height="120" fill="#f8f9fa" stroke="#dee2e6" strokeWidth="2" rx="8" />
              <text x="70" y="80" fontSize="16" fontWeight="bold" fill="#495057">输入与配置层</text>
              
              {/* 输入节点 */}
              <rect x="80" y="100" width="120" height="50" fill="#e3f2fd" stroke="#1976d2" strokeWidth="2" rx="4" />
              <text x="140" y="130" textAnchor="middle" fontSize="14" fill="#1976d2">用户输入</text>
              
              <rect x="220" y="100" width="120" height="50" fill="#fff3e0" stroke="#f57c00" strokeWidth="2" rx="4" />
              <text x="280" y="125" textAnchor="middle" fontSize="12" fill="#f57c00">SOUL.md</text>
              <text x="280" y="140" textAnchor="middle" fontSize="10" fill="#f57c00">身份定义</text>
              
              <rect x="360" y="100" width="120" height="50" fill="#e8f5e9" stroke="#388e3c" strokeWidth="2" rx="4" />
              <text x="420" y="125" textAnchor="middle" fontSize="12" fill="#388e3c">USER.md</text>
              <text x="420" y="140" textAnchor="middle" fontSize="10" fill="#388e3c">用户档案</text>
              
              <rect x="500" y="100" width="120" height="50" fill="#fce4ec" stroke="#c2185b" strokeWidth="2" rx="4" />
              <text x="560" y="125" textAnchor="middle" fontSize="12" fill="#c2185b">AGENTS.md</text>
              <text x="560" y="140" textAnchor="middle" fontSize="10" fill="#c2185b">执行准则</text>
              
              <rect x="640" y="100" width="120" height="50" fill="#f3e5f5" stroke="#9c27b0" strokeWidth="2" rx="4" />
              <text x="700" y="125" textAnchor="middle" fontSize="12" fill="#9c27b0">standards.md</text>
              <text x="700" y="140" textAnchor="middle" fontSize="10" fill="#9c27b0">标准规范</text>

              {/* 任务执行 */}
              <rect x="780" y="100" width="120" height="50" fill="#f3e5f5" stroke="#7b1fa2" strokeWidth="2" rx="4" />
              <text x="840" y="130" textAnchor="middle" fontSize="14" fill="#7b1fa2">任务执行</text>

              {/* 执行与记忆层 */}
              <rect x="50" y="200" width="900" height="180" fill="#f8f9fa" stroke="#dee2e6" strokeWidth="2" rx="8" />
              <text x="70" y="230" fontSize="16" fontWeight="bold" fill="#495057">执行与记忆层</text>
              
              <rect x="200" y="260" width="150" height="60" fill="#e0f2f1" stroke="#00796b" strokeWidth="2" rx="4" />
              <text x="275" y="285" textAnchor="middle" fontSize="12" fill="#00796b">MEMORY.md</text>
              <text x="275" y="305" textAnchor="middle" fontSize="10" fill="#00796b">长期记忆</text>
              
              <rect x="400" y="260" width="150" height="60" fill="#e8eaf6" stroke="#3f51b5" strokeWidth="2" rx="4" />
              <text x="475" y="290" textAnchor="middle" fontSize="14" fill="#3f51b5">结果输出</text>
              
              <rect x="600" y="260" width="150" height="60" fill="#fff8e1" stroke="#fbc02d" strokeWidth="2" rx="4" />
              <text x="675" y="285" textAnchor="middle" fontSize="12" fill="#fbc02d">HEARTBEAT.md</text>
              <text x="675" y="305" textAnchor="middle" fontSize="10" fill="#fbc02d">定时检查</text>

              {/* 连接线 */}
              <line x1="200" y1="125" x2="220" y2="125" stroke="#666" strokeWidth="2" markerEnd="url(#arrow)" />
              <line x1="340" y1="125" x2="360" y2="125" stroke="#666" strokeWidth="2" />
              <line x1="480" y1="125" x2="500" y2="125" stroke="#666" strokeWidth="2" />
              <line x1="620" y1="125" x2="640" y2="125" stroke="#666" strokeWidth="2" />
              <line x1="760" y1="125" x2="780" y2="125" stroke="#666" strokeWidth="2" />
              <line x1="840" y1="150" x2="840" y2="200" stroke="#666" strokeWidth="2" />
              <line x1="840" y1="200" x2="350" y2="200" stroke="#666" strokeWidth="2" />
              <line x1="350" y1="200" x2="350" y2="260" stroke="#666" strokeWidth="2" markerEnd="url(#arrow)" />
              <line x1="350" y1="290" x2="400" y2="290" stroke="#666" strokeWidth="2" />
              <line x1="550" y1="290" x2="600" y2="290" stroke="#666" strokeWidth="2" />
            </svg>
          </div>
          
          {/* 缩放控制 */}
          <div style={{ display: 'flex', justifyContent: 'center', gap: '12px', marginTop: '16px' }}>
            <button className="btn btn-secondary" onClick={() => setZoom(z => Math.max(0.5, z - 0.1))}>缩小</button>
            <span className="badge" style={{ padding: '8px 16px' }}>{Math.round(zoom * 100)}%</span>
            <button className="btn btn-secondary" onClick={() => setZoom(z => Math.min(2, z + 0.1))}>放大</button>
            <button className="btn btn-primary" onClick={() => setZoom(1)}>重置</button>
          </div>
        </div>
      </div>

      {/* 系统模块 */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h5>📦 系统模块 ({modules.length}个)</h5>
        </div>
        <div style={{ padding: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px' }}>
            {modules.map(m => (
              <div 
                key={m.id} 
                onClick={() => setSelectedModule(m.id)}
                style={{ 
                  padding: '16px', 
                  background: '#f8f9fa', 
                  borderRadius: '8px',
                  borderLeft: `4px solid ${m.color}`,
                  cursor: 'pointer',
                  transition: 'transform 0.2s, box-shadow 0.2s'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.transform = 'translateY(-2px)'
                  e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.1)'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.transform = 'translateY(0)'
                  e.currentTarget.style.boxShadow = 'none'
                }}
              >
                <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>{m.icon}</div>
                <h6 style={{ marginBottom: '4px' }}>{m.name}</h6>
                <p style={{ fontSize: '0.85rem', color: '#666', margin: 0 }}>{m.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 数据库表 */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <div className="card-header">
          <h5>🗄️ 数据库表 (常用表)</h5>
        </div>
        <div style={{ padding: '20px' }}>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>表名</th>
                  <th>说明</th>
                  <th>记录数</th>
                </tr>
              </thead>
              <tbody>
                {tables.map(t => (
                  <tr key={t.name} onClick={() => setSelectedTable(t.name)} style={{ cursor: 'pointer' }}>
                    <td><code>{t.name}</code></td>
                    <td>{t.desc}</td>
                    <td>{tableCounts[t.name] || '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p style={{ textAlign: 'center', color: '#999', fontSize: '0.85rem', marginTop: '16px' }}>
            显示前15个常用表，共49张表
          </p>
        </div>
      </div>

      {/* 核心文件 */}
      <div className="card">
        <div className="card-header">
          <h5>📄 核心配置文件</h5>
        </div>
        <div style={{ padding: '20px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '16px' }}>
            {files.map(f => (
              <div key={f.name} style={{ 
                padding: '16px', 
                background: '#f8f9fa', 
                borderRadius: '8px',
                borderLeft: `4px solid ${f.color}`
              }}>
                <h6 style={{ marginBottom: '4px' }}>{f.name}</h6>
                <p style={{ fontSize: '0.85rem', color: '#666', margin: 0 }}>{f.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 模块详情弹窗 */}
      {selectedModule && (
        <div className="modal-overlay" onClick={() => setSelectedModule(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <h3>模块详情</h3>
            {(() => {
              const m = modules.find(x => x.id === selectedModule)
              return m ? (
                <div>
                  <div style={{ fontSize: '3rem', marginBottom: '16px' }}>{m.icon}</div>
                  <h4>{m.name}</h4>
                  <p style={{ color: '#666', marginTop: '8px' }}>{m.desc}</p>
                  <div style={{ marginTop: '16px' }}>
                    <span className="badge badge-blue">状态: 正常</span>
                  </div>
                </div>
              ) : null
            })()}
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setSelectedModule(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}

      {/* 表详情弹窗 */}
      {selectedTable && (
        <div className="modal-overlay" onClick={() => setSelectedTable(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <h3>表结构: {selectedTable}</h3>
            <p style={{ color: '#666' }}>记录数: {tableCounts[selectedTable] || '加载中...'}</p>
            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setSelectedTable(null)}>关闭</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
