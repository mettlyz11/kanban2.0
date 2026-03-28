import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'

export function Stocks() {
  const [stocks, setStocks] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedStock, setSelectedStock] = useState<any>(null)
  const [activeTab, setActiveTab] = useState('holdings')
  const [fundLinks, setFundLinks] = useState<any[]>([])
  const navigate = useNavigate()

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [stocksRes, statsRes, linksRes] = await Promise.all([
        fetch('/api/stocks').then(r => r.json()),
        fetch('/api/stocks/stats').then(r => r.json()),
        fetch('/api/stock-fund-links').then(r => r.json())
      ])
      
      if (stocksRes.success) setStocks(stocksRes.stocks || [])
      if (statsRes.success) setStats(statsRes)
      if (linksRes.success) setFundLinks(linksRes.links || [])
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  // 计算总收益
  const totalProfit = (stats?.total_value || 0) - (stats?.total_cost || 0)
  const totalReturn = stats?.total_return || 0

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📈 资产管理</h2>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className="btn btn-primary" onClick={() => setActiveTab('holdings')}>📊 持仓</button>
          <button className="btn btn-secondary" onClick={() => setActiveTab('analysis')}>📈 分析</button>
          <button className="btn btn-secondary" onClick={() => setActiveTab('fund-links')}>🔗 基股关联</button>
        </div>
      </div>

      {/* 统计卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        <div className="stat-card green" style={{ padding: '16px', background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>💰</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>¥{(stats?.total_value || 0).toLocaleString()}</h3>
            <p style={{ fontSize: '0.8rem' }}>总资产</p>
          </div>
        </div>
        <div className="stat-card" style={{ padding: '16px', background: 'linear-gradient(135deg, #3b82f6 0%, #2563eb 100%)' }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>💵</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>¥{(stats?.total_cost || 0).toLocaleString()}</h3>
            <p style={{ fontSize: '0.8rem' }}>总成本</p>
          </div>
        </div>
        <div className={`stat-card ${totalReturn >= 0 ? 'green' : 'red'}`} style={{ 
          padding: '16px', 
          background: totalReturn >= 0 ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
        }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>📊</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>{totalReturn.toFixed(2)}%</h3>
            <p style={{ fontSize: '0.8rem' }}>总收益率</p>
          </div>
        </div>
        <div className={`stat-card ${totalProfit >= 0 ? 'green' : 'red'}`} style={{ 
          padding: '16px',
          background: totalProfit >= 0 ? 'linear-gradient(135deg, #22c55e 0%, #16a34a 100%)' : 'linear-gradient(135deg, #ef4444 0%, #dc2626 100%)'
        }}>
          <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>{totalProfit >= 0 ? '📈' : '📉'}</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '1.5rem' }}>¥{totalProfit.toLocaleString()}</h3>
            <p style={{ fontSize: '0.8rem' }}>总盈亏</p>
          </div>
        </div>
      </div>

      {/* 持仓列表 */}
      {activeTab === 'holdings' && (
        <div className="card">
          <div className="card-header">
            <h5>📊 持仓明细</h5>
            <span className="badge badge-blue">{stocks.length} 只持仓</span>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th>类型</th>
                  <th>持仓</th>
                  <th>成本价</th>
                  <th>现价</th>
                  <th>市值</th>
                  <th>收益率</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {stocks.length === 0 ? (
                  <tr>
                    <td colSpan={9} className="empty-state">
                      <div style={{ 
                        padding: '60px 20px', 
                        textAlign: 'center',
                        background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
                        borderRadius: '12px',
                        margin: '20px 0'
                      }}>
                        <div style={{ fontSize: '64px', marginBottom: '16px' }}>💰</div>
                        <h4 style={{ margin: '0 0 8px 0', color: '#1e293b', fontSize: '18px' }}>暂无持仓资产</h4>
                        <p style={{ margin: '0 0 24px 0', color: '#64748b', fontSize: '14px' }}>
                          还没有添加任何股票或基金，点击下方按钮开始投资
                        </p>
                        <button
                          onClick={() => setShowAddModal(true)}
                          style={{
                            padding: '12px 32px',
                            borderRadius: '8px',
                            border: 'none',
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: '15px',
                            fontWeight: 600,
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '8px'
                          }}
                        >
                          <span style={{ fontSize: '18px' }}>➕</span>
                          添加第一笔持仓
                        </button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  stocks.map(stock => (
                    <tr 
                      key={stock.id} 
                      onClick={() => setSelectedStock(stock)}
                      style={{ cursor: 'pointer' }}
                    >
                      <td><strong>{stock.code}</strong></td>
                      <td>{stock.name}</td>
                      <td>
                        <span className={`badge ${stock.type === 'stock' ? 'badge-blue' : 'badge-green'}`}>
                          {stock.type === 'stock' ? '股票' : '基金'}
                        </span>
                      </td>
                      <td>{stock.shares}</td>
                      <td>¥{stock.cost_price?.toFixed(3)}</td>
                      <td>¥{stock.current_price?.toFixed(3)}</td>
                      <td>¥{(stock.shares * stock.current_price)?.toLocaleString()}</td>
                      <td>
                        <span style={{ 
                          color: (stock.return_rate || 0) >= 0 ? '#22c55e' : '#ef4444',
                          fontWeight: 600
                        }}>
                          {(stock.return_rate || 0).toFixed(2)}%
                        </span>
                      </td>
                      <td>
                        <button 
                          className="btn btn-sm btn-outline-primary"
                          onClick={e => {
                            e.stopPropagation()
                            navigate(`/stocks/${stock.code}`)
                          }}
                        >
                          详情
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 基股关联 */}
      {activeTab === 'fund-links' && (
        <div className="card">
          <div className="card-header">
            <h5>🔗 股票基金关联</h5>
            <button className="btn btn-sm btn-primary" onClick={() => alert('自动检测关联功能')}>🔍 自动检测</button>
          </div>
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>股票</th>
                  <th>基金</th>
                  <th>关联类型</th>
                  <th>相关性</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {fundLinks.length === 0 ? (
                  <tr>
                    <td colSpan={5} className="empty-state">
                      <div>暂无关联数据</div>
                      <div style={{ fontSize: '0.85rem', color: '#999', marginTop: '8px' }}>
                        点击"自动检测"分析股票基金关联关系
                      </div>
                    </td>
                  </tr>
                ) : (
                  fundLinks.map((link: any) => (
                    <tr key={link.id}>
                      <td>{link.stock_symbol}</td>
                      <td>{link.fund_name}</td>
                      <td>{link.link_type}</td>
                      <td>{link.correlation}%</td>
                      <td>
                        <button className="btn btn-sm btn-danger">删除</button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 分析页面 */}
      {activeTab === 'analysis' && (
        <div className="card">
          <div className="card-header">
            <h5>📈 资产分析</h5>
          </div>
          <div style={{ padding: '40px', textAlign: 'center' }}>
            <div className="empty-state-icon">📊</div>
            <p>资产分析功能开发中</p>
            <p style={{ fontSize: '0.85rem', color: '#999' }}>
              将包含：收益率走势图、资产配置分析、风险评估等功能
            </p>
          </div>
        </div>
      )}

      {/* 股票详情弹窗 */}
      {selectedStock && (
        <div className="modal-overlay" onClick={() => setSelectedStock(null)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '600px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
              <h3>{selectedStock.name} ({selectedStock.code})</h3>
              <button className="btn btn-sm btn-secondary" onClick={() => setSelectedStock(null)}>✕</button>
            </div>
            
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px', marginBottom: '20px' }}>
              <div style={{ padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.85rem', color: '#666' }}>持仓数量</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>{selectedStock.shares}</div>
              </div>
              <div style={{ padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.85rem', color: '#666' }}>当前市值</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>
                  ¥{(selectedStock.shares * selectedStock.current_price).toLocaleString()}
                </div>
              </div>
              <div style={{ padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.85rem', color: '#666' }}>成本价</div>
                <div style={{ fontSize: '1.5rem', fontWeight: 600 }}>¥{selectedStock.cost_price?.toFixed(3)}</div>
              </div>
              <div style={{ padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
                <div style={{ fontSize: '0.85rem', color: '#666' }}>收益率</div>
                <div style={{ 
                  fontSize: '1.5rem', 
                  fontWeight: 600,
                  color: (selectedStock.return_rate || 0) >= 0 ? '#22c55e' : '#ef4444'
                }}>
                  {(selectedStock.return_rate || 0).toFixed(2)}%
                </div>
              </div>
            </div>

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setSelectedStock(null)}>关闭</button>
              <button className="btn btn-primary" onClick={() => navigate(`/stocks/${selectedStock.code}`)}>
                查看完整详情 →
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Stocks
