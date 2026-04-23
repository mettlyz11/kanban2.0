// API 服务 - 复用 v1.0 后端
// 使用相对路径，自动适配当前域名
const API_BASE = '/api'

export const api = {
  // 统计
  async getStats() {
    const res = await fetch(`${API_BASE}/stats`)
    return res.json()
  },

  // 项目
  async getProjects() {
    const res = await fetch(`${API_BASE}/projects`)
    return res.json()
  },
  async createProject(data: any) {
    const res = await fetch(`${API_BASE}/projects`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },
  async updateProject(projectId: number, data: any) {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },
  async deleteProject(projectId: number) {
    const res = await fetch(`${API_BASE}/projects/${projectId}`, {
      method: 'DELETE'
    })
    return res.json()
  },
  // 获取项目关联的任务列表
  async getProjectTasks(projectId: number) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/tasks`)
    return res.json()
  },

  // 任务
  async getTasks(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/tasks${query ? '?' + query : ''}`)
    return res.json()
  },
  async createTask(data: any) {
    const res = await fetch(`${API_BASE}/tasks`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },
  async updateTask(taskId: number, data: any) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },
  async deleteTask(taskId: number) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}`, {
      method: 'DELETE'
    })
    return res.json()
  },
  // 获取任务执行历史
  async getTaskHistory(taskId: number) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/history`)
    return res.json()
  },

  // 目标
  async getGoals(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/goals${query ? '?' + query : ''}`)
    return res.json()
  },
  // 人生目标
  async getLifeGoals(params = {}) {
    const query = new URLSearchParams(params).toString()
    const res = await fetch(`${API_BASE}/life-goals${query ? '?' + query : ''}`)
    return res.json()
  },
  async createGoal(data: any) {
    const res = await fetch(`${API_BASE}/goals`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },

  // 资源监控
  async getMetricsHistory(timeRange: string = '24h') {
    const res = await fetch(`${API_BASE}/metrics/history?range=${timeRange}`)
    return res.json()
  },

  // Cron 任务
  async getCronTasks() {
    const res = await fetch(`${API_BASE}/cron/tasks`)
    return res.json()
  },
  async getCronStats() {
    const res = await fetch(`${API_BASE}/cron/stats`)
    return res.json()
  },
  async addCronTask(data: any) {
    const res = await fetch(`${API_BASE}/cron/add`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },
  async deleteCronTask(taskId: number) {
    const res = await fetch(`${API_BASE}/cron/delete/${taskId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' }
    })
    return res.json()
  },

  // 资产/股票
  async getStocks() {
    const res = await fetch(`${API_BASE}/stocks`)
    return res.json()
  },
  async getStockStats() {
    const res = await fetch(`${API_BASE}/stocks/stats`)
    return res.json()
  },

  // 手动审核
  async getManualReviewTasks() {
    const res = await fetch(`${API_BASE}/manual-review/tasks`)
    return res.json()
  },
  async completeManualReviewTask(taskId: number, data: any) {
    const res = await fetch(`${API_BASE}/manual-review/tasks/${taskId}/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    })
    return res.json()
  },

  // 技能库
  async getSkills() {
    const res = await fetch(`${API_BASE}/skills`)
    return res.json()
  },

  // 系统监控
  async getSystemHistory() {
    const res = await fetch(`${API_BASE}/system/history`)
    return res.json()
  },

  // 访问统计
  async getPageViews() {
    const res = await fetch(`${API_BASE}/access/page-views`)
    return res.json()
  },

  // Cron 历史
  async getCronHistory() {
    const res = await fetch(`${API_BASE}/cron/history`)
    return res.json()
  },

  // ========== 任务审核系统 API ==========
  
  // 获取待审核任务列表
  async getPendingAudits(source?: string) {
    const query = source ? `?source=${source}` : ''
    const res = await fetch(`${API_BASE}/audit/tasks/pending${query}`)
    return res.json()
  },
  
  // 批准任务
  async approveAudit(auditId: number, reviewer: string, notes?: string) {
    const res = await fetch(`${API_BASE}/audit/tasks/${auditId}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer, notes })
    })
    return res.json()
  },
  
  // 拒绝任务
  async rejectAudit(auditId: number, reviewer: string, reason?: string) {
    const res = await fetch(`${API_BASE}/audit/tasks/${auditId}/reject`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ reviewer, reason })
    })
    return res.json()
  },
  
  // 检查任务执行权限
  async checkTaskBeforeExecution(taskId: number) {
    const res = await fetch(`${API_BASE}/audit/tasks/${taskId}/check`)
    return res.json()
  },
  
  // 获取审核统计
  async getAuditStats() {
    const res = await fetch(`${API_BASE}/audit/tasks/stats`)
    return res.json()
  },
  
  // 获取审核仪表板
  async getAuditDashboard() {
    const res = await fetch(`${API_BASE}/audit/dashboard`)
    return res.json()
  },
  
  // 监督系统 - 强制执行审核
  async enforceAuditPolicy(taskId: number) {
    const res = await fetch(`${API_BASE}/audit/supervisor/enforce`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ task_id: taskId })
    })
    return res.json()
  },
  
  // 监督系统 - 扫描未审核任务
  async scanUnauditedTasks() {
    const res = await fetch(`${API_BASE}/audit/supervisor/scan`, {
      method: 'POST'
    })
    return res.json()
  },
  
  // 监督系统 - 获取报告
  async getSupervisorReport() {
    const res = await fetch(`${API_BASE}/audit/supervisor/report`)
    return res.json()
  }
}

// 项目文件管理 API
export const projectFilesApi = {
  async getFiles(projectId: number) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/documents`)
    return res.json()
  },
  async uploadFile(projectId: number, file: File, description?: string, uploadedBy?: string) {
    const formData = new FormData()
    formData.append('file', file)
    if (description) formData.append('description', description)
    if (uploadedBy) formData.append('uploaded_by', uploadedBy)
    
    const res = await fetch(`${API_BASE}/projects/${projectId}/documents`, {
      method: 'POST',
      body: formData
    })
    return res.json()
  },
  async downloadFile(projectId: number, fileId: number) {
    window.open(`${API_BASE}/projects/${projectId}/documents/${fileId}/download`, '_blank')
  },
  async deleteFile(projectId: number, fileId: number) {
    const res = await fetch(`${API_BASE}/projects/${projectId}/documents/${fileId}`, {
      method: 'DELETE'
    })
    return res.json()
  }
}

// 感知 Agent API
export const perceptionApi = {
  // 获取感知 Agent 状态
  async getStatus() {
    const res = await fetch(`${API_BASE}/perception/status`)
    return res.json()
  },

  // 获取感知事件
  async getEvents() {
    const res = await fetch(`${API_BASE}/perception/events`)
    return res.json()
  },

  // 发送测试事件
  async testEvent(type: string = 'test') {
    const res = await fetch(`${API_BASE}/perception/test`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ type })
    })
    return res.json()
  },

  // 记录用户行为
  async recordAction(userId: string, action: string, target?: string) {
    const res = await fetch(`${API_BASE}/perception/record-action`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: userId, action, target })
    })
    return res.json()
  }
}
