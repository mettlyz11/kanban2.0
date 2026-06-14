import { useState, useEffect } from 'react'

type Theme = 'dark' | 'light' | 'auto'

export const useTheme = () => {
  const [theme, setTheme] = useState<Theme>(() => {
    const saved = localStorage.getItem('sprout_theme')
    return (saved as Theme) || 'dark'
  })

  useEffect(() => {
    const root = document.documentElement
    
    if (theme === 'auto') {
      const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
      root.setAttribute('data-theme', prefersDark ? 'dark' : 'light')
    } else {
      root.setAttribute('data-theme', theme)
    }
    
    localStorage.setItem('sprout_theme', theme)
  }, [theme])

  const toggleTheme = () => {
    setTheme(prev => prev === 'dark' ? 'light' : 'dark')
  }

  return { theme, setTheme, toggleTheme }
}
