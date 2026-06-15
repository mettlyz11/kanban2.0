import React, { useState, useEffect } from 'react'
import { Line, Bar, Pie } from 'react-chartjs-2'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  ArcElement,
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, BarElement, Title, Tooltip, Legend, ArcElement)

interface TokenStat {
  provider: string; model: string; total_tokens: number; total_calls: number
  total_prompt_tokens: number; total_completion_tokens: number; total_cost: number
}
interface DailyStat { date: string; total_calls: number; total_tokens: number; total_cost: number }
interface CallStat { provider: string; model: string; scenario: string; total_calls: number; avg_response_time: number }
interface ActorStat { source: string; method: string; total_calls: number }
interface Overview { total_calls: number; total_tokens: number; total_cost: number; unique_providers: number; unique_models: number }
interface ApiData {
  token_stats: TokenStat[]; daily_stats: DailyStat[]; overview: Overview
  call_stats: CallStat[]; actor_stats: ActorStat[]
}

const COLORS = ['#5470c6','#91cc75','#fac858','#ee6666','#73c0de','#3ba272','#fc8452','#9a60b4','#ea7ccc','#6a0dad']

const LLMUsage: React.FC = () => {
  const [data, setData] = useState<ApiData | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/llm/usage')
      .then(r => r.json())
      .then(d => { if (d.success) setData(d.data); else setError(d.error || 'Unknown error') })
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="llm-loading"><h2>Loading LLM usage data...</h2></div>
  if (error) return <div className="llm-error"><h2>Error: {error}</h2></div>
  if (!data) return <div className="llm-empty"><h2>No data available</h2></div>

  const { overview, token_stats, daily_stats, call_stats, actor_stats } = data

  const dailyLine = {
    labels: daily_stats.map(d => d.date.slice(5)),
    datasets: [
      { label: 'Total Calls', data: daily_stats.map(d => d.total_calls), borderColor: '#5470c6', backgroundColor: '#5470c6', yAxisID: 'y', tension: 0.3 },
      { label: 'Total Tokens (M)', data: daily_stats.map(d => +(d.total_tokens / 1e6).toFixed(2)), borderColor: '#ee6666', backgroundColor: '#ee6666', yAxisID: 'y1', tension: 0.3 },
    ],
  }
  const dailyOpts = { responsive: true, interaction: { mode: 'index' as const, intersect: false }, plugins: { title: { display: true, text: 'Daily Trend (7 days)' } }, scales: { y: { type: 'linear' as const, display: true, position: 'left' as const, title: { display: true, text: 'Calls' } }, y1: { type: 'linear' as const, display: true, position: 'right' as const, grid: { drawOnChartArea: false }, title: { display: true, text: 'Tokens (M)' } } } }

  const sortedProviders = [...token_stats].sort((a,b) => b.total_tokens - a.total_tokens).slice(0, 10)
  const providerLabels = sortedProviders.map(s => (s.provider + '/' + s.model).slice(0, 40))
  const providerBar = {
    labels: providerLabels,
    datasets: [{ label: 'Total Tokens (M)', data: sortedProviders.map(s => Math.round(s.total_tokens / 1e6 * 100) / 100), backgroundColor: sortedProviders.map((_,i) => COLORS[i % COLORS.length]) }],
  }
  const providerOpts = { responsive: true, indexAxis: 'y' as const, plugins: { title: { display: true, text: 'Top 10 Models by Token' } } }

  const scenarioCalls: Record<string,number> = {}
  call_stats.forEach(c => { scenarioCalls[c.scenario] = (scenarioCalls[c.scenario] || 0) + c.total_calls })
  const sortedScenarios = Object.entries(scenarioCalls).sort((a,b) => b[1] - a[1]).slice(0, 8)
  const pieChart = { labels: sortedScenarios.map(s => s[0]), datasets: [{ label: 'Calls by Scenario', data: sortedScenarios.map(s => s[1]), backgroundColor: COLORS.slice(0, sortedScenarios.length), borderWidth: 1 }] }

  const infoCards = [
    { label: 'Total Calls (30d)', value: (overview.total_calls || 0).toLocaleString(), color: '#5470c6' },
    { label: 'Total Tokens (30d)', value: ((overview.total_tokens || 0) / 1e6).toFixed(1) + 'M', color: '#91cc75' },
    { label: 'Providers', value: String(overview.unique_providers || 0), color: '#fac858' },
    { label: 'Models', value: String(overview.unique_models || 0), color: '#ee6666' },
  ]

  return (
    <div style={{ padding: '20px', maxWidth: '1400px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: '24px', marginBottom: '20px' }}>LLM Usage Monitor</h1>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: '15px', marginBottom: '25px' }}>
        {infoCards.map((c,i) => (
          <div key={i} style={{ background: '#fff', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)', borderLeft: '4px solid ' + c.color }}>
            <div style={{ fontSize: '13px', color: '#666', marginBottom: '5px' }}>{c.label}</div>
            <div style={{ fontSize: '28px', fontWeight: 'bold', color: '#333' }}>{c.value}</div>
          </div>
        ))}
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '25px' }}>
        <div style={{ background: '#fff', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}><Line data={dailyLine} options={dailyOpts} /></div>
        <div style={{ background: '#fff', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}><Bar data={providerBar} options={providerOpts} /></div>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '25px' }}>
        <div style={{ background: '#fff', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}><Pie data={pieChart} options={{ plugins: { title: { display: true, text: 'Calls by Scenario' } } }} /></div>
        <div style={{ background: '#fff', borderRadius: '10px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.1)' }}>
          <h3 style={{ marginBottom: '15px' }}>Actor LLM Invocations</h3>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
            <thead><tr style={{ background: '#f5f5f5' }}>
              <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Source</th>
              <th style={{ padding: '8px', textAlign: 'left', borderBottom: '1px solid #ddd' }}>Method</th>
              <th style={{ padding: '8px', textAlign: 'right', borderBottom: '1px solid #ddd' }}>Calls</th>
            </tr></thead>
            <tbody>{actor_stats.filter(a => a.total_calls > 0).map((a,i) => (
              <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                <td style={{ padding: '6px 8px' }}>{a.source}</td>
                <td style={{ padding: '6px 8px' }}>{a.method}</td>
                <td style={{ padding: '6px 8px', textAlign: 'right', fontWeight: 'bold' }}>{a.total_calls.toLocaleString()}</td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
export default LLMUsage
