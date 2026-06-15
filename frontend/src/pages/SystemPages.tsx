import { useState, useEffect, useRef } from 'react'
import { useLocalSystemMonitor } from "../hooks/useLocalSystemMonitor"
import { Line, Doughnut } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js'

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
)

// 图标组件 - 缩小尺寸
const CPUIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
    <rect x="9" y="9" width="6" height="6"/>
    <line x1="9" y1="1" x2="9" y2="4"/><line x1="15" y1="1" x2="15" y2="4"/>
    <line x1="9" y1="20" x2="9" y2="23"/><line x1="15" y1="20" x2="15" y2="23"/>
    <line x1="20" y1="9" x2="23" y2="9"/><line x1="20" y1="14" x2="23" y2="14"/>
    <line x1="1" y1="9" x2="4" y2="9"/><line x1="1" y1="14" x2="4" y2="14"/>
  </svg>
)

const MemoryIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="2" y="4" width="20" height="16" rx="2" ry="2"/>
    <line x1="6" y1="8" x2="6" y2="16"/><line x1="10" y1="8" x2="10" y2="16"/>
    <line x1="14" y1="8" x2="14" y2="16"/><line x1="18" y1="8" x2="18" y2="16"/>
  </svg>
)

const DiskIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <ellipse cx="12" cy="12" rx="10" ry="4"/><path d="M2 12v4a10 4 0 0 0 20 0v-4"/>
    <line x1="12" y1="12" x2="12" y2="16"/><circle cx="12" cy="14" r="1"/>
  </svg>
)

const ProcessIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
    <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
  </svg>
)

const UptimeIcon = () => (
  <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
  </svg>
)

// 进度条组件
const ProgressBar = ({ value, color = "#3b82f6", label }: { value: number; color?: string; label?: string }) => (
  <div style={{ width: '100%' }}>
    {label && <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4, fontSize: 12 }}>
      <span>{label}</span><span>{value.toFixed(1)}%</span>
    </div>}
    <div style={{ background: 'rgba(255,255,255,0.2)', borderRadius: 4, height: 6 }}>
      <div style={{ 
        background: color, 
        borderRadius: 4, 
        height: '100%', 
        width: `${Math.min(value, 100)}%`,
        transition: 'width 0.3s ease'
      }}></div>
    </div>
  </div>
)

