import React, { useState, useEffect, useRef } from 'react'
import { Line } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

interface CycleData {
  time: string
  score: number
  cycle?: number
  strategy?: string
}
interface EvalData {
  cycles: CycleData[]
  tasks?: unknown
  timestamp?: string
  trend?: string
  version?: number
}
interface DaemonStatus {
  status: string
  cycle_id: string
  phase: string
  uptime: string
  pid: number
  activity: string[]
  updated_at: string
}

const COLORS = { line: '#38bdf8', fill: '#0c4a6e', bg: '#0f172a', card: '#1e293b', text: '#e2e8f0', subtext: '#94a3b8' }

const EvolutionTrend: React.FC = () => {
  const [data, setData] = useState<EvalData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [daemonStatus, setDaemonStatus] = useState<DaemonStatus | null>(null)
  const [daemonErr, setDaemonErr] = useState('')
  const [lastDataRefresh, setLastDataRefresh] = useState<string>('')
  const [dataRefreshErr, setDataRefreshErr] = useState('')
  const hasTrendDataRef = useRef(false)

  useEffect(() => {
    const fetchTrendData = () => {
      fetch('/uploads/docs/std_eval_data.json?t=' + Date.now(), { cache: 'no-store' })
        .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.json() })
        .then(d => {
          setData(d)
          hasTrendDataRef.current = true
          setError('')
          setDataRefreshErr('')
          setLastDataRefresh(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
          setLoading(false)
        })
        .catch(e => {
          const msg = String(e)
          if (!hasTrendDataRef.current) setError(msg)
          setDataRefreshErr(msg)
          setLoading(false)
        })
    }
    fetchTrendData()
    const iv = setInterval(fetchTrendData, 60000)
    return () => clearInterval(iv)
  }, [])

  useEffect(() => {
    const fetchStatus = () => {
      fetch('/api/evolution-daemon/status?t=' + Date.now(), { cache: 'no-store' })
        .then(r => r.ok ? r.json() : Promise.reject('HTTP' + r.status))
        .then(d => { if (d.data) setDaemonStatus(d.data); setDaemonErr('') })
        .catch(e => setDaemonErr(String(e)))
    }
    fetchStatus()
    const iv = setInterval(fetchStatus, 15000)
    return () => clearInterval(iv)
  }, [])

  if (loading) return (
    <div style={{ padding: '30px', minHeight: '400px', background: COLORS.bg, color: COLORS.text, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2>📊 加载进化趋势数据...</h2>
    </div>
  )
  if (error) return (
    <div style={{ padding: '30px', minHeight: '400px', background: COLORS.bg, color: '#f87171', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2>错误: {error}</h2>
    </div>
  )
  if (!data || !data.cycles || data.cycles.length === 0) return (
    <div style={{ padding: '30px', minHeight: '400px', background: COLORS.bg, color: COLORS.text, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2>暂无数据</h2>
    </div>
  )

  const cycles = data.cycles
  const scores = cycles.map(c => c.score)
  const maxScore = Math.max(...scores)
  const minScore = Math.min(...scores)
  const avgScore = +(scores.reduce((a, b) => a + b, 0) / scores.length).toFixed(2)
  const lastScore = scores[scores.length - 1]
  const firstScore = scores[0]
  const improvement = lastScore - firstScore

  const step = Math.max(1, Math.floor(cycles.length / 200))
  const sampled = cycles.filter((_, i) => i % step === 0 || i === cycles.length - 1)

  const lineData = {
    labels: sampled.map((_, i) => {
      const idx = i * step
      const label = cycles[idx]?.cycle ? '#' + cycles[idx].cycle : (idx + 1).toString()
      if (cycles.length <= 100) return label
      return idx % Math.ceil(cycles.length / 10) === 0 ? label : ''
    }),
    datasets: [{
      label: 'Score',
      data: sampled.map(c => c.score),
      borderColor: COLORS.line,
      backgroundColor: COLORS.fill,
      fill: true,
      tension: 0.3,
      pointRadius: cycles.length > 100 ? 0 : 2,
      pointHoverRadius: 4,
    }],
  }

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index' as const, intersect: false },
    plugins: {
      legend: { display: false },
      tooltip: {
        backgroundColor: '#1e293b',
        titleColor: '#e2e8f0',
        bodyColor: '#38bdf8',
        callbacks: {
          label: function(ctx: any) {
            return '评分: ' + ctx.parsed.y.toFixed(2)
          },
          title: function(items: { dataIndex: number }[]) {
            const idx = items[0].dataIndex * step
            const cyc = cycles[idx]
            if (!cyc) return ''
            const id = cyc.cycle ? '#' + cyc.cycle : '周期 ' + (idx + 1)
            return id + ' (' + (cyc.time || '') + ')'
          },
        },
      },
    },
    scales: {
      x: {
        display: cycles.length <= 100,
        ticks: { color: COLORS.subtext, maxTicksLimit: 10 },
        grid: { color: 'rgba(148,163,184,0.1)' },
      },
      y: {
        min: Math.max(0, minScore - 1),
        max: maxScore + 1,
        ticks: { color: COLORS.subtext },
        grid: { color: 'rgba(148,163,184,0.1)' },
      },
    },
  }

  const ds = daemonStatus
  const latestCycle = cycles[cycles.length - 1]
  const latestCycleLabel = latestCycle?.cycle ? '#' + latestCycle.cycle : '#' + cycles.length
  const daemonCycleLabel = ds?.cycle_id || '-'
  const isCycleBehind = Boolean(ds?.cycle_id && latestCycle?.cycle && ds.cycle_id.replace('#', '') !== String(latestCycle.cycle))
  const daemonUpdatedAt = ds?.updated_at ? new Date(ds.updated_at) : null
  const daemonLagSeconds = daemonUpdatedAt ? Math.max(0, Math.floor((Date.now() - daemonUpdatedAt.getTime()) / 1000)) : null
  const isDaemonStale = daemonLagSeconds !== null && daemonLagSeconds > 180
  const parseTodayTime = (value?: string) => {
    if (!value) return null
    const m = value.match(/(\d{1,2}):(\d{2})(?::(\d{2}))?/)
    if (!m) return null
    const d = new Date()
    d.setHours(Number(m[1]), Number(m[2]), Number(m[3] || 0), 0)
    if (d.getTime() - Date.now() > 12 * 60 * 60 * 1000) d.setDate(d.getDate() - 1)
    return d
  }
  const trendUpdatedAt = parseTodayTime(data.timestamp || latestCycle?.time)
  const trendLagSeconds = trendUpdatedAt ? Math.max(0, Math.floor((Date.now() - trendUpdatedAt.getTime()) / 1000)) : null
  const isTrendDataStale = trendLagSeconds !== null && trendLagSeconds > 600
  const formatLag = (seconds: number | null) => {
    if (seconds === null) return '-'
    if (seconds < 60) return seconds + 's'
    const minutes = Math.floor(seconds / 60)
    const remain = seconds % 60
    if (minutes < 60) return minutes + 'm' + (remain ? remain + 's' : '')
    return Math.floor(minutes / 60) + 'h' + (minutes % 60 ? (minutes % 60) + 'm' : '')
  }

  return (
    <div style={{ padding: '20px', minHeight: 'calc(100vh - 80px)', background: COLORS.bg, color: COLORS.text, fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: '22px', marginBottom: '6px', color: COLORS.line }}>SDS 质量进化趋势</h1>
      <div style={{ fontSize: '12px', color: COLORS.subtext, marginBottom: '20px', display: 'flex', flexWrap: 'wrap', gap: '10px', alignItems: 'center' }}>
        <span>共 {cycles.length} 个进化周期</span>
        <span>· 数据文件更新: {data.timestamp || '近期'}{trendLagSeconds !== null ? ` (${formatLag(trendLagSeconds)} 前)` : ''}</span>
        <span>· 页面刷新: {lastDataRefresh || '-'}</span>
        <span>· 最新周期: {latestCycleLabel} ({latestCycle?.time || '-'})</span>
        <button
          onClick={() => window.location.reload()}
          style={{ background: COLORS.card, color: COLORS.line, border: '1px solid #334155', borderRadius: '6px', padding: '4px 8px', cursor: 'pointer', fontSize: '12px' }}
          title="强制重新加载页面"
        >手动刷新</button>
        {dataRefreshErr && <span style={{ color: '#f87171' }}>趋势数据刷新失败: {dataRefreshErr}</span>}
        {isTrendDataStale && <span style={{ color: '#f87171' }}>⚠️ 趋势数据 {formatLag(trendLagSeconds)} 未更新</span>}
        {isCycleBehind && <span style={{ color: '#fbbf24' }}>⚠️ 图表周期 {latestCycleLabel} 与守护进程 {daemonCycleLabel} 不一致，等待下一次同步</span>}
        {isDaemonStale && <span style={{ color: '#f87171' }}>⚠️ 守护进程状态 {daemonLagSeconds}s 未更新</span>}
      </div>

      {/* 两列布局：左侧趋势图，右侧指标与守护进程状态 */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(360px, 0.75fr)', gap: '16px', alignItems: 'start' }}>
        <div style={{ background: COLORS.card, borderRadius: '8px', padding: '16px', minWidth: 0 }}>
          <h3 style={{ fontSize: '15px', color: COLORS.text, marginBottom: '12px' }}>得分趋势折线图</h3>
          <div style={{ height: '520px' }}>
            <Line data={lineData} options={chartOptions} />
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', minWidth: 0 }}>
          {/* 统计卡片 */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '12px' }}>
            {[
              { label: '最新得分', value: lastScore.toFixed(2), color: '#38bdf8' },
              { label: '最高得分', value: maxScore.toFixed(2), color: '#34d399' },
              { label: '最低得分', value: minScore.toFixed(2), color: '#f87171' },
              { label: '平均得分', value: avgScore.toFixed(2), color: '#a78bfa' },
              { label: '改善幅度', value: (improvement > 0 ? '+' : '') + improvement.toFixed(2), color: improvement >= 0 ? '#34d399' : '#f87171' },
              { label: '版本', value: data.version || '-', color: '#fbbf24' },
            ].map((c, i) => (
              <div key={i} style={{ background: COLORS.card, borderRadius: '8px', padding: '14px', borderLeft: '3px solid ' + c.color }}>
                <div style={{ fontSize: '11px', color: COLORS.subtext, marginBottom: '4px' }}>{c.label}</div>
                <div style={{ fontSize: '22px', fontWeight: 'bold', color: c.color }}>{c.value}</div>
              </div>
            ))}
          </div>

          <div style={{ background: COLORS.card, borderRadius: '8px', padding: '16px' }}>
            <h3 style={{ fontSize: '15px', color: COLORS.text, marginBottom: '12px' }}>🤖 守护进程实时状态</h3>
          {daemonErr && <p style={{ color: '#f87171', fontSize: '12px' }}>连接守护进程: {daemonErr}</p>}
          {ds ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
                <div style={{ padding: '8px', background: COLORS.bg, borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: COLORS.subtext }}>状态</div>
                  <div style={{ fontSize: '14px', fontWeight: 'bold', color: ds.status === 'running' ? '#34d399' : '#f87171' }}>
                    {ds.status === 'running' ? '🟢 运行中' : '🔴 已停止'}
                  </div>
                </div>
                <div style={{ padding: '8px', background: COLORS.bg, borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: COLORS.subtext }}>周期</div>
                  <div style={{ fontSize: '14px', fontWeight: 'bold', color: isCycleBehind ? '#fbbf24' : COLORS.line }}>{ds.cycle_id || '-'}</div>
                </div>
                <div style={{ padding: '8px', background: COLORS.bg, borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: COLORS.subtext }}>阶段</div>
                  <div style={{ fontSize: '13px', fontWeight: 'bold', color: '#fbbf24', wordBreak: 'break-word' }}>{ds.phase || '-'}</div>
                </div>
                <div style={{ padding: '8px', background: COLORS.bg, borderRadius: '6px' }}>
                  <div style={{ fontSize: '10px', color: COLORS.subtext }}>运行时长</div>
                  <div style={{ fontSize: '14px', fontWeight: 'bold', color: COLORS.text }}>{ds.uptime || '-'}</div>
                </div>
              </div>
              <div style={{ padding: '8px', background: COLORS.bg, borderRadius: '6px' }}>
                <div style={{ fontSize: '10px', color: COLORS.subtext, marginBottom: '4px' }}>PID</div>
                <div style={{ fontSize: '13px', fontWeight: 'bold', color: COLORS.subtext, fontFamily: 'monospace' }}>{ds.pid || '-'}</div>
              </div>
              {ds.activity && ds.activity.length > 0 && (
                <div style={{ padding: '8px', background: COLORS.bg, borderRadius: '6px', maxHeight: '600px', overflowY: 'auto' }}>
                  <div style={{ fontSize: '10px', color: COLORS.subtext, marginBottom: '4px' }}>最近活动</div>
                  {ds.activity.map((line: string, i: number) => (
                    <div key={i} style={{ fontSize: '10px', color: '#94a3b8', padding: '1px 0', fontFamily: 'monospace', lineHeight: '1.4' }}>{line}</div>
                  ))}
                </div>
              )}
              <div style={{ fontSize: '9px', color: isDaemonStale ? '#f87171' : COLORS.subtext, textAlign: 'right' }}>
                状态15秒刷新 / 图表60秒刷新 · {ds?.updated_at ? new Date(ds.updated_at).toLocaleTimeString() : '-'}
                {daemonLagSeconds !== null ? ` · ${daemonLagSeconds}s 前` : ''}
              </div>
            </div>
          ) : (
            <p style={{ color: COLORS.subtext, fontSize: '12px' }}>等待守护进程上报状态...</p>
          )}
          </div>
        </div>
      </div>
    </div>
  )
}
export default EvolutionTrend
