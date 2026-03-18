import { useState, useEffect } from 'react'

// SVG图标组件
const ChevronLeftIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="15 18 9 12 15 6"></polyline>
  </svg>
)

const ChevronRightIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <polyline points="9 18 15 12 9 6"></polyline>
  </svg>
)

const PlusIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <line x1="12" y1="5" x2="12" y2="19"></line>
    <line x1="5" y1="12" x2="19" y2="12"></line>
  </svg>
)

export function Calendar() {
  const [currentDate, setCurrentDate] = useState(new Date())
  const [events, setEvents] = useState<any[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [showModal, setShowModal] = useState(false)
  const [viewMode, setViewMode] = useState<'month' | 'week' | 'day'>('month')
  
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    start_time: '',
    end_time: '',
    all_day: false,
    location: '',
    category: 'default',
    color: '#667eea',
    reminder_minutes: 15
  })

  useEffect(() => {
    loadData()
  }, [currentDate])

  const loadData = async () => {
    try {
      const year = currentDate.getFullYear()
      const month = currentDate.getMonth()
      
      const endDate = new Date(year, month + 1, 0)
      
      // 使用本地时间格式，避免时区偏差
      const startStr = `${year}-${String(month + 1).padStart(2, '0')}-01`
      const endStr = `${year}-${String(month + 1).padStart(2, '0')}-${String(endDate.getDate()).padStart(2, '0')}`
      
      const [eventsRes, statsRes] = await Promise.all([
        fetch(`/api/calendar/events?start=${startStr}&end=${endStr}`).then(r => r.json()),
        fetch('/api/calendar/stats').then(r => r.json())
      ])
      
      if (eventsRes.success) setEvents(eventsRes.events || [])
      if (statsRes.success) setStats(statsRes.stats)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    
    try {
      const res = await fetch('/api/calendar/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      })
      
      const data = await res.json()
      if (data.success) {
        setShowModal(false)
        setFormData({
          title: '',
          description: '',
          start_time: '',
          end_time: '',
          all_day: false,
          location: '',
          category: 'default',
          color: '#667eea',
          reminder_minutes: 15
        })
        loadData()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const handlePrevMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() - 1, 1))
  }

  const handleNextMonth = () => {
    setCurrentDate(new Date(currentDate.getFullYear(), currentDate.getMonth() + 1, 1))
  }

  const handleToday = () => {
    setCurrentDate(new Date())
  }

  const generateCalendarDays = () => {
    const year = currentDate.getFullYear()
    const month = currentDate.getMonth()
    
    const firstDay = new Date(year, month, 1)
    const lastDay = new Date(year, month + 1, 0)
    
    const startDayOfWeek = firstDay.getDay()
    const daysInMonth = lastDay.getDate()
    
    const days = []
    
    for (let i = 0; i < startDayOfWeek; i++) {
      days.push(null)
    }
    
    for (let i = 1; i <= daysInMonth; i++) {
      days.push(new Date(year, month, i))
    }
    
    return days
  }

  const getEventsForDate = (date: Date) => {
    if (!date) return []
    // 使用本地时间格式，避免时区偏差
    const dateStr = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
    return events.filter(e => e.start_time?.startsWith(dateStr))
  }

  const isToday = (date: Date) => {
    if (!date) return false
    const today = new Date()
    // 使用本地日期字符串比较，避免时区问题
    const dateStr = date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0') + '-' + String(date.getDate()).padStart(2, '0')
    const todayStr = today.getFullYear() + '-' + String(today.getMonth() + 1).padStart(2, '0') + '-' + String(today.getDate()).padStart(2, '0')
    return dateStr === todayStr
  }

  const weekDays = ['日', '一', '二', '三', '四', '五', '六']
  const calendarDays = generateCalendarDays()
  const monthNames = ['一月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '十一月', '十二月']

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">📅 日历</h2>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => window.location.href = '/calendar-settings'}>
            ⚙️ 同步设置
          </button>
          <button className="btn btn-success" onClick={() => setShowModal(true)}>
            <PlusIcon /> 新建事件
          </button>
        </div>
      </div>

      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div className="stat-card blue" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>📅</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.today}</h3>
              <p style={{ fontSize: '0.75rem' }}>今日事件</p>
            </div>
          </div>
          <div className="stat-card purple" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>📊</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.week}</h3>
              <p style={{ fontSize: '0.75rem' }}>本周事件</p>
            </div>
          </div>
          <div className="stat-card green" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>📈</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.month}</h3>
              <p style={{ fontSize: '0.75rem' }}>本月事件</p>
            </div>
          </div>
          <div className="stat-card orange" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>⏰</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.upcoming}</h3>
              <p style={{ fontSize: '0.75rem' }}>待处理</p>
            </div>
          </div>
        </div>
      )}

      <div className="card" style={{ marginBottom: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <button className="btn btn-secondary" onClick={handlePrevMonth}>
              <ChevronLeftIcon />
            </button>
            <h3 style={{ margin: 0, minWidth: '150px', textAlign: 'center' }}>
              {currentDate.getFullYear()}年 {monthNames[currentDate.getMonth()]}
            </h3>
            <button className="btn btn-secondary" onClick={handleNextMonth}>
              <ChevronRightIcon />
            </button>
          </div>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button className="btn btn-secondary" onClick={handleToday}>今天</button>
            <button className={`btn ${viewMode === 'month' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setViewMode('month')}>月</button>
            <button className={`btn ${viewMode === 'week' ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setViewMode('week')}>周</button>
          </div>
        </div>
      </div>

      {viewMode === 'month' && (
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', marginBottom: '8px' }}>
            {weekDays.map(day => (
              <div key={day} style={{ textAlign: 'center', fontWeight: 600, padding: '8px', color: '#666' }}>{day}</div>
            ))}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
            {calendarDays.map((date, index) => {
              if (!date) return <div key={`empty-${index}`} style={{ height: '100px', background: '#f8f9fa', borderRadius: '4px' }} />
              
              const dayEvents = getEventsForDate(date)
              const today = isToday(date)
              
              return (
                <div 
                  key={date.toISOString()} 
                  style={{ 
                    height: '100px', 
                    padding: '8px',
                    background: today ? '#e3f2fd' : 'white',
                    border: today ? '2px solid #2196f3' : '1px solid #e0e0e0',
                    borderRadius: '4px',
                    cursor: 'pointer',
                    overflow: 'hidden',
                    display: 'flex',
                    flexDirection: 'column'
                  }}
                  onClick={() => {
                    setFormData(prev => ({ ...prev, start_time: date.toISOString().slice(0, 16) }))
                    setShowModal(true)
                  }}
                >
                  <div style={{ fontWeight: today ? 700 : 500, color: today ? '#2196f3' : '#333', marginBottom: '4px' }}>
                    {date.getDate()}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {dayEvents.map((event, i) => (
                      <div key={i} style={{
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        padding: '4px 6px',
                        background: event.color || '#667eea',
                        color: 'white',
                        borderRadius: '6px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.2)',
                        border: event.is_subscribed || event.source?.includes('订阅') ? '3px solid #ff1744' : '2px solid transparent',
                        transform: event.is_subscribed || event.source?.includes('订阅') ? 'scale(1.02)' : 'none',
                        transition: 'all 0.2s'
                      }} title={event.title + (event.is_subscribed || event.source?.includes('订阅') ? ' [订阅]' : '')}>
                        <span style={{ marginRight: '4px' }}>
                          {event.is_subscribed || event.source?.includes('订阅') ? '🔔 ' : '📅 '}
                        </span>
                        {event.title}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}


      {viewMode === 'week' && (
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px', marginBottom: '8px' }}>
            {weekDays.map((day, index) => {
              const weekDate = new Date(currentDate)
              const dayOfWeek = weekDate.getDay()
              weekDate.setDate(weekDate.getDate() - dayOfWeek + index)
              const isTodayWeek = isToday(weekDate)
              return (
                <div key={day} style={{ 
                  textAlign: 'center', 
                  fontWeight: 600, 
                  padding: '8px', 
                  color: isTodayWeek ? '#2196f3' : '#666',
                  background: isTodayWeek ? '#e3f2fd' : 'transparent',
                  borderRadius: '4px'
                }}>
                  <div>{day}</div>
                  <div style={{ fontSize: '0.9rem' }}>{weekDate.getDate()}</div>
                </div>
              )
            })}
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: '4px' }}>
            {Array.from({ length: 7 }, (_, index) => {
              const weekDate = new Date(currentDate)
              const dayOfWeek = weekDate.getDay()
              weekDate.setDate(weekDate.getDate() - dayOfWeek + index)
              const dayEvents = getEventsForDate(weekDate)
              const today = isToday(weekDate)
              
              return (
                <div 
                  key={index} 
                  style={{ 
                    minHeight: '200px', 
                    padding: '8px',
                    background: today ? '#e3f2fd' : 'white',
                    border: today ? '2px solid #2196f3' : '1px solid #e0e0e0',
                    borderRadius: '4px'
                  }}
                >
                  <div style={{ fontWeight: today ? 700 : 500, color: today ? '#2196f3' : '#333', marginBottom: '4px', textAlign: 'center' }}>
                    {weekDate.getDate()}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {dayEvents.map((event, i) => (
                      <div key={i} style={{
                        fontSize: '0.8rem',
                        fontWeight: 600,
                        padding: '4px 6px',
                        background: event.color || '#667eea',
                        color: 'white',
                        borderRadius: '6px',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                        boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                      }} title={event.title}>
                        <span style={{ marginRight: '4px' }}>📅</span>
                        {event.title}
                      </div>
                    ))}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {viewMode === 'day' && (
        <div className="card" style={{ padding: '16px' }}>
          <div style={{ textAlign: 'center', marginBottom: '16px' }}>
            <h3 style={{ color: isToday(currentDate) ? '#2196f3' : '#333' }}>
              {currentDate.getFullYear()}年{currentDate.getMonth() + 1}月{currentDate.getDate()}日
              {isToday(currentDate) && <span style={{ marginLeft: '8px', fontSize: '0.8rem', background: '#2196f3', color: 'white', padding: '2px 8px', borderRadius: '12px' }}>今天</span>}
            </h3>
          </div>
          <div style={{ minHeight: '400px', padding: '16px', background: isToday(currentDate) ? '#e3f2fd' : 'white', border: isToday(currentDate) ? '2px solid #2196f3' : '1px solid #e0e0e0', borderRadius: '4px' }}>
            {(() => {
              const dayEvents = getEventsForDate(currentDate)
              if (dayEvents.length === 0) {
                return <div style={{ textAlign: 'center', color: '#999', padding: '40px' }}>今日暂无事件</div>
              }
              return (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {dayEvents.map((event, i) => (
                    <div key={i} style={{
                      padding: '12px',
                      background: event.color || '#667eea',
                      color: 'white',
                      borderRadius: '8px',
                      boxShadow: '0 2px 4px rgba(0,0,0,0.2)'
                    }}>
                      <div style={{ fontWeight: 700, fontSize: '1.1rem', marginBottom: '4px' }}>
                        <span style={{ marginRight: '8px' }}>📅</span>
                        {event.title}
                      </div>
                      {event.description && <div style={{ fontSize: '0.9rem', opacity: 0.9 }}>{event.description}</div>}
                      {event.location && <div style={{ fontSize: '0.8rem', marginTop: '4px' }}>📍 {event.location}</div>}
                    </div>
                  ))}
                </div>
              )
            })()}
          </div>
        </div>
      )}
      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: '500px' }}>
            <h3><PlusIcon /> 新建事件</h3>
            <form onSubmit={handleSubmit} style={{ marginTop: '16px' }}>
              <div style={{ marginBottom: '12px' }}>
                <label>标题 *</label>
                <input type="text" value={formData.title} onChange={e => setFormData({...formData, title: e.target.value})} placeholder="事件标题" required />
              </div>
              <div style={{ marginBottom: '12px' }}>
                <label>描述</label>
                <textarea value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} placeholder="事件描述..." rows={2} />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label>开始时间 *</label>
                  <input type="datetime-local" value={formData.start_time} onChange={e => setFormData({...formData, start_time: e.target.value})} required />
                </div>
                <div>
                  <label>结束时间</label>
                  <input type="datetime-local" value={formData.end_time} onChange={e => setFormData({...formData, end_time: e.target.value})} />
                </div>
              </div>
              <div style={{ marginBottom: '12px' }}>
                <label>地点</label>
                <input type="text" value={formData.location} onChange={e => setFormData({...formData, location: e.target.value})} placeholder="事件地点" />
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '12px' }}>
                <div>
                  <label>分类</label>
                  <select value={formData.category} onChange={e => setFormData({...formData, category: e.target.value})}>
                    <option value="default">默认</option>
                    <option value="work">工作</option>
                    <option value="personal">个人</option>
                    <option value="meeting">会议</option>
                    <option value="reminder">提醒</option>
                  </select>
                </div>
                <div>
                  <label>颜色</label>
                  <input type="color" value={formData.color} onChange={e => setFormData({...formData, color: e.target.value})} style={{ width: '100%', height: '38px' }} />
                </div>
              </div>
              <div style={{ marginBottom: '16px' }}>
                <label><input type="checkbox" checked={formData.all_day} onChange={e => setFormData({...formData, all_day: e.target.checked})} /> 全天事件</label>
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setShowModal(false)}>取消</button>
                <button type="submit" className="btn btn-success">创建事件</button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

// 事件详情弹窗组件
function EventDetailModal({ event, onClose, onEdit, onDelete }: { 
  event: any, 
  onClose: () => void, 
  onEdit: (e: any) => void,
  onDelete: (id: string) => void 
}) {
  if (!event) return null
  
  return (
    <div className="modal-overlay" onClick={onClose} style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center',
      zIndex: 1000
    }}>
      <div onClick={e => e.stopPropagation()} style={{
        background: 'white', borderRadius: '12px', padding: '24px', maxWidth: '500px', width: '90%'
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h3 style={{ margin: 0 }}>{event.title}</h3>
          <button onClick={onClose} style={{ background: 'none', border: 'none', fontSize: '24px', cursor: 'pointer' }}>×</button>
        </div>
        <div style={{ marginBottom: '16px' }}>
          <p><strong>时间:</strong> {event.start_time?.slice(0, 16).replace('T', ' ')} - {event.end_time?.slice(0, 16).replace('T', ' ')}</p>
          {event.location && <p><strong>地点:</strong> {event.location}</p>}
          {event.description && <p><strong>描述:</strong> {event.description}</p>}
        </div>
        <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end' }}>
          <button onClick={() => onEdit(event)} className="btn btn-secondary">编辑</button>
          <button onClick={() => onDelete(event.id)} className="btn btn-danger">删除</button>
        </div>
      </div>
    </div>
  )
}
