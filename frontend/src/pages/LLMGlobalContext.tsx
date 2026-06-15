import React, { useState, useEffect } from 'react'

const LLMGlobalContext: React.FC = () => {
  const [content, setContent] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    fetch('/llm_global_context.txt')
      .then(r => { if (!r.ok) throw new Error('HTTP ' + r.status); return r.text() })
      .then(t => { setContent(t); setLoading(false) })
      .catch(e => { setError(String(e)); setLoading(false) })
  }, [])

  if (loading) return (
    <div style={{ padding: '30px', minHeight: '400px', background: '#0f172a', color: '#e2e8f0', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2>⏳ 加载全局上下文...</h2>
    </div>
  )
  if (error) return (
    <div style={{ padding: '30px', minHeight: '400px', background: '#0f172a', color: '#f87171', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <h2>错误: {error}</h2>
    </div>
  )

  return (
    <div style={{ padding: '20px', minHeight: 'calc(100vh - 80px)', background: '#0f172a', color: '#e2e8f0', fontFamily: 'sans-serif' }}>
      <h1 style={{ fontSize: '22px', marginBottom: '20px', color: '#38bdf8' }}>🤖 LLM 全局上下文</h1>
      <pre style={{
        background: '#1e293b',
        borderRadius: '8px',
        padding: '20px',
        overflow: 'auto',
        fontSize: '13px',
        lineHeight: '1.6',
        color: '#cbd5e1',
        whiteSpace: 'pre-wrap',
        wordBreak: 'break-word',
        maxHeight: 'calc(100vh - 180px)',
        border: '1px solid #334155',
      }}>{content}</pre>
    </div>
  )
}
export default LLMGlobalContext
