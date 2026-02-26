import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../utils/api'

export function Dashboard() {
  const [stats, setStats] = useState<any>(null)
  const [cronStats, setCronStats] = useState<any>(null)
  const [stockStats, setStockStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadAllStats()
  }, [])

  const loadAllStats = async () => {
    try {
      const [statsRes, cronRes, stockRes] = await Promise.all([
        api.getStats(),
        api.getCronStats().catch(() => ({ success: false })),
        api.getStockStats().catch(() => ({ success: false }))
      ])
      
      if (statsRes.success) setStats(statsRes.stats)
      if (cronRes.success) setCronStats(cronRes.stats)
      if (stockRes.success) setStockStats(stockRes)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <h2 className="page-title">📊 看板总览</h2>
      
      {/* 核心统计 - 带链接 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
        <Link to="/projects" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card blue" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>📁</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats?.projects || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>项目总数</p>
            </div>
          </div>
        </Link>
        <Link to="/tasks" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card green" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>✅</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats?.tasks?.total || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>任务总数</p>
            </div>
          </div>
        </Link>
        <Link to="/tasks" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card orange" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>✨</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats?.tasks?.done || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>已完成</p>
            </div>
          </div>
        </Link>
        <Link to="/tasks" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card cyan" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>🚀</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.5rem' }}>{stats?.tasks?.progress || 0}</h3>
              <p style={{ fontSize: '0.8rem' }}>进行中</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Cron统计 */}
      {cronStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <Link to="/cron" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="stat-card purple" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
              <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>⏰</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.5rem' }}>{cronStats.total || 0}</h3>
                <p style={{ fontSize: '0.8rem' }}>Cron任务</p>
              </div>
            </div>
          </Link>
          <Link to="/cron" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="stat-card green" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
              <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>▶️</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.5rem' }}>{cronStats.active || 0}</h3>
                <p style={{ fontSize: '0.8rem' }}>运行中</p>
              </div>
            </div>
          </Link>
        </div>
      )}

      {/* 资产统计 */}
      {stockStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <Link to="/stocks" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="stat-card pink" style={{ padding: '16px', cursor: 'pointer', transition: 'transform 0.2s' }}>
              <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>💰</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.5rem' }}>¥{(stockStats.total_value || 0).toLocaleString()}</h3>
                <p style={{ fontSize: '0.8rem' }}>总资产</p>
              </div>
            </div>
          </Link>
          <Link to="/stocks" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className={`stat-card ${(stockStats.total_return || 0) >= 0 ? 'green' : 'orange'}`} style={{ 
              padding: '16px', 
              cursor: 'pointer', 
              transition: 'transform 0.2s'
            }}>
              <div className="stat-icon" style={{ width: '48px', height: '48px', fontSize: '1.25rem' }}>📈</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.5rem' }}>{(stockStats.total_return || 0).toFixed(2)}%</h3>
                <p style={{ fontSize: '0.8rem' }}>总收益率</p>
              </div>
            </div>
          </Link>
        </div>
      )}

      <div className="card">
        <h3>👋 欢迎使用看板系统 v2.0</h3>
        <p style={{ color: '#666', marginTop: '8px' }}>
          这是使用 React + Flask 构建的新版本看板系统，与原系统共用数据库，数据实时同步。
          点击上方统计卡片可快速跳转到对应页面。
        </p>
      </div>
    </div>
  )
}
