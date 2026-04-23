import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import { Target, TrendingUp, CheckCircle2, Clock, BarChart3 } from 'lucide-react'

interface KeyResult {
  id: number
  description: string
  target_value: number
  current_value: number
  unit: string
  status: string
}

interface Goal {
  id: number
  title: string
  description: string
  category: string
  progress: number
  status: string
  deadline: string
  key_results: KeyResult[]
  project_count: number
  task_count: number
  created_at: string
}

export function Goals() {
  const [goals, setGoals] = useState<Goal[]>([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('')
  const [showAddModal, setShowAddModal] = useState(false)

  useEffect(() => {
    loadGoals()
  }, [filter])

  const loadGoals = async () => {
    try {
      const data = await api.getLifeGoals(filter ? { category: filter } : {})
      if (data.success) {
        setGoals(data.goals || [])
      }
    } catch (e) {
      console.error('Failed to load goals:', e)
      // 使用模拟数据作为后备
      setGoals(getMockGoals())
    } finally {
      setLoading(false)
    }
  }

  if (loading) return <div className="loading">加载中...</div>

  const avgProgress = goals.length > 0 
    ? Math.round(goals.reduce((sum, g) => sum + g.progress, 0) / goals.length)
    : 0

  const completedGoals = goals.filter(g => g.progress >= 100).length
  const activeGoals = goals.filter(g => g.progress > 0 && g.progress < 100).length

  return (
    <div className="page-container" style={{ maxWidth: "100%", padding: "0 32px" }}>
      <div className="page-header">
        <h2 className="page-title">🎯 我的人生目标</h2>
      </div>

      {/* 统计概览 */}
      <div className="stats-grid" style={{ marginBottom: '24px' }}>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#667eea20', color: '#667eea' }}>
            <Target size={24} />
          </div>
          <div className="stat-value">{goals.length}</div>
          <div className="stat-label">总目标数</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#28a74520', color: '#28a745' }}>
            <TrendingUp size={24} />
          </div>
          <div className="stat-value">{avgProgress}%</div>
          <div className="stat-label">平均进度</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#007bff20', color: '#007bff' }}>
            <CheckCircle2 size={24} />
          </div>
          <div className="stat-value">{completedGoals}</div>
          <div className="stat-label">已完成</div>
        </div>
        <div className="stat-card">
          <div className="stat-icon" style={{ background: '#ffc10720', color: '#ffc107' }}>
            <Clock size={24} />
          </div>
          <div className="stat-value">{activeGoals}</div>
          <div className="stat-label">进行中</div>
        </div>
      </div>

      {/* 分类筛选 */}
      <div className="filter-bar" style={{ marginBottom: '24px' }}>
        {[
          { key: '', label: '全部目标' },
          { key: 'product', label: '产品目标' },
          { key: 'tech', label: '技术目标' },
          { key: 'business', label: '业务目标' },
          { key: 'team', label: '团队目标' }
        ].map(item => (
          <button
            key={item.key || 'all'}
            className={`filter-btn ${filter === item.key ? 'active' : ''}`}
            onClick={() => setFilter(item.key)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* 目标卡片网格 */}
      <div className="grid-2">
        {goals.length === 0 ? (
          <div className="card" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '60px 20px' }}>
            <Target size={48} style={{ opacity: 0.3, marginBottom: '16px' }} />
            <div style={{ 
              padding: '60px 20px', 
              textAlign: 'center',
              background: 'linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%)',
              borderRadius: '12px',
              margin: '20px 0'
            }}>
              <div style={{ fontSize: '64px', marginBottom: '16px' }}>🎯</div>
              <h3 style={{ margin: '0 0 8px 0', color: '#1e293b', fontSize: '18px' }}>暂无我的人生目标</h3>
              <p style={{ margin: '0 0 24px 0', color: '#64748b', fontSize: '14px' }}>
                还没有设定任何目标，点击下方按钮创建第一个人生目标
              </p>
              <button
                onClick={() => setShowAddModal(true)}
                style={{
                  padding: '12px 32px',
                  borderRadius: '8px',
                  border: 'none',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  cursor: 'pointer',
                  fontSize: '15px',
                  fontWeight: 600,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '8px'
                }}
              >
                <span style={{ fontSize: '18px' }}>➕</span>
                创建第一个人生目标
              </button>
            </div>
          </div>
        ) : (
          goals.map(goal => (
            <GoalCard key={goal.id} goal={goal} />
          ))
        )}
      </div>
    </div>
  )
}

function GoalCard({ goal }: { goal: Goal }) {
  const [expanded, setExpanded] = useState(false)

  const getCategoryColor = (category: string) => {
    switch (category) {
      case 'product': return '#e74c3c'
      case 'tech': return '#3498db'
      case 'business': return '#2ecc71'
      case 'team': return '#9b59b6'
      default: return '#667eea'
    }
  }

  const getCategoryLabel = (category: string) => {
    switch (category) {
      case 'product': return '产品'
      case 'tech': return '技术'
      case 'business': return '业务'
      case 'team': return '团队'
      default: return '其他'
    }
  }

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'done': return '#28a745'
      case 'progress': return '#007bff'
      case 'todo': return '#ffc107'
      default: return '#6c757d'
    }
  }

  const getStatusLabel = (status: string) => {
    switch (status) {
      case 'done': return '已完成'
      case 'progress': return '进行中'
      case 'todo': return '待开始'
      default: return status
    }
  }

  const color = getCategoryColor(goal.category)

  return (
    <div className="card goal-card" style={{
      borderLeft: `4px solid ${color}`,
      transition: 'transform 0.2s, box-shadow 0.2s'
    }}>
      {/* 头部 */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '16px' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <span style={{
              padding: '4px 10px',
              borderRadius: '12px',
              fontSize: '0.7rem',
              fontWeight: 600,
              background: `${color}20`,
              color: color
            }}>
              {getCategoryLabel(goal.category)}
            </span>
            <span style={{
              padding: '4px 10px',
              borderRadius: '12px',
              fontSize: '0.7rem',
              fontWeight: 600,
              background: `${getStatusColor(goal.status)}20`,
              color: getStatusColor(goal.status)
            }}>
              {getStatusLabel(goal.status)}
            </span>
          </div>
          <h3 style={{ margin: 0, fontSize: '1.1rem', color: '#333' }}>{goal.title}</h3>
        </div>
        <div style={{ 
          width: '50px', 
          height: '50px', 
          borderRadius: '50%', 
          background: `conic-gradient(${color} ${goal.progress}%, #e0e0e0 0)`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          position: 'relative'
        }}>
          <div style={{
            width: '40px',
            height: '40px',
            borderRadius: '50%',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontSize: '0.75rem',
            fontWeight: 700,
            color: color
          }}>
            {goal.progress}%
          </div>
        </div>
      </div>

      {/* 描述 */}
      <p style={{ color: '#666', fontSize: '0.9rem', marginBottom: '16px', lineHeight: 1.5 }}>
        {goal.description}
      </p>

      {/* 进度条 */}
      <div style={{ marginBottom: '16px' }}>
        <div style={{ 
          height: '8px', 
          background: '#e0e0e0', 
          borderRadius: '4px', 
          overflow: 'hidden' 
        }}>
          <div style={{ 
            width: `${goal.progress}%`, 
            height: '100%', 
            background: `linear-gradient(90deg, ${color}, ${color}dd)`,
            borderRadius: '4px',
            transition: 'width 0.5s ease'
          }} />
        </div>
      </div>

      {/* 统计信息 */}
      <div style={{ 
        display: 'flex', 
        gap: '16px', 
        marginBottom: '16px',
        fontSize: '0.85rem',
        color: '#666'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <BarChart3 size={14} />
          <span>{goal.key_results?.length || 0} 关键结果</span>
        </div>
        <div>•</div>
        <div>{goal.project_count || 0} 关联项目</div>
        <div>•</div>
        <div>{goal.task_count || 0} 关联任务</div>
      </div>

      {/* 截止日期 */}
      {goal.deadline && (
        <div style={{ 
          fontSize: '0.8rem', 
          color: new Date(goal.deadline) < new Date() ? '#dc3545' : '#666',
          marginBottom: '12px'
        }}>
          <Clock size={12} style={{ verticalAlign: 'middle', marginRight: '4px' }} />
          截止日期: {new Date(goal.deadline).toLocaleDateString('zh-CN')}
          {new Date(goal.deadline) < new Date() && goal.status !== 'done' && (
            <span style={{ color: '#dc3545', marginLeft: '8px', fontWeight: 600 }}>已逾期</span>
          )}
        </div>
      )}

      {/* 展开/收起关键结果 */}
      <button
        onClick={() => setExpanded(!expanded)}
        style={{
          width: '100%',
          padding: '10px',
          background: '#f8f9fa',
          border: 'none',
          borderRadius: '6px',
          cursor: 'pointer',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '6px',
          color: '#667eea',
          fontWeight: 500,
          fontSize: '0.9rem'
        }}
      >
        {expanded ? '收起关键结果' : '查看关键结果'}
      </button>

      {/* 关键结果列表 */}
      {expanded && goal.key_results && goal.key_results.length > 0 && (
        <div style={{ marginTop: '16px', paddingTop: '16px', borderTop: '1px dashed #ddd' }}>
          <h4 style={{ fontSize: '0.9rem', color: '#333', marginBottom: '12px' }}>关键结果 (KR)</h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
            {goal.key_results.map((kr, idx) => (
              <KeyResultItem key={kr.id} kr={kr} index={idx + 1} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

function KeyResultItem({ kr, index }: { kr: KeyResult; index: number }) {
  const progress = kr.target_value > 0 
    ? Math.min(Math.round((kr.current_value / kr.target_value) * 100), 100)
    : 0

  const isCompleted = kr.status === 'done' || progress >= 100

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      gap: '12px',
      padding: '12px',
      background: isCompleted ? '#e8f5e9' : '#f8f9fa',
      borderRadius: '8px',
      border: `1px solid ${isCompleted ? '#4caf50' : '#e0e0e0'}`
    }}>
      <div style={{ 
        width: '24px', 
        height: '24px', 
        borderRadius: '50%',
        background: isCompleted ? '#4caf50' : '#fff',
        border: `2px solid ${isCompleted ? '#4caf50' : '#ccc'}`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0
      }}>
        {isCompleted && <CheckCircle2 size={14} color="#fff" />}
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ 
          fontSize: '0.85rem', 
          color: isCompleted ? '#2e7d32' : '#333',
          fontWeight: isCompleted ? 600 : 400,
          textDecoration: isCompleted ? 'line-through' : 'none',
          marginBottom: '4px'
        }}>
          KR{index}: {kr.description}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ 
            flex: 1, 
            height: '4px', 
            background: '#e0e0e0', 
            borderRadius: '2px',
            overflow: 'hidden'
          }}>
            <div style={{ 
              width: `${progress}%`, 
              height: '100%', 
              background: isCompleted ? '#4caf50' : '#667eea',
              borderRadius: '2px'
            }} />
          </div>
          <span style={{ fontSize: '0.75rem', color: '#666', whiteSpace: 'nowrap' }}>
            {kr.current_value}/{kr.target_value} {kr.unit}
          </span>
        </div>
      </div>
    </div>
  )
}

// 模拟数据（用于后备）
function getMockGoals(): Goal[] {
  return [
    {
      id: 1,
      title: 'T109计算平台上线',
      description: '完成T109量子化学计算平台的开发和部署，支持PSI4等主流计算引擎',
      category: 'tech',
      progress: 75,
      status: 'progress',
      deadline: '2026-03-31',
      key_results: [
        { id: 1, description: '完成基础架构搭建', target_value: 100, current_value: 100, unit: '%', status: 'done' },
        { id: 2, description: 'PSI4集成测试', target_value: 100, current_value: 80, unit: '%', status: 'progress' },
        { id: 3, description: '用户界面优化', target_value: 100, current_value: 60, unit: '%', status: 'progress' },
        { id: 4, description: '性能测试通过', target_value: 1, current_value: 0, unit: '次', status: 'todo' }
      ],
      project_count: 3,
      task_count: 12,
      created_at: '2026-01-01'
    },
    {
      id: 2,
      title: 'Pepi数字员工系统',
      description: '开发Pepi数字员工系统，实现自动化任务执行和智能决策支持',
      category: 'product',
      progress: 60,
      status: 'progress',
      deadline: '2026-04-15',
      key_results: [
        { id: 5, description: '核心引擎开发', target_value: 100, current_value: 90, unit: '%', status: 'progress' },
        { id: 6, description: '视觉能力集成', target_value: 100, current_value: 40, unit: '%', status: 'progress' },
        { id: 7, description: '工作记录系统', target_value: 100, current_value: 50, unit: '%', status: 'progress' }
      ],
      project_count: 2,
      task_count: 8,
      created_at: '2026-01-15'
    },
    {
      id: 3,
      title: '商业化准备',
      description: '完成产品商业化准备，包括法律合规、定价策略和客户支持体系',
      category: 'business',
      progress: 30,
      status: 'progress',
      deadline: '2026-06-30',
      key_results: [
        { id: 8, description: '法律合规审查', target_value: 100, current_value: 50, unit: '%', status: 'progress' },
        { id: 9, description: '定价策略制定', target_value: 1, current_value: 0, unit: '套', status: 'todo' },
        { id: 10, description: '客户支持流程', target_value: 100, current_value: 20, unit: '%', status: 'progress' }
      ],
      project_count: 1,
      task_count: 5,
      created_at: '2026-02-01'
    }
  ]
}

export default Goals
