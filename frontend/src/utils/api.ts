// API服务 - 复用v1.0后端
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
  async updateTaskStatus(taskId: number, status: string) {
    const res = await fetch(`${API_BASE}/tasks/${taskId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status })
    })
    return res.json()
  },

  // Cron任务
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
  async getCronHistory() {
    const res = await fetch(`${API_BASE}/cron/history`)
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
  }
}
