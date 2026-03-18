import React, { useState, useEffect } from 'react'
import { Clock, Image as ImageIcon, Film, Download, Calendar } from 'lucide-react'
import './PepiWorkHistory.css'

const API_URL = import.meta.env.VITE_API_URL || ''

interface WorkRecord {
  id: number
  task_name: string
  task_description: string
  gif_path: string
  gif_size: number
  gif_size_formatted?: string
  duration_seconds: number
  frame_count: number
  fps: number
  work_type: string
  created_at: string
  status: string
}

interface WorkType {
  work_type: string
  count: number
}

const PepiWorkHistory: React.FC = () => {
  const [records, setRecords] = useState<WorkRecord[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedRecord, setSelectedRecord] = useState<WorkRecord | null>(null)
  const [workTypes, setWorkTypes] = useState<WorkType[]>([])
  const [filter, setFilter] = useState<string>('all')

  useEffect(() => {
    fetchWorkHistory()
    fetchWorkTypes()
  }, [filter])

  const fetchWorkHistory = async () => {
    try {
      setLoading(true)
      const url = filter === 'all' 
        ? `${API_URL}/api/pepi/work-history?limit=50`
        : `${API_URL}/api/pepi/work-history?limit=50&work_type=${filter}`
      
      const response = await fetch(url)
      const data = await response.json()
      
      if (data.success) {
        setRecords(data.records)
      }
    } catch (error) {
      console.error('Error fetching work history:', error)
    } finally {
      setLoading(false)
    }
  }

  const fetchWorkTypes = async () => {
    try {
      const response = await fetch(`${API_URL}/api/pepi/work-types`)
      const data = await response.json()
      
      if (data.success) {
        setWorkTypes(data.work_types)
      }
    } catch (error) {
      console.error('Error fetching work types:', error)
    }
  }

  const formatDate = (dateString: string) => {
    const date = new Date(dateString)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  }

  const formatDuration = (seconds: number) => {
    if (seconds < 60) {
      return `${seconds}秒`
    }
    const minutes = Math.floor(seconds / 60)
    const remainingSeconds = seconds % 60
    return `${minutes}分${remainingSeconds}秒`
  }

  const getWorkTypeLabel = (type: string) => {
    const labels: Record<string, string> = {
      'desktop': '桌面操作',
      'control': '键鼠控制',
      'brain': '任务规划',
      'auto_record': '自动录制',
      'search': '搜索任务',
      'calculate': '计算任务'
    }
    return labels[type] || type
  }

  const getWorkTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'desktop': '#4CAF50',
      'control': '#2196F3',
      'brain': '#9C27B0',
      'auto_record': '#FF9800',
      'search': '#00BCD4',
      'calculate': '#E91E63'
    }
    return colors[type] || '#757575'
  }

  return (
    <div className="pepi-work-history">
      <div className="pepi-header">
        <div className="pepi-title">
          <Film className="pepi-icon" />
          <h2>Pepi 工作历史</h2>
        </div>
        <div className="pepi-stats">
          <div className="stat-item">
            <span className="stat-value">{records.length}</span>
            <span className="stat-label">总记录</span>
          </div>
          {workTypes.map(type => (
            <div key={type.work_type} className="stat-item">
              <span className="stat-value" style={{ color: getWorkTypeColor(type.work_type) }}>
                {type.count}
              </span>
              <span className="stat-label">{getWorkTypeLabel(type.work_type)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="pepi-filters">
        <button 
          className={`filter-btn ${filter === 'all' ? 'active' : ''}`}
          onClick={() => setFilter('all')}
        >
          全部
        </button>
        {workTypes.map(type => (
          <button 
            key={type.work_type}
            className={`filter-btn ${filter === type.work_type ? 'active' : ''}`}
            onClick={() => setFilter(type.work_type)}
            style={{ '--type-color': getWorkTypeColor(type.work_type) } as React.CSSProperties}
          >
            {getWorkTypeLabel(type.work_type)}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="pepi-loading">
          <div className="loading-spinner"></div>
          <p>加载中...</p>
        </div>
      ) : (
        <div className="pepi-records-grid">
          {records.map(record => (
            <div 
              key={record.id} 
              className="pepi-record-card"
              onClick={() => setSelectedRecord(record)}
            >
              <div className="record-gif-container">
                <img 
                  src={`${API_URL}${record.gif_path}`} 
                  alt={record.task_name}
                  className="record-gif"
                  
                  onError={(e) => {
                    // 如果GIF加载失败，显示占位符
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent) {
                      const placeholder = document.createElement('div');
                      placeholder.className = 'record-gif-placeholder';
                      placeholder.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line></svg><span>GIF</span>';
                      parent.appendChild(placeholder);
                    }
                  }}
                />
              </div>
              
              <div className="record-info">
                <div className="record-header">
                  <h3 className="record-title">{record.task_name}</h3>
                  <span 
                    className="record-type"
                    style={{ backgroundColor: getWorkTypeColor(record.work_type) }}
                  >
                    {getWorkTypeLabel(record.work_type)}
                  </span>
                </div>
                
                <p className="record-description">{record.task_description}</p>
                
                <div className="record-meta">
                  <div className="meta-item">
                    <Calendar size={14} />
                    <span>{formatDate(record.created_at)}</span>
                  </div>
                  <div className="meta-item">
                    <Clock size={14} />
                    <span>{formatDuration(record.duration_seconds)}</span>
                  </div>
                  <div className="meta-item">
                    <ImageIcon size={14} />
                    <span>{record.frame_count}帧</span>
                  </div>
                  <div className="meta-item">
                    <span className="file-size">{record.gif_size_formatted || 'N/A'}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {records.length === 0 && !loading && (
        <div className="pepi-empty">
          <Film size={64} />
          <h3>暂无工作记录</h3>
          <p>Pepi执行任务后会自动生成GIF记录</p>
        </div>
      )}

      {/* 详情弹窗 */}
      {selectedRecord && (
        <div className="record-modal" onClick={() => setSelectedRecord(null)}>
          <div className="modal-content" onClick={e => e.stopPropagation()}>
            <div className="modal-header">
              <h3>{selectedRecord.task_name}</h3>
              <button className="close-btn" onClick={() => setSelectedRecord(null)}>×</button>
            </div>
            <div className="modal-body">
              <div className="modal-gif-container">
                <img 
                  src={`${API_URL}${selectedRecord.gif_path}`} 
                  alt={selectedRecord.task_name}
                  className="modal-gif"
                  
                  onError={(e) => {
                    const target = e.target as HTMLImageElement;
                    target.style.display = 'none';
                    const parent = target.parentElement;
                    if (parent) {
                      const placeholder = document.createElement('div');
                      placeholder.className = 'modal-gif-placeholder';
                      placeholder.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"></rect><line x1="7" y1="2" x2="7" y2="22"></line><line x1="17" y1="2" x2="17" y2="22"></line><line x1="2" y1="12" x2="22" y2="12"></line><line x1="2" y1="7" x2="7" y2="7"></line><line x1="2" y1="17" x2="7" y2="17"></line><line x1="17" y1="17" x2="22" y2="17"></line><line x1="17" y1="7" x2="22" y2="7"></line></svg><p>GIF预览</p><code>' + selectedRecord.gif_path + '</code>';
                      parent.appendChild(placeholder);
                    }
                  }}
                />
              </div>
              <div className="modal-details">
                <p><strong>描述:</strong> {selectedRecord.task_description}</p>
                <p><strong>类型:</strong> {getWorkTypeLabel(selectedRecord.work_type)}</p>
                <p><strong>时长:</strong> {formatDuration(selectedRecord.duration_seconds)}</p>
                <p><strong>帧数:</strong> {selectedRecord.frame_count}帧 ({selectedRecord.fps}fps)</p>
                <p><strong>大小:</strong> {selectedRecord.gif_size_formatted || 'N/A'}</p>
                <p><strong>创建时间:</strong> {formatDate(selectedRecord.created_at)}</p>
                <p><strong>文件路径:</strong> <code>{selectedRecord.gif_path}</code></p>
              </div>
            </div>
            <div className="modal-footer">
              <a 
                href={`file://${selectedRecord.gif_path}`} 
                download 
                className="download-btn"
              >
                <Download size={16} />
                下载GIF
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default PepiWorkHistory
