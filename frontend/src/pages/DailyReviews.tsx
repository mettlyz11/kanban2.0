import { useState, useEffect } from 'react'
import { Plus, BookOpen, Calendar, TrendingUp } from 'lucide-react'

export function DailyReviews() {
  const [reviews, setReviews] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [showAddModal, setShowAddModal] = useState(false)
  const [reviewDate, setReviewDate] = useState('')
  const [mood, setMood] = useState('')
  const [summary, setSummary] = useState('')

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

  const handleCreateReview = async () => {
    if (!reviewDate || !summary) {
      alert('请填写日期和总结内容')
      return
    }
    
    try {
      const res = await fetch('/api/daily-reviews', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ review_date: reviewDate, mood, summary })
      })
      const data = await res.json()
      if (data.success) {
        alert('复盘创建成功！')
        setShowAddModal(false)
        setReviewDate('')
        setMood('')
        setSummary('')
        loadReviews()
      }
    } catch (e) {
      console.error(e)
      alert('创建失败')
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🔄 每日复盘 (T013)</h2>
        <button
          onClick={() => setShowAddModal(true)}
          className="btn btn-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '8px' }}
        >
          <Plus size={20} />
          创建复盘
        </button>
      </div>

      {/* 使用说明卡片 */}
      <div className="card" style={{ marginBottom: '20px', background: '#f0f9ff', border: '1px solid #bae6fd' }}>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
          <BookOpen size={24} className="text-blue-600" style={{ flexShrink: 0 }} />
          <div>
            <h4 style={{ margin: '0 0 8px 0', color: '#0369a1' }}>每日复盘说明</h4>
            <ul style={{ margin: 0, paddingLeft: '20px', color: '#0c4a6e', lineHeight: '1.6' }}>
              <li>每天花 5-10 分钟记录当天的工作和收获</li>
              <li>记录完成的任务、遇到的问题和解决方案</li>
              <li>规划明天的重要事项</li>
              <li>定期回顾可以发现改进点和成长轨迹</li>
            </ul>
          </div>
        </div>
      </div>

      <div className="card">
        {reviews.length === 0 ? (
          <div className="empty-state">
            <div className="empty-state-icon">📝</div>
            <h3 style={{ margin: '16px 0 8px', color: '#374151' }}>还没有复盘记录</h3>
            <p style={{ color: '#6b7280', marginBottom: '20px' }}>
              开始你的第一次每日复盘，记录成长和收获
            </p>
            <button
              onClick={() => setShowAddModal(true)}
              className="btn btn-primary"
              style={{ display: 'flex', alignItems: 'center', gap: '8px', margin: '0 auto' }}
            >
              <Plus size={20} />
              创建第一个复盘
            </button>
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

      {/* 创建复盘弹窗 */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-lg p-6 w-full max-w-2xl">
            <h3 className="text-lg font-bold mb-4">📝 创建每日复盘</h3>
            
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <Calendar size={16} className="inline mr-1" />
                复盘日期
              </label>
              <input
                type="date"
                value={reviewDate}
                onChange={(e) => setReviewDate(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
                max={new Date().toISOString().split('T')[0]}
              />
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                <TrendingUp size={16} className="inline mr-1" />
                今日心情
              </label>
              <div className="flex gap-2">
                {['😄 很好', '😊 不错', '😐 一般', '😔 有点累', '😫 很累'].map((emoji) => (
                  <button
                    key={emoji}
                    onClick={() => setMood(emoji)}
                    className={`flex-1 px-3 py-2 rounded-lg border ${
                      mood === emoji
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'bg-white text-gray-700 border-gray-300 hover:bg-gray-50'
                    }`}
                  >
                    {emoji}
                  </button>
                ))}
              </div>
            </div>

            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                复盘总结
              </label>
              <textarea
                value={summary}
                onChange={(e) => setSummary(e.target.value)}
                placeholder="今天完成了什么？遇到了什么问题？有什么收获？明天计划做什么？"
                rows={6}
                className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
              />
            </div>

            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowAddModal(false)
                  setReviewDate('')
                  setMood('')
                  setSummary('')
                }}
                className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleCreateReview}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                保存复盘
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default DailyReviews
