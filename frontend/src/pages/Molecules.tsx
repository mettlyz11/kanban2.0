export function Molecules() {
  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🧪 和光智成 (Helight)</h2>
      </div>

      {/* 和光智成网站 */}
      <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
        <div style={{ 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', 
          padding: '16px 20px',
          color: 'white',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center'
        }}>
          <div>
            <h4 style={{ margin: 0 }}>🧪 和光智成</h4>
            <p style={{ margin: '4px 0 0 0', opacity: 0.9, fontSize: '0.9rem' }}>
              AI驱动的智能化学计算平台
            </p>
          </div>
          <a 
            href="http://47.93.184.128/helight/" 
            target="_blank" 
            rel="noopener noreferrer"
            className="btn"
            style={{ 
              background: 'white', 
              color: '#667eea',
              padding: '10px 20px',
              borderRadius: '8px',
              textDecoration: 'none',
              fontWeight: 600
            }}
          >
            访问网站 ↗
          </a>
        </div>
        <div style={{ padding: '30px', textAlign: 'center' }}>
          <div style={{ fontSize: '4rem', marginBottom: '16px' }}>🧪</div>
          <h3>和光智成 (Helight)</h3>
          <p style={{ color: '#666', maxWidth: '600px', margin: '16px auto', lineHeight: '1.6' }}>
            和光智成是一个AI驱动的智能化学计算平台，提供分子建模、
            反应预测、性质计算等功能，助力化学研究和药物开发。
          </p>
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'center', flexWrap: 'wrap', marginTop: '24px' }}>
            <a
              href="http://47.93.184.128/helight/"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
              style={{ padding: '12px 24px' }}
            >
              🚀 进入平台
            </a>
            <a
              href="http://47.93.184.128/helight/docs"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-secondary"
              style={{ padding: '12px 24px' }}
            >
              📖 查看文档
            </a>
          </div>
        </div>
      </div>

      {/* 功能特性 */}
      <div className="card">
        <h5 style={{ marginBottom: '16px' }}>✨ 核心功能</h5>
        <div className="grid-3">
          {[
            { icon: '🧬', title: '分子建模', desc: '3D分子结构构建与可视化' },
            { icon: '⚡', title: '反应预测', desc: 'AI预测化学反应路径和产物' },
            { icon: '📊', title: '性质计算', desc: '计算分子物理化学性质' },
            { icon: '🔬', title: '光谱模拟', desc: '模拟各类光谱数据' },
            { icon: '💊', title: '药物设计', desc: '基于AI的药物分子设计' },
            { icon: '📈', title: '数据分析', desc: '化学数据智能分析' }
          ].map((feature, i) => (
            <div key={i} className="card" style={{ marginBottom: 0, padding: '20px', textAlign: 'center' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '12px' }}>{feature.icon}</div>
              <h6>{feature.title}</h6>
              <p style={{ color: '#666', fontSize: '0.85rem', margin: 0 }}>{feature.desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Molecules
