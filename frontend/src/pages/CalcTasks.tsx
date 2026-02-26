import { useState } from 'react'

export function CalcTasks() {
  const [activeTab, setActiveTab] = useState('submit')

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🔢 计算任务 (T109)</h2>
      </div>

      {/* Tab切换 */}
      <div className="filter-bar" style={{ marginBottom: '16px' }}>
        <button 
          className={`filter-btn ${activeTab === 'submit' ? 'active' : ''}`}
          onClick={() => setActiveTab('submit')}
        >
          📝 提交任务
        </button>
        <button 
          className={`filter-btn ${activeTab === 'results' ? 'active' : ''}`}
          onClick={() => setActiveTab('results')}
        >
          📊 查看结果
        </button>
        <button 
          className={`filter-btn ${activeTab === 'tasks' ? 'active' : ''}`}
          onClick={() => setActiveTab('tasks')}
        >
          📋 任务列表
        </button>
      </div>

      {/* 提交任务 - T109网站 */}
      {activeTab === 'submit' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ 
            background: '#f8f9fa', 
            padding: '12px 16px', 
            borderBottom: '1px solid #e9ecef',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ fontWeight: 600 }}>📝 T109 - 提交计算任务</span>
            <a 
              href="https://t109.mettlyz.com/submit" 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn btn-primary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              在新窗口打开 ↗
            </a>
          </div>
          <iframe
            src="https://t109.mettlyz.com/submit"
            style={{ 
              width: '100%', 
              height: '600px', 
              border: 'none',
              display: 'block'
            }}
            title="T109 Submit"
          />
        </div>
      )}

      {/* 查看结果 - T109结果页面 */}
      {activeTab === 'results' && (
        <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
          <div style={{ 
            background: '#f8f9fa', 
            padding: '12px 16px', 
            borderBottom: '1px solid #e9ecef',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center'
          }}>
            <span style={{ fontWeight: 600 }}>📊 T109 - 计算结果</span>
            <a 
              href="https://t109.mettlyz.com/results" 
              target="_blank" 
              rel="noopener noreferrer"
              className="btn btn-primary"
              style={{ padding: '6px 12px', fontSize: '12px' }}
            >
              在新窗口打开 ↗
            </a>
          </div>
          <iframe
            src="https://t109.mettlyz.com/results"
            style={{ 
              width: '100%', 
              height: '600px', 
              border: 'none',
              display: 'block'
            }}
            title="T109 Results"
          />
        </div>
      )}

      {/* 任务列表 */}
      {activeTab === 'tasks' && (
        <div className="card">
          <div className="card-header">
            <h5>本地任务列表</h5>
          </div>
          <div className="empty-state">
            <div className="empty-state-icon">🔢</div>
            <p>暂无本地计算任务</p>
            <p style={{ fontSize: '0.85rem', color: '#999', marginTop: '8px' }}>
              请在"提交任务"标签页使用T109网站提交计算任务
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
