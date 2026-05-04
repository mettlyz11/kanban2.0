import { useState, useEffect, useCallback } from 'react'
import { useSDSWebSocket } from '../hooks/useSDSWebSocket'

interface SdsStats {
  pending: number
  running: number
  completed: number
  failed: number
  failed_retryable: number
  archived: number
}

interface GoalConfig {
  id: number
  title: string
  description: string
  category: string
  status: string
  project_count: number
}

interface ProjectConfig {
  id: number
  name: string
  number: string
  description: string
  status: string
  priority: string
  goal_id: number
  goal_title: string | null
}

interface ScriptInfo {
  path: string
  description: string
}

interface CronJob {
  name: string
  schedule: string
  command: string
  description: string
}

interface SdsCoreConfig {
  version: string
  cycle_interval_minutes: number
  max_concurrent_tasks: number
  quality_gates: {
    execution_log_min_chars: number
    result_summary_min_chars: number
  }
  triple_guards: Record<string, any>
  smart_retry: Record<string, string>
  zombie_detection: Record<string, string>
  heartbeat_schedule: Record<string, string>
}

interface FileItem {
  path: string
  name: string
  size: number
  modified: string
}

// WebSocket 事件通知组件
function WSDEventToast({ event, onClear }: { event: any; onClear: () => void }) {
  if (!event) return null
  const isAlert = event.type === 'alert'
  const isError = event.data?.severity === 'error' || event.data?.severity === 'critical'
  const isSuccess = event.type === 'task_completed'
  const bg = isError ? '#fef2f2' : isAlert ? '#fffbeb' : isSuccess ? '#f0fdf4' : '#eff6ff'
  const border = isError ? '#ef4444' : isAlert ? '#f59e0b' : isSuccess ? '#10b981' : '#3b82f6'
  
  let title = ''
  let message = ''
  if (event.type === 'task_created') { title = '新任务生成'; message = event.data?.task?.title || event.data?.task?.id }
  else if (event.type === 'task_executing') { title = '任务执行中'; message = `${event.data?.task_id} - ${event.data?.status_message} (${event.data?.progress}%)` }
  else if (event.type === 'task_completed') { title = '任务完成'; message = event.data?.result_summary || event.data?.task_id }
  else if (event.type === 'task_failed') { title = '任务失败'; message = event.data?.error || event.data?.task_id }
  else if (event.type === 'system_status') { title = '系统状态变更'; message = event.data?.status }
  else if (event.type === 'alert') { title = event.data?.type || '告警'; message = event.data?.message }

  return (
    <div style={{
      position: 'fixed', top: 20, right: 20, zIndex: 9999,
      background: bg, border: `2px solid ${border}`, borderRadius: 8,
      padding: '12px 16px', maxWidth: 360, boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
      animation: 'slideIn 0.3s ease-out'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start' }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, color: border }}>{title}</div>
          <div style={{ fontSize: 12, color: '#374151', marginTop: 4 }}>{message}</div>
        </div>
        <button onClick={onClear} style={{
          background: 'none', border: 'none', cursor: 'pointer', fontSize: 16, color: '#9ca3af', padding: '0 0 0 8px'
        }}>×</button>
      </div>
    </div>
  )
}

export default function SelfDrivingSystem() {
  const [activeTab, setActiveTab] = useState('dashboard')
  const [loading, setLoading] = useState(true)
  
  // WebSocket 集成
  const {
    connected: wsConnected,
    taskCreated,
    taskExecuting,
    taskCompleted,
    taskFailed,
    systemStatus,
    alert: wsAlert,
    clearEvent,
    clearAllEvents,
  } = useSDSWebSocket()
  
  // 数据 states
  const [stats, setStats] = useState<SdsStats | null>(null)
  const [goals, setGoals] = useState<GoalConfig[]>([])
  const [projects, setProjects] = useState<ProjectConfig[]>([])
  const [projectThresholds, setProjectThresholds] = useState<Record<string, any>>({})
  const [sdsCore, setSdsCore] = useState<SdsCoreConfig | null>(null)
  const [cronJobs, setCronJobs] = useState<CronJob[]>([])
  const [scripts, setScripts] = useState<ScriptInfo[]>([])
  const [goalDefs, setGoalDefs] = useState<Record<string, any>>({})
  const [recoverySteps, setRecoverySteps] = useState<string[]>([])
  const [dbSchemas, setDbSchemas] = useState<Record<string, string>>({})
  const [exportData, setExportData] = useState<string>('')
  const [historyData, setHistoryData] = useState<any[]>([])
  
  // WebSocket 实时数据
  const [liveStats, setLiveStats] = useState<SdsStats | null>(null)
  const [activeNotifications, setActiveNotifications] = useState<any[]>([])

  // Editing states
  const [editingGoal, setEditingGoal] = useState<number | null>(null)
  const [editingGoalField, setEditingGoalField] = useState('')
  const [editingGoalValue, setEditingGoalValue] = useState('')
  const [editingProject, setEditingProject] = useState<number | null>(null)
  const [editingProjectField, setEditingProjectField] = useState('')
  const [editingProjectValue, setEditingProjectValue] = useState('')
  const [editingRules, setEditingRules] = useState<string>('')
  const [savingRules, setSavingRules] = useState(false)

  // File management states
  const [fileList, setFileList] = useState<FileItem[]>([])
  const [selectedFile, setSelectedFile] = useState<string>('')
  const [fileContent, setFileContent] = useState('')
  const [fileLoading, setFileLoading] = useState(false)
  const [fileSaving, setFileSaving] = useState(false)

  // WebSocket 事件处理
  useEffect(() => {
    const events = [
      { type: 'task_created', data: taskCreated },
      { type: 'task_executing', data: taskExecuting },
      { type: 'task_completed', data: taskCompleted },
      { type: 'task_failed', data: taskFailed },
      { type: 'system_status', data: systemStatus },
      { type: 'alert', data: wsAlert },
    ]
    for (const e of events) {
      if (e.data) {
        setActiveNotifications(prev => [{ ...e, id: Date.now() }, ...prev].slice(0, 10))
        // 如果是任务相关事件，刷新 stats
        if (e.type.startsWith('task_')) {
          fetch('/api/sds/stats').then(r => r.json()).then(json => {
            if (json.success) {
              const ts = json.data.task_stats || {}
              setLiveStats({
                pending: ts.pending || 0,
                running: ts.in_progress || 0,
                completed: ts.completed || 0,
                failed: (ts.failed || 0) + (ts.failed_retryable || 0),
                failed_retryable: ts.failed_retryable || 0,
                archived: ts.archived || 0,
              })
            }
          }).catch(() => {})
        }
      }
    }
  }, [taskCreated, taskExecuting, taskCompleted, taskFailed, systemStatus, wsAlert])

  const fetchConfig = useCallback(async (key: string) => {
    try {
      const res = await fetch(`/api/sds/config/${key}`)
      const json = await res.json()
      if (json.success) {
        return typeof json.data === 'string' ? JSON.parse(json.data) : json.data
      }
    } catch (e) {
      console.error(`Failed to fetch ${key}:`, e)
    }
    return null
  }, [])

  useEffect(() => {
    const loadData = async () => {
      try {
        const res = await fetch('/api/sds/stats')
        const json = await res.json()
        if (json.success) {
          const ts = json.data.task_stats || {}
          setStats({
            pending: ts.pending || 0,
            running: ts.in_progress || 0,
            completed: ts.completed || 0,
            failed: (ts.failed || 0) + (ts.failed_retryable || 0),
            failed_retryable: ts.failed_retryable || 0,
            archived: ts.archived || 0,
          })
          setLiveStats({
            pending: ts.pending || 0,
            running: ts.in_progress || 0,
            completed: ts.completed || 0,
            failed: (ts.failed || 0) + (ts.failed_retryable || 0),
            failed_retryable: ts.failed_retryable || 0,
            archived: ts.archived || 0,
          })
        }
      } catch (e) { console.error('Stats error:', e) }

      const [goalsRes, projectsRes, thresholdsRes, coreRes, cronRes, scriptsRes, recoveryRes, schemasRes] = await Promise.all([
        fetchConfig('goals_config'),
        fetchConfig('projects_config'),
        fetchConfig('project_thresholds'),
        fetchConfig('sds_core_config'),
        fetchConfig('cron_jobs'),
        fetchConfig('scripts'),
        fetchConfig('recovery_instructions'),
        fetchConfig('database_schema'),
      ])

      if (goalsRes) {
        if (Array.isArray(goalsRes)) { setGoals(goalsRes); setGoalDefs(Object.fromEntries(goalsRes.map((g: any) => [String(g.id), g]))) }
        else { setGoals(goalsRes.goals || []); setGoalDefs(goalsRes.goal_defs || {}) }
      }
      if (projectsRes) {
        if (Array.isArray(projectsRes)) setProjects(projectsRes)
        else setProjects(projectsRes.projects || [])
      }
      if (thresholdsRes) {
        setProjectThresholds(thresholdsRes)
      }
      if (coreRes) setSdsCore(coreRes)
      if (cronRes) setCronJobs(Array.isArray(cronRes) ? cronRes : cronRes.jobs || [])
      if (scriptsRes) setScripts(Array.isArray(scriptsRes) ? scriptsRes : scriptsRes.scripts || [])
      if (recoveryRes) setRecoverySteps(Array.isArray(recoveryRes) ? recoveryRes : recoveryRes.steps || [])
      if (schemasRes) {
        if (typeof schemasRes === 'string') setDbSchemas(JSON.parse(schemasRes))
        else setDbSchemas(schemasRes)
      }

      try {
        const historyRes = await fetch('/api/sds/history')
        const historyJson = await historyRes.json()
        if (historyJson.success && historyJson.data && historyJson.data.daily) {
          setHistoryData(historyJson.data.daily)
        }
      } catch (e) { console.error('History error:', e) }

      setLoading(false)
    }
    loadData()
  }, [fetchConfig])

  const saveGoalField = async (goalId: number, field: string, value: string) => {
    try {
      const res = await fetch('/api/sds/config/goals', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ goal_id: goalId, field, value }),
      })
      const json = await res.json()
      if (json.success) {
        setGoals(prev => prev.map(g => g.id === goalId ? { ...g, [field]: value } : g))
        setEditingGoal(null)
      }
    } catch (e) { console.error('Save goal error:', e) }
  }

  const saveProjectField = async (projectId: number, field: string, value: string) => {
    try {
      const res = await fetch(`/api/sds/config/projects/${projectId}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field, value }),
      })
      const json = await res.json()
      if (json.success) {
        setProjects(prev => prev.map(p => p.id === projectId ? { ...p, [field]: value } : p))
        setEditingProject(null)
      }
    } catch (e) { console.error('Save project error:', e) }
  }

  const saveRules = async () => {
    setSavingRules(true)
    try {
      const rules = { task_generation_rules: editingRules }
      const res = await fetch('/api/sds/config/rules', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(rules),
      })
      const json = await res.json()
      if (json.success) alert('规则已保存')
      else alert('保存失败: ' + json.error)
    } catch (e) { alert('保存失败: ' + e) }
    setSavingRules(false)
  }

  const loadFileList = async () => {
    try {
      const res = await fetch('/api/files/index')
      const json = await res.json()
      if (json.success) setFileList(json.files || [])
    } catch (e) { console.error('Load file list error:', e) }
  }

  const loadFileContent = async (filePath: string) => {
    setFileLoading(true)
    setSelectedFile(filePath)
    try {
      const res = await fetch(`/api/files/content/${encodeURIComponent(filePath)}`)
      const json = await res.json()
      if (json.success) setFileContent(json.content || '')
      else setFileContent('加载失败: ' + json.error)
    } catch (e) { setFileContent('加载失败: ' + e) }
    setFileLoading(false)
  }

  const saveFileContent = async () => {
    setFileSaving(true)
    try {
      const blob = new Blob([fileContent], { type: 'text/plain' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = selectedFile.split('/').pop() || 'file.txt'
      a.click()
      URL.revokeObjectURL(url)
      alert('文件已下载（保存功能需要后端支持）')
    } catch (e) { alert('操作失败: ' + e) }
    setFileSaving(false)
  }

  const exportConfig = () => {
    const data = { goals, projects, sdsCore, cronJobs, scripts, goalDefs, recoverySteps, dbSchemas }
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `sds-system-config-${new Date().toISOString().slice(0,10)}.json`
    a.click()
    URL.revokeObjectURL(url)
  }

  const [sdsFiles, setSdsFiles] = useState<{path: string, url: string, size: number}[]>([])
  const [sdsFilesLoading, setSdsFilesLoading] = useState(false)
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetch('/api/sds1/documents')
      .then(r => r.json())
      .then(data => {
        if (data.success) { setSdsFiles(data.documents) }
        else { console.error('加载SDS1文件列表失败:', data.error) }
      })
      .catch(e => console.error('加载SDS1文件列表失败:', e))
  }, [])

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return bytes + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  const toggleSelectFile = (path: string) => {
    setSelectedFiles(prev => {
      const next = new Set(prev)
      if (next.has(path)) next.delete(path)
      else next.add(path)
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedFiles.size === sdsFiles.length) {
      setSelectedFiles(new Set())
    } else {
      setSelectedFiles(new Set(sdsFiles.map(f => f.path)))
    }
  }

  const downloadSelected = () => {
    selectedFiles.forEach(path => {
      const f = sdsFiles.find(x => x.path === path)
      if (f) {
        const a = document.createElement('a')
        a.href = f.url
        a.download = path.split('/').pop() || path
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
      }
    })
  }

  const selectByType = (ext: string) => {
    setSelectedFiles(new Set(
      sdsFiles.filter(f => f.path.endsWith(ext)).map(f => f.path)
    ))
  }

  const displayStats = liveStats || stats

  if (loading) return <div style={{ padding: 40, textAlign: 'center' }}>加载中...</div>

  const renderDashboard = () => (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>📊 SDS1 系统概览</h2>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div style={{
            width: 10, height: 10, borderRadius: '50%',
            background: wsConnected ? '#10b981' : '#ef4444'
          }}></div>
          <span style={{ fontSize: 12, color: wsConnected ? '#10b981' : '#ef4444' }}>
            {wsConnected ? 'WebSocket 实时连接' : 'WebSocket 未连接'}
          </span>
        </div>
      </div>
      {displayStats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', gap: 16, marginBottom: 24 }}>
          {[
            { label: '待处理', value: displayStats.pending, color: '#3b82f6' },
            { label: '运行中', value: displayStats.running, color: '#f59e0b' },
            { label: '已完成', value: displayStats.completed, color: '#10b981' },
            { label: '失败', value: displayStats.failed, color: '#ef4444' },
            { label: '已归档', value: displayStats.archived, color: '#6b7280' },
          ].map(s => (
            <div key={s.label} style={{ background: s.color, color: '#fff', borderRadius: 8, padding: 16, textAlign: 'center' }}>
              <div style={{ fontSize: 28, fontWeight: 700 }}>{s.value}</div>
              <div style={{ fontSize: 13, opacity: 0.9 }}>{s.label}</div>
            </div>
          ))}
        </div>
      )}
      
      {/* WebSocket 实时状态指示 */}
      {taskExecuting && (
        <div style={{ background: '#fffbeb', border: '1px solid #f59e0b', borderRadius: 8, padding: 12, marginBottom: 16 }}>
          <div style={{ fontSize: 13, color: '#92400e' }}>
            ⚡ 任务执行中: #{taskExecuting.task_id} - {taskExecuting.status_message} ({taskExecuting.progress}%)
          </div>
          <div style={{ background: '#f3f4f6', borderRadius: 4, height: 6, marginTop: 8 }}>
            <div style={{ background: '#f59e0b', borderRadius: 4, height: '100%', width: `${taskExecuting.progress}%`, transition: 'width 0.3s' }}></div>
          </div>
        </div>
      )}
      
      {systemStatus && (
        <div style={{
          background: systemStatus.status === 'running' ? '#f0fdf4' : systemStatus.status === 'error' ? '#fef2f2' : '#eff6ff',
          border: `1px solid ${systemStatus.status === 'running' ? '#10b981' : systemStatus.status === 'error' ? '#ef4444' : '#3b82f6'}`,
          borderRadius: 8, padding: 12, marginBottom: 16, fontSize: 13
        }}>
          系统状态: <strong>{systemStatus.status}</strong>
        </div>
      )}

      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
        <h3 style={{ marginBottom: 12 }}>📋 定时任务 ({cronJobs.length}个)</h3>
        {cronJobs.map((job, i) => (
          <div key={i} style={{ padding: 8, borderBottom: '1px solid #f0f0f0', fontSize: 13 }}>
            <strong>{job.name}</strong> - {job.schedule}
            <div style={{ color: '#666', fontSize: 12 }}>{job.description}</div>
          </div>
        ))}
      </div>
    </div>
  )

  const renderGoals = () => (
    <div>
      <h2 style={{ marginBottom: 20 }}>🎯 目标配置</h2>
      <p style={{ color: '#666', marginBottom: 16 }}>7大战略目标配置 - 点击字段可编辑</p>
      {goals.map(g => {
        const def = goalDefs[String(g.id)] || {}
        const isEditing = editingGoal === g.id
        return (
          <div key={g.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 12 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 8 }}>
              {isEditing && editingGoalField === 'title' ? (
                <input value={editingGoalValue} onChange={e => setEditingGoalValue(e.target.value)}
                  onBlur={() => saveGoalField(g.id, 'title', editingGoalValue)}
                  onKeyDown={e => e.key === 'Enter' && saveGoalField(g.id, 'title', editingGoalValue)}
                  autoFocus style={{ fontSize: 16, fontWeight: 600, border: '2px solid #3b82f6', borderRadius: 4, padding: '2px 8px', flex: 1 }} />
              ) : (
                <h3 style={{ margin: 0, fontSize: 16, cursor: 'pointer' }}
                  onClick={() => { setEditingGoal(g.id); setEditingGoalField('title'); setEditingGoalValue(g.title) }}>
                  G{g.id}: {g.title} ✏️
                </h3>
              )}
              <span style={{
                background: def.priority === 'P1' ? '#fee2e2' : def.priority === 'P2' ? '#fef3c7' : '#d1fae5',
                color: def.priority === 'P1' ? '#dc2626' : def.priority === 'P2' ? '#d97706' : '#059669',
                padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 600
              }}>{def.priority || 'P2'}</span>
            </div>
            {isEditing && editingGoalField === 'description' ? (
              <textarea value={editingGoalValue} onChange={e => setEditingGoalValue(e.target.value)}
                onBlur={() => saveGoalField(g.id, 'description', editingGoalValue)}
                autoFocus style={{ width: '100%', minHeight: 60, border: '2px solid #3b82f6', borderRadius: 4, padding: 8, fontSize: 13, marginBottom: 8 }} />
            ) : (
              <p style={{ margin: '4px 0 8px', fontSize: 13, color: '#666', cursor: 'pointer' }}
                onClick={() => { setEditingGoal(g.id); setEditingGoalField('description'); setEditingGoalValue(g.description) }}>
                {g.description} ✏️
              </p>
            )}
            <div style={{ fontSize: 12, color: '#888' }}>
              <strong>核心项目:</strong> {(def.key_projects || []).join('、') || '暂无'}
            </div>
            <div style={{ fontSize: 12, color: '#888', marginTop: 4 }}>
              <strong>任务规则:</strong> {def.task_generation_rules || '暂无'}
            </div>
          </div>
        )
      })}
    </div>
  )

  const renderTasks = () => (
    <div>
      <h2 style={{ marginBottom: 20 }}>📋 任务规则</h2>
      {sdsCore && (
        <>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 16 }}>
            <h3 style={{ marginBottom: 12 }}>🛡️ 三重保障</h3>
            <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse' }}>
              <thead><tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: 8 }}>保障</th>
                <th style={{ textAlign: 'left', padding: 8 }}>说明</th>
              </tr></thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: 8 }}>幂等性</td>
                  <td style={{ padding: 8 }}>相同标题+目标的任务只生成一次</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: 8 }}>频率限制</td>
                  <td style={{ padding: 8 }}>每目标每24h最多2个任务</td>
                </tr>
                <tr>
                  <td style={{ padding: 8 }}>语义去重</td>
                  <td style={{ padding: 8 }}>Levenshtein相似度85%</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
            <h3 style={{ marginBottom: 12 }}>📝 任务生成规则</h3>
            <textarea value={editingRules || JSON.stringify(sdsCore, null, 2)} onChange={e => setEditingRules(e.target.value)}
              style={{ width: '100%', minHeight: 200, fontFamily: 'monospace', fontSize: 12, padding: 8, border: '1px solid #e5e7eb', borderRadius: 4 }} />
            <button onClick={saveRules} disabled={savingRules} style={{
              marginTop: 8, padding: '8px 16px', background: '#3b82f6', color: '#fff',
              border: 'none', borderRadius: 4, cursor: savingRules ? 'not-allowed' : 'pointer', opacity: savingRules ? 0.6 : 1
            }}>{savingRules ? '保存中...' : '💾 保存规则'}</button>
          </div>
        </>
      )}
    </div>
  )

  const renderProjects = () => {
    const thresholds = projectThresholds.thresholds || []
    const globalConfig = projectThresholds.global || {}
    return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📁 项目阈值</h2>
      {globalConfig.max_total_tasks && (
        <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 8, padding: 16, marginBottom: 16 }}>
          <h3 style={{ marginBottom: 8, color: '#0369a1' }}>🌍 全局配置</h3>
          <div style={{ display: 'flex', gap: 24, flexWrap: 'wrap' }}>
            <div><span style={{ color: '#666' }}>总任务上限:</span> <strong>{globalConfig.max_total_tasks}</strong></div>
            <div><span style={{ color: '#666' }}>每目标上限:</span> <strong>{globalConfig.max_pending_per_goal}</strong></div>
            <div><span style={{ color: '#666' }}>逾期权重:</span> <strong>{globalConfig.priority_boost_for_overdue}x</strong></div>
            <div><span style={{ color: '#666' }}>周期间隔:</span> <strong>{globalConfig.sdsl_cycle_interval_minutes}分钟</strong></div>
          </div>
        </div>
      )}
      {thresholds.length > 0 && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, overflow: 'hidden', marginBottom: 20 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead><tr style={{ background: '#f8f9fa' }}>
              <th style={{ padding: '10px 12px', textAlign: 'left', borderBottom: '1px solid #e5e7eb', fontSize: 13 }}>项目</th>
              <th style={{ padding: '10px 12px', textAlign: 'center', borderBottom: '1px solid #e5e7eb', fontSize: 13 }}>最大任务</th>
              <th style={{ padding: '10px 12px', textAlign: 'center', borderBottom: '1px solid #e5e7eb', fontSize: 13 }}>最小任务</th>
              <th style={{ padding: '10px 12px', textAlign: 'center', borderBottom: '1px solid #e5e7eb', fontSize: 13 }}>权重</th>
            </tr></thead>
            <tbody>
              {thresholds.map((t: any) => (
                <tr key={t.project_id}>
                  <td style={{ padding: '8px 12px', borderBottom: '1px solid #f0f0f0' }}>
                    <div style={{ fontWeight: 500 }}>{t.project_name}</div>
                    <div style={{ fontSize: 11, color: '#999' }}>ID: {t.project_id}</div>
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'center', borderBottom: '1px solid #f0f0f0' }}>
                    <span style={{ color: '#ef4444', fontWeight: 600 }}>{t.max_tasks}</span>
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'center', borderBottom: '1px solid #f0f0f0' }}>
                    <span style={{ color: '#3b82f6' }}>{t.min_tasks}</span>
                  </td>
                  <td style={{ padding: '8px 12px', textAlign: 'center', borderBottom: '1px solid #f0f0f0' }}>
                    <span style={{ 
                      background: t.priority_weight >= 1.3 ? '#fee2e2' : t.priority_weight >= 1.0 ? '#fef3c7' : '#f3f4f6',
                      color: t.priority_weight >= 1.3 ? '#dc2626' : t.priority_weight >= 1.0 ? '#d97706' : '#6b7280',
                      padding: '2px 8px', borderRadius: 4, fontSize: 12, fontWeight: 500
                    }}>{t.priority_weight}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p style={{ color: '#666', marginBottom: 16 }}>{projects.length}个项目 - 点击字段可编辑</p>
      {projects.map(p => {
        const isEditing = editingProject === p.id
        return (
          <div key={p.id} style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 8 }}>
            <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
              <span style={{ fontWeight: 600, color: '#3b82f6' }}>{p.number}</span>
              {isEditing && editingProjectField === 'name' ? (
                <input value={editingProjectValue} onChange={e => setEditingProjectValue(e.target.value)}
                  onBlur={() => saveProjectField(p.id, 'name', editingProjectValue)}
                  onKeyDown={e => e.key === 'Enter' && saveProjectField(p.id, 'name', editingProjectValue)}
                  autoFocus style={{ flex: 1, border: '2px solid #3b82f6', borderRadius: 4, padding: '2px 8px' }} />
              ) : (
                <span style={{ flex: 1, cursor: 'pointer' }}
                  onClick={() => { setEditingProject(p.id); setEditingProjectField('name'); setEditingProjectValue(p.name) }}>
                  {p.name} ✏️
                </span>
              )}
              <span style={{
                background: p.status === 'active' ? '#d1fae5' : '#f3f4f6',
                color: p.status === 'active' ? '#059669' : '#6b7280',
                padding: '2px 8px', borderRadius: 4, fontSize: 12
              }}>{p.status}</span>
            </div>
          </div>
        )
      })}
    </div>
    )
  }

  const renderRealtime = () => (
    <div>
      <h2 style={{ marginBottom: 20 }}>📡 实时监控</h2>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
        <div style={{ width: 10, height: 10, borderRadius: '50%', background: wsConnected ? '#10b981' : '#ef4444' }}></div>
        <span style={{ fontSize: 14, color: wsConnected ? '#10b981' : '#ef4444' }}>
          {wsConnected ? 'WebSocket 已连接 - 实时数据推送中' : 'WebSocket 未连接'}
        </span>
      </div>
      {displayStats && (
        <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
          <h3>任务状态分布</h3>
          <div style={{ display: 'flex', gap: 16, marginTop: 12 }}>
            {Object.entries(displayStats).map(([k, v]) => (
              <div key={k} style={{ textAlign: 'center' }}>
                <div style={{ fontSize: 24, fontWeight: 700 }}>{v}</div>
                <div style={{ fontSize: 12, color: '#666' }}>{k}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {activeNotifications.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <h3>实时事件 ({activeNotifications.length})</h3>
          {activeNotifications.slice(0, 10).map((n: any) => (
            <div key={n.id} style={{
              background: n.type === 'task_failed' ? '#fef2f2' : n.type === 'task_completed' ? '#f0fdf4' : '#eff6ff',
              border: `1px solid ${n.type === 'task_failed' ? '#fecaca' : n.type === 'task_completed' ? '#bbf7d0' : '#bfdbfe'}`,
              borderRadius: 8, padding: 12, marginBottom: 8, fontSize: 13
            }}>
              <div style={{ fontWeight: 600 }}>
                {n.type === 'task_created' && '🆕 新任务'}
                {n.type === 'task_executing' && '⚡ 执行中'}
                {n.type === 'task_completed' && '✅ 已完成'}
                {n.type === 'task_failed' && '❌ 失败'}
                {n.type === 'system_status' && '🔄 状态变更'}
                {n.type === 'alert' && '⚠️ 告警'}
              </div>
              <div style={{ color: '#374151', marginTop: 4 }}>
                {n.data?.task?.title || n.data?.task_id || n.data?.message || JSON.stringify(n.data)}
              </div>
            </div>
          ))}
          {activeNotifications.length > 0 && (
            <button onClick={() => clearAllEvents()} style={{
              marginTop: 8, padding: '6px 12px', background: '#f3f4f6', border: '1px solid #e5e7eb',
              borderRadius: 4, cursor: 'pointer', fontSize: 12
            }}>清除通知</button>
          )}
        </div>
      )}
    </div>
  )

  const renderHistory = () => {
    const maxCreated = Math.max(...historyData.map((d: any) => d.created || 0), 1)
    const maxCompleted = Math.max(...historyData.map((d: any) => d.completed || 0), 1)
    return (
    <div>
      <h2 style={{ marginBottom: 20 }}>📈 历史趋势</h2>
      {historyData.length === 0 ? (
        <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>加载中...</div>
      ) : (
        <div>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 16 }}>
            <h3 style={{ marginBottom: 16 }}>任务创建与完成趋势（最近30天）</h3>
            <div style={{ display: 'flex', alignItems: 'flex-end', gap: 4, height: 200, padding: '0 8px', borderBottom: '1px solid #e5e7eb' }}>
              {historyData.map((row: any) => (
                <div key={row.date} style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                  <div style={{ display: 'flex', gap: 1, alignItems: 'flex-end', width: '100%' }}>
                    <div style={{ flex: 1, background: '#3b82f6', borderRadius: '2px 2px 0 0', minHeight: 2, height: `${(row.created / maxCreated) * 160}px` }} title={`${row.date}: 创建 ${row.created}`} />
                    <div style={{ flex: 1, background: '#10b981', borderRadius: '2px 2px 0 0', minHeight: 2, height: `${(row.completed / maxCompleted) * 160}px` }} title={`${row.date}: 完成 ${row.completed}`} />
                  </div>
                  <div style={{ fontSize: 9, color: '#999', transform: 'rotate(-45deg)', whiteSpace: 'nowrap', marginTop: 8 }}>{row.date.slice(5)}</div>
                </div>
              ))}
            </div>
            <div style={{ display: 'flex', gap: 16, justifyContent: 'center', marginTop: 24 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 12, height: 12, background: '#3b82f6', borderRadius: 2 }}></div>
                <span style={{ fontSize: 12, color: '#666' }}>创建任务</span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                <div style={{ width: 12, height: 12, background: '#10b981', borderRadius: 2 }}></div>
                <span style={{ fontSize: 12, color: '#666' }}>完成任务</span>
              </div>
            </div>
          </div>
          <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
            <h3>详细数据</h3>
            <table style={{ width: '100%', marginTop: 12, borderCollapse: 'collapse' }}>
              <thead><tr style={{ background: '#f8f9fa' }}>
                <th style={{ padding: 8, textAlign: 'left', borderBottom: '1px solid #e5e7eb' }}>日期</th>
                <th style={{ padding: 8, textAlign: 'center', borderBottom: '1px solid #e5e7eb' }}>创建</th>
                <th style={{ padding: 8, textAlign: 'center', borderBottom: '1px solid #e5e7eb' }}>完成</th>
              </tr></thead>
              <tbody>
                {historyData.map((row: any) => (
                  <tr key={row.date}>
                    <td style={{ padding: 8, borderBottom: '1px solid #f0f0f0' }}>{row.date}</td>
                    <td style={{ padding: 8, textAlign: 'center', borderBottom: '1px solid #f0f0f0', color: '#1890ff' }}>{row.created}</td>
                    <td style={{ padding: 8, textAlign: 'center', borderBottom: '1px solid #f0f0f0', color: '#52c41a' }}>{row.completed}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
    )
  }

  const renderArchitecture = () => (
    <div>
      <h2 style={{ marginBottom: 20 }}>🏗️ 架构编辑</h2>
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
        <h3>系统架构配置</h3>
        {sdsCore ? (
          <pre style={{ background: '#f8f9fa', padding: 12, borderRadius: 4, overflow: 'auto', maxHeight: 400 }}>
            {JSON.stringify(sdsCore, null, 2)}
          </pre>
        ) : (
          <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>暂无架构数据</div>
        )}
      </div>
    </div>
  )

  const renderDocuments = () => (
    <div>
      <h2 style={{ marginBottom: 20 }}>📄 文档管理</h2>
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16, marginBottom: 24 }}>
        <h3 style={{ marginBottom: 12 }}>📥 导出配置</h3>
        <button onClick={exportConfig} style={{
          padding: '10px 20px', background: '#3b82f6', color: '#fff',
          border: 'none', borderRadius: 6, cursor: 'pointer', fontSize: 14
        }}>下载完整SDS1配置JSON</button>
        <p style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
          导出完整SDS1配置JSON。即使Mac mini被完全重置，也可从此配置恢复所有目标、项目、任务规则和脚本清单。
        </p>
      </div>
      <div style={{ background: '#fff', border: '1px solid #e5e7eb', borderRadius: 8, padding: 16 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <h3 style={{ margin: 0 }}>📁 SDS1 系统文件 ({sdsFiles.length}个)</h3>
          {selectedFiles.size > 0 && (
            <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
              <span style={{ fontSize: 13, color: '#3b82f6' }}>已选 {selectedFiles.size} 个</span>
              <button onClick={downloadSelected} style={{
                padding: '6px 16px', background: '#10b981', color: '#fff',
                border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 13
              }}>📥 批量下载</button>
            </div>
          )}
        </div>
        <div style={{ display: 'flex', gap: 6, marginBottom: 12, flexWrap: 'wrap' }}>
          <button onClick={() => setSelectedFiles(new Set())} style={{
            padding: '4px 12px', background: '#f3f4f6', border: '1px solid #e5e7eb',
            borderRadius: 4, cursor: 'pointer', fontSize: 12, color: '#374151' }}>取消全选</button>
          <button onClick={toggleSelectAll} style={{
            padding: '4px 12px', background: selectedFiles.size === sdsFiles.length ? '#3b82f6' : '#f3f4f6',
            color: selectedFiles.size === sdsFiles.length ? '#fff' : '#374151',
            border: '1px solid #e5e7eb', borderRadius: 4, cursor: 'pointer', fontSize: 12 }}>全选</button>
          {['.py', '.md', '.yaml', '.json', '.sh', '.html', '.txt'].map(ext => (
            <button key={ext} onClick={() => selectByType(ext)} style={{
              padding: '4px 12px', background: '#f3f4f6', border: '1px solid #e5e7eb',
              borderRadius: 4, cursor: 'pointer', fontSize: 12, color: '#374151' }}>{ext}</button>
          ))}
        </div>
        <div style={{ maxHeight: 500, overflowY: 'auto' }}>
          {sdsFiles.length === 0 ? (
            <div style={{ padding: 20, textAlign: 'center', color: '#999' }}>加载中...</div>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
              <thead><tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#666', width: 40 }}>☑️</th>
                <th style={{ textAlign: 'left', padding: '8px 12px', color: '#666' }}>文件名</th>
                <th style={{ textAlign: 'right', padding: '8px 12px', color: '#666', width: 100 }}>大小</th>
                <th style={{ textAlign: 'center', padding: '8px 12px', color: '#666', width: 80 }}>操作</th>
              </tr></thead>
              <tbody>
                {sdsFiles.map((f, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #f0f0f0', background: selectedFiles.has(f.path) ? '#eff6ff' : 'transparent' }}>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <input type='checkbox' checked={selectedFiles.has(f.path)} onChange={() => toggleSelectFile(f.path)}
                        style={{ cursor: 'pointer', width: 16, height: 16 }} />
                    </td>
                    <td style={{ padding: '8px 12px', fontFamily: 'monospace', fontSize: 12 }}>{f.path}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'right', color: '#666' }}>{formatFileSize(f.size)}</td>
                    <td style={{ padding: '8px 12px', textAlign: 'center' }}>
                      <a href={f.url} download style={{ color: '#3b82f6', textDecoration: 'none' }}>📥</a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  )

  const tabs = [
    { key: 'dashboard', label: '📊 系统概览' },
    { key: 'goals', label: '🎯 目标配置' },
    { key: 'tasks', label: '📋 任务规则' },
    { key: 'projects', label: '📁 项目阈值' },
    { key: 'realtime', label: '📡 实时监控' },
    { key: 'history', label: '📈 历史趋势' },
    { key: 'architecture', label: '🏗️ 架构编辑' },
    { key: 'documents', label: '📄 文档管理' },
  ]

  const renderContent = () => {
    switch (activeTab) {
      case 'dashboard': return renderDashboard()
      case 'goals': return renderGoals()
      case 'tasks': return renderTasks()
      case 'projects': return renderProjects()
      case 'realtime': return renderRealtime()
      case 'history': return renderHistory()
      case 'architecture': return renderArchitecture()
      case 'documents': return renderDocuments()
      default: return null
    }
  }

  // 获取最高优先级通知
  const topNotification = activeNotifications[0] || null

  return (
    <div className='page-container' style={{ maxWidth: '100%', padding: '0 32px' }}>
      {/* WebSocket 实时通知 */}
      {topNotification && (
        <WSDEventToast event={topNotification} onClear={() => {
          setActiveNotifications(prev => prev.slice(1))
          clearAllEvents()
        }} />
      )}
      <div className='page-header'>
        <h2 className='page-title'>🤖 SDS1 自我驱动系统</h2>
      </div>
      <div style={{ display: 'flex', gap: 8, marginBottom: 24, flexWrap: 'wrap' }}>
        {tabs.map(tab => (
          <button key={tab.key} onClick={() => setActiveTab(tab.key)} style={{
            padding: '8px 16px', border: 'none', borderRadius: 6,
            background: activeTab === tab.key ? '#3b82f6' : '#f3f4f6',
            color: activeTab === tab.key ? '#fff' : '#374151',
            cursor: 'pointer', fontSize: 13, fontWeight: activeTab === tab.key ? 600 : 400
          }}>{tab.label}</button>
        ))}
      </div>
      {renderContent()}
    </div>
  )
}
