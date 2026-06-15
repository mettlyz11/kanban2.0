import { useState, useEffect } from 'react'

export default function ResearchDaily() {
  const [reports, setReports] = useState<any[]>([])
  const [selected, setSelected] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    fetch('/api/research-daily/list')
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          setReports(data.reports || [])
          if (data.reports?.length > 0) {
            setSelected(data.reports[0])
          }
        }
      })
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [])

  const loadReport = (report: any) => {
    setSelected(report)
    fetch(`/api/research-daily/content?file=${encodeURIComponent(report.filename)}`)
      .then(r => r.json())
      .then(data => {
        if (data.success) {
          setSelected({ ...report, content: data.content })
        }
      })
      .catch(console.error)
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🔬 AI+材料科学日报</h2>
      </div>

      <div style={{ display: 'flex', gap: '20px' }}>
        {/* 左侧列表 */}
        <div className="card" style={{ width: 280, minWidth: 280, height: 'fit-content' }}>
          <h5>📋 报告列表</h5>
          <div style={{ marginTop: 12, display: 'flex', flexDirection: 'column', gap: 4 }}>
            {reports.length === 0 ? (
              <p style={{ color: '#999', fontSize: '0.85rem' }}>暂无报告</p>
            ) : reports.map((r, i) => (
              <div key={i}
                onClick={() => loadReport(r)}
                style={{
                  padding: '10px 12px',
                  borderRadius: 6,
                  cursor: 'pointer',
                  background: selected?.filename === r.filename ? '#667eea' : '#f8f9fa',
                  color: selected?.filename === r.filename ? 'white' : '#333',
                  fontSize: '0.85rem',
                  transition: 'all 0.2s',
                }}
              >
                <div style={{ fontWeight: 600 }}>{r.date}</div>
                <div style={{ opacity: 0.7, fontSize: '0.8rem', marginTop: 4 }}>
                  {r.summary?.substring(0, 50)}{r.summary?.length > 50 ? '...' : ''}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 右侧内容 */}
        <div className="card" style={{ flex: 1 }}>
          {selected ? (
            <>
              <h4>{selected.date} 报告</h4>
              {selected.content ? (
                <div style={{ 
                  marginTop: 16, 
                  lineHeight: 1.8, 
                  fontSize: '0.9rem',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word',
                }}>
                  {selected.content}
                </div>
              ) : (
                <div className="loading" style={{ marginTop: 40 }}>加载报告内容...</div>
              )}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-state-icon">🔬</div>
              <p>选择左侧报告查看详情</p>
              <p style={{ fontSize: '0.85rem', color: '#999' }}>每天 9:35 AM 自动更新</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
