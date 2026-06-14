import React, { useRef, useEffect, useState } from 'react'

interface Leaf {
  id: string; name: string; emoji?: string
  status: 'growing' | 'alive' | 'withered' | 'frozen'
  deps?: string[]; complexity?: number; description?: string
  children?: Leaf[]
}

interface Props {
  leaves: Leaf[]
  onGrow: (speech: string) => void
  onPrune: (leafId: string) => void
  onEvent?: (emoji: string, desc: string) => void
}

const LEAF_COLORS: Record<string, string> = {
  growing: '#f59e0b', alive: '#22c55e', withered: '#475569', frozen: '#06b6d4'
}

const VineWall: React.FC<Props> = ({ leaves, onGrow, onPrune, onEvent }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [speech, setSpeech] = useState('')
  const [showInput, setShowInput] = useState(false)
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [hoveredId, setHoveredId] = useState<string | null>(null)
  const animRef = useRef<number>(0)
  const phaseRef = useRef(0)

  // Draw vine wall
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const W = canvas.width = canvas.parentElement?.clientWidth || 800
    const H = canvas.height = 600
    const cx = W / 2
    const cy = 30

    let phase = phaseRef.current
    phase += 0.02
    phaseRef.current = phase

    const draw = () => {
      ctx.clearRect(0, 0, W, H)

      // Draw main vine (stem)
      ctx.strokeStyle = '#334155'
      ctx.lineWidth = 4
      ctx.beginPath()
      ctx.moveTo(cx, cy)

      const vinePoints: { x: number; y: number }[] = []
      let y = cy
      const spacing = Math.min(80, (H - 60) / Math.max(leaves.length || 1, 1))

      // Draw segmented vine with gentle curves
      leaves.forEach((leaf, i) => {
        y = cy + (i + 1) * spacing + Math.sin(phase + i * 0.5) * 8
        const sway = Math.sin(phase * 0.5 + i * 0.7) * 20
        const x = cx + sway
        vinePoints.push({ x, y })

        // Draw vine segment
        ctx.strokeStyle = leaf.status === 'withered' ? '#1e293b' : '#334155'
        ctx.lineWidth = leaf.status === 'growing' ? 3 : 2
        ctx.beginPath()
        if (i === 0) {
          ctx.moveTo(cx, cy)
        } else {
          const prev = vinePoints[i - 1]
          ctx.moveTo(prev.x, prev.y - spacing * 0.3)
        }
        ctx.quadraticCurveTo(
          x + sway * 0.3, y - spacing * 0.5,
          x, y
        )
        ctx.stroke()

        // Draw small tendrils
        for (let t = 0; t < 2; t++) {
          ctx.strokeStyle = '#1e293b'
          ctx.lineWidth = 1
          ctx.beginPath()
          const tx = x + (t === 0 ? -15 : 15) + Math.sin(phase * 1.5 + i + t) * 5
          const ty = y - 10 + t * 5
          ctx.moveTo(x, y - 5)
          ctx.quadraticCurveTo(x + (t === 0 ? -20 : 20), ty - 15, tx, ty)
          ctx.stroke()
        }

        // Draw leaf (circle for alive, diamond for growing, etc.)
        const isSelected = selectedId === leaf.id
        const isHovered = hoveredId === leaf.id
        const r = isSelected ? 32 : isHovered ? 28 : 24
        const color = LEAF_COLORS[leaf.status]

        ctx.beginPath()
        if (leaf.status === 'growing') {
          // Pulsating circle
          const pulse = 1 + Math.sin(phase * 3 + i) * 0.1
          ctx.arc(x, y, r * pulse, 0, Math.PI * 2)
        } else if (leaf.status === 'withered') {
          // Diamond
          ctx.moveTo(x, y - r)
          ctx.lineTo(x + r * 0.7, y)
          ctx.lineTo(x, y + r)
          ctx.lineTo(x - r * 0.7, y)
          ctx.closePath()
        } else if (leaf.status === 'frozen') {
          // Square with rounded corners
          ctx.roundRect(x - r, y - r, r * 2, r * 2, 6)
        } else {
          // Normal rounded circle
          ctx.arc(x, y, r, 0, Math.PI * 2)
        }

        ctx.fillStyle = color + '30'
        ctx.fill()
        ctx.strokeStyle = isSelected ? '#3b82f6' : isHovered ? '#94a3b8' : color + '60'
        ctx.lineWidth = isSelected ? 2.5 : 1.5
        ctx.stroke()

        // Emoji in center
        ctx.font = '16px system-ui'
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = '#e2e8f0'
        ctx.fillText(leaf.emoji || '🍃', x, y)

        // Name below leaf
        ctx.font = '10px system-ui'
        ctx.fillStyle = isHovered ? '#94a3b8' : '#64748b'
        ctx.fillText(leaf.name.length > 6 ? leaf.name.slice(0, 6) + '..' : leaf.name, x, y + r + 14)

        // Status indicator
        if (leaf.status === 'growing') {
          ctx.fillStyle = '#f59e0b'
          ctx.font = '8px monospace'
          ctx.fillText('⟳', x + r + 2, y - r - 2)
        }
      })

      // Draw connection lines between dependent leaves
      leaves.forEach((leaf, i) => {
        if (!leaf.deps || leaf.deps.length === 0) return
        leaf.deps.forEach(depId => {
          const depIdx = leaves.findIndex(l => l.id === depId)
          if (depIdx >= 0 && vinePoints[i] && vinePoints[depIdx]) {
            ctx.strokeStyle = '#1e293b'
            ctx.lineWidth = 1
            ctx.setLineDash([4, 4])
            ctx.beginPath()
            ctx.moveTo(vinePoints[i].x, vinePoints[i].y - 25)
            ctx.lineTo(vinePoints[depIdx].x, vinePoints[depIdx].y + 25)
            ctx.stroke()
            ctx.setLineDash([])
          }
        })
      })

      animRef.current = requestAnimationFrame(draw)
    }

    draw()
    return () => cancelAnimationFrame(animRef.current)
  }, [leaves, selectedId, hoveredId])

  // Click handler
  const handleClick = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const W = canvas.width
    const cx = W / 2
    const spacing = Math.min(80, (canvas.height - 60) / Math.max(leaves.length || 1, 1))

    let found = false
    leaves.forEach((leaf, i) => {
      const y = 30 + (i + 1) * spacing + Math.sin(phaseRef.current + i * 0.5) * 8
      const sway = Math.sin(phaseRef.current * 0.5 + i * 0.7) * 20
      const x = cx + sway
      const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2)
      if (dist < 30) {
        setSelectedId(selectedId === leaf.id ? null : leaf.id)
        found = true
      }
    })
    if (!found) setSelectedId(null)
  }

  const handleMouseMove = (e: React.MouseEvent) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const rect = canvas.getBoundingClientRect()
    const mx = e.clientX - rect.left
    const my = e.clientY - rect.top
    const W = canvas.width
    const cx = W / 2
    const spacing = Math.min(80, (canvas.height - 60) / Math.max(leaves.length || 1, 1))

    let found = false
    leaves.forEach((leaf, i) => {
      const y = 30 + (i + 1) * spacing + Math.sin(phaseRef.current + i * 0.5) * 8
      const sway = Math.sin(phaseRef.current * 0.5 + i * 0.7) * 20
      const x = cx + sway
      const dist = Math.sqrt((mx - x) ** 2 + (my - y) ** 2)
      if (dist < 30) { setHoveredId(leaf.id); found = true }
    })
    if (!found) setHoveredId(null)
  }

  const selectedLeaf = leaves.find(l => l.id === selectedId)

  const handleSubmit = () => {
    if (!speech.trim()) return
    onGrow(speech.trim())
    onEvent?.('🌱', '说: ' + speech.trim())
    setSpeech('')
  }

  return (
    <div style={{
      background: '#0f172a',
      borderRadius: 12,
      border: '1px solid #1e293b',
      overflow: 'hidden',
      position: 'relative'
    }}>
      {/* Header */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '12px 16px',
        borderBottom: '1px solid #1e293b'
      }}>
        <span style={{ fontSize: 20 }}>🌱</span>
        <div>
          <div style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 600 }}>SproutOS 藤蔓</div>
          <div style={{ color: '#475569', fontSize: 10 }}>
            {leaves.length} 片叶子 · {leaves.filter(l => l.status === 'alive').length} 可用
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button onClick={() => setShowInput(!showInput)}
            style={{padding:'4px 12px',border:'1px solid #334155',borderRadius:6,background:showInput?'#334155':'transparent',color:'#e2e8f0',fontSize:11,cursor:'pointer'}}>
            💬 {showInput ? '收起' : '说话'}
          </button>
        </div>
      </div>

      {/* Chat input */}
      {showInput && (
        <div style={{ padding: '8px 16px', borderBottom: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input value={speech} onChange={e => setSpeech(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="说一个需求..."
              style={{flex:1,padding:'8px 12px',background:'#1e293b',border:'1px solid #334155',borderRadius:6,color:'#e2e8f0',fontSize:12,outline:'none'}}/>
            <button onClick={handleSubmit}
              style={{padding:'8px 16px',background:'#3b82f6',border:'none',borderRadius:6,color:'#fff',fontSize:12,fontWeight:600,cursor:'pointer'}}>
              长
            </button>
          </div>
        </div>
      )}

      {/* Canvas */}
      <canvas ref={canvasRef} onClick={handleClick} onMouseMove={handleMouseMove}
        style={{ width: '100%', height: 600, cursor: 'pointer', display: 'block' }} />

      {/* Selection detail panel */}
      {selectedLeaf && (
        <div style={{
          position: 'absolute', bottom: 12, left: 12, right: 12,
          background: '#1e293b', border: '1px solid #334155', borderRadius: 8,
          padding: 12, fontSize: 11
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <div>
              <span style={{color:'#e2e8f0',fontWeight:600}}>{selectedLeaf.emoji} {selectedLeaf.name}</span>
              <span style={{color:'#64748b',marginLeft:8}}>· {selectedLeaf.description || ''}</span>
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <span style={{color:'#475569',fontSize:10}}>复杂度: {'⭐'.repeat(selectedLeaf.complexity || 1)}</span>
              {selectedLeaf.status !== 'withered' && (
                <button onClick={() => { onPrune(selectedLeaf.id); setSelectedId(null) }}
                  style={{padding:'2px 8px',background:'transparent',border:'1px solid #475569',borderRadius:4,color:'#ef4444',fontSize:10,cursor:'pointer'}}>
                  ✂️
                </button>
              )}
            </div>
          </div>
          {selectedLeaf.deps && selectedLeaf.deps.length > 0 && (
            <div style={{color:'#475569',fontSize:9,marginTop:4}}>依赖: {selectedLeaf.deps.join(', ')}</div>
          )}
        </div>
      )}

      {/* Empty state */}
      {leaves.length === 0 && (
        <div style={{
          position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)',
          textAlign: 'center', color: '#475569'
        }}>
          <div style={{fontSize:48,marginBottom:8}}>🌱</div>
          <div style={{fontSize:14,fontWeight:600,color:'#64748b',marginBottom:4}}>还没有叶子</div>
          <button onClick={() => setShowInput(true)}
            style={{marginTop:8,padding:'8px 20px',background:'#3b82f6',border:'none',borderRadius:8,color:'#fff',fontSize:13,fontWeight:600,cursor:'pointer'}}>
            🌱 开始养
          </button>
        </div>
      )}
    </div>
  )
}

export default VineWall
