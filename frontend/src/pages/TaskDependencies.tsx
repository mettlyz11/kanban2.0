import React, { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { ArrowLeft, Loader2 } from 'lucide-react'
import TaskDependencyGraph from '../components/TaskDependencyGraph'
import TaskGanttChart from '../components/TaskGanttChart'

interface Task {
  id: number
  title: string
  status: string
  priority: string
  depends_on?: number | null
  start_date?: string
  end_date?: string
}

const TaskDependencies: React.FC = () => {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const [tasks, setTasks] = useState<Task[]>([])
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'graph' | 'gantt'>('graph')
  const [projectName, setProjectName] = useState('')

  useEffect(() => {
    loadTasks()
  }, [projectId])

  const loadTasks = async () => {
    if (!projectId) return
    setLoading(true)
    try {
      const res = await fetch(`/api/projects/${projectId}/tasks`)
      const data = await res.json()
      if (data.success) {
        setTasks(data.tasks || [])
      }
      
      // 获取项目名称
      const projectRes = await fetch(`/api/projects/${projectId}`)
      const projectData = await projectRes.json()
      if (projectData.success) {
        setProjectName(projectData.project?.name || '')
      }
    } catch (e) {
      console.error(e)
    }
    setLoading(false)
  }

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#f5f5f5' }}>
        <div style={{ textAlign: 'center' }}>
          <Loader2 size={40} style={{ animation: 'spin 1s linear infinite', marginBottom: '16px' }} />
          <div>加载任务依赖...</div>
        </div>
      </div>
    )
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f5f5', padding: '20px' }}>
      {/* Header */}
      <div style={{ maxWidth: '1200px', margin: '0 auto', marginBottom: '20px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', marginBottom: '16px' }}>
          <button
            onClick={() => navigate('/projects')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 16px',
              background: 'white',
              border: '1px solid #ddd',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px'
            }}
          >
            <ArrowLeft size={16} />
            返回项目
          </button>
          <h1 style={{ fontSize: '24px', fontWeight: 600 }}>
            {projectName ? `${projectName} - 任务依赖` : '任务依赖'}
          </h1>
        </div>

        {/* View Toggle */}
        <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
          <button
            onClick={() => setView('graph')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              background: view === 'graph' ? '#667eea' : 'white',
              color: view === 'graph' ? 'white' : '#666',
              cursor: 'pointer',
              fontWeight: view === 'graph' ? 600 : 400,
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}
          >
            依赖关系图
          </button>
          <button
            onClick={() => setView('gantt')}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              background: view === 'gantt' ? '#667eea' : 'white',
              color: view === 'gantt' ? 'white' : '#666',
              cursor: 'pointer',
              fontWeight: view === 'gantt' ? 600 : 400,
              boxShadow: '0 1px 3px rgba(0,0,0,0.1)'
            }}
          >
            甘特图
          </button>
        </div>

        {/* Stats */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>总任务</div>
            <div style={{ fontSize: '24px', fontWeight: 600 }}>{tasks.length}</div>
          </div>
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>有依赖</div>
            <div style={{ fontSize: '24px', fontWeight: 600 }}>{tasks.filter(t => t.depends_on).length}</div>
          </div>
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>已完成</div>
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#22c55e' }}>{tasks.filter(t => t.status === 'completed').length}</div>
          </div>
          <div style={{ background: 'white', padding: '16px', borderRadius: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
            <div style={{ fontSize: '12px', color: '#666', marginBottom: '4px' }}>进行中</div>
            <div style={{ fontSize: '24px', fontWeight: 600, color: '#3b82f6' }}>{tasks.filter(t => t.status === 'in_progress').length}</div>
          </div>
        </div>

        {/* Chart */}
        <div style={{ background: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          {view === 'graph' ? (
            <TaskDependencyGraph
              tasks={tasks.map(t => ({
                id: t.id,
                title: t.title,
                status: t.status as any,
                depends_on: t.depends_on
              }))}
              onTaskClick={(task) => console.log('Clicked:', task)}
            />
          ) : (
            <TaskGanttChart
              tasks={tasks.map(t => ({
                id: t.id,
                title: t.title,
                status: t.status as any,
                depends_on: t.depends_on,
                start_date: t.start_date ? new Date(t.start_date) : undefined,
                end_date: t.end_date ? new Date(t.end_date) : undefined
              }))}
              onTaskClick={(task) => console.log('Clicked:', task)}
            />
          )}
        </div>
      </div>
    </div>
  )
}

export default TaskDependencies
