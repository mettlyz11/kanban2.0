import { useState, useEffect } from 'react'

export function DailyReviews() {
  const [reviews, setReviews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadReviews()
  }, [])

  const loadReviews = async () => {
    try {
      const res = await fetch('/api/daily-reviews')
      const data = await res.json()
      if (data.success) setReviews(data.reviews || [])
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
        <h2 className="page-title">🔄 每日复盘 (T013)</h2>
      </div>

      <div className="card">
        {reviews.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">🔄</div>
            <p>暂无复盘记录</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            {reviews.map((review: any, i: number) => (
              <div key={i} style={{
                padding: '20px',
                background: '#f8f9fa',
                borderRadius: '8px',
                borderLeft: '4px solid #11998e'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <h4 style={{ margin: 0 }}>{review.review_date || '未命名复盘'}</h4>
                  <span className="badge badge-green">{review.mood || '正常'}</span>
                </div>
                <p style={{ color: '#666' }}>{review.summary || review.content || ''}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
