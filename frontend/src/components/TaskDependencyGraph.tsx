import React, { useEffect, useRef, useState } from 'react'

interface Task {
  id: string | number
  title: string
  status: 'todo' | 'in_progress' | 'completed' | 'blocked'
  depends_on?: string | number | null
  x?: number
  y?: number
}

interface TaskDependencyGraphProps {
  tasks: Task[]
  onTaskClick?: (task: Task) => void
  highlightedTask?: string | number | null
}

const TaskDependencyGraph: React.FC<TaskDependencyGraphProps> = ({
  tasks,
  onTaskClick,
  highlightedTask
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [hoveredTask, setHoveredTask] = useState<Task | null>(null)
  const [selectedTask, setSelectedTask] = useState<Task | null>(null)

  // 计算任务位置（简单的层级布局）
  const calculatePositions = (tasks: Task[]): Task[] => {
    const taskMap = new Map(tasks.map(t => [t.id, t]))
    const levels: Task[][] = []
    const visited = new Set()

    // 找到所有根任务（没有依赖或依赖不在列表中）
    const getLevel = (task: Task, visited = new Set()): number => {
      if (visited.has(task.id)) return 0
      visited.add(task.id)
      
      if (!task.depends_on || !taskMap.has(task.depends_on)) {
        return 0
      }
      const parent = taskMap.get(task.depends_on)
      return parent ? getLevel(parent, visited) + 1 : 0
    }

    // 按层级分组
    tasks.forEach(task => {
      const level = getLevel(task)
      if (!levels[level]) levels[level] = []
      levels[level].push(task)
    })

    // 分配位置
    const nodeWidth = 180
    const nodeHeight = 60
    const levelGap = 100
    const nodeGap = 20

    return tasks.map(task => {
      const level = getLevel(task)
      const indexInLevel = levels[level].findIndex(t => t.id === task.id)
      const levelWidth = levels[level].length * (nodeWidth + nodeGap) - nodeGap
      const startX = (800 - levelWidth) / 2

      return {
        ...task,
        x: startX + indexInLevel * (nodeWidth + nodeGap) + nodeWidth / 2,
        y: 50 + level * (nodeHeight + levelGap) + nodeHeight / 2
      }
    })
  }

  const positionedTasks = calculatePositions(tasks)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    // 设置画布大小
    canvas.width = 900
    canvas.height = Math.max(400, positionedTasks.length * 80)

    // 清空画布
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    // 绘制依赖连线
    positionedTasks.forEach(task => {
      if (task.depends_on) {
        const parent = positionedTasks.find(t => t.id === task.depends_on)
        if (parent && parent.x && parent.y && task.x && task.y) {
          // 绘制连线
          ctx.beginPath()
          ctx.strokeStyle = highlightedTask && (task.id === highlightedTask || parent.id === highlightedTask) 
            ? '#22c55e' 
            : '#64748b'
          ctx.lineWidth = highlightedTask && (task.id === highlightedTask || parent.id === highlightedTask) ? 3 : 2
          
          // 贝塞尔曲线
          const startX = parent.x
          const startY = parent.y + 30
          const endX = task.x
          const endY = task.y - 30
          const cpY = (startY + endY) / 2
          
          ctx.moveTo(startX, startY)
          ctx.quadraticCurveTo(startX, cpY, endX, cpY)
          ctx.quadraticCurveTo(endX, cpY, endX, endY)
          ctx.stroke()

          // 绘制箭头
          ctx.beginPath()
          ctx.fillStyle = ctx.strokeStyle
          ctx.moveTo(endX, endY)
          ctx.lineTo(endX - 5, endY - 10)
          ctx.lineTo(endX + 5, endY - 10)
          ctx.closePath()
          ctx.fill()
        }
      }
    })

    // 绘制任务节点
    positionedTasks.forEach(task => {
      if (!task.x || !task.y) return

      const isHovered = hoveredTask?.id === task.id
      const isSelected = selectedTask?.id === task.id
      const isHighlighted = highlightedTask === task.id

      // 节点背景
      ctx.beginPath()
      ctx.roundRect(task.x - 90, task.y - 30, 180, 60, 8)
      
      // 根据状态设置颜色
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
      } else if (isHovered) {
        strokeColor = '#64748b'
        ctx.lineWidth = 2
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
      ctx.textAlign = 'center'
      
      // 截断长标题
      const maxWidth = 160
      let title = task.title
      if (ctx.measureText(title).width > maxWidth) {
        while (ctx.measureText(title + '...').width > maxWidth && title.length > 0) {
          title = title.slice(0, -1)
        }
        title += '...'
      }
      ctx.fillText(title, task.x, task.y - 5)

      // 状态标签
      ctx.font = '10px sans-serif'
      const statusColors: Record<string, string> = {
        todo: '#94a3b8',
        in_progress: '#3b82f6',
        completed: '#22c55e',
        blocked: '#ef4444'
      }
      ctx.fillStyle = statusColors[task.status] || '#94a3b8'
      ctx.fillText(task.status, task.x, task.y + 15)
    })
  }, [positionedTasks, hoveredTask, selectedTask, highlightedTask])

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    // 查找悬停的任务
    const hovered = positionedTasks.find(task => {
      if (!task.x || !task.y) return false
      return x >= task.x - 90 && x <= task.x + 90 &&
             y >= task.y - 30 && y <= task.y + 30
    })

    setHoveredTask(hovered || null)
  }

  const handleClick = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current
    if (!canvas) return

    const rect = canvas.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top

    const clicked = positionedTasks.find(task => {
      if (!task.x || !task.y) return false
      return x >= task.x - 90 && x <= task.x + 90 &&
             y >= task.y - 30 && y <= task.y + 30
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
          maxWidth: '900px',
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
        </div>
      )}
    </div>
  )
}

export default TaskDependencyGraph
