import { useState, useEffect } from 'react'
import { Search, RefreshCw, FolderOpen, File, Tag, ChevronDown, ChevronRight } from 'lucide-react'
import { io } from 'socket.io-client'

interface ResourceItem {
  id: number
  path: string
  name: string
  type: 'dir' | 'file'
  size: number
  item_count: number
  llm_summary: string
  tags: string
  suggested_use: string
  updated_at: string
}

const socket = io('/', { path: '/socket.io', transports: ['polling'] })

export default function ResourceLibrary() {
  const [items, setItems] = useState<ResourceItem[]>([])
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [lastUpdate, setLastUpdate] = useState<string>('')
  const [expanded, setExpanded] = useState<Record<number, boolean>>({})

  const fetchItems = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/resource-library')
      const data = await res.json()
      if (data.success) {
        setItems(data.items)
        setLastUpdate(new Date().toLocaleString())
      }
    } catch (e) {
      console.error('Failed to fetch resource library:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { fetchItems() }, [])

  useEffect(() => {
    socket.on('resource_library_updated', () => { fetchItems() })
    return () => { socket.off('resource_library_updated') }
  }, [])

  const filtered = items.filter(i =>
    !search || i.name.toLowerCase().includes(search.toLowerCase()) ||
    (i.llm_summary || '').toLowerCase().includes(search.toLowerCase()) ||
    (i.tags || '').toLowerCase().includes(search.toLowerCase())
  )

  const dirs = filtered.filter(i => i.type === 'dir')
  const files = filtered.filter(i => i.type === 'file')

  return (
    <div style={{ padding: '24px', maxWidth: '1200px', margin: '0 auto' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
        <h1 style={{ margin: 0, fontSize: '28px', fontWeight: 700 }}>资源库</h1>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {lastUpdate && <span style={{ fontSize: '12px', color: '#888' }}>更新: {lastUpdate}</span>}
          <button onClick={fetchItems} disabled={loading} style={{
            padding: '8px 16px', background: '#667eea', color: 'white', border: 'none',
            borderRadius: '8px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', fontSize: '13px'
          }}>
            <RefreshCw size={16} /> 刷新
          </button>
        </div>
      </div>

      <div style={{ position: 'relative', marginBottom: '24px' }}>
        <Search size={18} style={{ position: 'absolute', left: '14px', top: '12px', color: '#888' }} />
        <input type="text" placeholder="搜索名称、简介、标签..." value={search} onChange={e => setSearch(e.target.value)}
          style={{ width: '100%', padding: '12px 14px 12px 42px', border: '1px solid #d1d5db', borderRadius: '10px',
            fontSize: '14px', outline: 'none', boxSizing: 'border-box', background: '#f9fafb' }}
        />
      </div>

      {loading && items.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '60px', color: '#888' }}>加载中...</div>
      ) : (
        <>
          {dirs.length > 0 && (
            <>
              <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', color: '#374151' }}>
                目录 ({dirs.length})
              </h2>
              <div style={{ display: 'grid', gap: '16px', marginBottom: '32px', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))' }}>
                {dirs.map(item => (
                  <div key={item.id} style={{
                    padding: '16px', background: 'white', borderRadius: '12px',
                    border: '1px solid #e5e7eb', boxShadow: '0 1px 4px rgba(0,0,0,0.04)',
                    cursor: 'pointer', transition: 'box-shadow 0.2s'
                  }} onClick={() => setExpanded(p => ({...p, [item.id]: !p[item.id]}))}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '8px' }}>
                      <FolderOpen size={22} color="#667eea" />
                      <strong style={{ fontSize: '15px', color: '#111', flex: 1 }}>{item.name}</strong>
                      <span style={{ fontSize: '11px', color: '#999' }}>{item.item_count} 项</span>
                      {expanded[item.id] ? <ChevronDown size={16} color="#888" /> : <ChevronRight size={16} color="#888" />}
                    </div>
                    {item.llm_summary && (
                      <p style={{ fontSize: '13px', color: '#555', lineHeight: '1.5', margin: '0 0 8px 32px' }}>{item.llm_summary}</p>
                    )}
                    <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap', marginLeft: '32px' }}>
                      {item.tags && item.tags.split(',').map((t, i) => (
                        <span key={i} style={{ fontSize: '11px', padding: '2px 8px', background: '#eef0ff', borderRadius: '4px', color: '#4f46e5', display: 'flex', alignItems: 'center', gap: '3px' }}>
                          <Tag size={10} /> {t.trim()}
                        </span>
                      ))}
                      {item.suggested_use && (
                        <span style={{ fontSize: '11px', padding: '2px 8px', background: '#ecfdf5', borderRadius: '4px', color: '#059669' }}>
                          {item.suggested_use}
                        </span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}

          {files.length > 0 && (
            <>
              <h2 style={{ fontSize: '18px', fontWeight: 600, marginBottom: '16px', color: '#374151' }}>
                文件 ({files.length})
              </h2>
              <div style={{ display: 'grid', gap: '12px', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))' }}>
                {files.map(item => (
                  <div key={item.id} style={{
                    padding: '14px', background: 'white', borderRadius: '10px',
                    border: '1px solid #e5e7eb', fontSize: '13px'
                  }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px' }}>
                      <File size={18} color="#888" />
                      <span style={{ fontWeight: 600, color: '#374151' }}>{item.name}</span>
                      <span style={{ fontSize: '11px', color: '#999', marginLeft: 'auto' }}>{item.size} bytes</span>
                    </div>
                    {item.llm_summary && <p style={{ fontSize: '12px', color: '#555', margin: '4px 0 0 26px' }}>{item.llm_summary}</p>}
                  </div>
                ))}
              </div>
            </>
          )}

          {filtered.length === 0 && (
            <div style={{ textAlign: 'center', padding: '60px', color: '#888' }}>没有匹配的资源</div>
          )}
        </>
      )}
    </div>
  )
}
