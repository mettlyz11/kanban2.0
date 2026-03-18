import { useState, useEffect } from 'react'
import { ArrowLeft, Save, RefreshCw, Plus, Trash2, ArrowUp, ArrowDown, Edit2, FileText } from 'lucide-react'

interface WorkflowStep {
  id: number
  title: string
  content: string
  file: string
}

const defaultWorkflow: WorkflowStep[] = [
  {
    id: 1,
    title: "HEARTBEAT检查",
    content: "每小时检查系统状态\n- 检查Git状态\n- 检查阿里云服务状态\n- 检查日历日程",
    file: "HEARTBEAT.md"
  },
  {
    id: 2,
    title: "邮件处理",
    content: "检查并处理新邮件\n- 同步邮件\n- 分析重要邮件\n- 生成回复建议",
    file: "email_handler.md"
  },
  {
    id: 3,
    title: "日历管理",
    content: "管理日程安排\n- 检查即将开始的日程\n- 发送提醒\n- 记录会议要点",
    file: "calendar_manager.md"
  },
  {
    id: 4,
    title: "任务执行",
    content: "执行看板任务\n- 读取任务列表\n- 执行开发/修复任务\n- 更新任务状态",
    file: "task_executor.md"
  },
  {
    id: 5,
    title: "进展汇报",
    content: "整点汇报进展\n- 汇总Git提交\n- 汇报服务状态\n- 报告任务进度",
    file: "progress_reporter.md"
  }
]

