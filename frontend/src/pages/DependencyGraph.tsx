import { useState, useEffect, useRef, useCallback } from 'react'
import { Card, Tag, Spin, Alert, Statistic, Row, Col, Tooltip, Select, Input } from 'antd'
import { ReloadOutlined, ZoomInOutlined, ZoomOutOutlined, ExpandOutlined } from '@ant-design/icons'

interface DepEdge {
  task_id: number
  dep_task_id: number
  task_title: string
  dep_task_title: string
  task_status: string
  dep_task_status: string
  source: string
  dep_type: string
}

interface GraphNode {
  id: number
  title: string
  status: string
  layer: number
  x: number
  y: number
  outDegree: number
  inDegree: number
}

interface GraphEdge {
  from: number
  to: number
  source: string
}

const STATUS_COLORS: Record<string, string> = {
  completed: '#52c41a',
  done: '#52c41a',
  success: '#52c41a',
  in_progress: '#1890ff',
  processing: '#1890ff',
  pending: '#faad14',
  paused: '#faad14',
  failed: '#f5222d',
  error: '#f5222d',
  cancelled: '#8c8c8c',
  deleted: '#8c8c8c',
}

const STATUS_BG: Record<string, string> = {
  completed: '#f6ffed',
  done: '#f6ffed',
  success: '#f6ffed',
  in_progress: '#e6f7ff',
  processing: '#e6f7ff',
  pending: '#fffbe6',
  paused: '#fffbe6',
  failed: '#fff1f0',
  error: '#fff1f0',
  cancelled: '#f5f5f5',
  deleted: '#f5f5f5',
}

const SHORT_TITLE_LEN = 16

function buildGraph(edges: DepEdge[]): { nodes: GraphNode[], edges: GraphEdge[] } {
  // Build adjacency
  const adj = new Map<number, number[]>()
  const revAdj = new Map<number, number[]>()
  const nodeInfo = new Map<number, { title: string; status: string }>()

  for (const e of edges) {
    // Forward
    if (!adj.has(e.task_id)) adj.set(e.task_id, [])
    adj.get(e.task_id)!.push(e.dep_task_id)
    // Reverse
    if (!revAdj.has(e.dep_task_id)) revAdj.set(e.dep_task_id, [])
    revAdj.get(e.dep_task_id)!.push(e.task_id)

    if (!nodeInfo.has(e.task_id)) nodeInfo.set(e.task_id, { title: e.task_title || `#${e.task_id}`, status: e.task_status })
    if (!nodeInfo.has(e.dep_task_id)) nodeInfo.set(e.dep_task_id, { title: e.dep_task_title || `#${e.dep_task_id}`, status: e.dep_task_status })
  }

  // Collect all node IDs
  const allIds = new Set<number>()
  for (const e of edges) {
    allIds.add(e.task_id)
    allIds.add(e.dep_task_id)
  }

  // Topological sort with Kahn's algorithm for layers
  const inDeg = new Map<number, number>()
  for (const id of allIds) inDeg.set(id, 0)
  for (const [from, tos] of adj) {
    for (const to of tos) {
      inDeg.set(to, (inDeg.get(to) || 0) + 1)
    }
  }

  const layers = new Map<number, number>()  // node id -> layer
  let queue: number[] = []
  for (const id of allIds) {
    if ((inDeg.get(id) || 0) === 0) {
      queue.push(id)
      layers.set(id, 0)
    }
  }

  let processed = 0
  while (queue.length > 0) {
    const next: number[] = []
    for (const node of queue) {
      processed++
      const deps = revAdj.get(node) || []
      for (const dep of deps) {
        const newLayer = (layers.get(node) || 0) + 1
        if (!layers.has(dep) || layers.get(dep)! < newLayer) {
          layers.set(dep, newLayer)
        }
        const curInDeg = (inDeg.get(dep) || 1) - 1
        inDeg.set(dep, curInDeg)
        if (curInDeg === 0) {
          next.push(dep)
        }
      }
    }
    queue = next
  }

  // Handle remaining nodes (cycles or start nodes)
  for (const id of allIds) {
    if (!layers.has(id)) layers.set(id, 0)
  }

  // Group nodes by layer
  const layerGroups = new Map<number, number[]>()
  for (const [id, layer] of layers) {
    if (!layerGroups.has(layer)) layerGroups.set(layer, [])
    layerGroups.get(layer)!.push(id)
  }

  // Assign x,y positions
  const NODE_WIDTH = 100
  const NODE_HEIGHT = 36
  const H_GAP = 60
  const V_GAP = 60
  const nodes: GraphNode[] = []

  for (const [layer, ids] of layerGroups) {
    const count = ids.length
    const startX = -(count - 1) * (NODE_WIDTH + H_GAP) / 2
    for (let i = 0; i < ids.length; i++) {
      const id = ids[i]
      const info = nodeInfo.get(id) || { title: `#${id}`, status: 'unknown' }
      const outDegree = (adj.get(id) || []).length
      const inDegree = (revAdj.get(id) || []).length
      nodes.push({
        id,
        title: info.title,
        status: info.status,
        layer,
        x: startX + i * (NODE_WIDTH + H_GAP),
        y: layer * (NODE_HEIGHT + V_GAP),
        outDegree,
        inDegree,
      })
    }
  }

  // Build edge list
  const graphEdges: GraphEdge[] = []
  for (const e of edges) {
    graphEdges.push({ from: e.task_id, to: e.dep_task_id, source: e.source })
  }

  return { nodes, edges: graphEdges }
}

