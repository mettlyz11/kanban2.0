import { useState } from 'react'
import { 
  ChevronDown, 
  ChevronUp, 
  Maximize2, 
  Minimize2, 
  Target, 
  ListTodo, 
  Edit2, 
  Trash2, 
  Plus,
  FileText,
  MoreHorizontal
} from 'lucide-react'
import { api } from '../utils/api'

interface Task {
  id: number
  number: string
  title: string
  status: string
  priority: string
  description?: string
  details?: string
  created_at: string
  updated_at?: string
}

interface Project {
  id: number
  number: string
  name: string
  description: string
  goal: string
  status: string
  priority: string
  created_at: string
  updated_at: string
}

interface ProjectWithTasks extends Project {
  tasks?: Task[]
  task_stats?: {
    total: number
    completed: number
    in_progress: number
    todo: number
  }
}

interface ProjectCardProps {
  project: ProjectWithTasks
  defaultCollapsed?: boolean
  onEdit?: (project: Project) => void
  onDelete?: (project: Project) => void
  onAddTask?: (projectId: number) => void
  onTaskClick?: (task: Task) => void
  className?: string
}

// 项目任务列表组件
function ProjectTaskList({ 
  tasks, 
  loading, 
  onTaskClick 
}: { 
  tasks: Task[]; 
  loading: boolean;
  onTaskClick?: (task: Task) => void
}) {
  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: '20px', color: '#999' }}>
        加载任务中...
      </div>
    )
  }

  if (tasks.length === 0) {
    return (
      <div style={{ 
        textAlign: 'center', 
        padding: '20px', 
        color: '#999',
        background: '#f8f9fa',
        borderRadius: '8px'
      }}>
        <ListTodo size={32} style={{ marginBottom: '8px', opacity: 0.5 }} />
        <div>暂无任务</div>
      </div>
    )
  }

  return (
    <>
      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#333', marginBottom: '10px' }}>
        关联任务 ({tasks.length})
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
        {tasks.map(task => (
          <div 
            key={task.id} 
            onClick={() => onTaskClick?.(task)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '10px 12px',
              background: '#fff',
              borderRadius: '6px',
              border: '1px solid #e0e0e0',
              cursor: onTaskClick ? 'pointer' : 'default',
              transition: 'all 0.2s ease'
            }}
            onMouseEnter={e => {
              if (onTaskClick) {
                e.currentTarget.style.background = '#f8f9fa'
                e.currentTarget.style.borderColor = '#667eea'
              }
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = '#fff'
              e.currentTarget.style.borderColor = '#e0e0e0'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1 }}>
              <span style={{ 
                fontSize: '0.7rem', 
                color: '#667eea', 
                fontWeight: 600, 
                fontFamily: 'monospace',
                background: '#f0f4ff',
                padding: '2px 6px',
                borderRadius: '4px'
              }}>
                {task.number}
              </span>
              <span style={{ fontSize: '0.9rem', color: '#333' }}>{task.title}</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={`badge ${
                task.priority === 'high' ? 'badge-red' : 
                task.priority === 'medium' ? 'badge-orange' : 'badge-green'
              }`} style={{ fontSize: '0.7rem', padding: '2px 6px' }}>
                {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
              </span>
              <span className={`status-badge status-${task.status}`} style={{ fontSize: '0.7rem' }}>
                {task.status === 'todo' ? '待办' : task.status === 'progress' ? '进行中' : '已完成'}
              </span>
            </div>
          </div>
        ))}
      </div>
    </>
  )
}

