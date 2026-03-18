import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { 
  LineChart, 
  Line, 
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  Legend, 
  ResponsiveContainer,
  AreaChart,
  Area
} from 'recharts'
import { Activity, Cpu, HardDrive, Database, RefreshCw, Calendar } from 'lucide-react'

interface MetricPoint {
  timestamp: string
  cpu: number
  memory: number
  disk: number
  timestamp_formatted?: string
}

interface StatsSummary {
  cpu_avg: number
  cpu_max: number
  memory_avg: number
  memory_max: number
  disk_avg: number
  disk_current: number
}

export function ResourceMonitor() {
  const [metrics, setMetrics] = useState<MetricPoint[]>([])
  const [loading, setLoading] = useState(true)
  const [timeRange, setTimeRange] = useState<'1h' | '6h' | '24h' | '7d'>('24h')
  const [stats, setStats] = useState<StatsSummary | null>(null)

  useEffect(() => {
    loadMetrics()
    // 自动刷新（每30秒）
    const interval = setInterval(loadMetrics, 30000)
    return () => clearInterval(interval)
  }, [timeRange])

  const loadMetrics = async () => {
    try {
      setLoading(true)
      const data = await api.getMetricsHistory(timeRange)
      if (data.success && data.metrics) {
        // 格式化数据
        const formattedData = data.metrics.map((m: MetricPoint) => ({
          ...m,
          timestamp_formatted: formatTimestamp(m.timestamp, timeRange)
        }))
        setMetrics(formattedData)
        setStats(calculateStats(formattedData))
      }
    } catch (e) {
      console.error('Failed to load metrics:', e)
      // 使用模拟数据
      const mockData = generateMockData(timeRange)
      setMetrics(mockData)
      setStats(calculateStats(mockData))
    } finally {
      setLoading(false)
    }
  }

  const formatTimestamp = (timestamp: string, range: string): string => {
    const date = new Date(timestamp)
    if (range === '1h' || range === '6h') {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } else if (range === '24h') {
      return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    } else {
      return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    }
  }

  const calculateStats = (data: MetricPoint[]): StatsSummary => {
    if (data.length === 0) {
      return { cpu_avg: 0, cpu_max: 0, memory_avg: 0, memory_max: 0, disk_avg: 0, disk_current: 0 }
    }

    const cpuValues = data.map(d => d.cpu)
    const memoryValues = data.map(d => d.memory)
    const diskValues = data.map(d => d.disk)

    return {
      cpu_avg: Math.round(cpuValues.reduce((a, b) => a + b, 0) / cpuValues.length),
      cpu_max: Math.round(Math.max(...cpuValues)),
      memory_avg: Math.round(memoryValues.reduce((a, b) => a + b, 0) / memoryValues.length),
      memory_max: Math.round(Math.max(...memoryValues)),
      disk_avg: Math.round(diskValues.reduce((a, b) => a + b, 0) / diskValues.length),
      disk_current: Math.round(diskValues[diskValues.length - 1] || 0)
    }
  }

  const getStatusColor = (value: number) => {
    if (value < 60) return '#28a745'
    if (value < 80) return '#ffc107'
    return '#dc3545'
  }

  const getStatusText = (value: number) => {
    if (value < 60) return '正常'
    if (value < 80) return '警告'
    return '危险'
  }

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📊 系统资源监控</h2>
        <button 
          className="btn btn-secondary"
          onClick={loadMetrics}
          disabled={loading}
          style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
        >
          <RefreshCw size={16} className={loading ? 'spin' : ''} />
          刷新
        </button>
      </div>

      {/* 时间范围选择 */}
      <div className="filter-bar" style={{ marginBottom: '24px' }}>
        {[
          { key: '1h', label: '最近1小时' },
          { key: '6h', label: '最近6小时' },
          { key: '24h', label: '最近24小时' },
          { key: '7d', label: '最近7天' }
        ].map(item => (
          <button
            key={item.key}
            className={`filter-btn ${timeRange === item.key ? 'active' : ''}`}
            onClick={() => setTimeRange(item.key as any)}
          >
            <Calendar size={14} style={{ marginRight: '4px', verticalAlign: 'middle' }} />
            {item.label}
          </button>
        ))}
      </div>

      {/* 统计概览卡片 */}
      {stats && (
        <div className="stats-grid" style={{ marginBottom: '24px' }}>
          <StatCard 
            icon={<Cpu size={24} />}
            title="CPU 使用率"
            value={`${stats.cpu_avg}%`}
            subtitle={`峰值: ${stats.cpu_max}%`}
            color={getStatusColor(stats.cpu_avg)}
            status={getStatusText(stats.cpu_avg)}
          />
          <StatCard 
            icon={<Activity size={24} />}
            title="内存使用率"
            value={`${stats.memory_avg}%`}
            subtitle={`峰值: ${stats.memory_max}%`}
            color={getStatusColor(stats.memory_avg)}
            status={getStatusText(stats.memory_avg)}
          />
          <StatCard 
            icon={<Database size={24} />}
            title="磁盘使用率"
            value={`${stats.disk_current}%`}
            subtitle={`平均: ${stats.disk_avg}%`}
            color={getStatusColor(stats.disk_current)}
            status={getStatusText(stats.disk_current)}
          />
          <StatCard 
            icon={<HardDrive size={24} />}
            title="数据点"
            value={metrics.length}
            subtitle="监控记录数"
            color="#667eea"
            status="正常"
          />
        </div>
      )}

      {/* 趋势图表 */}
      <div className="card" style={{ marginBottom: '24px' }}>
        <h3 style={{ marginBottom: '20px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Activity size={20} color="#667eea" />
          资源使用趋势
        </h3>
        
        {loading ? (
          <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
            加载数据中...
          </div>
        ) : metrics.length === 0 ? (
          <div style={{ height: '400px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
            暂无数据
          </div>
        ) : (
          <div style={{ height: '400px' }}>
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={metrics} margin={{ top: 10, right: 30, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="colorCpu" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#667eea" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#667eea" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorMemory" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#28a745" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#28a745" stopOpacity={0}/>
                  </linearGradient>
                  <linearGradient id="colorDisk" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#ffc107" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#ffc107" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                <XAxis 
                  dataKey="timestamp_formatted" 
                  stroke="#999"
                  fontSize={12}
                  tickMargin={10}
                />
                <YAxis 
                  stroke="#999"
                  fontSize={12}
                  domain={[0, 100]}
                  tickFormatter={(value) => `${value}%`}
                />
                <Tooltip 
                  contentStyle={{ 
                    background: '#fff', 
                    border: '1px solid #e0e0e0', 
                    borderRadius: '8px',
                    boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                  }}
                  formatter={(value: any) => [`${value}%`]}
                />
                <Legend />
                <Area 
                  type="monotone" 
                  dataKey="cpu" 
                  name="CPU使用率"
                  stroke="#667eea" 
                  fillOpacity={1} 
                  fill="url(#colorCpu)" 
                  strokeWidth={2}
                />
                <Area 
                  type="monotone" 
                  dataKey="memory" 
                  name="内存使用率"
                  stroke="#28a745" 
                  fillOpacity={1} 
                  fill="url(#colorMemory)" 
                  strokeWidth={2}
                />
                <Area 
                  type="monotone" 
                  dataKey="disk" 
                  name="磁盘使用率"
                  stroke="#ffc107" 
                  fillOpacity={1} 
                  fill="url(#colorDisk)" 
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>

      {/* 详细图表 - 各资源单独展示 */}
      <div className="grid-2">
        <ResourceChart 
          title="CPU 使用率趋势"
          data={metrics}
          dataKey="cpu"
          color="#667eea"
          loading={loading}
        />
        <ResourceChart 
          title="内存使用率趋势"
          data={metrics}
          dataKey="memory"
          color="#28a745"
          loading={loading}
        />
      </div>

      {/* 添加CSS动画 */}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        .spin {
          animation: spin 1s linear infinite;
        }
      `}</style>
    </div>
  )
}

function StatCard({ 
  icon, 
  title, 
  value, 
  subtitle, 
  color, 
  status 
}: { 
  icon: React.ReactNode
  title: string
  value: string | number
  subtitle: string
  color: string
  status: string
}) {
  return (
    <div className="card stat-card-enhanced" style={{
      display: 'flex',
      alignItems: 'center',
      gap: '16px',
      padding: '20px'
    }}>
      <div style={{
        width: '56px',
        height: '56px',
        borderRadius: '12px',
        background: `${color}20`,
        color: color,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center'
      }}>
        {icon}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontSize: '0.85rem', color: '#666', marginBottom: '4px' }}>{title}</div>
        <div style={{ fontSize: '1.8rem', fontWeight: 700, color, marginBottom: '4px' }}>{value}</div>
        <div style={{ fontSize: '0.75rem', color: '#999' }}>{subtitle}</div>
      </div>
      <div style={{
        padding: '6px 12px',
        borderRadius: '12px',
        fontSize: '0.75rem',
        fontWeight: 600,
        background: `${color}20`,
        color: color
      }}>
        {status}
      </div>
    </div>
  )
}

function ResourceChart({ 
  title, 
  data, 
  dataKey, 
  color, 
  loading 
}: { 
  title: string
  data: MetricPoint[]
  dataKey: keyof MetricPoint
  color: string
  loading: boolean
}) {
  return (
    <div className="card">
      <h4 style={{ marginBottom: '16px', fontSize: '1rem', color: '#333' }}>{title}</h4>
      {loading ? (
        <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
          加载中...
        </div>
      ) : data.length === 0 ? (
        <div style={{ height: '250px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#999' }}>
          暂无数据
        </div>
      ) : (
        <div style={{ height: '250px' }}>
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
              <XAxis 
                dataKey="timestamp_formatted" 
                stroke="#999"
                fontSize={11}
                tickMargin={8}
              />
              <YAxis 
                stroke="#999"
                fontSize={11}
                domain={[0, 100]}
                tickFormatter={(value) => `${value}%`}
              />
              <Tooltip 
                contentStyle={{ 
                  background: '#fff', 
                  border: '1px solid #e0e0e0', 
                  borderRadius: '8px'
                }}
                formatter={(value: any) => [`${value}%`]}
              />
              <Line 
                type="monotone" 
                dataKey={dataKey} 
                stroke={color} 
                strokeWidth={2}
                dot={false}
                activeDot={{ r: 6, strokeWidth: 0 }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  )
}

// 生成模拟数据
function generateMockData(timeRange: string): MetricPoint[] {
  const now = new Date()
  const points: MetricPoint[] = []
  let count = 24
  let interval = 60 * 60 * 1000 // 1小时

  switch (timeRange) {
    case '1h':
      count = 12
      interval = 5 * 60 * 1000 // 5分钟
      break
    case '6h':
      count = 24
      interval = 15 * 60 * 1000 // 15分钟
      break
    case '24h':
      count = 24
      interval = 60 * 60 * 1000 // 1小时
      break
    case '7d':
      count = 28
      interval = 6 * 60 * 60 * 1000 // 6小时
      break
  }

  for (let i = count - 1; i >= 0; i--) {
    const timestamp = new Date(now.getTime() - i * interval)
    points.push({
      timestamp: timestamp.toISOString(),
      cpu: Math.floor(Math.random() * 40) + 20 + (Math.random() > 0.8 ? 30 : 0), // 20-60% + 偶尔峰值
      memory: Math.floor(Math.random() * 30) + 40, // 40-70%
      disk: Math.floor(Math.random() * 10) + 55 // 55-65%
    })
  }

  return points
}
