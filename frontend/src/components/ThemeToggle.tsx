import React from 'react'
import { useTheme } from '../hooks/useTheme'

const ThemeToggle: React.FC = () => {
  const { theme, toggleTheme } = useTheme()

  return (
    <button
      onClick={toggleTheme}
      style={{
        padding: '8px 12px',
        background: 'transparent',
        border: '1px solid #334155',
        borderRadius: '8px',
        color: '#94a3b8',
        fontSize: '14px',
        cursor: 'pointer',
        display: 'flex',
        alignItems: 'center',
        gap: '6px'
      }}
    >
      {theme === 'dark' ? '🌙' : '☀️'}
      <span>{theme === 'dark' ? '深色' : '浅色'}</span>
    </button>
  )
}

export default ThemeToggle
