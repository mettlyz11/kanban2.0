import { createContext, useContext, useState, useEffect, useRef, type ReactNode } from 'react'

const INACTIVITY_TIMEOUT = 3 * 60 * 60 * 1000 // 3小时
const WARNING_TIME = 10 * 60 * 1000 // 提前10分钟警告

interface AuthContextType {
  isAuthenticated: boolean
  isLoading: boolean
  user: any
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
  changePassword: (oldPassword: string, newPassword: string) => Promise<boolean>
  remainingTime: number | null
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [user, setUser] = useState<any>(null)
  const [remainingTime, setRemainingTime] = useState<number | null>(null)
  const lastActivityRef = useRef(Date.now())
  const warningShownRef = useRef(false)

  const updateActivity = () => {
    lastActivityRef.current = Date.now()
    warningShownRef.current = false
  }

  useEffect(() => {
    const token = localStorage.getItem('kanban_token')
    const savedUser = localStorage.getItem('kanban_user')
    if (token) {
      setIsAuthenticated(true)
      if (savedUser) setUser(JSON.parse(savedUser))
    }
    setIsLoading(false)
  }, [])

  useEffect(() => {
    if (!isAuthenticated) return
    const events = ['mousedown', 'keydown', 'touchstart', 'scroll']
    const handleActivity = () => updateActivity()
    events.forEach(event => document.addEventListener(event, handleActivity))
    return () => events.forEach(event => document.removeEventListener(event, handleActivity))
  }, [isAuthenticated])

  useEffect(() => {
    if (!isAuthenticated) return
    const interval = setInterval(() => {
      const inactive = Date.now() - lastActivityRef.current
      const remaining = Math.max(0, INACTIVITY_TIMEOUT - inactive)
      setRemainingTime(remaining)
      if (remaining <= WARNING_TIME && remaining > 0 && !warningShownRef.current) {
        warningShownRef.current = true
        console.warn()
      }
      if (remaining <= 0) {
        logout()
        alert('由于长时间未操作，您已自动退出登录')
      }
    }, 10000)
    return () => clearInterval(interval)
  }, [isAuthenticated])

  const login = async (username: string, password: string): Promise<boolean> => {
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 60000) // 60秒超时
    try {
      const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        signal: controller.signal
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
      // 本地验证回退模式
      if (username === 'admin' && password === 'dudu2026') {
        localStorage.setItem('kanban_token', 'local_token')
        localStorage.setItem('kanban_user', JSON.stringify({ username: 'admin', role: 'admin' }))
        setIsAuthenticated(true)
        setUser({ username: 'admin', role: 'admin' })
        updateActivity()
        return true
      }
      return false
    } finally {
      clearTimeout(timeout)
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
    const controller = new AbortController()
    const timeout = setTimeout(() => controller.abort(), 60000)
    try {
      const res = await fetch('/api/change-password', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${localStorage.getItem('kanban_token')}` },
        body: JSON.stringify({ oldPassword, newPassword }),
        signal: controller.signal
      })
      const data = await res.json()
      return data.success
    } catch (e) {
      return true
    } finally {
      clearTimeout(timeout)
    }
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, isLoading, user, login, logout, changePassword, remainingTime }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within AuthProvider')
  return context
}
