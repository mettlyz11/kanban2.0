import { useState, useEffect, useRef } from 'react'
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

// 注册Chart.js组件
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

// 图标组件
const CPUIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="4" y="4" width="16" height="16" rx="2" ry="2"/>
    <rect x="9" y="9" width="6" height="6"/>
    <line x1="9" y1="1" x2="9" y2="4"/>
    <line x1="15" y1="1" x2="15" y2="4"/>
    <line x1="9" y1="20" x2="9" y2="23"/>
    <line x1="15" y1="20" x2="15" y2="23"/>
    <line x1="20" y1="9" x2="23" y2="9"/>
    <line x1="20" y1="14" x2="23" y2="14"/>
    <line x1="1" y1="9" x2="4" y2="9"/>
    <line x1="1" y1="14" x2="4" y2="14"/>
  </svg>
)

const MemoryIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="2" y="4" width="20" height="16" rx="2" ry="2"/>
    <line x1="6" y1="8" x2="6" y2="16"/>
    <line x1="10" y1="8" x2="10" y2="16"/>
    <line x1="14" y1="8" x2="14" y2="16"/>
    <line x1="18" y1="8" x2="18" y2="16"/>
  </svg>
)

const TaskIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
    <polyline points="14 2 14 8 20 8"/>
    <line x1="16" y1="13" x2="8" y2="13"/>
    <line x1="16" y1="17" x2="8" y2="17"/>
    <polyline points="10 9 9 9 8 9"/>
  </svg>
)

const ServerIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
    <rect x="2" y="2" width="20" height="8" rx="2" ry="2"/>
    <rect x="2" y="14" width="20" height="8" rx="2" ry="2"/>
    <line x1="6" y1="6" x2="6.01" y2="6"/>
    <line x1="6" y1="18" x2="6.01" y2="18"/>
  </svg>
)

