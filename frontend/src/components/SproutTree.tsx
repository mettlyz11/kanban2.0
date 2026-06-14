import React, { useState } from 'react'

interface TreeLeaf {
  id: string
  name: string
  emoji?: string
  status: 'growing' | 'alive' | 'withered' | 'frozen'
  children?: TreeLeaf[]
}

interface Props {
  leaves: TreeLeaf[]
  onGrow: (speech: string) => void
  onPrune: (leafId: string) => void
  onEvent?: (emoji: string, desc: string) => void
}

const LEAF_COLORS: Record<string, string> = {
  growing: '#f59e0b',
  alive: '#22c55e',
  withered: '#475569',
  frozen: '#06b6d4'
}

const LEAF_BG: Record<string, string> = {
  growing: '#f59e0b22',
  alive: '#22c55e22',
  withered: '#47556922',
  frozen: '#06b6d422'
}

const SproutTree: React.FC<Props> = ({ leaves, onGrow, onPrune, onEvent }) => {
  const [speech, setSpeech] = useState('')
  const [showInput, setShowInput] = useState(false)
  const [expandedId, setExpandedId] = useState<string | null>(null)

  const [journal, setJournal] = useState<{time:string;event:string}[]>([])
  const [growCount, setGrowCount] = useState(0)

  const handleSubmit = () => {
    if (!speech.trim()) return
    onGrow(speech.trim())
    addDiaryEntry('🌱', '说: ' + speech.trim())
    onEvent?.('🌱', '说: ' + speech.trim())
    setGrowCount(c => c + 1)
    setSpeech('')
  }

  const addDiaryEntry = (emoji:string, desc:string) => {
    setJournal(p => [{time:new Date().toLocaleTimeString('zh-CN',{hour12:false}), event:`${emoji} ${desc}`}, ...p.slice(0,49)])
  }

  const renderLeaf = (leaf: TreeLeaf, depth: number = 0) => (
    <div key={leaf.id} style={{ marginLeft: depth * 20, marginBottom: 4 }}>
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 8,
          padding: '6px 10px',
          borderRadius: 8,
          background: LEAF_BG[leaf.status],
          border: `1px solid ${LEAF_COLORS[leaf.status]}33`,
          cursor: 'pointer',
          transition: 'all 0.15s'
        }}
        onClick={() => setExpandedId(expandedId === leaf.id ? null : leaf.id)}
      >
        <span style={{ fontSize: 16 }}>{leaf.emoji || '🍃'}</span>
        <span style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 500, flex: 1 }}>
          {leaf.name}
        </span>
        <span
          style={{
            width: 8,
            height: 8,
            borderRadius: '50%',
            background: LEAF_COLORS[leaf.status],
            animation: leaf.status === 'growing' ? 'pulse-wait 1.5s ease-in-out infinite' : 'none'
          }}
        />
        <span style={{ color: '#475569', fontSize: 10 }}>
          {leaf.status === 'growing' ? '生长中' : leaf.status === 'alive' ? '可用' : leaf.status === 'withered' ? '已修剪' : '已冷冻'}
        </span>
        {leaf.status !== 'withered' && (
          <button
            onClick={(e) => { e.stopPropagation(); onPrune(leaf.id) }}
            style={{
              background: 'none', border: 'none', color: '#475569',
              cursor: 'pointer', fontSize: 12, padding: '0 4px'
            }}
            title="修剪"
          >✂️</button>
        )}
      </div>
      {expandedId === leaf.id && (
        <div style={{marginTop:6,padding:'8px 12px',background:'#0f172a',borderRadius:8,border:'1px solid #1e293b',fontSize:11}}>
          <div style={{color:'#94a3b8',marginBottom:4}}>📋 {leaf.name}</div>
          <div style={{color:'#cbd5e1'}}>{leaf.description||'暂无描述'}</div>
          <div style={{color:'#475569',marginTop:4,fontSize:10}}>
            复杂度: {'⭐'.repeat(leaf.complexity||1)} · 依赖: {leaf.deps?.join(', ')||'无'}
          </div>
        </div>
      )}
      {expandedId === leaf.id && leaf.children && leaf.children.length > 0 && (
        <div style={{ marginTop: 4 }}>
          {leaf.children.map(c => renderLeaf(c, depth + 1))}
        </div>
      )}
    </div>
  )

  return (
    <div style={{
      background: '#0f172a',
      borderRadius: 12,
      border: '1px solid #1e293b',
      padding: 16,
      minHeight: 200
    }}>
      {/* Tree header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        marginBottom: 16,
        paddingBottom: 12,
        borderBottom: '1px solid #1e293b'
      }}>
        <span style={{ fontSize: 24 }}>🌱</span>
        <div>
          <div style={{ color: '#e2e8f0', fontSize: 15, fontWeight: 600 }}>SproutOS</div>
          <div style={{ color: '#475569', fontSize: 10 }}>
            {leaves.length} 片叶子 · 完成度 {Math.min(Math.round(leaves.filter(l => l.status === 'alive').length / Math.max(leaves.length, 1) * 100), 100)}%
          </div>
        </div>
        <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
          <button
            onClick={() => setShowInput(!showInput)}
            style={{
              padding: '4px 12px', border: '1px solid #334155', borderRadius: 6,
              background: showInput ? '#334155' : 'transparent',
              color: '#e2e8f0', fontSize: 11, cursor: 'pointer', fontWeight: 600
            }}
          >
            💬 说话
          </button>
        </div>
      </div>

      {/* Chat input */}
      {showInput && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 8 }}>
            <input
              value={speech}
              onChange={e => setSpeech(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSubmit()}
              placeholder="说一个目标或需求..."
              style={{
                flex: 1,
                padding: '8px 12px',
                background: '#1e293b',
                border: '1px solid #334155',
                borderRadius: 8,
                color: '#e2e8f0',
                fontSize: 13,
                outline: 'none'
              }}
            />
            <button
              onClick={handleSubmit}
              style={{
                padding: '8px 16px',
                background: '#3b82f6',
                border: 'none',
                borderRadius: 8,
                color: '#fff',
                fontSize: 13,
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              长
            </button>
          </div>
          <div style={{ color: '#475569', fontSize: 9, marginTop: 4 }}>
            试试说："帮我加一个预算功能" 或 "这个分类不对"
          </div>
        </div>
      )}

      {/* Tree */}
      {leaves.length === 0 ? (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '40px 20px',
          color: '#475569'
        }}>
          <span style={{ fontSize: 48, marginBottom: 8 }}>🌱</span>
          <div style={{ fontSize: 14, fontWeight: 600, color: '#64748b', marginBottom: 4 }}>
            还没有叶子
          </div>
          <div style={{ fontSize: 11, textAlign: 'center', maxWidth: 300 }}>
            点击"说话"按钮，说一个目标，SproutOS 会帮你长出第一片叶子。
          </div>
          <button
            onClick={() => setShowInput(true)}
            style={{
              marginTop: 16,
              padding: '8px 20px',
              background: '#3b82f6',
              border: 'none',
              borderRadius: 8,
              color: '#fff',
              fontSize: 13,
              fontWeight: 600,
              cursor: 'pointer'
            }}
          >
            🌱 开始养
          </button>
        </div>
      ) : (
        <div>
          {leaves.map(l => renderLeaf(l))}
        </div>
      )}

      {/* Growth Journal */}
      {journal.length > 0 && (
        <div style={{marginTop:12,paddingTop:12,borderTop:'1px solid #1e293b'}}>
          <div style={{display:'flex',justifyContent:'space-between',marginBottom:6}}>
            <span style={{color:'#64748b',fontSize:10,fontWeight:600}}>📜 生长日记</span>
            <span style={{color:'#475569',fontSize:9}}>共{growCount}次生长</span>
          </div>
          <div style={{maxHeight:120,overflowY:'auto',fontSize:9,fontFamily:'monospace',color:'#64748b'}}>
            {journal.map((j,i)=><div key={i} style={{padding:'2px 0',display:'flex',gap:6}}>
              <span style={{color:'#475569',minWidth:36}}>{j.time}</span>
              <span>{j.event}</span>
            </div>)}
          </div>
        </div>
      )}

      {/* Growth progress */}
      {leaves.length > 0 && (
        <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid #1e293b' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ color: '#64748b', fontSize: 10 }}>生长进度</span>
            <span style={{ color: '#475569', fontSize: 10 }}>
              {leaves.filter(l => l.status === 'alive').length} / {leaves.length} 可用
            </span>
          </div>
          <div style={{
            height: 4,
            background: '#0f172a',
            borderRadius: 2,
            overflow: 'hidden'
          }}>
            <div style={{
              width: `${leaves.length > 0 ? (leaves.filter(l => l.status === 'alive').length / leaves.length) * 100 : 0}%`,
              height: '100%',
              background: 'linear-gradient(90deg, #22c55e, #3b82f6)',
              borderRadius: 2,
              transition: 'width 0.5s'
            }} />
          </div>
        </div>
      )}
    </div>
  )
}

export default SproutTree
