import { useState } from 'react'
import { Edit2, Save, X } from 'lucide-react'

interface TaskExecutionLogProps {
  taskId: number
  executionLog?: string
  remainingIssues?: string
  improvementSuggestions?: string
  onUpdate: (data: {
    execution_log?: string
    remaining_issues?: string
    improvement_suggestions?: string
  }) => void
}

export function TaskExecutionLog({
  taskId,
  executionLog = '',
  remainingIssues = '',
  improvementSuggestions = '',
  onUpdate
}: TaskExecutionLogProps) {
  const [isEditing, setIsEditing] = useState(false)
  const [editData, setEditData] = useState({
    execution_log: executionLog,
    remaining_issues: remainingIssues,
    improvement_suggestions: improvementSuggestions
  })

  const handleSave = () => {
    onUpdate(editData)
    setIsEditing(false)
  }

  const handleCancel = () => {
    setEditData({
      execution_log: executionLog,
      remaining_issues: remainingIssues,
      improvement_suggestions: improvementSuggestions
    })
    setIsEditing(false)
  }

  if (isEditing) {
    return (
      <div style={{ marginTop: '20px', padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <h4 style={{ margin: 0, color: '#333' }}>📝 执行详情记录</h4>
          <div style={{ display: 'flex', gap: '8px' }}>
            <button onClick={handleSave} style={{ padding: '6px 12px', background: '#28a745', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Save size={14} /> 保存
            </button>
            <button onClick={handleCancel} style={{ padding: '6px 12px', background: '#6c757d', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <X size={14} /> 取消
            </button>
          </div>
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
            执行详细过程
          </label>
          <textarea
            value={editData.execution_log}
            onChange={(e) => setEditData({ ...editData, execution_log: e.target.value })}
            placeholder="记录任务执行的详细步骤、过程和结果..."
            style={{ width: '100%', minHeight: '100px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '0.9rem', resize: 'vertical' }}
          />
        </div>

        <div style={{ marginBottom: '16px' }}>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
            剩余问题
          </label>
          <textarea
            value={editData.remaining_issues}
            onChange={(e) => setEditData({ ...editData, remaining_issues: e.target.value })}
            placeholder="记录尚未解决的问题、阻塞点..."
            style={{ width: '100%', minHeight: '80px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '0.9rem', resize: 'vertical' }}
          />
        </div>

        <div>
          <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
            建议的改进方向
          </label>
          <textarea
            value={editData.improvement_suggestions}
            onChange={(e) => setEditData({ ...editData, improvement_suggestions: e.target.value })}
            placeholder="记录对任务执行的改进建议、优化方向..."
            style={{ width: '100%', minHeight: '80px', padding: '10px', border: '1px solid #ddd', borderRadius: '4px', fontSize: '0.9rem', resize: 'vertical' }}
          />
        </div>
      </div>
    )
  }

  return (
    <div style={{ marginTop: '20px', padding: '16px', background: '#f8f9fa', borderRadius: '8px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
        <h4 style={{ margin: 0, color: '#333' }}>📝 执行详情记录</h4>
        <button onClick={() => setIsEditing(true)} style={{ padding: '6px 12px', background: '#667eea', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}>
          <Edit2 size={14} /> 编辑
        </button>
      </div>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
          执行详细过程
        </div>
        <div style={{ fontSize: '0.9rem', color: '#333', lineHeight: '1.6', whiteSpace: 'pre-wrap', background: 'white', padding: '12px', borderRadius: '4px', border: '1px solid #e0e0e0' }}>
          {executionLog || <span style={{ color: '#999', fontStyle: 'italic' }}>暂无记录</span>}
        </div>
      </div>

      <div style={{ marginBottom: '16px' }}>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
          剩余问题
        </div>
        <div style={{ fontSize: '0.9rem', color: '#333', lineHeight: '1.6', whiteSpace: 'pre-wrap', background: 'white', padding: '12px', borderRadius: '4px', border: '1px solid #e0e0e0' }}>
          {remainingIssues || <span style={{ color: '#999', fontStyle: 'italic' }}>暂无记录</span>}
        </div>
      </div>

      <div>
        <div style={{ fontSize: '0.8rem', fontWeight: 600, color: '#666', marginBottom: '8px' }}>
          建议的改进方向
        </div>
        <div style={{ fontSize: '0.9rem', color: '#333', lineHeight: '1.6', whiteSpace: 'pre-wrap', background: 'white', padding: '12px', borderRadius: '4px', border: '1px solid #e0e0e0' }}>
          {improvementSuggestions || <span style={{ color: '#999', fontStyle: 'italic' }}>暂无记录</span>}
        </div>
      </div>
    </div>
  )
}
