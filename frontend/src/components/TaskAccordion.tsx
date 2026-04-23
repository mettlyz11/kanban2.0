import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2 } from 'lucide-react'
import { TaskAttachments } from "../components/TaskAttachments"
import { TaskExecutionLog } from "../components/TaskExecutionLog"

interface Task {
  id: number
  number: string
  title: string
  status: string
  priority: string
  description?: string
  execution_log?: string
  remaining_issues?: string
  improvement_suggestions?: string
  created_at: string
}

interface TaskAccordionProps {
  tasks: Task[]
  onDeleteTask: (id: number) => void
}

export function TaskAccordion({ tasks, onDeleteTask }: TaskAccordionProps) {
  const [expandedTask, setExpandedTask] = useState<number | null>(null)
  const [taskData, setTaskData] = useState<Task[]>(tasks)

  const toggleTask = (taskId: number) => {
    setExpandedTask(expandedTask === taskId ? null : taskId)
  }

  const handleUpdateLog = async (taskId: number, data: {
    execution_log?: string
    remaining_issues?: string
    improvement_suggestions?: string
  }) => {
    try {
      const response = await fetch('/api/tasks/' + taskId + '/execution-log', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
      })
      if (response.ok) {
        setTaskData(prev => prev.map(t => 
          t.id === taskId ? { ...t, ...data } : t
        ))
      }
    } catch (error) {
      console.error('Failed to update execution log:', error)
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
      {taskData.map(task => (
        <div 
          key={task.id}
          style={{
            background: '#fff',
            borderRadius: '8px',
            border: '1px solid #e0e0e0',
            overflow: 'hidden'
          }}
        >
          <div 
            onClick={() => toggleTask(task.id)}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              padding: '12px 16px',
              cursor: 'pointer',
              background: expandedTask === task.id ? '#f8f9fa' : '#fff',
              borderBottom: expandedTask === task.id ? '1px solid #e0e0e0' : 'none'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1 }}>
              <span style={{ color: '#667eea' }}>
                {expandedTask === task.id ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </span>
              <span style={{ 
                fontSize: '0.75rem', 
                color: '#667eea', 
                fontWeight: 600, 
                fontFamily: 'monospace',
                background: '#f0f4ff',
                padding: '2px 8px',
                borderRadius: '4px'
              }}>
                {task.number}
              </span>
              <span style={{ fontSize: '0.95rem', color: '#333', fontWeight: 500 }}>
                {task.title}
              </span>
              <span style={{ 
                fontSize: '0.7rem', 
                color: '#999', 
                fontFamily: 'monospace',
                background: '#f5f5f5',
                padding: '2px 6px',
                borderRadius: '4px',
                marginLeft: '8px'
              }}>
                #{task.id}
              </span>
              <span style={{ 
                fontSize: '0.7rem', 
                color: task.task_type === 'guide' ? '#ff6b6b' : '#51cf66', 
                fontWeight: 600,
                background: task.task_type === 'guide' ? '#fff5f5' : '#f0fff4',
                padding: '2px 8px',
                borderRadius: '4px',
                marginLeft: '8px',
                border: '1px solid ' + (task.task_type === 'guide' ? '#ffc9c9' : '#b2f2bb')
              }}>
                {task.task_type === 'guide' ? '【指导性】' : '【普通】'}
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span className={'badge ' + (
                task.priority === 'high' ? 'badge-red' : 
                task.priority === 'medium' ? 'badge-orange' : 'badge-green'
              )} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
              </span>
              <span className={'status-badge status-' + task.status} style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                {task.status === 'todo' ? '待办' : task.status === 'progress' ? '进行中' : '已完成'}
              </span>
              <button
                onClick={(e) => {
                  e.stopPropagation()
                  onDeleteTask(task.id)
                }}
                style={{
                  background: '#ffebee',
                  border: 'none',
                  color: '#c62828',
                  cursor: 'pointer',
                  padding: '6px 10px',
                  borderRadius: '4px',
                  display: 'flex',
                  alignItems: 'center'
                }}
                title="删除任务"
              >
                <Trash2 size={16} />
              </button>
            </div>
          </div>

          {expandedTask === task.id && (
            <div style={{ padding: '16px', background: '#fafbfc' }}>
              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '6px' }}>
                  任务编号
                </div>
                <div style={{ fontSize: '0.9rem', color: '#667eea', fontFamily: 'monospace' }}>
                  {task.number}
                </div>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '6px' }}>
                  状态
                </div>
                <span className={'status-badge status-' + task.status}>
                  {task.status === 'todo' ? '待办' : task.status === 'progress' ? '进行中' : '已完成'}
                </span>
              </div>

              <div style={{ marginBottom: '12px' }}>
                <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '6px' }}>
                  优先级
                </div>
                <span className={'badge ' + (
                  task.priority === 'high' ? 'badge-red' : 
                  task.priority === 'medium' ? 'badge-orange' : 'badge-green'
                )}>
                  {task.priority === 'high' ? '高' : task.priority === 'medium' ? '中' : '低'}
                </span>
              </div>

              {task.description && (
                <div style={{ marginBottom: '12px' }}>
                  <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '6px' }}>
                    描述
                  </div>
                  <div style={{ fontSize: '0.9rem', color: '#333', lineHeight: '1.6', whiteSpace: 'pre-wrap' }}>
                    {task.description}
                  </div>
                </div>
              )}

              <div style={{ fontSize: '0.75rem', color: '#999', marginBottom: '16px' }}>
                创建时间：{new Date(task.created_at).toLocaleString('zh-CN')}
              </div>

              <TaskAttachments taskId={task.id} />
              
              <TaskExecutionLog
                taskId={task.id}
                executionLog={task.execution_log}
                remainingIssues={task.remaining_issues}
                improvementSuggestions={task.improvement_suggestions}
                onUpdate={(data) => handleUpdateLog(task.id, data)}
              />
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
