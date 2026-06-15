/**
 * 涟漪全景图 v15 — 可拖拽方块
 */
import React, { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const STATUS_COLORS: Record<string, string> = {
  completed: '#10b981', in_progress: '#3b82f6', pending: '#f59e0b',
  pending_review: '#f97316', blocked: '#ef4444', failed: '#dc2626',
  cancelled: '#9ca3af', default: '#6b7280',
}
const GOAL_COLORS: Record<string, string> = {
  '1-AI助手优化': '#6366f1', '2-和光智成': '#0891b2',
  '3-学术影响力': '#059669', '5-家庭幸福': '#d97706',
  '6-社会参与': '#7c3aed', '7-身心健康': '#dc2626',
  default: '#6b7280',
}
const GOAL_BG: Record<string, string> = {
  '1-AI助手优化': '#eef2ff', '2-和光智成': '#ecfeff',
  '3-学术影响力': '#ecfdf5', '5-家庭幸福': '#fffbeb',
  '6-社会参与': '#f5f3ff', '7-身心健康': '#fef2f2',
  '': '#f8fafc',
}

interface Task {
  id: number; title: string; status: string; goal?: string
  created_at?: string; updated_at?: string
  ripple_ids?: number[] | string
}
interface LinkD { source: number; target: number; type: string }

function getIds(t: Task): number[] {
  if (Array.isArray(t.ripple_ids)) return t.ripple_ids
  if (typeof t.ripple_ids === 'string') { try { return JSON.parse(t.ripple_ids) } catch {} }
  return []
}
function pDate(s?: string): Date | null {
  if (!s) return null; const d = new Date(s); return isNaN(d.getTime()) ? null : d
}

export default function RipplePanorama() {
  const svgRef = useRef<SVGSVGElement>(null)
  const [mode, setMode] = useState<'loading' | 'graph' | 'text'>('loading')
  const [stats, setStats] = useState({ visible: 0, total: 0, links: 0 })
  const [msg, setMsg] = useState('')
  const [dayIndex, setDayIndex] = useState(0)
  const [maxDays, setMaxDays] = useState(0)
  const [playing, setPlaying] = useState(false)
  const [speed, setSpeed] = useState(800)
  const loaded = useRef(false)

  const linkDayM = useRef<Map<string, number>>(new Map())
  const dayMap = useRef<Map<string, number>>(new Map())
  const dayToIdsM = useRef<Map<number, number[]>>(new Map())
  const nodePosMap = useRef<Map<number, { x: number; y: number }>>(new Map())
  const minDateR = useRef<Date>(new Date())
  const maxDaysR = useRef(0)
  const linkElements = useRef<any>(null)
  const allLinksR = useRef<LinkD[]>([])

  const doUpdate = (day: number) => {
    try {
      const el = svgRef.current
      if (!el) return
      const svg = d3.select(el)
      const g = svg.select('g.d3-root')
      if (g.empty()) return
      const nd = g.selectAll('circle.task-node')
      const lnk = g.selectAll('line.ripple-link')
      if (nd.empty()) return

      const visIds = new Set<number>()
      for (let d = 0; d <= day; d++) {
        const ts = dayToIdsM.current.get(d)
        if (ts) ts.forEach(id => visIds.add(id))
      }

      let visLinks = 0
      lnk.each(function(d: any) {
        const key = d.source + '-' + d.target
        const ld = linkDayM.current.get(key)
        const op = (ld !== undefined && ld <= day) ? 0.35 : 0
        if (op > 0) visLinks++
        d3.select(this).attr('stroke-opacity', op)
      })

      let visCount = 0
      nd.each(function(d: any) {
        const v = visIds.has(d.id)
        if (v) visCount++
        const e = d3.select(this)
        e.attr('opacity', v ? 1 : 0.04)
        if (v) {
          e.attr('r', d.status === 'in_progress' ? 9 : 7)
            .attr('fill', GOAL_COLORS[d.goal || ''] || STATUS_COLORS[d.status] || '#6b7280')
            .attr('stroke-width', 2)
        } else {
          e.attr('r', 3).attr('stroke-width', 0)
        }
      })

      g.selectAll('.day-label').remove()
      const dt = new Date(minDateR.current.getTime() + day * 86400000)
      g.append('text').attr('class', 'day-label')
        .attr('x', (el.clientWidth || 1000) - 16).attr('y', 28)
        .attr('text-anchor', 'end').attr('font-size', '15px').attr('font-weight', 'bold').attr('fill', '#6366f1')
        .text(dt.toISOString().slice(0, 10))

      setStats(s => ({ ...s, visible: visCount, links: visLinks }))
    } catch (e) { console.error('update:', e) }
  }

  // Redraw links when blocks are dragged
  const refreshLinks = () => {
    try {
      const el = svgRef.current
      if (!el) return
      const lnk = d3.select(el).select('g.d3-root').selectAll('line.ripple-link')
      const pm = nodePosMap.current
      lnk.attr('x1', (d: any) => pm.get(d.source)?.x || 0)
        .attr('y1', (d: any) => pm.get(d.source)?.y || 0)
        .attr('x2', (d: any) => pm.get(d.target)?.x || 0)
        .attr('y2', (d: any) => pm.get(d.target)?.y || 0)
    } catch (e) { console.error('refreshLinks:', e) }
  }

  const init = async (tasks: Task[]) => {
    try {
      const dates = tasks.map(t => pDate(t.created_at)).filter(d => d !== null) as Date[]
      if (!dates.length) { setMsg('无日期数据'); setMode('text'); return }
      dates.sort((a, b) => a.getTime() - b.getTime())
      minDateR.current = dates[0]
      const total = Math.ceil((Date.now() - dates[0].getTime()) / 86400000) + 1
      maxDaysR.current = total

      const dm = new Map<string, number>()
      for (let i = 0; i < total; i++) dm.set(new Date(dates[0].getTime() + i * 86400000).toISOString().slice(0, 10), i)
      dayMap.current = dm

      const dti = new Map<number, number[]>()
      for (let i = 0; i < total; i++) dti.set(i, [])
      for (const t of tasks) { const d = pDate(t.created_at); if (!d) continue; const idx = dm.get(d.toISOString().slice(0, 10)); if (idx !== undefined) dti.get(idx)!.push(t.id) }
      dayToIdsM.current = dti

      // Multi-level ripple chains
      const parentMap = new Map<number, number[]>()
      for (const t of tasks) { const p = getIds(t); if (p.length > 0) parentMap.set(t.id, p) }
      const resolved = new Map<number, Set<number>>()
      function getAncestors(id: number, visited: Set<number>): Set<number> {
        if (resolved.has(id)) return resolved.get(id)!
        if (visited.has(id)) return new Set()
        visited.add(id)
        const r = new Set<number>()
        const p = parentMap.get(id)
        if (p) { for (const pp of p) { r.add(pp); getAncestors(pp, visited).forEach(a => r.add(a)) } }
        resolved.set(id, r)
        return r
      }

      const allIds = new Set(tasks.map(n => n.id))
      const linkMap = new Map<string, LinkD>()
      const linkDayMap = new Map<string, number>()

      for (const t of tasks) {
        const ancestors = getAncestors(t.id, new Set())
        for (const a of ancestors) {
          allIds.add(a)
          const key = a + '-' + t.id
          if (!linkMap.has(key)) {
            const sD = pDate(tasks.find(n => n.id === a)?.created_at)
            const tD = pDate(t.created_at)
            const mx = Math.max(sD ? sD.getTime() : 0, tD ? tD.getTime() : 0)
            linkMap.set(key, { source: a, target: t.id, type: 'ripple' })
            linkDayMap.set(key, dm.get(new Date(mx).toISOString().slice(0, 10)) || 0)
          }
        }
      }

      for (const t of tasks.slice(0, 30)) {
        try {
          const c = new AbortController(); setTimeout(() => c.abort(), 2000)
          const r = await fetch('/api/tasks/' + t.id + '/dependencies?_t=' + Date.now(), { signal: c.signal })
          if (!r.ok) continue; const d = await r.json(); const deps = d.dependencies || {}
          for (const p of deps.prerequisites || []) {
            allIds.add(p.id); const key = t.id + '-' + p.id
            if (!linkMap.has(key)) { linkMap.set(key, { source: t.id, target: p.id, type: 'depends_on' }); linkDayMap.set(key, dm.get(new Date(pDate(t.created_at)?.getTime() || 0).toISOString().slice(0, 10)) || 0) }
          }
          for (const s of deps.subtasks || []) {
            allIds.add(s.id); const key = t.id + '-' + s.id
            if (!linkMap.has(key)) { linkMap.set(key, { source: t.id, target: s.id, type: 'subtask' }); linkDayMap.set(key, dm.get(new Date(pDate(t.created_at)?.getTime() || 0).toISOString().slice(0, 10)) || 0) }
          }
        } catch {}
      }
      linkDayM.current = linkDayMap

      let nodes = [...allIds].map(id => {
        const f = tasks.find(n => n.id === id)
        return { id, title: f?.title || '#' + id, status: f?.status || 'unknown', goal: f?.goal || '' }
      })
      const go = ['1-AI助手优化', '2-和光智成', '3-学术影响力', '5-家庭幸福', '6-社会参与', '7-身心健康', '']
      nodes.sort((a: any, b: any) => { const ai = go.indexOf(a.goal || ''), bi = go.indexOf(b.goal || ''); return (ai === -1 ? 999 : ai) - (bi === -1 ? 999 : bi) || a.id - b.id })
      const links = [...linkMap.values()]
      allLinksR.current = links
      setStats(s => ({ ...s, total: nodes.length, links: links.length }))

      // === DRAW ===
      const el = svgRef.current
      if (!el) { setMode('text'); return }
      const svg = d3.select(el)
      svg.selectAll('*').remove()

      const W = Math.max(el.clientWidth, 900)
      const H = Math.max(el.clientHeight || 800, 800)
      svg.attr('width', W).attr('height', H)

      const root = svg.append('g').attr('class', 'd3-root')
      svg.call(d3.zoom<SVGSVGElement, unknown>().scaleExtent([0.2, 4]).on('zoom', (ev) => root.attr('transform', ev.transform)))

      // Defs
      const defs = svg.append('defs')
      defs.append('marker').attr('id', 'a-ripple').attr('viewBox', '0 -5 10 10')
        .attr('refX', 12).attr('refY', 0).attr('markerWidth', 4).attr('markerHeight', 4).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#8b5cf6')
      defs.append('marker').attr('id', 'a-dep').attr('viewBox', '0 -5 10 10')
        .attr('refX', 12).attr('refY', 0).attr('markerWidth', 4).attr('markerHeight', 4).attr('orient', 'auto')
        .append('path').attr('d', 'M0,-5L10,0L0,5').attr('fill', '#94a3b8')

      // Links layer (behind blocks)
      const linksLayer = root.append('g').attr('class', 'links-layer')
      linksLayer.selectAll('line').data(links).join('line').attr('class', 'ripple-link')
        .attr('stroke', (d: any) => d.type === 'ripple' ? '#8b5cf6' : '#94a3b8')
        .attr('stroke-width', (d: any) => d.type === 'ripple' ? 0.4 : 0.6)
        .attr('stroke-dasharray', (d: any) => d.type === 'ripple' ? '3,3' : '')
        .attr('stroke-opacity', 0.35)
        .attr('marker-end', (d: any) => d.type === 'ripple' ? 'url(#a-ripple)' : 'url(#a-dep)')

      // Group by goal
      const groups = new Map<string, any[]>()
      for (const n of nodes) { const gk = n.goal || ''; if (!groups.has(gk)) groups.set(gk, []); groups.get(gk)!.push(n) }

      // Block layout
      const posMap = new Map<number, { x: number; y: number }>()
      const pad2 = 20, gap2 = 10, lh2 = 22
      const goalKeys = [...groups.keys()]
      const gridCols = Math.ceil(goalKeys.length / 2)
      const gridW = (W - pad2 * 2 - gap2 * (gridCols - 1)) / gridCols

      // Block groups layer
      const blocksLayer = root.append('g').attr('class', 'blocks-layer')

      let xOff2 = pad2, yOff2 = pad2, colIdx3 = 0, rowMaxH2 = 0
      for (let gi = 0; gi < goalKeys.length; gi++) {
        const gk = goalKeys[gi]
        const ns = groups.get(gk)!
        const nCount = ns.length

        let bestCols = 3, bestDiff2 = Infinity
        for (let c = 3; c <= Math.max(3, Math.min(18, nCount + 2)); c++) {
          const cellW = (gridW - 12) / c
          const rows = Math.ceil(nCount / c)
          const blockH = lh2 + rows * cellW + 10
          const diff = Math.abs(gridW - blockH)
          if (diff < bestDiff2) { bestDiff2 = diff; bestCols = c }
        }

        const innerCols = bestCols
        const cellW = (gridW - 12) / innerCols
        const cellH = cellW
        const rows = Math.ceil(nCount / innerCols)
        const blockH = lh2 + rows * cellH + 10

        // Create draggable group for this block
        const blockG = blocksLayer.append('g').attr('class', 'block-group')
          .attr('transform', `translate(${xOff2},${yOff2})`)
          .style('cursor', 'grab')

        // Block bg
        blockG.append('rect').attr('width', gridW).attr('height', blockH)
          .attr('rx', 8).attr('fill', GOAL_BG[gk] || '#f8fafc').attr('stroke', GOAL_COLORS[gk] || '#e2e8f0').attr('stroke-width', 1)

        // Label
        blockG.append('text').attr('x', 8).attr('y', 15)
          .attr('font-size', '11px').attr('font-weight', 'bold').attr('fill', GOAL_COLORS[gk] || '#64748b')
          .text(gk || '未分类')

        // Nodes inside the block (relative positions)
        for (let i = 0; i < ns.length; i++) {
          const nn = ns[i]
          const cx = 6 + (i % innerCols) * cellW + cellW / 2
          const cy = lh2 + 4 + Math.floor(i / innerCols) * cellH + cellH / 2
          const absX = xOff2 + cx
          const absY = yOff2 + cy
          posMap.set(nn.id, { x: absX, y: absY })

          blockG.append('circle').datum(nn).attr('class', 'task-node')
            .attr('cx', cx).attr('cy', cy)
            .attr('r', 3).attr('fill', '#6b7280').attr('stroke', '#fff').attr('stroke-width', 0)
            .attr('opacity', 0.04).style('cursor', 'pointer')
            .on('click', (ev: any) => ev.stopPropagation())
            .append('title').text('#' + nn.id + ' ' + nn.title + '\n' + nn.status + ' | ' + (nn.goal || ''))
        }

        // Drag behavior
        const drag = d3.drag<SVGGElement, unknown>()
          .on('start', function(ev) {
            d3.select(this).style('cursor', 'grabbing').raise()
          })
          .on('drag', function(ev) {
            const t = d3.select(this)
            const oldX = parseFloat(t.attr('transform')?.match(/translate\(([^,]+)/)?.[1] || '0')
            const oldY = parseFloat(t.attr('transform')?.match(/,([^)]+)/)?.[1] || '0')
            const newX = oldX + ev.dx
            const newY = oldY + ev.dy
            t.attr('transform', `translate(${newX},${newY})`)

            // Update node positions for link redrawing
            const deltaX = ev.dx
            const deltaY = ev.dy
            for (const nn of ns) {
              const old = posMap.get(nn.id)
              if (old) posMap.set(nn.id, { x: old.x + deltaX, y: old.y + deltaY })
            }
            nodePosMap.current = posMap

            // Redraw links
            const lnk = linksLayer.selectAll('line')
            lnk.attr('x1', (d: any) => posMap.get(d.source)?.x || 0)
              .attr('y1', (d: any) => posMap.get(d.source)?.y || 0)
              .attr('x2', (d: any) => posMap.get(d.target)?.x || 0)
              .attr('y2', (d: any) => posMap.get(d.target)?.y || 0)
          })
          .on('end', function() {
            d3.select(this).style('cursor', 'grab')
          })

        blockG.call(drag)

        if (blockH > rowMaxH2) rowMaxH2 = blockH
        colIdx3++
        if (colIdx3 >= gridCols) { xOff2 = pad2; yOff2 += rowMaxH2 + gap2; rowMaxH2 = 0; colIdx3 = 0 }
        else { xOff2 += gridW + gap2 }
      }
      nodePosMap.current = posMap

      // Set initial link positions
      linksLayer.selectAll('line')
        .attr('x1', (d: any) => posMap.get(d.source)?.x || 0)
        .attr('y1', (d: any) => posMap.get(d.source)?.y || 0)
        .attr('x2', (d: any) => posMap.get(d.target)?.x || 0)
        .attr('y2', (d: any) => posMap.get(d.target)?.y || 0)

      setMaxDays(total)
      setDayIndex(0)
      setMode('graph')
      setTimeout(() => doUpdate(0), 100)
    } catch (e: any) { console.error(e); setMsg(e.message || '初始化失败'); setMode('text') }
  }

  useEffect(() => {
    if (loaded.current) return
    loaded.current = true
    ;(async () => {
      setMode('loading')
      try {
        const c = new AbortController(); setTimeout(() => c.abort(), 20000)
        const r = await fetch('/api/tasks?per_page=500&sort_field=created_at', { signal: c.signal })
        if (!r.ok) throw new Error('' + r.status)
        const d = await r.json()
        const items: Task[] = (d.tasks || []).map((t: any) => ({
          id: t.id, title: t.title || '', status: t.status || 'unknown',
          goal: t.strategic_goal || '', created_at: t.created_at, updated_at: t.updated_at || t.created_at,
          ripple_ids: t.ripple_upstream_ids || [],
        }))
        await init(items)
      } catch (e: any) { setMsg('加载失败: ' + e.message); setMode('text') }
    })()
  }, [])

  useEffect(() => {
    if (playing) {
      const t = setInterval(() => { setDayIndex(prev => { if (prev >= maxDaysR.current - 1) { setPlaying(false); return maxDaysR.current - 1 } return prev + 1 }) }, speed)
      return () => clearInterval(t)
    }
  }, [playing, speed])

  useEffect(() => { if (mode === 'graph') doUpdate(dayIndex) }, [dayIndex, mode])

  const fmtDate = (d: number) => new Date(minDateR.current.getTime() + d * 86400000).toISOString().slice(0, 10)
  const pct = maxDays > 0 ? (dayIndex / (maxDays - 1)) * 100 : 0

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: '#f8fafc' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 16px', background: 'white', borderBottom: '1px solid #e2e8f0', minHeight: '48px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>🔮 涟漪全景 · 时间轴</span>
          {mode === 'graph' && <span style={{ fontSize: '0.75rem', color: '#64748b' }}>{stats.visible}/{stats.total} 任务 · 🟣 {stats.links} 链路</span>}
          {mode === 'loading' && <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>加载数据中...</span>}
        </div>
        <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
          <button onClick={() => setSpeed(s => s === 300 ? 600 : s === 600 ? 800 : s === 800 ? 1200 : 300)}
            style={{ fontSize: '0.7rem', padding: '3px 10px', borderRadius: '4px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer', color: '#64748b' }}>{speed}ms</button>
          <button onClick={() => setPlaying(!playing)}
            style={{ fontSize: '0.8rem', padding: '5px 16px', borderRadius: '6px', border: 'none', background: playing ? '#ef4444' : '#6366f1', color: 'white', cursor: 'pointer', fontWeight: 600 }}>
            {playing ? '⏹ 暂停' : '▶ 播放'}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, position: 'relative', overflow: 'auto' }}>
        <svg ref={svgRef} style={{ width: '100%', height: '100%', display: 'block', background: '#f8fafc', minHeight: '800px' }} />
        {mode === 'loading' && <div style={{ position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f8fafc' }}><span style={{ color: '#94a3b8' }}>🔮 加载任务数据及涟漪链...</span></div>}
        {mode === 'graph' && (
          <div style={{ position: 'absolute', top: 10, left: 10, fontSize: '0.7rem', background: 'rgba(255,255,255,0.92)', padding: '6px 10px', borderRadius: '6px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)', zIndex: 5, lineHeight: '1.6' }}>
            🟢完成 🔵进行 🟡待办 🔴阻塞 | 🟣多级涟漪·灰=依赖<br/>方块可拖拽移动 · 连线自动跟随
          </div>
        )}
        {mode === 'text' && <div style={{ position: 'absolute', inset: 0, display: 'flex', justifyContent: 'center', alignItems: 'center', background: '#f8fafc' }}><span style={{ color: '#64748b' }}>{msg}</span></div>}
      </div>

      {maxDays > 0 && (
        <div style={{ padding: '10px 20px 14px', background: 'white', borderTop: '1px solid #e2e8f0', minHeight: '80px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px', fontSize: '0.75rem', color: '#64748b' }}>
            <span>{fmtDate(0)}</span>
            <span style={{ fontWeight: 600, color: '#6366f1', fontSize: '0.8rem' }}>{fmtDate(dayIndex)}</span>
            <span>{fmtDate(maxDays - 1)}</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button onClick={() => setDayIndex(Math.max(0, dayIndex - 7))} style={{ fontSize: '0.75rem', padding: '2px 6px', borderRadius: '4px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer', color: '#64748b' }}>◀◀</button>
            <button onClick={() => setDayIndex(Math.max(0, dayIndex - 1))} style={{ fontSize: '0.85rem', padding: '2px 8px', borderRadius: '4px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer' }}>◀</button>
            <div style={{ flex: 1, height: '6px', borderRadius: '3px', background: '#e2e8f0', position: 'relative', cursor: 'pointer' }}
              onClick={(e) => { const r = e.currentTarget.getBoundingClientRect(); setDayIndex(Math.round(((e.clientX - r.left) / r.width) * (maxDays - 1))) }}>
              <div style={{ width: pct + '%', height: '100%', borderRadius: '3px', background: 'linear-gradient(90deg, #6366f1, #8b5cf6)', transition: 'width 0.1s' }} />
              <div style={{ position: 'absolute', left: 'calc(' + pct + '% - 6px)', top: '-4px', width: '14px', height: '14px', borderRadius: '50%', background: '#6366f1', boxShadow: '0 1px 4px rgba(99,102,241,0.4)', transition: 'left 0.08s' }} />
            </div>
            <button onClick={() => setDayIndex(Math.min(maxDays - 1, dayIndex + 1))} style={{ fontSize: '0.85rem', padding: '2px 8px', borderRadius: '4px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer' }}>▶</button>
            <button onClick={() => setDayIndex(Math.min(maxDays - 1, dayIndex + 7))} style={{ fontSize: '0.75rem', padding: '2px 6px', borderRadius: '4px', border: '1px solid #e2e8f0', background: 'white', cursor: 'pointer', color: '#64748b' }}>▶▶</button>
          </div>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '4px', fontSize: '0.65rem', color: '#94a3b8' }}>
            <span>第 {dayIndex + 1}/{maxDays} 天</span>
            <span>{playing ? '▶ 播放中' : '⏸ 已暂停'} · {speed}ms/天</span>
          </div>
        </div>
      )}
    </div>
  )
}
