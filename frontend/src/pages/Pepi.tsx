import { useState, useEffect } from 'react'

// 引入PepiWorkHistory组件
import PepiWorkHistory from '../components/PepiWorkHistory'

export function Pepi() {
  const [info, setInfo] = useState<any>(null)
  const [evaluations, setEvaluations] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [activeTab, setActiveTab] = useState<'evaluations' | 'work_history'>('evaluations')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [infoRes, evalRes] = await Promise.all([
        fetch('/api/pepi/info').then(r => r.json()),
        fetch('/api/pepi/evaluations').then(r => r.json())
      ])
      
      if (infoRes.success) setInfo(infoRes.info)
      if (evalRes.success) setEvaluations(evalRes.evaluations || [])
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
        <h2 className="page-title">🤖 Pepi 数字员工</h2>
      </div>

      {/* Pepi信息卡片 */}
      {info && (
        <div className="card" style={{ marginBottom: '24px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '24px' }}>
            <div style={{
              width: '120px',
              height: '120px',
              borderRadius: '50%',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '4rem'
            }}>
              🤖
            </div>
            <div style={{ flex: 1 }}>
              <h3 style={{ marginBottom: '8px' }}>{info.name || 'Pepi'}</h3>
              <p style={{ color: '#666', marginBottom: '12px' }}>
                {info.description || 'AI驱动的数字员工系统'}
              </p>
              <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                <span className="badge badge-blue">版本: {info.version || '1.0'}</span>
                <span className={`badge ${info.status === 'active' ? 'badge-green' : 'badge-gray'}`}>
                  {info.status === 'active' ? '运行中' : '离线'}
                </span>
                <span className="badge badge-purple">
                  任务完成: {info.tasks_completed || 0}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 统计卡片 */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card blue">
          <div className="stat-icon">✅</div>
          <div className="stat-info">
            <h3>{info?.tasks_completed || 0}</h3>
            <p>完成任务</p>
          </div>
        </div>
        <div className="stat-card green">
          <div className="stat-icon">⭐</div>
          <div className="stat-info">
            <h3>{info?.avg_rating?.toFixed(1) || '4.5'}</h3>
            <p>平均评分</p>
          </div>
        </div>
        <div className="stat-card purple">
          <div className="stat-icon">🕐</div>
          <div className="stat-info">
            <h3>{info?.total_hours || 0}h</h3>
            <p>工作时长</p>
          </div>
        </div>
        <div className="stat-card orange">
          <div className="stat-icon">📅</div>
          <div className="stat-info">
            <h3>{evaluations.length}</h3>
            <p>评估记录</p>
          </div>
        </div>
        <div className="stat-card red">
          <div className="stat-icon">🎬</div>
          <div className="stat-info">
            <h3>🎥</h3>
            <p>工作GIF</p>
          </div>
        </div>
      </div>

      {/* 标签页切换 */}
      <div className="tabs" style={{ marginBottom: '20px' }}>
        <button 
          className={`tab-btn ${activeTab === 'evaluations' ? 'active' : ''}`}
          onClick={() => setActiveTab('evaluations')}
        >
          📋 评估记录
        </button>
        <button 
          className={`tab-btn ${activeTab === 'work_history' ? 'active' : ''}`}
          onClick={() => setActiveTab('work_history')}
        >
          🎬 工作历史 (GIF)
        </button>
      </div>

      {/* 评估记录 */}
      {activeTab === 'evaluations' && (
        <div className="card">
          <div className="card-header">
            <h5>评估记录</h5>
          </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>日期</th>
                <th>任务类型</th>
                <th>完成质量</th>
                <th>评分</th>
                <th>备注</th>
              </tr>
            </thead>
            <tbody>
              {evaluations.length === 0 ? (
                <tr>
                  <td colSpan={5} className="empty-state">暂无评估记录</td>
                </tr>
              ) : (
                evaluations.map(eval_ => (
                  <tr key={eval_.id}>
                    <td>{new Date(eval_.eval_date).toLocaleDateString('zh-CN')}</td>
                    <td>{eval_.task_type || '-'}</td>
                    <td>
                      <div style={{
                        width: '100px',
                        height: '8px',
                        background: '#e9ecef',
                        borderRadius: '4px',
                        overflow: 'hidden'
                      }}>
                        <div style={{
                          width: `${(eval_.quality_score || 0) * 10}%`,
                          height: '100%',
                          background: '#667eea'
                        }}/>
                      </div>
                    </td>
                    <td>
                      <span style={{
                        color: (eval_.rating || 0) >= 4 ? '#28a745' : (eval_.rating || 0) >= 3 ? '#f57c00' : '#dc3545',
                        fontWeight: 600
                      }}>
                        {eval_.rating || '-'}/5
                      </span>
                    </td>
                    <td>{eval_.notes || '-'}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
      )}

      {/* 工作历史 (GIF) */}
      {activeTab === 'work_history' && (
        <PepiWorkHistory />
      )}
    </div>
  )
}

export default Pepi