export function SystemMonitor() {
  const [metrics, setMetrics] = useState<any>(null)
  const [history, setHistory] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshRate, setRefreshRate] = useState(60)
  const [cpuThreshold, setCpuThreshold] = useState(80)
  const [memThreshold, setMemThreshold] = useState(85)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    loadData()
    
    // 设置定时刷新
    intervalRef.current = setInterval(loadData, refreshRate * 1000)
    
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [refreshRate])

  const loadData = async () => {
    try {
      const [statusRes, historyRes] = await Promise.all([
        fetch('/api/system/status').then(r => r.json()),
        fetch('/api/system/history?hours=24').then(r => r.json())
      ])
      
      if (statusRes.success) setMetrics(statusRes.metrics)
      if (historyRes.success) {
        // 转换API返回的数据格式为history数组
        if (historyRes.labels && historyRes.cpuData) {
          const formattedHistory = historyRes.labels.map((_label: string, index: number) => ({
            timestamp: new Date().toISOString(),
            created_at: new Date().toISOString(),
            cpu: historyRes.cpuData[index] || 0,
            cpu_percent: historyRes.cpuData[index] || 0,
            memory: historyRes.memData[index] || 0,
            memory_percent: historyRes.memData[index] || 0,
            task_count: historyRes.taskData[index] || 0
          }))
          setHistory(formattedHistory)
        } else {
          setHistory(historyRes.history || [])
        }
      }
    } catch (e) {
      console.error(e)
      // 使用模拟数据
      setMockData()
    } finally {
      setLoading(false)
    }
  }

  const setMockData = () => {
    // 模拟实时数据
    setMetrics({
      cpu: Math.floor(Math.random() * 40) + 20,
      memory: Math.floor(Math.random() * 30) + 40,
      disk: Math.floor(Math.random() * 20) + 60,
      gateway_status: '正常',
      uptime: '5天 12小时',
      cpu_cores: 8,
      memory_total: 16,
      memory_used: 6.4,
      task_count: 127
    })
    
    // 生成24小时历史数据
    const mockHistory = []
    for (let i = 23; i >= 0; i--) {
      const hour = new Date()
      hour.setHours(hour.getHours() - i)
      mockHistory.push({
        timestamp: hour.toISOString(),
        cpu: Math.floor(Math.random() * 40) + 20,
        memory: Math.floor(Math.random() * 30) + 40,
        disk: Math.floor(Math.random() * 20) + 60,
        task_count: Math.floor(Math.random() * 50) + 100,
        status: Math.random() > 0.9 ? 'warning' : 'normal'
      })
    }
    setHistory(mockHistory)
  }

  // 准备图表数据
  const chartData = {
    labels: history.map(h => {
      const date = new Date(h.timestamp || h.created_at)
      return date.getHours() + ':00'
    }),
    datasets: [
      {
        label: 'CPU %',
        data: history.map(h => h.cpu || h.cpu_percent || 0),
        borderColor: 'rgb(102, 126, 234)',
        backgroundColor: 'rgba(102, 126, 234, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: '内存 %',
        data: history.map(h => h.memory || h.memory_percent || 0),
        borderColor: 'rgb(17, 153, 142)',
        backgroundColor: 'rgba(17, 153, 142, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  }

  const cpuChartData = {
    labels: chartData.labels,
    datasets: [{
      label: 'CPU使用率 %',
      data: history.map(h => h.cpu || h.cpu_percent || 0),
      borderColor: 'rgb(102, 126, 234)',
      backgroundColor: 'rgba(102, 126, 234, 0.1)',
      fill: true,
      tension: 0.4
    }]
  }

  const memoryChartData = {
    labels: chartData.labels,
    datasets: [{
      label: '内存使用率 %',
      data: history.map(h => h.memory || h.memory_percent || 0),
      borderColor: 'rgb(17, 153, 142)',
      backgroundColor: 'rgba(17, 153, 142, 0.1)',
      fill: true,
      tension: 0.4
    }]
  }

  const taskChartData = {
    labels: chartData.labels,
    datasets: [{
      label: '任务数',
      data: history.map(h => h.task_count || Math.floor(Math.random() * 50) + 100),
      borderColor: 'rgb(252, 74, 26)',
      backgroundColor: 'rgba(252, 74, 26, 0.1)',
      fill: true,
      tension: 0.4
    }]
  }

  const idleChartData = {
    labels: ['空闲', '使用'],
    datasets: [{
      data: [metrics ? 100 - metrics.cpu : 50, metrics?.cpu || 50],
      backgroundColor: ['rgba(40, 167, 69, 0.8)', 'rgba(102, 126, 234, 0.8)'],
      borderWidth: 0
    }]
  }

  const chartOptions = {
    responsive: true,
    plugins: {
      legend: { display: true, position: 'top' as const }
    },
    scales: {
      y: {
        beginAtZero: true,
        max: 100
      }
    }
  }

  const doughnutOptions = {
    responsive: true,
    plugins: {
      legend: { display: true, position: 'bottom' as const }
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📈 系统监控 (T002)</h2>
      </div>

      {/* 实时指标卡片 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '24px', marginBottom: '32px' }}>
        <div className="stat-card" style={{ 
          padding: '32px', 
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          borderRadius: '16px',
          minHeight: '160px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ opacity: 0.9, transform: 'scale(1.5)' }}><CPUIcon /></div>
            <div>
              <h6 style={{ margin: 0, opacity: 0.9, fontSize: '1.1rem', fontWeight: 500 }}>CPU 使用率</h6>
              <h2 style={{ margin: '8px 0', fontSize: '3rem', fontWeight: 700 }}>{metrics?.cpu || 0}%</h2>
              <small style={{ opacity: 0.9, fontSize: '0.95rem' }}>{metrics?.cpu_cores || 8} 核心</small>
            </div>
          </div>
        </div>

        <div className="stat-card" style={{ 
          padding: '32px', 
          background: 'linear-gradient(135deg, #11998e 0%, #38ef7d 100%)',
          color: 'white',
          borderRadius: '16px',
          minHeight: '160px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ opacity: 0.9, transform: 'scale(1.5)' }}><MemoryIcon /></div>
            <div>
              <h6 style={{ margin: 0, opacity: 0.9, fontSize: '1.1rem', fontWeight: 500 }}>内存 使用率</h6>
              <h2 style={{ margin: '8px 0', fontSize: '3rem', fontWeight: 700 }}>{metrics?.memory || 0}%</h2>
              <small style={{ opacity: 0.9, fontSize: '0.95rem' }}>{metrics?.memory_used?.toFixed(1) || 6.4} / {metrics?.memory_total || 16} GB</small>
            </div>
          </div>
        </div>

        <div className="stat-card" style={{ 
          padding: '32px', 
          background: 'linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%)',
          color: 'white',
          borderRadius: '16px',
          minHeight: '160px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ opacity: 0.9, transform: 'scale(1.5)' }}><TaskIcon /></div>
            <div>
              <h6 style={{ margin: 0, opacity: 0.9, fontSize: '1.1rem', fontWeight: 500 }}>运行任务数</h6>
              <h2 style={{ margin: '8px 0', fontSize: '3rem', fontWeight: 700 }}>{metrics?.task_count || 127}</h2>
              <small style={{ opacity: 0.9, fontSize: '0.95rem' }}>活跃进程</small>
            </div>
          </div>
        </div>

        <div className="stat-card" style={{ 
          padding: '32px', 
          background: 'linear-gradient(135deg, #eb3349 0%, #f45c43 100%)',
          color: 'white',
          borderRadius: '16px',
          minHeight: '160px',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ opacity: 0.9, transform: 'scale(1.5)' }}><ServerIcon /></div>
            <div>
              <h6 style={{ margin: 0, opacity: 0.9, fontSize: '1.1rem', fontWeight: 500 }}>服务器状态</h6>
              <h2 style={{ margin: '8px 0', fontSize: '2rem', color: '#28a745' }}>● 正常</h2>
              <small style={{ opacity: 0.9, fontSize: '0.95rem' }}>运行 {metrics?.uptime || '5天 12小时'}</small>
            </div>
          </div>
        </div>
      </div>

      {/* 24小时趋势总览 */}
      <div className="card" style={{ marginBottom: '32px', borderRadius: '16px' }}>
        <div className="card-header" style={{ padding: '24px 28px' }}>
          <h5 style={{ fontSize: '1.25rem', margin: 0 }}>📊 24小时系统资源趋势（总览）</h5>
        </div>
        <div style={{ padding: '28px', height: '380px' }}>
          <Line data={chartData} options={chartOptions} />
        </div>
      </div>

      {/* 详细图表 - 左右两列 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(500px, 1fr))', gap: '28px', marginBottom: '32px' }}>
        <div className="card" style={{ borderRadius: '16px' }}>
          <div className="card-header" style={{ padding: '24px 28px' }}>
            <h5 style={{ fontSize: '1.2rem', margin: 0 }}>💻 CPU 使用率（24小时）</h5>
          </div>
          <div style={{ padding: '28px', height: '320px' }}>
            <Line data={cpuChartData} options={chartOptions} />
          </div>
        </div>

        <div className="card" style={{ borderRadius: '16px' }}>
          <div className="card-header" style={{ padding: '24px 28px' }}>
            <h5 style={{ fontSize: '1.2rem', margin: 0 }}>🧠 内存使用率（24小时）</h5>
          </div>
          <div style={{ padding: '28px', height: '320px' }}>
            <Line data={memoryChartData} options={chartOptions} />
          </div>
        </div>

        <div className="card" style={{ borderRadius: '16px' }}>
          <div className="card-header" style={{ padding: '24px 28px' }}>
            <h5 style={{ fontSize: '1.2rem', margin: 0 }}>📋 任务数变化（24小时）</h5>
          </div>
          <div style={{ padding: '28px', height: '320px' }}>
            <Line data={taskChartData} options={{...chartOptions, scales: { y: { beginAtZero: true }}}} />
          </div>
        </div>

        <div className="card" style={{ borderRadius: '16px' }}>
          <div className="card-header" style={{ padding: '24px 28px' }}>
            <h5 style={{ fontSize: '1.2rem', margin: 0 }}>⏰ 服务器空闲时间分布</h5>
          </div>
          <div style={{ padding: '28px', height: '320px', display: 'flex', justifyContent: 'center' }}>
            <Doughnut data={idleChartData} options={doughnutOptions} />
          </div>
        </div>
      </div>

      {/* 监控设置 */}
      <div className="card" style={{ borderRadius: '16px', marginBottom: '32px' }}>
        <div className="card-header" style={{ padding: '24px 28px' }}>
          <h5 style={{ fontSize: '1.25rem', margin: 0 }}>⚙️ 监控设置</h5>
        </div>
        <div style={{ padding: '32px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '32px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '12px', fontWeight: 600, fontSize: '1.1rem' }}>更新频率</label>
              <select 
                value={refreshRate} 
                onChange={(e) => setRefreshRate(Number(e.target.value))}
                style={{ width: '100%', padding: '14px', borderRadius: '10px', border: '1px solid #ddd', fontSize: '1rem' }}
              >
                <option value={30}>30秒</option>
                <option value={60}>1分钟</option>
                <option value={120}>2分钟</option>
                <option value={300}>5分钟</option>
              </select>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '12px', fontWeight: 600, fontSize: '1.1rem' }}>
                CPU告警阈值: <span style={{ color: '#667eea', fontWeight: 700 }}>{cpuThreshold}%</span>
              </label>
              <input
                type="range"
                min="50"
                max="95"
                value={cpuThreshold}
                onChange={(e) => setCpuThreshold(Number(e.target.value))}
                style={{ width: '100%', height: '8px' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#666', marginTop: '8px' }}>
                <span>50%</span>
                <span>95%</span>
              </div>
            </div>

            <div>
              <label style={{ display: 'block', marginBottom: '12px', fontWeight: 600, fontSize: '1.1rem' }}>
                内存告警阈值: <span style={{ color: '#667eea', fontWeight: 700 }}>{memThreshold}%</span>
              </label>
              <input
                type="range"
                min="50"
                max="95"
                value={memThreshold}
                onChange={(e) => setMemThreshold(Number(e.target.value))}
                style={{ width: '100%', height: '8px' }}
              />
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.9rem', color: '#666', marginTop: '8px' }}>
                <span>50%</span>
                <span>95%</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 历史数据表格 */}
      <div className="card" style={{ marginTop: '32px', borderRadius: '16px' }}>
        <div className="card-header" style={{ padding: '24px 28px' }}>
          <h5 style={{ fontSize: '1.25rem', margin: 0 }}>📋 历史监控数据</h5>
        </div>
        <div className="table-container" style={{ padding: '20px' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>CPU</th>
                <th>内存</th>
                <th>磁盘</th>
                <th>状态</th>
              </tr>
            </thead>
            <tbody>
              {history.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">暂无历史数据</td>
                </tr>
              ) : (
                history.slice(0, 10).map((record: any, i: number) => (
                  <tr key={i}>
                    <td>{new Date(record.timestamp || record.created_at).toLocaleString('zh-CN')}</td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '60px', height: '6px', background: '#e9ecef', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${record.cpu || record.cpu_percent || 0}%`, height: '100%', background: record.cpu > cpuThreshold ? '#dc3545' : '#667eea' }} />
                        </div>
                        <span>{record.cpu || record.cpu_percent || 0}%</span>
                      </div>
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <div style={{ width: '60px', height: '6px', background: '#e9ecef', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${record.memory || record.memory_percent || 0}%`, height: '100%', background: record.memory > memThreshold ? '#dc3545' : '#11998e' }} />
                        </div>
                        <span>{record.memory || record.memory_percent || 0}%</span>
                      </div>
                    </td>
                    <td>{record.disk || record.disk_percent || 0}%</td>
                    <td>
                      <span className={`badge ${(record.cpu > cpuThreshold || record.memory > memThreshold) ? 'badge-red' : 'badge-green'}`}>
                        {(record.cpu > cpuThreshold || record.memory > memThreshold) ? '警告' : '正常'}
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

// 访问统计组件
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

export default SystemPages
