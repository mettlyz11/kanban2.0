import { useState, useEffect } from 'react'
import { Activity, CheckCircle, AlertCircle, Clock, RefreshCw, Play, Database, Zap, Beaker } from 'lucide-react'

interface CalcTask {
  id: string
  smiles: string
  basis_set: string
  functional: string
  status: string
  method: string
  total_energy: number
  activation_energy: number
  reaction_energy: number
  homo_energy: number
  lumo_energy: number
  dipole_moment: number
  created_at: string
}

interface CalcStats {
  total: number
  running: number
  completed: number
  failed: number
}

export function CalcTasks() {
  const [tasks, setTasks] = useState<CalcTask[]>([])
  const [stats, setStats] = useState<CalcStats>({ total: 0, running: 0, completed: 0, failed: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [lastSync, setLastSync] = useState<Date | null>(null)

  const fetchTasks = async () => {
    try {
      const response = await fetch('/api/calc-tasks')
      const data = await response.json()
      if (data.success) {
        setTasks(data.tasks)
        setLastSync(new Date())
      }
    } catch (err) {
      setError('获取任务列表失败')
    }
  }

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/calc-tasks/stats')
      const data = await response.json()
      if (data.success) {
        setStats(data.stats)
      }
    } catch (err) {
      console.error('获取统计失败:', err)
    }
  }

  const syncTasks = async () => {
    setLoading(true)
    try {
      await fetchTasks()
      await fetchStats()
    } catch (err) {
      setError('同步任务失败')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const loadData = async () => {
      setLoading(true)
      await Promise.all([fetchTasks(), fetchStats()])
      setLoading(false)
    }
    loadData()

    const interval = setInterval(() => {
      fetchTasks()
      fetchStats()
    }, 30000)

    return () => clearInterval(interval)
  }, [])

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed': return '#10b981'
      case 'running': return '#3b82f6'
      case 'pending': return '#f59e0b'
      case 'error': case 'failed': return '#ef4444'
      default: return '#6b7280'
    }
  }

  const formatSmiles = (smiles: string) => {
    if (!smiles) return '-'
    return smiles.length > 30 ? smiles.substring(0, 30) + '...' : smiles
  }

  const formatEnergy = (value: number) => {
    if (value === null || value === undefined) return '-'
    return value.toFixed(4)
  }

  return (
    <div className="calc-tasks-page" style={{ padding: '20px' }}>
      <div style={{ marginBottom: '24px' }}>
        <h2 style={{ margin: 0, color: '#1f2937' }}>T109 量子化学计算平台</h2>
        <p style={{ color: '#6b7280', marginTop: '8px' }}>实时监控分子计算任务队列</p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div style={{ background: 'linear-gradient(135deg, #667eea, #764ba2)', padding: '20px', borderRadius: '12px', color: 'white' }}>
          <Database size={24} />
          <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '8px' }}>总任务数</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.total}</div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, #3b82f6, #1d4ed8)', padding: '20px', borderRadius: '12px', color: 'white' }}>
          <Activity size={24} />
          <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '8px' }}>运行中</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.running}</div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, #10b981, #059669)', padding: '20px', borderRadius: '12px', color: 'white' }}>
          <CheckCircle size={24} />
          <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '8px' }}>已完成</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.completed}</div>
        </div>
        <div style={{ background: 'linear-gradient(135deg, #ef4444, #dc2626)', padding: '20px', borderRadius: '12px', color: 'white' }}>
          <AlertCircle size={24} />
          <div style={{ fontSize: '0.9rem', opacity: 0.9, marginTop: '8px' }}>失败</div>
          <div style={{ fontSize: '2rem', fontWeight: 'bold' }}>{stats.failed}</div>
        </div>
      </div>

      <div style={{ background: 'white', padding: '16px', borderRadius: '8px', marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={syncTasks} disabled={loading} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: '#667eea', color: 'white', border: 'none', borderRadius: '8px', cursor: loading ? 'not-allowed' : 'pointer' }}>
            <RefreshCw size={16} />
            刷新任务
          </button>
          <a href="http://60.205.197.9:8000/docs" target="_blank" rel="noopener noreferrer" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 20px', background: '#f3f4f6', color: '#374151', borderRadius: '8px', textDecoration: 'none' }}>
            <Play size={16} />
            T109 API
          </a>
        </div>
        {lastSync && <div style={{ color: '#6b7280', fontSize: '0.9rem' }}>最后同步: {lastSync.toLocaleTimeString()}</div>}
      </div>

      <div style={{ background: 'white', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <div style={{ padding: '16px 20px', borderBottom: '1px solid #e5e7eb', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Zap size={20} color="#667eea" />
            <h5 style={{ margin: 0 }}>计算任务队列</h5>
          </div>
          <span style={{ background: '#f3f4f6', padding: '4px 12px', borderRadius: '12px', fontSize: '0.85rem' }}>{tasks.length} 个任务</span>
        </div>

        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center' }}>加载中...</div>
        ) : tasks.length === 0 ? (
          <div style={{ padding: '60px', textAlign: 'center' }}>
            <Beaker size={48} color="#d1d5db" />
            <p style={{ color: '#6b7280' }}>暂无计算任务</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ background: '#f9fafb' }}>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', color: '#6b7280' }}>状态</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', color: '#6b7280' }}>SMILES</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', color: '#6b7280' }}>基组</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', color: '#6b7280' }}>总能</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', color: '#6b7280' }}>活化能</th>
                  <th style={{ padding: '12px 16px', textAlign: 'left', fontSize: '0.85rem', color: '#6b7280' }}>创建时间</th>
                </tr>
              </thead>
              <tbody>
                {tasks.map((task, index) => (
                  <tr key={task.id} style={{ borderBottom: '1px solid #e5e7eb', background: index % 2 === 0 ? 'white' : '#f9fafb' }}>
                    <td style={{ padding: '12px 16px' }}>
                      <span style={{ color: getStatusColor(task.status), fontWeight: 500 }}>{task.status || 'unknown'}</span>
                    </td>
                    <td style={{ padding: '12px 16px', fontSize: '0.85rem', fontFamily: 'monospace' }}>{formatSmiles(task.smiles)}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.85rem' }}>{task.basis_set || '-'}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.85rem', fontFamily: 'monospace' }}>{formatEnergy(task.total_energy)}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.85rem', fontFamily: 'monospace' }}>{formatEnergy(task.activation_energy)}</td>
                    <td style={{ padding: '12px 16px', fontSize: '0.85rem', color: '#6b7280' }}>{task.created_at ? new Date(task.created_at).toLocaleString() : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <div style={{ background: 'white', padding: '20px', borderRadius: '8px', marginTop: '24px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
        <h5 style={{ margin: '0 0 16px 0' }}>T109服务器信息</h5>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '16px' }}>
          <div><div style={{ fontSize: '0.85rem', color: '#6b7280' }}>服务器地址</div><div>60.205.197.9:8000</div></div>
          <div><div style={{ fontSize: '0.85rem', color: '#6b7280' }}>API文档</div><a href="http://60.205.197.9:8000/docs" target="_blank" style={{ color: '#667eea' }}>Swagger UI</a></div>
          <div><div style={{ fontSize: '0.85rem', color: '#6b7280' }}>数据库</div><div>阿里云 RDS</div></div>
          <div><div style={{ fontSize: '0.85rem', color: '#6b7280' }}>表名</div><div>t109_calculations</div></div>
        </div>
      </div>
    </div>
  )
}

export default CalcTasks
