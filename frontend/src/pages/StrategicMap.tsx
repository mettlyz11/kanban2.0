import { useState, useEffect, useCallback } from 'react'
import { Tree, RawNodeDatum } from 'react-d3-tree'
import { Target, FolderOpen, CheckCircle2, Clock, AlertCircle, Loader2 } from 'lucide-react'

interface TreeNode {
  id: string
  type: 'goal' | 'project' | 'task'
  name: string
  category?: string
  progress?: number
  status?: string
  priority?: string
  project_count?: number
  task_count?: number
  raw_id?: number
  children?: TreeNode[]
}

interface ApiResponse {
  success: boolean
  data?: TreeNode[]
  summary?: {
    total_goals: number
    total_projects: number
    total_tasks: number
  }
  error?: string
}

const nodeColors: Record<string, string> = {
  goal: '#1e3a5f',
  project: '#667eea',
  task: '#10b981'
}

const statusColors: Record<string, string> = {
  completed: '#10b981',
  pending: '#f59e0b',
  in_progress: '#3b82f6',
  failed_retryable: '#ef4444'
}

export default function StrategicMap() {
  const [treeData, setTreeData] = useState<RawNodeDatum[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [summary, setSummary] = useState({ total_goals: 0, total_projects: 0, total_tasks: 0 })
  const [selectedNode, setSelectedNode] = useState<TreeNode | null>(null)
  const [translate, setTranslate] = useState({ x: 0, y: 0 })
  const [viewMode, setViewMode] = useState<'tree' | 'card'>('card')
  const [expandedGoal, setExpandedGoal] = useState<string | null>(null)
  const [goalNodes, setGoalNodes] = useState<TreeNode[]>([])

  useEffect(() => {
    const container = document.getElementById('tree-container')
    if (container) {
      setTranslate({ x: container.clientWidth / 2, y: 80 })
    }
  }, [])

  const fetchData = useCallback(async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/strategic-map')
      const data: ApiResponse = await res.json()
      
      if (data.success && data.data) {
        // Convert to react-d3-tree format
        const converted = data.data.map(convertNode)
        setTreeData(converted)
        // Store goal nodes for card view
        setGoalNodes(data.data.filter(n => n.type === 'goal'))
        if (data.summary) setSummary(data.summary)
      } else {
        setError(data.error || '获取数据失败')
      }
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
  }, [fetchData])

  const convertNode = (node: TreeNode): RawNodeDatum => {
    const result: RawNodeDatum = {
      name: node.name,
      attributes: {
        id: node.id,
        type: node.type,
        status: node.status || '',
        progress: String(node.progress || ''),
        project_count: String(node.project_count || ''),
        task_count: String(node.task_count || ''),
        priority: node.priority || '',
        raw_id: String(node.raw_id || '')
      }
    }
    if (node.children && node.children.length > 0) {
      result.children = node.children.map(convertNode)
    }
    return result
  }

  const renderNode = ({ nodeDatum }: { nodeDatum: RawNodeDatum }) => {
    const type = (nodeDatum.attributes?.type as string) || 'task'
    const status = (nodeDatum.attributes?.status as string) || ''
    const color = nodeColors[type] || '#999'
    const statusColor = statusColors[status] || '#999'
    const isGoal = type === 'goal'
    const isProject = type === 'project'
    
    const size = isGoal ? 32 : isProject ? 24 : 16
    
    return (
      <g onClick={() => {
        setSelectedNode({
          id: String(nodeDatum.attributes?.id || ''),
          type: type as 'goal' | 'project' | 'task',
          name: nodeDatum.name,
          status: status,
          progress: Number(nodeDatum.attributes?.progress || 0),
          project_count: Number(nodeDatum.attributes?.project_count || 0),
          task_count: Number(nodeDatum.attributes?.task_count || 0),
          priority: String(nodeDatum.attributes?.priority || ''),
          raw_id: Number(nodeDatum.attributes?.raw_id || 0)
        })
      }} style={{ cursor: 'pointer' }}>
        <circle r={size} fill={color} stroke="#fff" strokeWidth={2} />
        {status && !isGoal && (
          <circle r={size + 4} fill="none" stroke={statusColor} strokeWidth={2} strokeDasharray="3,2" />
        )}
        <text
          x={isGoal ? 42 : 32}
          y={5}
          fill="#333"
          fontSize={isGoal ? 18 : 15}
          fontWeight={isGoal ? 600 : 400}
          style={{ pointerEvents: 'none' }}
        >
          {nodeDatum.name.length > 20 ? nodeDatum.name.slice(0, 20) + '...' : nodeDatum.name}
        </text>
        {isGoal && nodeDatum.attributes?.project_count && (
          <text x={30} y={26} fill="#666" fontSize={13} style={{ pointerEvents: 'none' }}>
            {nodeDatum.attributes.project_count} 项目 · {nodeDatum.attributes.task_count} 任务
          </text>
        )}
      </g>
    )
  }

  const getProgressColor = (progress: number) => {
    if (progress < 20) return 'bg-red-500'
    if (progress < 50) return 'bg-orange-500'
    if (progress < 80) return 'bg-blue-500'
    return 'bg-green-500'
  }

  const flattenProjects = (goal: TreeNode): TreeNode[] => {
    return (goal.children || []).filter(c => c.type === 'project')
  }

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '80vh' }}>
        <Loader2 size={32} className="animate-spin" style={{ color: '#667eea' }} />
        <span style={{ marginLeft: 12, color: '#666' }}>加载战略全景图...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div style={{ padding: 40, textAlign: 'center' }}>
        <AlertCircle size={48} style={{ color: '#ef4444', marginBottom: 16 }} />
        <h3 style={{ color: '#ef4444', marginBottom: 8 }}>加载失败</h3>
        <p style={{ color: '#666' }}>{error}</p>
        <button
          onClick={fetchData}
          style={{
            marginTop: 16,
            padding: '8px 16px',
            background: '#667eea',
            color: '#fff',
            border: 'none',
            borderRadius: 4,
            cursor: 'pointer'
          }}
        >
          重试
        </button>
      </div>
    )
  }

  return (
    <div style={{ padding: '10px 20px', height: 'calc(100vh - 20px)', display: 'flex', flexDirection: 'column' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h2 style={{ margin: 0, display: 'flex', alignItems: 'center', gap: 8 }}>
            <Target size={24} style={{ color: '#667eea' }} />
            战略全景图
          </h2>
          <p style={{ margin: '4px 0 0', color: '#666', fontSize: 14 }}>
            战略目标 · 项目 · 任务 层级关系
          </p>
        </div>
        <div className="flex items-center gap-4">
          {/* View toggle buttons */}
          <div className="inline-flex rounded-lg border border-gray-200 bg-white p-1 shadow-sm">
            <button
              onClick={() => setViewMode('card')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                viewMode === 'card'
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              📋 卡片视图
            </button>
            <button
              onClick={() => setViewMode('tree')}
              className={`flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                viewMode === 'tree'
                  ? 'bg-indigo-100 text-indigo-700'
                  : 'text-gray-500 hover:bg-gray-50'
              }`}
            >
              🌳 树形视图
            </button>
          </div>
          {/* Legend */}
          <div style={{ display: 'flex', gap: 16, fontSize: 14 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#1e3a5f' }} />
            目标 ({summary.total_goals})
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#667eea' }} />
            项目 ({summary.total_projects})
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
            <span style={{ width: 12, height: 12, borderRadius: '50%', background: '#10b981' }} />
            任务 ({summary.total_tasks})
          </span>
          </div>
        </div>
      </div>

      {/* Main content */}
      <div style={{ display: 'flex', flex: 1, gap: 16, overflow: 'hidden' }}>
        {/* Card View */}
        {viewMode === 'card' && (
          <div className="flex-1 overflow-auto p-2">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {goalNodes.map((goal) => (
                <div
                  key={goal.id}
                  className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm hover:shadow-md transition-shadow"
                >
                  {/* Goal name */}
                  <h3 className="font-bold text-lg mb-3 text-gray-800 truncate">{goal.name}</h3>

                  {/* Progress bar */}
                  {goal.progress !== undefined && goal.progress > 0 && (
                    <div className="mb-3">
                      <div className="flex justify-between mb-1 text-sm">
                        <span className="text-gray-500">进度</span>
                        <span className="font-semibold text-gray-700">{goal.progress}%</span>
                      </div>
                      <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                        <div
                          className={`h-full rounded-full transition-all ${getProgressColor(goal.progress)}`}
                          style={{ width: `${goal.progress}%` }}
                        />
                      </div>
                    </div>
                  )}

                  {/* Counts */}
                  <div className="flex items-center gap-4 text-sm text-gray-600 mb-3">
                    <span className="flex items-center gap-1.5">
                      <FolderOpen size={14} />
                      项目 {goal.project_count || 0}
                    </span>
                    <span className="flex items-center gap-1.5">
                      <CheckCircle2 size={14} />
                      任务 {goal.task_count || 0}
                    </span>
                  </div>

                  {/* Expand/Collapse button */}
                  {goal.children && goal.children.length > 0 && (
                    <button
                      onClick={() => setExpandedGoal(expandedGoal === goal.id ? null : goal.id)}
                      className="w-full mt-1 text-sm text-indigo-600 hover:text-indigo-800 font-medium py-1.5 rounded-lg border border-indigo-200 hover:bg-indigo-50 transition-colors"
                    >
                      {expandedGoal === goal.id ? '收起项目 ▲' : '展开项目 ▼'}
                    </button>
                  )}

                  {/* Expanded project list */}
                  {expandedGoal === goal.id && (
                    <div className="mt-3 pt-3 border-t border-gray-100 space-y-2">
                      {flattenProjects(goal).map((project) => (
                        <div
                          key={project.id}
                          className="rounded-lg bg-gray-50 p-3 text-sm"
                        >
                          <div className="font-medium text-gray-800 mb-1">{project.name}</div>
                          <div className="flex items-center gap-2 text-xs text-gray-500">
                            {project.status && (
                              <span
                                className="px-1.5 py-0.5 rounded"
                                style={{
                                  background: (statusColors[project.status] || '#999') + '20',
                                  color: statusColors[project.status] || '#999'
                                }}
                              >
                                {project.status === 'completed' ? '已完成' : project.status === 'pending' ? '待办' : project.status === 'in_progress' ? '进行中' : project.status}
                              </span>
                            )}
                            {project.progress !== undefined && project.progress > 0 && (
                              <span>{project.progress}%</span>
                            )}
                            {project.task_count !== undefined && project.task_count > 0 && (
                              <span>{project.task_count} 任务</span>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Tree View */}
        {viewMode === 'tree' && (
        <div id="tree-container" style={{ flex: 1, border: '1px solid #e5e7eb', borderRadius: 8, background: '#fafbfc', overflow: 'hidden' }}>
          {treeData.length > 0 && (
            <Tree
              data={treeData}
              translate={translate}
              orientation="vertical"
              renderCustomNodeElement={renderNode}
              collapsible={true}
              initialDepth={1}
              zoom={1.0}
              separation={{ siblings: 1.5, nonSiblings: 2.0 }}
              nodeSize={{ x: 220, y: 160 }}
              pathClassFunc={() => 'link'}
              styles={{
                links: { stroke: '#d1d5db', strokeWidth: 1.5 }
              }}
            />
          )}
        </div>
        )}

        {/* Detail panel (shown in both views) */}
        {selectedNode && viewMode === 'tree' && (
          <div style={{ width: 300, border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, background: '#fff', overflow: 'auto' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
              {selectedNode.type === 'goal' && <Target size={18} style={{ color: '#1e3a5f' }} />}
              {selectedNode.type === 'project' && <FolderOpen size={18} style={{ color: '#667eea' }} />}
              {selectedNode.type === 'task' && <CheckCircle2 size={18} style={{ color: '#10b981' }} />}
              <h3 style={{ margin: 0, fontSize: 16 }}>{selectedNode.type === 'goal' ? '战略目标' : selectedNode.type === 'project' ? '项目' : '任务'}</h3>
            </div>
            
            <p style={{ fontWeight: 600, marginBottom: 12 }}>{selectedNode.name}</p>
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8, fontSize: 14 }}>
              {selectedNode.status && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <Clock size={14} style={{ color: '#666' }} />
                  <span style={{ color: '#666' }}>状态:</span>
                  <span style={{
                    padding: '2px 8px',
                    borderRadius: 4,
                    fontSize: 12,
                    background: statusColors[selectedNode.status] + '20',
                    color: statusColors[selectedNode.status]
                  }}>
                    {selectedNode.status === 'completed' ? '已完成' : selectedNode.status === 'pending' ? '待办' : selectedNode.status === 'in_progress' ? '进行中' : selectedNode.status}
                  </span>
                </div>
              )}
              
              {selectedNode.progress !== undefined && selectedNode.progress > 0 && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                    <span style={{ color: '#666' }}>进度</span>
                    <span style={{ fontWeight: 600 }}>{selectedNode.progress}%</span>
                  </div>
                  <div style={{ height: 6, background: '#e5e7eb', borderRadius: 3 }}>
                    <div style={{ height: '100%', width: `${selectedNode.progress}%`, background: '#667eea', borderRadius: 3 }} />
                  </div>
                </div>
              )}
              
              {selectedNode.project_count !== undefined && selectedNode.project_count > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <FolderOpen size={14} style={{ color: '#666' }} />
                  <span style={{ color: '#666' }}>项目数:</span>
                  <span>{selectedNode.project_count}</span>
                </div>
              )}
              
              {selectedNode.task_count !== undefined && selectedNode.task_count > 0 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <CheckCircle2 size={14} style={{ color: '#666' }} />
                  <span style={{ color: '#666' }}>任务数:</span>
                  <span>{selectedNode.task_count}</span>
                </div>
              )}
              
              {selectedNode.priority && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <AlertCircle size={14} style={{ color: '#666' }} />
                  <span style={{ color: '#666' }}>优先级:</span>
                  <span>{selectedNode.priority}</span>
                </div>
              )}
              
              {selectedNode.raw_id && selectedNode.raw_id > 0 && (
                <a
                  href={selectedNode.type === 'task' ? `/tasks?id=${selectedNode.raw_id}` : '#'}
                  style={{
                    marginTop: 8,
                    padding: '6px 12px',
                    background: '#667eea',
                    color: '#fff',
                    borderRadius: 4,
                    textDecoration: 'none',
                    textAlign: 'center',
                    fontSize: 13
                  }}
                >
                  {selectedNode.type === 'task' ? '查看任务详情' : 'ID: ' + selectedNode.raw_id}
                </a>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
