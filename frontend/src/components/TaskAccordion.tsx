import { useState } from 'react'
import { ChevronDown, ChevronUp, Trash2, CheckCircle, XCircle, MessageSquare, History } from 'lucide-react'
import { TaskAttachments } from "../components/TaskAttachments"
import { TaskExecutionLog } from "../components/TaskExecutionLog"

interface Task {
  project_name?: string;
  project_number?: string;
  task_type?: string;
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
  review_round?: number
  review_feedback?: string
}

interface TaskAccordionProps {
  tasks: Task[]
  onDeleteTask: (id: number) => void
  onReviewTask?: (id: number, action: 'approve' | 'reject' | 'skip') => void
  showReviewActions?: boolean
}

export function TaskAccordion({ tasks, onDeleteTask, onReviewTask, showReviewActions = false }: TaskAccordionProps) {
  const [expandedTask, setExpandedTask] = useState<number | null>(null)
  const [taskData, setTaskData] = useState<Task[]>(tasks)
  const [feedbackTaskId, setFeedbackTaskId] = useState<number | null>(null)
  const [feedbackText, setFeedbackText] = useState('')
  const [reviewHistory, setReviewHistory] = useState<{[key: number]: any[]}>({})

  const handleSubmitFeedback = async (taskId: number) => {
    if (!feedbackText.trim()) return
    if (onReviewTask) {
      onReviewTask(taskId, 'feedback', feedbackText)
      setFeedbackTaskId(null)
      setFeedbackText('')
    }
  }

  const fetchReviewHistory = async (taskId: number) => {
    try {
      const response = await fetch(`/api/tasks/${taskId}/review-history`)
      const data = await response.json()
      if (data.success) {
        setReviewHistory(prev => ({ ...prev, [taskId]: data.history }))
      }
    } catch (error) {
      console.error('Failed to fetch review history:', error)
    }
  }

  const toggleTaskWithHistory = (taskId: number) => {
    const isExpanding = expandedTask !== taskId
    setExpandedTask(expandedTask === taskId ? null : taskId)
    if (isExpanding) {
      fetchReviewHistory(taskId)
    }
  }

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
            onClick={() => toggleTaskWithHistory(task.id)}
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
              {task.project_name && (
                <span style={{
                  fontSize: '0.75rem',
                  color: '#666',
                  background: '#f0f4ff',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  marginRight: '8px'
                }}>
                  [{task.project_number || 'N/A'}] {task.project_name}
                </span>
              )}
              <span style={{ fontSize: '0.95rem', color: '#333', fontWeight: 500 }}>
                {task.title}
              </span>
              {task.review_round > 0 && (
                <span style={{
                  fontSize: '0.7rem',
                  color: '#ff9800',
                  background: '#fff3e0',
                  padding: '2px 6px',
                  borderRadius: '4px',
                  marginLeft: '8px',
                  border: '1px solid #ffcc80'
                }}>
                  第{task.review_round}轮
                </span>
              )}
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
              <span className={'status-badge status-' + task.status} style={{
                  fontSize: '0.75rem',
                  padding: '4px 10px',
                  background:
                    task.status === 'failed' || task.status === 'cancelled' ? '#f8d7da' :
                    task.status === 'failed_retryable' ? '#ffeeba' :
                    task.status === 'redundant' ? '#e2e3e5' :
                    task.status === 'todo' || task.status === 'pending' ? '#fff3cd' :
                    task.status === 'progress' || task.status === 'in_progress' ? '#cce5ff' :
                    '#d4edda',
                  color:
                    task.status === 'failed' || task.status === 'cancelled' ? '#721c24' :
                    task.status === 'failed_retryable' ? '#856404' :
                    task.status === 'redundant' ? '#383d41' :
                    task.status === 'todo' || task.status === 'pending' ? '#856404' :
                    task.status === 'progress' || task.status === 'in_progress' ? '#004085' :
                    '#155724'
                }}>
                {task.status === 'failed' ? '失败' : task.status === 'failed_retryable' ? '重试中' : task.status === 'redundant' ? '冗余' : task.status === 'cancelled' ? '已取消' : task.status === 'todo' || task.status === 'pending' ? '待办' : task.status === 'progress' || task.status === 'in_progress' ? '进行中' : '已完成'}
              </span>
              {showReviewActions && task.status === 'pending_review' && onReviewTask && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onReviewTask(task.id, 'approve')
                    }}
                    style={{
                      background: '#e8f5e9',
                      border: '1px solid #4caf50',
                      color: '#2e7d32',
                      cursor: 'pointer',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      fontWeight: 500
                    }}
                    title="通过"
                  >
                    <CheckCircle size={14} />
                    通过
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      setFeedbackTaskId(task.id)
                    }}
                    style={{
                      background: '#fff3e0',
                      border: '1px solid #ff9800',
                      color: '#e65100',
                      cursor: 'pointer',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      fontWeight: 500
                    }}
                    title="要求修改"
                  >
                    <MessageSquare size={14} />
                    要求修改
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation()
                      onReviewTask(task.id, 'reject')
                    }}
                    style={{
                      background: '#ffebee',
                      border: '1px solid #ef5350',
                      color: '#c62828',
                      cursor: 'pointer',
                      padding: '6px 12px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center',
                      gap: '4px',
                      fontSize: '0.8rem',
                      fontWeight: 500
                    }}
                    title="驳回"
                  >
                    <XCircle size={14} />
                    驳回
                  </button>
                </div>
              )}
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
                <span className={'status-badge status-' + task.status} style={{
                    background:
                      task.status === 'failed' || task.status === 'cancelled' ? '#f8d7da' :
                      task.status === 'failed_retryable' ? '#ffeeba' :
                      task.status === 'redundant' ? '#e2e3e5' :
                      task.status === 'todo' || task.status === 'pending' ? '#fff3cd' :
                      task.status === 'progress' || task.status === 'in_progress' ? '#cce5ff' :
                      '#d4edda',
                    color:
                      task.status === 'failed' || task.status === 'cancelled' ? '#721c24' :
                      task.status === 'failed_retryable' ? '#856404' :
                      task.status === 'redundant' ? '#383d41' :
                      task.status === 'todo' || task.status === 'pending' ? '#856404' :
                      task.status === 'progress' || task.status === 'in_progress' ? '#004085' :
                      '#155724'
                  }}>
                  {task.status === 'failed' ? '失败' : task.status === 'failed_retryable' ? '重试中' : task.status === 'redundant' ? '冗余' : task.status === 'cancelled' ? '已取消' : task.status === 'todo' || task.status === 'pending' ? '待办' : task.status === 'progress' || task.status === 'in_progress' ? '进行中' : '已完成'}
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

              {/* 反馈输入框 */}
              {feedbackTaskId === task.id && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px',
                  background: '#fff8e1',
                  borderRadius: '8px',
                  border: '1px solid #ffcc80'
                }}>
                  <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#e65100', marginBottom: '8px' }}>
                    提供修改反馈
                  </div>
                  <textarea
                    value={feedbackText}
                    onChange={(e) => setFeedbackText(e.target.value)}
                    placeholder="请描述需要修改的内容..."
                    style={{
                      width: '100%',
                      minHeight: '80px',
                      padding: '8px',
                      borderRadius: '4px',
                      border: '1px solid #ddd',
                      fontSize: '0.85rem',
                      resize: 'vertical'
                    }}
                  />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px', justifyContent: 'flex-end' }}>
                    <button
                      onClick={() => {
                        setFeedbackTaskId(null)
                        setFeedbackText('')
                      }}
                      style={{
                        padding: '6px 12px',
                        border: '1px solid #ddd',
                        background: '#fff',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      取消
                    </button>
                    <button
                      onClick={() => handleSubmitFeedback(task.id)}
                      style={{
                        padding: '6px 12px',
                        border: 'none',
                        background: '#ff9800',
                        color: '#fff',
                        borderRadius: '4px',
                        cursor: 'pointer',
                        fontSize: '0.8rem'
                      }}
                    >
                      提交反馈
                    </button>
                  </div>
                </div>
              )}

              {/* 审核历史记录 */}
              {reviewHistory[task.id] && reviewHistory[task.id].length > 0 && (
                <div style={{
                  marginTop: '16px',
                  padding: '12px',
                  background: '#f5f5f5',
                  borderRadius: '8px'
                }}>
                  <div style={{ 
                    fontSize: '0.85rem', 
                    fontWeight: 600, 
                    color: '#666', 
                    marginBottom: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '6px'
                  }}>
                    <History size={14} />
                    审核历史
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {reviewHistory[task.id].map((item: any) => (
                      <div key={item.id} style={{
                        padding: '8px',
                        background: '#fff',
                        borderRadius: '4px',
                        borderLeft: `3px solid ${
                          item.action === 'approve' ? '#4caf50' :
                          item.action === 'reject' ? '#ef5350' :
                          item.action === 'feedback' ? '#ff9800' : '#999'
                        }`
                      }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600 }}>
                            {item.action === 'approve' ? '✓ 通过' :
                             item.action === 'reject' ? '✗ 驳回' :
                             item.action === 'feedback' ? '💬 要求修改' : item.action}
                          </span>
                          <span style={{ fontSize: '0.75rem', color: '#999' }}>
                            第{item.round_number}轮
                          </span>
                        </div>
                        {item.feedback && (
                          <div style={{ fontSize: '0.8rem', color: '#333', marginTop: '4px' }}>
                            {item.feedback}
                          </div>
                        )}
                        <div style={{ fontSize: '0.75rem', color: '#999', marginTop: '4px' }}>
                          {new Date(item.created_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}
