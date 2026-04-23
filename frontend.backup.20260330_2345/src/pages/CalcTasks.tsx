export function CalcTasks() {

  const t109Links = [
    { name: 'T109平台首页', url: 'http://47.93.184.128/t109/', desc: '访问T109过渡态计算平台', icon: '🧪' },
    { name: '提交计算任务', url: 'http://47.93.184.128/t109/submit', desc: '提交新的计算任务到T109平台', icon: '📝' },
    { name: '查看计算结果', url: 'http://47.93.184.128/t109/results', desc: '查看已完成的计算任务结果', icon: '📊' },
    { name: '任务队列', url: 'http://47.93.184.128/t109/queue', desc: '查看当前运行中的任务队列', icon: '⏳' },
  ]

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🔢 计算任务 (T109)</h2>
      </div>

      {/* 说明卡片 */}
      <div className="card" style={{ marginBottom: '20px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', color: 'white' }}>
        <h4 style={{ marginBottom: '12px' }}>🧪 T109 过渡态计算平台</h4>
        <p style={{ opacity: 0.9, lineHeight: '1.6' }}>
          T109是专门为过渡态计算设计的分布式计算平台。由于安全策略限制，
          请点击下方链接在新窗口中访问T109网站。
        </p>
      </div>

      {/* T109快捷链接 */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <h5>🔗 T109 快捷链接</h5>
        </div>
        <div className="grid-2">
          {t109Links.map((link, i) => (
            <a
              key={i}
              href={link.url}
              target="_blank"
              rel="noopener noreferrer"
              className="card"
              style={{ 
                marginBottom: 0, 
                textDecoration: 'none', 
                color: 'inherit',
                borderLeft: '4px solid #667eea',
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
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                <div style={{ fontSize: '2.5rem' }}>{link.icon}</div>
                <div style={{ flex: 1 }}>
                  <h5 style={{ marginBottom: '4px' }}>{link.name}</h5>
                  <p style={{ color: '#666', fontSize: '0.9rem', margin: 0 }}>{link.desc}</p>
                </div>
                <span style={{ fontSize: '1.5rem', color: '#667eea' }}>↗</span>
              </div>
            </a>
          ))}
        </div>
      </div>

      {/* 本地任务列表 */}
      <div className="card">
        <div className="card-header">
          <h5>📋 本地任务关联</h5>
        </div>
        <div className="empty-state">
          <div className="empty-state-icon">🔢</div>
          <p>暂无本地关联任务</p>
          <p style={{ fontSize: '0.85rem', color: '#999', marginTop: '8px' }}>
            此功能用于关联T109计算任务与本地看板项目
          </p>
        </div>
      </div>

      {/* 使用说明 */}
      <div className="card">
        <div className="card-header">
          <h5>📖 使用说明</h5>
        </div>
        <div style={{ padding: '20px' }}>
          <ol style={{ lineHeight: '2', paddingLeft: '20px' }}>
            <li>点击"提交计算任务"链接，在新窗口中打开T109提交页面</li>
            <li>填写计算参数并提交任务</li>
            <li>任务完成后，点击"查看计算结果"获取结果</li>
            <li>可在"任务队列"中查看当前运行状态</li>
            <li>在"用户面板"查看个人统计信息</li>
          </ol>
          <div style={{ marginTop: '16px', padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
            <strong>💡 提示：</strong>
            <span style={{ color: '#666' }}>T109平台需要单独登录，建议使用相同的账号密码以便管理</span>
          </div>
        </div>
      </div>
    </div>
  )
}

export default CalcTasks
