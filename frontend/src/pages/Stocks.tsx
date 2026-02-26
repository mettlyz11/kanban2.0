import { useState, useEffect } from 'react'
import { api } from '../utils/api'

export function Stocks() {
  const [stocks, setStocks] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [stocksRes, statsRes] = await Promise.all([
        api.getStocks(),
        api.getStockStats()
      ])
      if (stocksRes.success) setStocks(stocksRes.stocks || [])
      if (statsRes.success) setStats(statsRes)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📈 资产管理</h2>
      </div>

      {/* 资产统计 */}
      {stats && (
        <div className="stats-grid" style={{ marginBottom: '24px' }}>
          <div className="stat-card pink">
            <div className="stat-icon">💰</div>
            <div className="stat-info">
              <h3>¥{(stats.total_value || 0).toLocaleString()}</h3>
              <p>总资产</p>
            </div>
          </div>
          <div className="stat-card green">
            <div className="stat-icon">💵</div>
            <div className="stat-info">
              <h3>¥{(stats.total_cost || 0).toLocaleString()}</h3>
              <p>总成本</p>
            </div>
          </div>
          <div className={`stat-card ${(stats.total_return || 0) >= 0 ? 'green' : 'orange'}`}>
            <div className="stat-icon">📊</div>
            <div className="stat-info">
              <h3>{(stats.total_return || 0).toFixed(2)}%</h3>
              <p>总收益率</p>
            </div>
          </div>
          <div className={`stat-card ${(stats.total_profit || 0) >= 0 ? 'green' : 'orange'}`}>
            <div className="stat-icon">{stats.total_profit >= 0 ? '📈' : '📉'}</div>
            <div className="stat-info">
              <h3>¥{(stats.total_profit || 0).toLocaleString()}</h3>
              <p>总盈亏</p>
            </div>
          </div>
        </div>
      )}

      {/* 持仓列表 */}
      <div className="card">
        <div className="card-header">
          <h5>持仓明细</h5>
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
              </tr>
            </thead>
            <tbody>
              {stocks.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-state">暂无持仓</td>
                </tr>
              ) : (
                stocks.map(stock => (
                  <tr key={stock.id}>
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
                        color: (stock.return_rate || 0) >= 0 ? '#28a745' : '#dc3545',
                        fontWeight: 600
                      }}>
                        {(stock.return_rate || 0).toFixed(2)}%
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
