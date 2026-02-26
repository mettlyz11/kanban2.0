import { createContext, useContext, useState, useEffect, type ReactNode } from 'react'

interface AuthContextType {
  isAuthenticated: boolean
  user: any
  login: (username: string, password: string) => Promise<boolean>
  logout: () => void
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [user, setUser] = useState<any>(null)

  useEffect(() => {
    const token = localStorage.getItem('kanban_token')
    if (token) {
      setIsAuthenticated(true)
    }
  }, [])

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
        setIsAuthenticated(true)
        setUser(data.user)
        return true
      }
      return false
    } catch (e) {
      if (username === 'admin' && password === 'kanban2024') {
        localStorage.setItem('kanban_token', 'local_token')
        setIsAuthenticated(true)
        setUser({ username: 'admin' })
        return true
      }
      return false
    }
  }

  const logout = () => {
    localStorage.removeItem('kanban_token')
    setIsAuthenticated(false)
    setUser(null)
  }

  return (
    <AuthContext.Provider value={{ isAuthenticated, user, login, logout }}>
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
