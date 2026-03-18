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

  const completionRate = stats?.tasks?.total 
    ? Math.round((stats.tasks.done / stats.tasks.total) * 100) 
    : 0

  return (
    <div>
      <h2 className="page-title">📊 看板总览</h2>
      
      {/* 项目统计 */}
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
      </div>

      {/* 目标卡片 - 放在项目和任务之间 */}
      <div className="goals-section" style={{ marginBottom: '24px' }}>
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
          gap: '16px'
        }}>
          {/* 核心目标卡片 */}
          <div className="card goal-card" style={{ 
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              🎯 核心目标
            </h3>
            <ul style={{ margin: 0, paddingLeft: '20px', lineHeight: '1.8' }}>
              <li>建立自完善认知架构 (方案B)</li>
              <li>优化18+ AI模型配置</li>
              <li>推进T109/Pepi/看板系统</li>
              <li>支持7大人生目标</li>
            </ul>
          </div>
          
          {/* 今日进度卡片 */}
          <div className="card goal-card" style={{ 
            background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
            color: 'white',
            border: 'none'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              📈 今日进度
            </h3>
            <div style={{ marginBottom: '16px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px', fontSize: '0.9rem' }}>
                <span>任务完成率</span>
                <span>{completionRate}%</span>
              </div>
              <div style={{ 
                height: '10px', 
                background: 'rgba(255,255,255,0.3)', 
                borderRadius: '5px',
                overflow: 'hidden'
              }}>
                <div style={{ 
                  height: '100%', 
                  width: `${completionRate}%`,
                  background: 'white',
                  borderRadius: '5px',
                  transition: 'width 0.3s ease'
                }} />
              </div>
            </div>
            <div style={{ display: 'flex', gap: '16px', justifyContent: 'space-around' }}>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats?.tasks?.done || 0}</div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>已完成</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats?.tasks?.progress || 0}</div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>进行中</div>
              </div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>{stats?.tasks?.todo || 0}</div>
                <div style={{ fontSize: '0.8rem', opacity: 0.9 }}>待处理</div>
              </div>
            </div>
          </div>
          
          {/* 快捷操作卡片 */}
          <div className="card goal-card" style={{ 
            background: 'linear-gradient(135deg, #4facfe 0%, #00f2fe 100%)',
            color: 'white',
            border: 'none'
          }}>
            <h3 style={{ margin: '0 0 16px 0', fontSize: '1.1rem', display: 'flex', alignItems: 'center', gap: '8px' }}>
              ⚡ 快捷操作
            </h3>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <Link to="/tasks/new" className="quick-action-btn" style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.2)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                transition: 'all 0.2s'
              }}>
                <span>➕</span> 新建任务
              </Link>
              <Link to="/projects/new" style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.2)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                transition: 'all 0.2s'
              }}>
                <span>📁</span> 新建项目
              </Link>
              <Link to="/cron" style={{ 
                textDecoration: 'none', 
                color: 'inherit',
                padding: '10px 14px',
                background: 'rgba(255,255,255,0.2)',
                borderRadius: '8px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                transition: 'all 0.2s'
              }}>
                <span>⏰</span> 查看Cron任务
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* 任务统计 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '10px', marginBottom: '16px' }}>
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