export function SystemMonitor() {
  const {
    connected: localConnected,
    metrics: localMetrics,
    history: localHistory,
    error: localError,
    formatUptime: formatLocalUptime,
    reconnect: localReconnect,
  } = useLocalSystemMonitor()

  const metrics = localMetrics ? {
    cpu: localMetrics.cpu.percent,
    memory: localMetrics.memory.percent,
    disk: localMetrics.disk.percent,
    gateway_status: "正常",
    uptime: localMetrics.uptime ? formatLocalUptime(localMetrics.uptime) : "--",
    cpu_cores: localMetrics.cpu.cores,
    memory_total: localMetrics.memory.total_gb,
    memory_used: localMetrics.memory.used_gb,
    task_count: localMetrics.processes,
    disk_used: localMetrics.disk.used_gb,
    disk_total: localMetrics.disk.total_gb,
    freq_mhz: localMetrics.cpu.freq_mhz,
  } : null

  const history = (localHistory || []).map((h: any) => ({
    timestamp: h.timestamp,
    cpu: h.cpu,
    memory: h.memory,
    task_count: h.processes
  }))

  const [loading] = useState(false)

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: true, position: 'top' as const, labels: { boxWidth: 12, padding: 12 } }
    },
    scales: {
      y: { beginAtZero: true, max: 100, grid: { color: 'rgba(0,0,0,0.05)' } },
      x: { grid: { color: 'rgba(0,0,0,0.05)' } }
    }
  }

  const chartData = {
    labels: history.slice(-30).map((h, i) => {
      const date = new Date(h.timestamp)
      return `${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')}`
    }),
    datasets: [
      {
        label: 'CPU %',
        data: history.slice(-30).map(h => h.cpu || 0),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
      },
      {
        label: '内存 %',
        data: history.slice(-30).map(h => h.memory || 0),
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
        borderWidth: 2,
        pointRadius: 0,
      }
    ]
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '24px 32px' }}>
      {/* 页面标题 + 连接状态 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
        <h2 style={{ margin: 0, fontSize: '1.5rem', fontWeight: 600 }}>📈 Mac mini 系统监控</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '4px 12px', background: localConnected ? '#dcfce7' : '#fef2f2', borderRadius: 20 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: localConnected ? '#10b981' : '#ef4444' }}></div>
          <span style={{ fontSize: 12, color: localConnected ? '#166534' : '#991b1b', fontWeight: 500 }}>
            {localConnected ? '实时连接' : '连接中...'}
          </span>
        </div>
        {localError && (
          <span style={{ fontSize: 12, color: '#ef4444', background: '#fef2f2', padding: '4px 12px', borderRadius: 20 }}>
            ⚠️ {localError}
          </span>
        )}
      </div>

      {/* 指标卡片 - 5列布局 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 16, marginBottom: 24 }}>
        {[
          { label: 'CPU 使用率', value: `${metrics?.cpu || 0}%`, sub: `${metrics?.cpu_cores || 8} 核心 · ${metrics?.freq_mhz || '--'} MHz`, icon: <CPUIcon />, bg: 'linear-gradient(135deg, #3b82f6, #2563eb)', color: '#fff' },
          { label: '内存使用率', value: `${metrics?.memory || 0}%`, sub: `${metrics?.memory_used?.toFixed(1) || '--'} / ${metrics?.memory_total || '--'} GB`, icon: <MemoryIcon />, bg: 'linear-gradient(135deg, #10b981, #059669)', color: '#fff' },
          { label: '磁盘使用率', value: `${metrics?.disk || 0}%`, sub: `${metrics?.disk_used || '--'} / ${metrics?.disk_total || '--'} GB`, icon: <DiskIcon />, bg: 'linear-gradient(135deg, #f59e0b, #d97706)', color: '#fff' },
          { label: '运行进程', value: `${metrics?.task_count || '--'}`, sub: '活跃进程数', icon: <ProcessIcon />, bg: 'linear-gradient(135deg, #8b5cf6, #7c3aed)', color: '#fff' },
          { label: '运行时间', value: metrics?.uptime || '--', sub: '系统持续运行', icon: <UptimeIcon />, bg: 'linear-gradient(135deg, #ec4899, #db2777)', color: '#fff' },
        ].map((card, i) => (
          <div key={i} style={{
            background: card.bg,
            borderRadius: 12,
            padding: '16px 20px',
            color: card.color,
            display: 'flex',
            flexDirection: 'column',
            gap: 8,
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: 0.9 }}>
              {card.icon}
              <span style={{ fontSize: 13, fontWeight: 500 }}>{card.label}</span>
            </div>
            <div style={{ fontSize: '1.75rem', fontWeight: 700, lineHeight: 1 }}>{card.value}</div>
            <div style={{ fontSize: 11, opacity: 0.8 }}>{card.sub}</div>
          </div>
        ))}
      </div>

      {/* 进度条区域 */}
      {metrics && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, color: '#374151' }}>资源使用概览</h3>
          <div style={{ display: 'flex', gap: 24 }}>
            <div style={{ flex: 1 }}>
              <ProgressBar value={metrics.cpu} color="#3b82f6" label="CPU" />
            </div>
            <div style={{ flex: 1 }}>
              <ProgressBar value={metrics.memory} color="#10b981" label="内存" />
            </div>
            <div style={{ flex: 1 }}>
              <ProgressBar value={metrics.disk} color="#f59e0b" label="磁盘" />
            </div>
          </div>
        </div>
      )}

      {/* 趋势图 */}
      <div style={{ background: '#fff', borderRadius: 12, padding: 20, marginBottom: 24, border: '1px solid #e5e7eb' }}>
        <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, color: '#374151' }}>最近 30 分钟趋势</h3>
        <div style={{ height: 300 }}>
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      {/* 历史数据表格 */}
      {history.length > 0 && (
        <div style={{ background: '#fff', borderRadius: 12, padding: 20, border: '1px solid #e5e7eb' }}>
          <h3 style={{ margin: '0 0 16px', fontSize: 14, fontWeight: 600, color: '#374151' }}>最近记录</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#666' }}>时间</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', color: '#666' }}>CPU</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', color: '#666' }}>内存</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', color: '#666' }}>进程</th>
              </tr>
            </thead>
            <tbody>
              {history.slice(-10).reverse().map((h, i) => {
                const date = new Date(h.timestamp)
                const time = `${date.getHours().toString().padStart(2,'0')}:${date.getMinutes().toString().padStart(2,'0')}:${date.getSeconds().toString().padStart(2,'0')}`
                return (
                  <tr key={i} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 12 }}>{time}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', color: h.cpu > 80 ? '#ef4444' : h.cpu > 50 ? '#f59e0b' : '#10b981' }}>{h.cpu.toFixed(1)}%</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', color: h.memory > 80 ? '#ef4444' : h.memory > 50 ? '#f59e0b' : '#10b981' }}>{h.memory.toFixed(1)}%</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right' }}>{h.task_count}</td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

export function AccessStats() {
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const res = await fetch('/api/access/stats')
      const data = await res.json()
      if (data.success) setStats(data.stats)
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
        <h2 className="page-title">🌐 访问统计 (T002a)</h2>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        <div className="stat-card blue" style={{ padding: '28px', borderRadius: '16px', minHeight: '140px' }}>
          <div className="stat-icon" style={{ width: '56px', height: '56px', fontSize: '1.5rem', marginBottom: '16px' }}>👁️</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '2.2rem', margin: '8px 0' }}>{stats?.total_views || 0}</h3>
            <p style={{ fontSize: '1rem', opacity: 0.8 }}>总访问量</p>
          </div>
        </div>
        <div className="stat-card green" style={{ padding: '28px', borderRadius: '16px', minHeight: '140px' }}>
          <div className="stat-icon" style={{ width: '56px', height: '56px', fontSize: '1.5rem', marginBottom: '16px' }}>👤</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '2.2rem', margin: '8px 0' }}>{stats?.unique_visitors || 0}</h3>
            <p style={{ fontSize: '1rem', opacity: 0.8 }}>独立访客</p>
          </div>
        </div>
        <div className="stat-card purple" style={{ padding: '28px', borderRadius: '16px', minHeight: '140px' }}>
          <div className="stat-icon" style={{ width: '56px', height: '56px', fontSize: '1.5rem', marginBottom: '16px' }}>📄</div>
          <div className="stat-info">
            <h3 style={{ fontSize: '2.2rem', margin: '8px 0' }}>{stats?.page_count || 0}</h3>
            <p style={{ fontSize: '1rem', opacity: 0.8 }}>页面数</p>
          </div>
        </div>
      </div>

      <div className="card" style={{ borderRadius: '16px' }}>
        <div className="card-header" style={{ padding: '24px 28px' }}>
          <h5 style={{ fontSize: '1.25rem', margin: 0 }}>📊 访问趋势</h5>
        </div>
        <div style={{ padding: '32px' }}>
          <p style={{ color: '#666', fontSize: '1.1rem' }}>访问统计功能开发中...</p>
        </div>
      </div>
    </div>
  )
}


// 主页面组件
function SystemPages() {
  return (
    <div className="system-pages">
      <SystemMonitor />
      <AccessStats />
    </div>
  )
}

export function PageViewTracker() { return null }

export default SystemPages
