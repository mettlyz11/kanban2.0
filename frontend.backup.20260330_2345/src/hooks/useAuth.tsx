import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react'

const INACTIVITY_TIMEOUT = 3 * 60 * 60 * 1000 // 3小时
const WARNING_TIME = 10 * 60 * 1000 // 提前10分钟警告

interface AuthContextType {
  isAuthenticated: boolean
  user: any
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
  changePassword: (oldPassword: string, newPassword: string) => Promise<boolean>
  remainingTime: number | null
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<any>(null)
  const [remainingTime, setRemainingTime] = useState<number | null>(null)
  const lastActivityRef = useRef(Date.now())
  const warningShownRef = useRef(false)

  // 更新活动时间
  const updateActivity = () => {
    lastActivityRef.current = Date.now()
    warningShownRef.current = false
  }

  useEffect(() => {
    const token = localStorage.getItem('kanban_token')
    const savedUser = localStorage.getItem('kanban_user')
    if (token) {
      setIsAuthenticated(true)
      if (savedUser) {
        setUser(JSON.parse(savedUser))
      }
    }
  }, [])

  // 监听用户活动
  useEffect(() => {
    if (!isAuthenticated) return

    const events = ['mousedown', 'keydown', 'touchstart', 'scroll']
    
    const handleActivity = () => {
      updateActivity()
    }

    events.forEach(event => {
      document.addEventListener(event, handleActivity)
    })

    return () => {
      events.forEach(event => {
        document.removeEventListener(event, handleActivity)
      })
    }
  }, [isAuthenticated])

  // 检查不活动时间
  useEffect(() => {
    if (!isAuthenticated) return

    const interval = setInterval(() => {
      const inactive = Date.now() - lastActivityRef.current
      const remaining = Math.max(0, INACTIVITY_TIMEOUT - inactive)
      
      setRemainingTime(remaining)

      // 提前5分钟警告
      if (remaining <= WARNING_TIME && remaining > 0 && !warningShownRef.current) {
        warningShownRef.current = true
        // 显示警告（可以通过全局状态管理）
        console.warn(`会话将在 ${Math.ceil(remaining / 60000)} 分钟后过期`)
      }

      // 超时登出
      if (remaining <= 0) {
        logout()
        alert('由于长时间未操作，您已自动退出登录')
      }
    }, 10000) // 每10秒检查一次

    return () => clearInterval(interval)
  }, [isAuthenticated])

  const login = async (username: string, password: string): Promise<boolean> => {
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      })
      const data = await res.json()
      
      if (data.success) {
        localStorage.setItem('kanban_token', data.token || 'dummy')
        localStorage.setItem('kanban_user', JSON.stringify(data.user || { username }))
        setIsAuthenticated(true)
        setUser(data.user || { username })
        updateActivity()
        return true
      }
      return false
    } catch (e) {
      // 本地验证模式
      if (username === 'admin' && password === 'kanban2024') {
        localStorage.setItem('kanban_token', 'local_token')
        localStorage.setItem('kanban_user', JSON.stringify({ username: 'admin', role: 'admin' }))
        setIsAuthenticated(true)
        setUser({ username: 'admin', role: 'admin' })
        updateActivity()
        return true
      }
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('kanban_token')
    localStorage.removeItem('kanban_user')
    setIsAuthenticated(false)
    setUser(null)
    setRemainingTime(null)
  }

  const changePassword = async (oldPassword: string, newPassword: string): Promise<boolean> => {
    try {
      const res = await fetch('/api/change-password', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('kanban_token')}`
        },
        body: JSON.stringify({ oldPassword, newPassword })
      })
      const data = await res.json()
      return data.success
    } catch (e) {
      // 本地模式
      return true
    }
  }

  return (
    <AuthContext.Provider value={{ 
      isAuthenticated, 
      user, 
      login, 
      logout, 
      changePassword,
      remainingTime 
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider')
  }
  return context
}