export function ProjectCard({ 
  project, 
  defaultCollapsed = true,
  onEdit,
  onDelete,
  onAddTask,
  onTaskClick,
  className = ''
}: ProjectCardProps) {
  const [isExpanded, setIsExpanded] = useState(!defaultCollapsed)
  const [isFullscreen, setIsFullscreen] = useState(false)
  const [tasks, setTasks] = useState<Task[]>([])
  const [loadingTasks, setLoadingTasks] = useState(false)
  const [showActions, setShowActions] = useState(false)

  const progress = project.task_stats ? 
    Math.round((project.task_stats.completed / project.task_stats.total) * 100) : 0

  const toggleExpand = async () => {
    if (!isExpanded && tasks.length === 0) {
      setLoadingTasks(true)
      try {
        const data = await api.getProjectTasks(project.id)
        if (data.success) {
          setTasks(data.tasks || [])
        }
      } catch (e) {
        console.error('Failed to load project tasks:', e)
      } finally {
        setLoadingTasks(false)
      }
    }
    setIsExpanded(!isExpanded)
  }

  const toggleFullscreen = () => {
    setIsFullscreen(!isFullscreen)
    // 全屏时自动展开
    if (!isFullscreen && !isExpanded) {
      setIsExpanded(true)
      if (tasks.length === 0) {
        setLoadingTasks(true)
        api.getProjectTasks(project.id).then(data => {
          if (data.success) {
            setTasks(data.tasks || [])
          }
          setLoadingTasks(false)
        })
      }
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'todo': return '#ffc107'
      case 'progress': return '#667eea'
      case 'done': return '#28a745'
      default: return '#ddd'
    }
  }

  const getPriorityLabel = (priority: string) => {
    switch (priority) {
      case 'high': return '高'
      case 'medium': return '中'
      case 'low': return '低'
      default: return '中'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'todo': return '待办'
      case 'progress': return '进行中'
      case 'done': return '已完成'
      default: return '待办'
    }
  }

  const cardContent = (
    <>
      {/* 卡片头部 */}
      <div style={{ 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'flex-start',
        marginBottom: isExpanded ? '12px' : '0'
      }}>
        <div style={{ flex: 1 }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px',
            marginBottom: isExpanded ? '8px' : '4px'
          }}>
            <span style={{ 
              fontSize: '0.85rem', 
              color: '#667eea', 
              fontWeight: 600 
            }}>
              {project.number}
            </span>
            <span className={`badge ${
              project.priority === 'high' ? 'badge-red' : 
              project.priority === 'medium' ? 'badge-orange' : 'badge-green'
            }`}>
              {getPriorityLabel(project.priority)}
            </span>
            <span className={`status-badge status-${project.status}`}>
              {getStatusLabel(project.status)}
            </span>
          </div>
          
          <h4 style={{ 
            margin: 0,
            fontSize: isExpanded ? '1.2rem' : '1rem',
            color: '#333',
            fontWeight: 600
          }}>
            {project.name}
          </h4>
        </div>

        {/* 操作按钮组 */}
        <div style={{ display: 'flex', gap: '4px', alignItems: 'center' }}>
          {/* 更多操作菜单 */}
          <div style={{ position: 'relative' }}>
            <button
              onClick={(e) => {
                e.stopPropagation()
                setShowActions(!showActions)
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: '32px',
                height: '32px',
                background: 'transparent',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                color: '#666',
                transition: 'all 0.2s'
              }}
              onMouseEnter={e => {
                e.currentTarget.style.background = '#f0f0f0'
              }}
              onMouseLeave={e => {
                e.currentTarget.style.background = 'transparent'
              }}
            >
              <MoreHorizontal size={18} />
            </button>
            
            {showActions && (
              <>
                <div 
                  style={{
                    position: 'fixed',
                    top: 0,
                    left: 0,
                    right: 0,
                    bottom: 0,
                    zIndex: 999
                  }}
                  onClick={() => setShowActions(false)}
                />
                <div style={{
                  position: 'absolute',
                  top: '100%',
                  right: 0,
                  marginTop: '4px',
                  background: 'white',
                  borderRadius: '8px',
                  boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
                  padding: '4px',
                  minWidth: '120px',
                  zIndex: 1000
                }}>
                  {onEdit && (
                    <button
                      onClick={() => {
                        onEdit(project)
                        setShowActions(false)
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        width: '100%',
                        padding: '8px 12px',
                        background: 'transparent',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        color: '#667eea',
                        transition: 'background 0.2s'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.background = '#f0f4ff'
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      <Edit2 size={14} />
                      编辑
                    </button>
                  )}
                  {onAddTask && (
                    <button
                      onClick={() => {
                        onAddTask(project.id)
                        setShowActions(false)
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        width: '100%',
                        padding: '8px 12px',
                        background: 'transparent',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        color: '#28a745',
                        transition: 'background 0.2s'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.background = '#e8f5e9'
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      <Plus size={14} />
                      添加任务
                    </button>
                  )}
                  {onDelete && (
                    <button
                      onClick={() => {
                        onDelete(project)
                        setShowActions(false)
                      }}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        width: '100%',
                        padding: '8px 12px',
                        background: 'transparent',
                        border: 'none',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.85rem',
                        color: '#c62828',
                        transition: 'background 0.2s'
                      }}
                      onMouseEnter={e => {
                        e.currentTarget.style.background = '#ffebee'
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.background = 'transparent'
                      }}
                    >
                      <Trash2 size={14} />
                      删除
                    </button>
                  )}
                </div>
              </>
            )}
          </div>

          {/* 全屏按钮 */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              toggleFullscreen()
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              background: 'transparent',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              color: '#666',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#f0f0f0'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
            }}
            title={isFullscreen ? '退出全屏' : '全屏查看'}
          >
            {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
          </button>

          {/* 展开/折叠按钮 */}
          <button
            onClick={(e) => {
              e.stopPropagation()
              toggleExpand()
            }}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '32px',
              height: '32px',
              background: 'transparent',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
              color: '#667eea',
              transition: 'all 0.2s'
            }}
            onMouseEnter={e => {
              e.currentTarget.style.background = '#f0f4ff'
            }}
            onMouseLeave={e => {
              e.currentTarget.style.background = 'transparent'
            }}
            title={isExpanded ? '收起' : '展开'}
          >
            {isExpanded ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
          </button>
        </div>
      </div>

      {/* 展开内容 */}
      {isExpanded && (
        <div 
          className="project-card-expanded"
          style={{
            animation: 'slideDown 0.3s ease-out'
          }}
        >
          {/* 项目目标 */}
          <div style={{ 
            background: '#f0f4ff', 
            padding: '12px', 
            borderRadius: '8px', 
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'flex-start',
            gap: '8px'
          }}>
            <Target size={18} color="#667eea" style={{ marginTop: '2px', flexShrink: 0 }} />
            <div style={{ flex: 1 }}>
              <div style={{ 
                fontSize: '0.75rem', 
                color: '#667eea', 
                fontWeight: 600, 
                marginBottom: '4px' 
              }}>
                项目目标
              </div>
              <div style={{ fontSize: '0.9rem', color: '#555' }}>
                {project.goal || '暂无目标'}
              </div>
            </div>
          </div>

          {/* 项目描述 */}
          {project.description && (
            <div style={{ marginBottom: '16px' }}>
              <div style={{ 
                fontSize: '0.75rem', 
                color: '#666', 
                fontWeight: 600, 
                marginBottom: '4px' 
              }}>
                项目描述
              </div>
              <div style={{ 
                fontSize: '0.9rem', 
                color: '#555',
                lineHeight: '1.5'
              }}>
                {project.description}
              </div>
            </div>
          )}

          {/* 项目健康度 */}
          <div style={{ 
            background: progress >= 80 ? '#e8f5e9' : progress >= 50 ? '#fff3e0' : '#ffebee', 
            padding: '12px', 
            borderRadius: '8px', 
            marginBottom: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '1.2rem' }}>
                {progress >= 80 ? '✅' : progress >= 50 ? '⚠️' : '🔴'}
              </span>
              <div>
                <div style={{ 
                  fontSize: '0.75rem', 
                  fontWeight: 600, 
                  color: progress >= 80 ? '#2e7d32' : progress >= 50 ? '#ef6c00' : '#c62828' 
                }}>
                  项目健康度
                </div>
                <div style={{ fontSize: '0.8rem', color: '#666' }}>
                  {progress >= 80 ? '良好' : progress >= 50 ? '一般' : '需关注'}
                </div>
              </div>
            </div>
            <span style={{ 
              fontSize: '1rem', 
              fontWeight: 700, 
              color: progress >= 80 ? '#2e7d32' : progress >= 50 ? '#ef6c00' : '#c62828'
            }}>
              {progress}%
            </span>
          </div>

          {/* 任务进度 */}
          <div style={{ 
            background: '#f8f9fa', 
            padding: '12px', 
            borderRadius: '8px', 
            marginBottom: '16px' 
          }}>
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              marginBottom: '8px' 
            }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '6px', 
                fontSize: '0.85rem', 
                color: '#666' 
              }}>
                <ListTodo size={16} />
                任务进度
              </div>
              <span style={{ 
                fontSize: '0.85rem', 
                fontWeight: 600, 
                color: '#667eea' 
              }}>
                {progress}%
              </span>
            </div>
            
            {/* 进度条 */}
            <div style={{ 
              height: '8px', 
              background: '#e0e0e0', 
              borderRadius: '4px', 
              overflow: 'hidden', 
              marginBottom: '8px' 
            }}>
              <div style={{ 
                width: `${progress}%`, 
                height: '100%', 
                background: progress === 100 ? '#28a745' : '#667eea',
                borderRadius: '4px',
                transition: 'width 0.3s'
              }} />
            </div>

            {/* 统计数字 */}
            <div style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              fontSize: '0.75rem' 
            }}>
              <span style={{ color: '#28a745' }}>
                ✓ {project.task_stats?.completed || 0}
              </span>
              <span style={{ color: '#007bff' }}>
                ▶ {project.task_stats?.in_progress || 0}
              </span>
              <span style={{ color: '#ffc107' }}>
                ○ {project.task_stats?.todo || 0}
              </span>
              <span style={{ color: '#666', fontWeight: 600 }}>
                共 {project.task_stats?.total || 0}
              </span>
            </div>
          </div>

          {/* 任务列表 */}
          <div style={{ 
            marginTop: '16px', 
            paddingTop: '16px', 
            borderTop: '1px solid #e0e0e0' 
          }}>
            <ProjectTaskList 
              tasks={tasks} 
              loading={loadingTasks} 
              onTaskClick={onTaskClick}
            />
          </div>

          {/* 创建时间 */}
          <div style={{ 
            marginTop: '16px',
            paddingTop: '12px',
            borderTop: '1px solid #e0e0e0',
            fontSize: '0.75rem',
            color: '#999',
            display: 'flex',
            alignItems: 'center',
            gap: '4px'
          }}>
            <FileText size={12} />
            创建于 {new Date(project.created_at).toLocaleDateString('zh-CN')}
          </div>
        </div>
      )}
    </>
  )

  // 全屏遮罩
  if (isFullscreen) {
    return (
      <div 
        className="fullscreen-overlay"
        onClick={() => setIsFullscreen(false)}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0,0,0,0.7)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 9999,
          padding: '24px',
          backdropFilter: 'blur(4px)'
        }}
      >
        <div 
          className={`card project-card ${className}`}
          onClick={e => e.stopPropagation()}
          style={{
            width: '100%',
            maxWidth: '800px',
            maxHeight: '90vh',
            overflow: 'auto',
            background: 'white',
            borderRadius: '16px',
            padding: '32px',
            boxShadow: '0 25px 80px rgba(0,0,0,0.3)',
            borderLeft: `4px solid ${getStatusColor(project.status)}`,
            animation: 'zoomIn 0.3s ease-out'
          }}
        >
          {cardContent}
        </div>
      </div>
    )
  }

  // 普通卡片
  return (
    <div 
      className={`card project-card project-card-collapsible ${className}`}
      style={{
        borderLeft: `4px solid ${getStatusColor(project.status)}`,
        transition: 'all 0.3s ease',
        cursor: 'pointer'
      }}
      onClick={toggleExpand}
    >
      {cardContent}
    </div>
  )
}

export default ProjectCard
