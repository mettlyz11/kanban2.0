import React, { useEffect, useRef, useState } from 'react'

interface Task {
  id: string | number
  title: string
  status: 'todo' | 'in_progress' | 'completed' | 'blocked'
  depends_on?: string | number | null
  start_date?: Date
  end_date?: Date
  duration?: number // 天数
}

interface TaskGanttChartProps {
  tasks: Task[]
  onTaskClick?: (task: Task) => void
  highlightedTask?: string | number | null
}

const TaskGanttChart: React.FC<TaskGanttChartProps> = ({
  tasks,
  onTaskClick,
  highlightedTask
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hoveredTask, setHoveredTask] = useState<Task | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  // 计算时间范围
  const calculateTimeRange = (tasks: Task[]) => {
    const now = new Date()
    const dates = tasks.flatMap(task => [
      task.start_date || now,
      task.end_date || new Date(now.getTime() + 7 * 24 * 60 * 60 * 1000)
    ])
    
    const minDate = new Date(Math.min(...dates.map(d => d.getTime())))
    const maxDate = new Date(Math.max(...dates.map(d => d.getTime())))
    
    // 扩展一点边界
    minDate.setDate(minDate.getDate() - 1)
    maxDate.setDate(maxDate.getDate() + 1)
    
    return { minDate, maxDate }
  }

  const { minDate, maxDate } = calculateTimeRange(tasks)
  const totalDays = Math.ceil((maxDate.getTime() - minDate.getTime()) / (24 * 60 * 60 * 1000))

  // 格式化日期
  const formatDate = (date: Date) => {
    return date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
  }

  // 计算任务位置
  const getTaskPosition = (task: Task) => {
    const start = task.start_date || minDate
    const end = task.end_date || new Date(start.getTime() + (task.duration || 7) * 24 * 60 * 60 * 1000)
    
    const x = ((start.getTime() - minDate.getTime()) / (24 * 60 * 60 * 1000)) / totalDays * 800 + 200
    const width = ((end.getTime() - start.getTime()) / (24 * 60 * 60 * 1000)) / totalDays * 800
    
    return { x, width }
  }

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    canvas.width = 1000
    canvas.height = 400 + tasks.length * 60

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 绘制时间轴
    ctx.fillStyle = '#e2e8f0'
    ctx.font = '12px sans-serif'
    ctx.textAlign = 'center'
    
    const timelineHeight = 40
    for (let i = 0; i <= totalDays; i += 3) {
      const x = 200 + (i / totalDays) * 800
      const date = new Date(minDate.getTime() + i * 24 * 60 * 60 * 1000)
      
      ctx.fillText(formatDate(date), x, 30)
      
      ctx.beginPath()
      ctx.strokeStyle = '#334155'
      ctx.lineWidth = 1
      ctx.moveTo(x, 40)
      ctx.lineTo(x, canvas.height)
      ctx.stroke()
    }

    // 绘制任务条
    tasks.forEach((task, index) => {
      const { x, width } = getTaskPosition(task)
      const y = 80 + index * 60
      const height = 40

      const isHighlighted = highlightedTask === task.id
      const isSelected = selectedTask?.id === task.id
      
      // 任务条背景
      ctx.beginPath()
      ctx.roundRect(x, y, width, height, 6)
      
      let fillColor = '#1e293b'
      let strokeColor = '#334155'
      
      if (task.status === 'completed') {
        fillColor = '#064e3b'
        strokeColor = '#22c55e'
      } else if (task.status === 'in_progress') {
        fillColor = '#1e3a5f'
        strokeColor = '#3b82f6'
      } else if (task.status === 'blocked') {
        fillColor = '#451a1a'
        strokeColor = '#ef4444'
      }

      if (isHighlighted) {
        strokeColor = '#22c55e'
        ctx.lineWidth = 3
      } else if (isSelected) {
        strokeColor = '#a855f7'
        ctx.lineWidth = 3
      } else {
        ctx.lineWidth = 1
      }

      ctx.fillStyle = fillColor
      ctx.fill()
      ctx.strokeStyle = strokeColor
      ctx.stroke()

      // 任务标题
      ctx.fillStyle = '#e2e8f0'
      ctx.font = '12px sans-serif'
      ctx.textAlign = 'left'
      
      // 截断长标题
      const maxWidth = width - 16
      let title = task.title
      ctx.save()
      ctx.translate(x + 8, y + height / 2 + 4)
      ctx.beginPath()
      ctx.rect(0, -height / 2 + 4, maxWidth, height)
      ctx.clip()
      
      if (ctx.measureText(title).width > maxWidth) {
        while (ctx.measureText(title + '...').width > maxWidth && title.length > 0) {
          title = title.slice(0, -1)
        }
        title += '...'
      }
      ctx.fillText(title, 0, 0)
      ctx.restore()

      // 任务编号
      ctx.textAlign = 'left'
      ctx.font = '12px sans-serif'
      ctx.fillStyle = '#64748b'
      ctx.fillText(, 50, y + height / 2 + 4)

      // 绘制依赖连线
      if (task.depends_on) {
        const depTask = tasks.find(t => t.id === task.depends_on)
        if (depTask) {
          const depIndex = tasks.findIndex(t => t.id === depTask.id)
          const depY = 80 + depIndex * 60 + height / 2
          const depX = getTaskPosition(depTask).x + getTaskPosition(depTask).width
          
          ctx.beginPath()
          ctx.strokeStyle = '#64748b'
          ctx.lineWidth = 2
          ctx.moveTo(depX, depY)
          ctx.lineTo(x, y + height / 2)
          ctx.stroke()

          // 箭头
          ctx.beginPath()
          ctx.fillStyle = '#64748b'
          ctx.moveTo(x, y + height / 2)
          ctx.lineTo(x - 5, y + height / 2 - 5)
          ctx.lineTo(x - 5, y + height / 2 + 5)
          ctx.closePath()
          ctx.fill()
        }
      }
    })
  }, [tasks, selectedTask, highlightedTask])

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const hovered = tasks.find((task, index) => {
      const taskY = 80 + index * 60
      const taskHeight = 40
      return y >= taskY && y <= taskY + taskHeight
    })

    setHoveredTask(hovered || null)
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const y = e.clientY - rect.top

    const clicked = tasks.find((task, index) => {
      const taskY = 80 + index * 60
      const taskHeight = 40
      return y >= taskY && y <= taskY + taskHeight
    })

    if (clicked) {
      setSelectedTask(clicked)
      onTaskClick?.(clicked)
    }
  }

  return (
    <div style={{ position: 'relative' }}>
      <canvas
        ref={canvasRef}
        style={{
          width: '100%',
          maxWidth: '1000px',
          height: ,
          borderRadius: '12px',
          background: '#0f172a',
          cursor: hoveredTask ? 'pointer' : 'default'
        }}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => setHoveredTask(null)}
        onClick={handleClick}
      />
      {hoveredTask && (
        <div style={{
          position: 'absolute',
          top: 10,
          right: 10,
          background: '#1e293b',
          padding: '12px',
          borderRadius: '8px',
          border: '1px solid #334155',
          color: '#e2e8f0',
          fontSize: '12px',
          maxWidth: '200px'
        }}>
          <div style={{ fontWeight: 600, marginBottom: '4px' }}>{hoveredTask.title}</div>
          <div style={{ color: '#64748b' }}>状态: {hoveredTask.status}</div>
          {hoveredTask.depends_on && (
            <div style={{ color: '#64748b' }}>依赖: {hoveredTask.depends_on}</div>
          )}
          {hoveredTask.start_date && (
            <div style={{ color: '#64748b' }}>开始: {formatDate(hoveredTask.start_date)}</div>
          )}
          {hoveredTask.end_date && (
            <div style={{ color: '#64748b' }}>结束: {formatDate(hoveredTask.end_date)}</div>
          )}
        </div>
      )}
    </div>
  )
}

export default TaskGanttChart