export function Architecture() {
  const [steps, setSteps] = useState<WorkflowStep[]>([])
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [editMode, setEditMode] = useState(false)
  const [editingStep, setEditingStep] = useState<number | null>(null)
  const [editForm, setEditForm] = useState<WorkflowStep | null>(null)

  useEffect(() => {
    loadWorkflow()
  }, [])

  const loadWorkflow = () => {
    setLoading(true)
    // 从localStorage加载或使用默认
    const saved = localStorage.getItem('dudu_workflow')
    if (saved) {
      setSteps(JSON.parse(saved))
    } else {
      setSteps(defaultWorkflow)
    }
    setLoading(false)
  }

  const saveWorkflow = async () => {
    setSaving(true)
    localStorage.setItem('dudu_workflow', JSON.stringify(steps))
    
    // 同时保存到后端
    try {
      await fetch('/api/workflow', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ steps })
      })
    } catch (e) {
      console.log('后端保存失败，已保存到本地')
    }
    
    alert('保存成功！')
    setSaving(false)
  }

  const resetWorkflow = () => {
    if (confirm('确定要重置为默认工作流程吗？所有修改将丢失。')) {
      localStorage.removeItem('dudu_workflow')
      setSteps(defaultWorkflow)
    }
  }

  const moveStep = (index: number, direction: 'up' | 'down') => {
    const newSteps = [...steps]
    if (direction === 'up' && index > 0) {
      [newSteps[index], newSteps[index - 1]] = [newSteps[index - 1], newSteps[index]]
    } else if (direction === 'down' && index < newSteps.length - 1) {
      [newSteps[index], newSteps[index + 1]] = [newSteps[index + 1], newSteps[index]]
    }
    setSteps(newSteps)
  }

  const deleteStep = (index: number) => {
    if (confirm('确定要删除这个步骤吗？')) {
      const newSteps = steps.filter((_, i) => i !== index)
      setSteps(newSteps)
    }
  }

  const addStep = () => {
    const newStep: WorkflowStep = {
      id: Date.now(),
      title: "新步骤",
      content: "点击编辑内容...",
      file: "new_step.md"
    }
    setSteps([...steps, newStep])
  }

  const startEdit = (step: WorkflowStep, index: number) => {
    setEditingStep(index)
    setEditForm({ ...step })
  }

  const saveEdit = () => {
    if (editForm && editingStep !== null) {
      const newSteps = [...steps]
      newSteps[editingStep] = editForm
      setSteps(newSteps)
      setEditingStep(null)
      setEditForm(null)
    }
  }

  const cancelEdit = () => {
    setEditingStep(null)
    setEditForm(null)
  }

  const editFile = async (filename: string, content: string) => {
    const newContent = prompt(`编辑文件: ${filename}\n\n文件内容:`, content)
    if (newContent !== null) {
      // 保存到localStorage
      const files = JSON.parse(localStorage.getItem('workflow_files') || '{}')
      files[filename] = newContent
      localStorage.setItem('workflow_files', JSON.stringify(files))
      alert(`文件 ${filename} 已保存！`)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 p-6">
      <div className="max-w-5xl mx-auto">
        {/* 头部 */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-4">
            <a href="/" className="p-2 bg-white rounded-lg shadow hover:shadow-md transition">
              <ArrowLeft className="h-5 w-5 text-gray-600" />
            </a>
            <div>
              <h1 className="text-2xl font-bold text-gray-900">Dudu工作流程架构</h1>
              <p className="text-sm text-gray-500 mt-1">可编辑的工作流程管理系统</p>
            </div>
          </div>
          <div className="flex space-x-3">
            <button
              onClick={resetWorkflow}
              className="px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 transition"
            >
              重置
            </button>
            <button
              onClick={() => setEditMode(!editMode)}
              className={`px-4 py-2 rounded-lg transition flex items-center gap-2 ${
                editMode 
                  ? 'bg-green-600 text-white hover:bg-green-700' 
                  : 'bg-blue-600 text-white hover:bg-blue-700'
              }`}
            >
              <Edit2 className="h-4 w-4" />
              {editMode ? '完成编辑' : '编辑模式'}
            </button>
            <button
              onClick={saveWorkflow}
              disabled={saving}
              className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {saving ? '保存中...' : '保存'}
            </button>
          </div>
        </div>

        {/* 信息提示 */}
        <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-r-lg mb-6">
          <p className="text-sm text-yellow-800">
            <strong>💡 提示：</strong>
            {editMode 
              ? '编辑模式已开启。点击任意步骤的"编辑"按钮修改内容，使用上下箭头调整顺序，或拖拽重新排序。' 
              : '点击"编辑模式"可以修改工作流程。每个步骤都可以编辑标题、内容和关联的MD文件。'}
          </p>
        </div>

        {/* 添加步骤按钮 */}
        {editMode && (
          <button
            onClick={addStep}
            className="w-full mb-4 p-4 border-2 border-dashed border-gray-300 rounded-xl text-gray-500 hover:border-blue-400 hover:text-blue-600 transition flex items-center justify-center gap-2"
          >
            <Plus className="h-5 w-5" />
            添加新步骤
          </button>
        )}

        {/* 工作流程步骤 */}
        <div className="space-y-4">
          {steps.map((step, index) => (
            <div key={step.id}>
              <div 
                className={`bg-white rounded-xl shadow-sm border p-6 transition ${
                  editMode ? 'border-blue-300 shadow-md' : ''
                }`}
              >
                {/* 步骤头部 */}
                <div className="flex items-start justify-between mb-4">
                  <div className="flex items-center gap-4">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-purple-600 text-white flex items-center justify-center font-bold text-lg">
                      {index + 1}
                    </div>
                    
                    {editingStep === index ? (
                      <input
                        type="text"
                        value={editForm?.title || ''}
                        onChange={(e) => setEditForm({ ...editForm!, title: e.target.value })}
                        className="text-xl font-bold text-gray-900 border-b-2 border-blue-500 focus:outline-none bg-transparent"
                      />
                    ) : (
                      <h3 className="text-xl font-bold text-gray-900">{step.title}</h3>
                    )}
                  </div>
                  
                  {/* 操作按钮 */}
                  <div className="flex items-center gap-2">
                    {editMode && (
                      <>
                        {editingStep === index ? (
                          <>
                            <button
                              onClick={saveEdit}
                              className="p-2 text-green-600 hover:bg-green-50 rounded-lg"
                              title="保存"
                            >
                              <Save className="h-4 w-4" />
                            </button>
                            <button
                              onClick={cancelEdit}
                              className="p-2 text-gray-600 hover:bg-gray-50 rounded-lg"
                              title="取消"
                            >
                              ×
                            </button>
                          </>
                        ) : (
                          <button
                            onClick={() => startEdit(step, index)}
                            className="p-2 text-blue-600 hover:bg-blue-50 rounded-lg"
                            title="编辑"
                          >
                            <Edit2 className="h-4 w-4" />
                          </button>
                        )}
                        <button
                          onClick={() => moveStep(index, 'up')}
                          disabled={index === 0}
                          className="p-2 text-gray-600 hover:bg-gray-50 rounded-lg disabled:opacity-30"
                          title="上移"
                        >
                          <ArrowUp className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => moveStep(index, 'down')}
                          disabled={index === steps.length - 1}
                          className="p-2 text-gray-600 hover:bg-gray-50 rounded-lg disabled:opacity-30"
                          title="下移"
                        >
                          <ArrowDown className="h-4 w-4" />
                        </button>
                        <button
                          onClick={() => deleteStep(index)}
                          className="p-2 text-red-600 hover:bg-red-50 rounded-lg"
                          title="删除"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </>
                    )}
                  </div>
                </div>

                {/* 步骤内容 */}
                <div className="ml-14">
                  {editingStep === index ? (
                    <textarea
                      value={editForm?.content || ''}
                      onChange={(e) => setEditForm({ ...editForm!, content: e.target.value })}
                      className="w-full h-32 p-3 border rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
                    />
                  ) : (
                    <div className="text-gray-600 whitespace-pre-line leading-relaxed">
                      {step.content}
                    </div>
                  )}

                  {/* 关联文件 */}
                  <div className="mt-4 flex items-center gap-2">
                    <FileText className="h-4 w-4 text-gray-400" />
                    <span className="text-sm text-gray-500">关联文件:</span>
                    {editingStep === index ? (
                      <input
                        type="text"
                        value={editForm?.file || ''}
                        onChange={(e) => setEditForm({ ...editForm!, file: e.target.value })}
                        className="text-sm border-b border-gray-300 focus:border-blue-500 focus:outline-none"
                      />
                    ) : (
                      <span className="text-sm font-mono bg-gray-100 px-2 py-1 rounded">{step.file}</span>
                    )}
                    <button
                      onClick={() => editFile(step.file, step.content)}
                      className="text-sm text-blue-600 hover:text-blue-700 ml-2"
                    >
                      编辑文件
                    </button>
                  </div>
                </div>
              </div>

              {/* 箭头（除了最后一个） */}
              {index < steps.length - 1 && (
                <div className="flex justify-center my-2">
                  <div className="text-2xl text-gray-300">↓</div>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* 底部信息 */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>共 {steps.length} 个步骤 | 上次保存: {new Date().toLocaleString('zh-CN')}</p>
        </div>
      </div>
    </div>
  )
}export default Architecture
