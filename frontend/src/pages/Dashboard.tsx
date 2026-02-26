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
      
      {/* 核心统计 - 紧凑尺寸 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '16px' }}>
        <Link to="/projects" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card blue" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>📁</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.2rem' }}>{stats?.projects || 0}</h3>
              <p style={{ fontSize: '0.7rem' }}>项目总数</p>
            </div>
          </div>
        </Link>
        <Link to="/tasks" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card green" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>✅</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.2rem' }}>{stats?.tasks?.total || 0}</h3>
              <p style={{ fontSize: '0.7rem' }}>任务总数</p>
            </div>
          </div>
        </Link>
        <Link to="/tasks" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card orange" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>✨</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.2rem' }}>{stats?.tasks?.done || 0}</h3>
              <p style={{ fontSize: '0.7rem' }}>已完成</p>
            </div>
          </div>
        </Link>
        <Link to="/tasks" style={{ textDecoration: 'none', color: 'inherit' }}>
          <div className="stat-card cyan" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
            <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>🚀</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.2rem' }}>{stats?.tasks?.progress || 0}</h3>
              <p style={{ fontSize: '0.7rem' }}>进行中</p>
            </div>
          </div>
        </Link>
      </div>

      {/* Cron统计 */}
      {cronStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '16px' }}>
          <Link to="/cron" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="stat-card purple" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
              <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>⏰</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.2rem' }}>{cronStats.total || 0}</h3>
                <p style={{ fontSize: '0.7rem' }}>Cron任务</p>
              </div>
            </div>
          </Link>
          <Link to="/cron" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="stat-card green" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
              <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>▶️</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.2rem' }}>{cronStats.active || 0}</h3>
                <p style={{ fontSize: '0.7rem' }}>运行中</p>
              </div>
            </div>
          </Link>
        </div>
      )}

      {/* 资产统计 */}
      {stockStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '16px' }}>
          <Link to="/stocks" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className="stat-card pink" style={{ padding: '12px', cursor: 'pointer', transition: 'transform 0.2s' }}>
              <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>💰</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.1rem' }}>¥{(stockStats.total_value || 0).toLocaleString()}</h3>
                <p style={{ fontSize: '0.7rem' }}>总资产</p>
              </div>
            </div>
          </Link>
          <Link to="/stocks" style={{ textDecoration: 'none', color: 'inherit' }}>
            <div className={`stat-card ${(stockStats.total_return || 0) >= 0 ? 'green' : 'orange'}`} style={{ 
              padding: '12px', 
              cursor: 'pointer', 
              transition: 'transform 0.2s'
            }}>
              <div className="stat-icon" style={{ width: '36px', height: '36px', fontSize: '1.1rem' }}>📈</div>
              <div className="stat-info">
                <h3 style={{ fontSize: '1.1rem' }}>{(stockStats.total_return || 0).toFixed(2)}%</h3>
                <p style={{ fontSize: '0.7rem' }}>总收益率</p>
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