// Simple SVG arrow marker
const MARKER_ID = 'arrowhead'

export default function DependencyGraph() {
  const [edges, setEdges] = useState<DepEdge[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [graph, setGraph] = useState<{ nodes: GraphNode[]; edges: GraphEdge[] }>({ nodes: [], edges: [] })
  const [scale, setScale] = useState(0.8)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const [dragging, setDragging] = useState(false)
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 })
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const svgRef = useRef<SVGSVGElement>(null)

  const loadData = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)
      const res = await fetch('/api/tasks/dependencies/graph')
      const data = await res.json()
      if (data.success) {
        setEdges(data.edges)
        const g = buildGraph(data.edges)
        setGraph(g)
      } else {
        setError(data.error || '获取依赖数据失败')
      }
    } catch (e: any) {
      setError(e.message || '网络错误')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -0.05 : 0.05
    setScale(s => Math.max(0.2, Math.min(3, s + delta)))
  }, [])

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    if (e.button === 0) {
      setDragging(true)
      setDragStart({ x: e.clientX - offset.x, y: e.clientY - offset.y })
    }
  }, [offset])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (dragging) {
      setOffset({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y })
    }
  }, [dragging, dragStart])

  const handleMouseUp = useCallback(() => {
    setDragging(false)
  }, [])

  const handleResetView = useCallback(() => {
    setScale(0.8)
    setOffset({ x: 0, y: 0 })
  }, [])

  const nodeById = new Map(graph.nodes.map(n => [n.id, n]))

  const uniqueNodes = graph.nodes.length
  const uniqueEdges = graph.edges.length

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spin size="large" tip="加载依赖图谱..." /></div>
  }

  if (error) {
    return <div style={{ padding: 24 }}><Alert message="加载失败" description={error} type="error" showIcon action={<a onClick={loadData}>重新加载</a>} /></div>
  }

  return (
    <div style={{ padding: 24, height: '100vh', display: 'flex', flexDirection: 'column', background: '#0d1117' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div>
          <h1 style={{ margin: 0, color: '#e6edf3', fontSize: 20 }}>
            🕸️ 依赖图谱
          </h1>
          <div style={{ marginTop: 4, color: '#8b949e', fontSize: 13 }}>
            所有 {uniqueEdges} 条依赖关系 · {uniqueNodes} 个任务
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <Tag icon={<ReloadOutlined />} color="blue" style={{ cursor: 'pointer' }} onClick={loadData}>刷新</Tag>
          <Tag icon={<ZoomInOutlined />} color="default" style={{ cursor: 'pointer' }} onClick={() => setScale(s => Math.min(3, s + 0.1))}>放大</Tag>
          <Tag icon={<ZoomOutOutlined />} color="default" style={{ cursor: 'pointer' }} onClick={() => setScale(s => Math.max(0.2, s - 0.1))}>缩小</Tag>
          <Tag icon={<ExpandOutlined />} color="default" style={{ cursor: 'pointer' }} onClick={handleResetView}>重置</Tag>
        </div>
      </div>

      {/* Legend */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 12, fontSize: 12, color: '#8b949e' }}>
        <span>● 已完成</span>
        <span>● 进行中</span>
        <span>● 待处理</span>
        <span>● 失败/取消</span>
        <span style={{ marginLeft: 16 }}>
          <svg width="20" height="2" style={{ verticalAlign: 'middle' }}><line x1="0" y1="1" x2="20" y2="1" stroke="#58a6ff" strokeWidth="2" strokeDasharray="4,2"/></svg>
          &nbsp;依赖方向 (task → dep)
        </span>
      </div>

      {/* SVG Canvas */}
      <div
        style={{
          flex: 1,
          border: '1px solid #30363d',
          borderRadius: 8,
          overflow: 'hidden',
          background: '#161b22',
          position: 'relative',
          cursor: dragging ? 'grabbing' : 'grab',
        }}
        onWheel={handleWheel}
        onMouseDown={handleMouseDown}
        onMouseMove={handleMouseMove}
        onMouseUp={handleMouseUp}
        onMouseLeave={handleMouseUp}
      >
        <svg
          ref={svgRef}
          width="100%"
          height="100%"
          style={{ display: 'block' }}
        >
          <defs>
            <marker
              id={MARKER_ID}
              markerWidth="8"
              markerHeight="6"
              refX="8"
              refY="3"
              orient="auto"
            >
              <polygon points="0 0, 8 3, 0 6" fill="#58a6ff" />
            </marker>
          </defs>

          <g transform={`translate(${offset.x + 400}, ${offset.y + 100}) scale(${scale})`}>
            {/* Edges */}
            {graph.edges.map((edge, i) => {
              const fromNode = nodeById.get(edge.from)
              const toNode = nodeById.get(edge.to)
              if (!fromNode || !toNode) return null

              // Arrow curves: calculate start/end along the bounding box edges
              const dx = toNode.x - fromNode.x
              const dy = toNode.y - fromNode.y
              const dist = Math.sqrt(dx * dx + dy * dy) || 1
              const nx = dx / dist
              const ny = dy / dist

              // Node dimensions
              const rw = 100 // approximate node width
              const rh = 36 // approximate node height

              // Calculate edge point from source node boundary
              const sx = fromNode.x + Math.sign(nx) * rw / 2
              const sy = fromNode.y + Math.sign(ny) * rh / 2

              // Calculate endpoint at target node boundary
              const tx = toNode.x - Math.sign(nx) * rw / 2
              const ty = toNode.y - Math.sign(ny) * rh / 2

              // Curved path for overlapping edges
              const midX = (sx + tx) / 2
              const midY = (sy + ty) / 2
              const curve = 20 * (i % 3 - 1) * 0.5
              const cx = midX
              const cy = midY - Math.abs(dx) * 0.1 - curve

              return (
                <path
                  key={`edge-${edge.from}-${edge.to}-${i}`}
                  d={`M ${sx} ${sy} Q ${cx} ${cy + Math.abs(dx) * 0.08 + 20}, ${tx} ${ty}`}
                  fill="none"
                  stroke="#58a6ff"
                  strokeWidth={1.5}
                  strokeOpacity={0.6}
                  markerEnd={`url(#${MARKER_ID})`}
                />
              )
            })}

            {/* Nodes */}
            {graph.nodes.map((node) => {
              const statusColor = STATUS_COLORS[node.status] || '#8b949e'
              const bgColor = STATUS_BG[node.status] || '#1c2128'
              const shortTitle = node.title.length > SHORT_TITLE_LEN
                ? node.title.substring(0, SHORT_TITLE_LEN) + '...'
                : node.title

              return (
                <g
                  key={`node-${node.id}`}
                  transform={`translate(${node.x - 50}, ${node.y - 18})`}
                  style={{ cursor: 'pointer' }}
                  onClick={() => setSelectedNode(node)}
                >
                  {/* Node background */}
                  <rect
                    x="0" y="0"
                    width="100" height="36"
                    rx="6"
                    fill={bgColor}
                    stroke={selectedNode?.id === node.id ? '#58a6ff' : statusColor}
                    strokeWidth={selectedNode?.id === node.id ? 2 : 1.5}
                    opacity={0.95}
                  />
                  {/* Status indicator dot */}
                  <circle cx="10" cy="18" r="4" fill={statusColor} />
                  {/* Title */}
                  <text
                    x="18" y="22"
                    fill="#e6edf3"
                    fontSize="10"
                    fontFamily="monospace"
                    textLength="76"
                    lengthAdjust="spacingAndGlyphs"
                  >
                    {shortTitle}
                  </text>
                  {/* ID badge */}
                  <text
                    x="94" y="9"
                    fill="#8b949e"
                    fontSize="8"
                    textAnchor="end"
                    fontFamily="monospace"
                  >
                    #{node.id}
                  </text>
                </g>
              )
            })}
          </g>
        </svg>

        {/* Node tooltip on click */}
        {selectedNode && (
          <div
            style={{
              position: 'absolute',
              top: 16,
              right: 16,
              background: '#1c2128',
              border: '1px solid #30363d',
              borderRadius: 8,
              padding: '12px 16px',
              minWidth: 240,
              maxWidth: 350,
              zIndex: 10,
              color: '#e6edf3',
              fontSize: 13,
              boxShadow: '0 4px 12px rgba(0,0,0,0.4)',
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'start', marginBottom: 8 }}>
              <strong style={{ fontSize: 14 }}>#{selectedNode.id}</strong>
              <Tag
                style={{ cursor: 'pointer', fontSize: 11 }}
                onClick={() => setSelectedNode(null)}
              >
                ✕
              </Tag>
            </div>
            <div style={{ marginBottom: 6, wordBreak: 'break-all' }}>{selectedNode.title}</div>
            <div style={{ display: 'flex', gap: 8, fontSize: 12, color: '#8b949e' }}>
              <Tag color={STATUS_COLORS[selectedNode.status] || 'default'}>{selectedNode.status}</Tag>
              <span>入度: {selectedNode.inDegree}</span>
              <span>出度: {selectedNode.outDegree}</span>
            </div>
            <div style={{ marginTop: 8, fontSize: 12 }}>
              <a
                href={`/tasks?search=${selectedNode.id}`}
                style={{ color: '#58a6ff' }}
                target="_blank"
                rel="noreferrer"
              >
                在任务列表查看 →
              </a>
            </div>
          </div>
        )}

        {/* Empty state */}
        {graph.nodes.length === 0 && !loading && (
          <div style={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            color: '#8b949e',
            textAlign: 'center',
          }}>
            <div style={{ fontSize: 40, marginBottom: 8 }}>📭</div>
            <div>暂无依赖关系</div>
          </div>
        )}
      </div>

      {/* Stats bar */}
      <div style={{ display: 'flex', gap: 24, marginTop: 12, fontSize: 12, color: '#8b949e' }}>
        <span>缩放: {Math.round(scale * 100)}%</span>
        <span>节点: {uniqueNodes}</span>
        <span>边: {uniqueEdges}</span>
        <span>层级: {new Set(graph.nodes.map(n => n.layer)).size}</span>
      </div>
    </div>
  )
}
