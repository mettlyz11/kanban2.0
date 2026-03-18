import { useState, useEffect } from 'react'
import { useAuth } from '../hooks/useAuth'

// 生成随机数学验证码
function generateCaptcha() {
  const num1 = Math.floor(Math.random() * 10) + 1
  const num2 = Math.floor(Math.random() * 10) + 1
  const operators = ['+', '-', '*']
  const operator = operators[Math.floor(Math.random() * operators.length)]
  
  let answer
  switch(operator) {
    case '+': answer = num1 + num2; break
    case '-': answer = num1 - num2; break
    case '*': answer = num1 * num2; break
    default: answer = num1 + num2
  }
  
  return { question: `${num1} ${operator} ${num2} = ?`, answer }
}

export function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [captchaInput, setCaptchaInput] = useState('')
  const [captcha, setCaptcha] = useState(generateCaptcha())
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [attempts, setAttempts] = useState(0)
  const [isLocked, setIsLocked] = useState(false)
  const [lockTime, setLockTime] = useState(0)
  const { login } = useAuth()

  // 检查登录锁定
  useEffect(() => {
    const lockedUntil = localStorage.getItem('login_locked_until')
    if (lockedUntil) {
      const remaining = parseInt(lockedUntil) - Date.now()
      if (remaining > 0) {
        setIsLocked(true)
        setLockTime(Math.ceil(remaining / 1000))
        const timer = setInterval(() => {
          const newRemaining = parseInt(lockedUntil) - Date.now()
          if (newRemaining <= 0) {
            setIsLocked(false)
            localStorage.removeItem('login_locked_until')
            clearInterval(timer)
          } else {
            setLockTime(Math.ceil(newRemaining / 1000))
          }
        }, 1000)
        return () => clearInterval(timer)
      } else {
        localStorage.removeItem('login_locked_until')
      }
    }
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    // 检查锁定状态
    if (isLocked) {
      setError(`登录已锁定，请 ${lockTime} 秒后重试`)
      return
    }

    // 验证验证码
    if (parseInt(captchaInput) !== captcha.answer) {
      setError('验证码错误，请重新计算')
      setCaptcha(generateCaptcha())
      setCaptchaInput('')
      return
    }

    setLoading(true)

    const success = await login(username, password)
    if (!success) {
      const newAttempts = attempts + 1
      setAttempts(newAttempts)
      
      // 5次失败后锁定5分钟
      if (newAttempts >= 5) {
        const lockUntil = Date.now() + 5 * 60 * 1000
        localStorage.setItem('login_locked_until', lockUntil.toString())
        setIsLocked(true)
        setLockTime(300)
        setError('登录失败次数过多，已锁定5分钟')
      } else {
        setError(`用户名或密码错误（剩余 ${5 - newAttempts} 次机会）`)
      }
      
      // 刷新验证码
      setCaptcha(generateCaptcha())
      setCaptchaInput('')
    } else {
      // 登录成功，清除失败次数
      setAttempts(0)
      localStorage.removeItem('login_attempts')
    }

    setLoading(false)
  }

  const refreshCaptcha = () => {
    setCaptcha(generateCaptcha())
    setCaptchaInput('')
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
    }}>
      <div style={{
        background: 'white',
        padding: '40px',
        borderRadius: '16px',
        boxShadow: '0 20px 60px rgba(0,0,0,0.3)',
        width: '100%',
        maxWidth: '400px'
      }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div style={{ fontSize: '4rem', marginBottom: '16px' }}>📊</div>
          <h1 style={{ margin: 0, color: '#333' }}>看板系统 v2.0</h1>
          <p style={{ color: '#666', marginTop: '8px' }}>请登录以继续</p>
        </div>

        {error && (
          <div style={{
            padding: '12px',
            background: '#ffebee',
            color: '#c62828',
            borderRadius: '8px',
            marginBottom: '20px',
            textAlign: 'center'
          }}>
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontWeight: 600,
              color: '#555'
            }}>
              用户名
            </label>
            <input
              type="text"
              value={username}
              onChange={e => setUsername(e.target.value)}
              style={{
                width: '100%',
                padding: '12px',
                borderRadius: '8px',
                border: '1px solid #ddd',
                fontSize: '16px',
                boxSizing: 'border-box'
              }}
              placeholder="请输入用户名"
              required
              disabled={isLocked}
            />
          </div>

          <div style={{ marginBottom: '20px' }}>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontWeight: 600,
              color: '#555'
            }}>
              密码
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={e => setPassword(e.target.value)}
                style={{
                  width: '100%',
                  padding: '12px 45px 12px 12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '16px',
                  boxSizing: 'border-box'
                }}
                placeholder="请输入密码"
                required
                disabled={isLocked}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                style={{
                  position: 'absolute',
                  right: '8px',
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '20px',
                  padding: '4px 8px',
                  color: '#666'
                }}
                title={showPassword ? '隐藏密码' : '显示密码'}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>

          {/* 验证码 */}
          <div style={{ marginBottom: '24px' }}>
            <label style={{
              display: 'block',
              marginBottom: '8px',
              fontWeight: 600,
              color: '#555'
            }}>
              验证码（防机器人）
            </label>
            <div style={{ display: 'flex', gap: '12px' }}>
              <div style={{
                padding: '12px 20px',
                background: '#f5f5f5',
                borderRadius: '8px',
                fontFamily: 'monospace',
                fontSize: '18px',
                fontWeight: 600,
                color: '#667eea',
                letterSpacing: '2px',
                userSelect: 'none',
                cursor: 'pointer'
              }} onClick={refreshCaptcha} title="点击刷新">
                {captcha.question}
              </div>
              <input
                type="text"
                value={captchaInput}
                onChange={e => setCaptchaInput(e.target.value)}
                style={{
                  flex: 1,
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '16px',
                  boxSizing: 'border-box'
                }}
                placeholder="计算结果"
                required
                disabled={isLocked}
                maxLength={3}
              />
            </div>
            <p style={{ fontSize: '12px', color: '#999', marginTop: '4px' }}>
              点击算式可刷新验证码 | 5次错误将锁定5分钟
            </p>
          </div>

          <button
            type="submit"
            disabled={loading || isLocked}
            style={{
              width: '100%',
              padding: '14px',
              background: isLocked ? '#ccc' : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '8px',
              fontSize: '16px',
              fontWeight: 600,
              cursor: (loading || isLocked) ? 'not-allowed' : 'pointer',
              opacity: (loading || isLocked) ? 0.7 : 1
            }}
          >
            {loading ? '登录中...' : isLocked ? `已锁定 (${lockTime}s)` : '登录'}
          </button>
        </form>

        {/* 安全提示 */}
        <div style={{
          marginTop: '20px',
          padding: '12px',
          background: '#e8f5e9',
          borderRadius: '8px',
          fontSize: '12px',
          color: '#2e7d32'
        }}>
          <strong>🔒 安全措施：</strong>
          <ul style={{ margin: '8px 0 0 0', paddingLeft: '16px' }}>
            <li>验证码防暴力破解</li>
            <li>5次错误自动锁定</li>
            <li>30分钟无操作自动退出</li>
          </ul>
        </div>
      </div>
    </div>
  )
}
