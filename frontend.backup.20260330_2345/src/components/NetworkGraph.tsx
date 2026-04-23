import { useEffect, useRef, useState, useCallback } from 'react'
import * as d3 from 'd3'

interface Node {
  id: string
  name: string
  type: string
  description?: string
  x?: number
  y?: number
  vx?: number
  vy?: number
  fx?: number | null
  fy?: number | null
}

interface Link {
  source: string
  target: string
  relation: string
  strength?: number
}

interface NetworkGraphProps {
  nodes: Node[]
  links: Link[]
  width?: number
  height?: number
  onNodeClick?: (node: Node) => void
  selectedNode?: string | null
  showAllLinks?: boolean
  onToggleLinks?: () => void
  debug?: boolean
}

const typeColors: Record<string, string> = {
  'person': '#667eea',
  'org': '#11998e',
  'product': '#fc4a1a',
  'project': '#f7b733',
  'group': '#a855f7',
  'event': '#ec4899',
  'default': '#94a3b8'
}

// 关系线样式配置 - 增强可见性
const LINK_STYLES = {
  default: {
    stroke: '#ff6b6b', // 醒目的红色
    strokeWidth: 3,    // 加粗到3px
    strokeOpacity: 0.9 // 增加不透明度
  },
  hover: {
    stroke: '#ff4757', // 悬停时更深的红色
    strokeWidth: 5,    // 悬停时更粗
    strokeOpacity: 1
  },
  dimmed: {
    stroke: '#94a3b8',
    strokeWidth: 1,
    strokeOpacity: 0.2
  }
}

export function NetworkGraph({
  nodes,
  links,
  width = 900,
  height = 600,
  onNodeClick,
  selectedNode,
  showAllLinks: externalShowAllLinks,
  onToggleLinks,
  debug = false
}: NetworkGraphProps) {
  const svgRef = useRef<SVGSVGElement>(null)
  const [hoveredNode, setHoveredNode] = useState<Node | null>(null)
  const [hoveredLink, setHoveredLink] = useState<Link | null>(null)
  const [transform, setTransform] = useState<d3.ZoomTransform>(d3.zoomIdentity)
  const [internalShowAllLinks, setInternalShowAllLinks] = useState(true)
  
  // 优先使用外部传入的状态
  const showAllLinks = externalShowAllLinks !== undefined ? externalShowAllLinks : internalShowAllLinks
  
  const linkElementsRef = useRef<d3.Selection<SVGLineElement, Link, SVGGElement, unknown> | null>(null)
  const linkLabelElementsRef = useRef<d3.Selection<SVGTextElement, Link, SVGGElement, unknown> | null>(null)

  // 切换关系线显示状态
  const toggleLinksVisibility = useCallback(() => {
    if (onToggleLinks) {
      onToggleLinks()
    } else {
      setInternalShowAllLinks(prev => !prev)
    }
  }, [onToggleLinks])

  useEffect(() => {
    if (!svgRef.current || nodes.length === 0) return

    // Debug output
    if (debug) {
      console.log('NetworkGraph Debug:', {
        nodesCount: nodes.length,
        linksCount: links.length,
        nodeIds: nodes.map(n => n.id).slice(0, 10),
        linksSample: links.slice(0, 3)
      })
    }

    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // 创建容器组
    const g = svg.append('g')

    // 缩放功能
    const zoom = d3.zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform.toString())
        setTransform(event.transform)
      })

    svg.call(zoom)

    // 准备数据 - 确保ID是字符串
    const nodeData = nodes.map(n => ({ ...n, id: String(n.id) }))
    const nodeIds = new Set(nodeData.map(n => n.id))

    // 过滤掉无效的连线（source或target节点不存在）
    const linkData = links
      .map(l => ({
        ...l,
        source: String(l.source),
        target: String(l.target)
      }))
      .filter(l => nodeIds.has(l.source) && nodeIds.has(l.target))

    // Debug output after filtering
    if (debug) {
      console.log('After filtering:', {
        nodeIdsSize: nodeIds.size,
        linkDataCount: linkData.length,
        filteredOut: links.length - linkData.length,
        missingSource: links.filter(l => !nodeIds.has(String(l.source))).length,
        missingTarget: links.filter(l => !nodeIds.has(String(l.target))).length
      })
    }

    // 创建力导向模拟
    const simulation = d3.forceSimulation<Node>(nodeData)
      .force('link', d3.forceLink<Node, Link>(linkData as any)
        .id((d: any) => d.id)
        .distance(120)
        .strength(0.5)
      )
      .force('charge', d3.forceManyBody().strength(-500))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collision', d3.forceCollide().radius(50))

    // 绘制连线（在节点之前绘制，确保线在节点下层）
    const linkGroup = g.append('g').attr('class', 'links')
    const link = linkGroup.selectAll('line')
      .data(linkData)
      .enter()
      .append('line')
      .attr('stroke', LINK_STYLES.default.stroke)
      .attr('stroke-width', LINK_STYLES.default.strokeWidth)
      .attr('stroke-opacity', showAllLinks ? LINK_STYLES.default.strokeOpacity : 0)
      .attr('stroke-linecap', 'round')
      .style('cursor', 'pointer')
      .style('transition', 'all 0.2s ease')
      .on('mouseenter', function(_event, d) {
        if (!showAllLinks) return
        setHoveredLink(d)
        d3.select(this)
          .attr('stroke', LINK_STYLES.hover.stroke)
          .attr('stroke-width', LINK_STYLES.hover.strokeWidth)
          .attr('stroke-opacity', LINK_STYLES.hover.strokeOpacity)
      })
      .on('mouseleave', function() {
        if (!showAllLinks) return
        setHoveredLink(null)
        d3.select(this)
          .attr('stroke', LINK_STYLES.default.stroke)
          .attr('stroke-width', LINK_STYLES.default.strokeWidth)
          .attr('stroke-opacity', LINK_STYLES.default.strokeOpacity)
      })

    linkElementsRef.current = link

    // 连线标签
    const linkLabelGroup = g.append('g').attr('class', 'link-labels')
    const linkLabel = linkLabelGroup.selectAll('text')
      .data(linkData)
      .enter()
      .append('text')
      .attr('font-size', '12px')
      .attr('fill', '#475569')
      .attr('text-anchor', 'middle')
      .attr('dy', -8)
      .attr('font-weight', '500')
      .style('pointer-events', 'none')
      .style('opacity', showAllLinks ? 1 : 0)
      .style('transition', 'opacity 0.2s ease')
      .style('text-shadow', '0 1px 2px rgba(255,255,255,0.8)')
      .text((d: any) => d.relation)

    linkLabelElementsRef.current = linkLabel

    // 绘制节点组
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const node = nodeGroup.selectAll('g')
      .data(nodeData)
      .enter()
      .append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(d3.drag<SVGGElement, Node>()
        .on('start', (event: any, d: Node) => {
          if (!event.active) simulation.alphaTarget(0.3).restart()
          d.fx = d.x
          d.fy = d.y
        })
        .on('drag', (event: any, d: Node) => {
          d.fx = event.x
          d.fy = event.y
        })
        .on('end', (_event: any, d: Node) => {
          if (!_event.active) simulation.alphaTarget(0)
          d.fx = null
          d.fy = null
        })
      )
      .on('click', (event, d) => {
        event.stopPropagation()
        onNodeClick?.(d)
      })
      .on('mouseenter', (_event, d) => setHoveredNode(d))
      .on('mouseleave', () => setHoveredNode(null))

    // 节点外圈（选中状态）
    node.append('circle')
      .attr('r', 28)
      .attr('fill', 'none')
      .attr('stroke', (d: Node) => selectedNode === d.id ? '#f59e0b' : 'none')
      .attr('stroke-width', 3)

    // 节点圆形
    node.append('circle')
      .attr('r', 22)
      .attr('fill', (d: Node) => typeColors[d.type] || typeColors.default)
      .attr('stroke', '#fff')
      .attr('stroke-width', 3)
      .style('filter', 'drop-shadow(0 4px 6px rgba(0,0,0,0.1))')

    // 节点图标/首字母
    node.append('text')
      .attr('dy', '0.35em')
      .attr('text-anchor', 'middle')
      .attr('fill', '#fff')
      .attr('font-size', '14px')
      .attr('font-weight', 'bold')
      .text((d: Node) => {
        const icons: Record<string, string> = {
          'person': '👤',
          'org': '🏢',
          'product': '📦',
          'project': '📁',
          'group': '👥',
          'event': '📅'
        }
        return icons[d.type] || d.name.charAt(0).toUpperCase()
      })

    // 节点名称标签
    node.append('text')
      .attr('dy', 40)
      .attr('text-anchor', 'middle')
      .attr('fill', '#334155')
      .attr('font-size', '12px')
      .attr('font-weight', '500')
      .style('pointer-events', 'none')
      .text((d: Node) => d.name.length > 10 ? d.name.slice(0, 10) + '...' : d.name)

    // 节点类型标签
    node.append('text')
      .attr('dy', 54)
      .attr('text-anchor', 'middle')
      .attr('fill', '#64748b')
      .attr('font-size', '10px')
      .style('pointer-events', 'none')
      .text((d: Node) => d.type)

    // 更新位置
    simulation.on('tick', () => {
      link
        .attr('x1', (d: any) => (d.source as Node).x!)
        .attr('y1', (d: any) => (d.source as Node).y!)
        .attr('x2', (d: any) => (d.target as Node).x!)
        .attr('y2', (d: any) => (d.target as Node).y!)

      linkLabel
        .attr('x', (d: any) => ((d.source as Node).x! + (d.target as Node).x!) / 2)
        .attr('y', (d: any) => ((d.source as Node).y! + (d.target as Node).y!) / 2)

      node.attr('transform', (d: Node) => `translate(${d.x},${d.y})`)
    })

    return () => {
      simulation.stop()
    }
  }, [nodes, links, width, height, selectedNode, showAllLinks])

  return (
    <div style={{ position: 'relative' }}>
      <svg
        ref={svgRef}
        width={width}
        height={height}
        style={{
          background: 'linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%)',
          borderRadius: '16px',
          cursor: 'grab'
        }}
      />
      
      {/* 悬浮提示 - 节点 */}
      {hoveredNode && (
        <div style={{
          position: 'absolute',
          top: 10,
          left: 10,
          background: 'rgba(255,255,255,0.95)',
          padding: '16px',
          borderRadius: '12px',
          boxShadow: '0 10px 40px rgba(0,0,0,0.15)',
          maxWidth: '280px',
          zIndex: 100
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '10px',
            marginBottom: '8px'
          }}>
            <div style={{
              width: '12px',
              height: '12px',
              borderRadius: '50%',
              background: typeColors[hoveredNode.type] || typeColors.default
            }} />
            <strong style={{ fontSize: '16px' }}>{hoveredNode.name}</strong>
          </div>
          <div style={{ color: '#64748b', fontSize: '13px', marginBottom: '4px' }}>
            类型: {hoveredNode.type}
          </div>
          {hoveredNode.description && (
            <div style={{ color: '#475569', fontSize: '12px', marginTop: '8px' }}>
              {hoveredNode.description}
            </div>
          )}
        </div>
      )}

      {/* 悬浮提示 - 关系线 */}
      {hoveredLink && showAllLinks && (
        <div style={{
          position: 'absolute',
          top: 10,
          right: 10,
          background: 'rgba(255,255,255,0.95)',
          padding: '12px 16px',
          borderRadius: '8px',
          boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
          zIndex: 100
        }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            gap: '8px'
          }}>
            <div style={{
              width: '20px',
              height: '3px',
              background: LINK_STYLES.hover.stroke,
              borderRadius: '2px'
            }} />
            <span style={{ fontSize: '14px', fontWeight: '500' }}>
              {(hoveredLink.source as unknown as Node).name} → {(hoveredLink.target as unknown as Node).name}
            </span>
          </div>
          <div style={{ color: '#64748b', fontSize: '12px', marginTop: '4px', marginLeft: '28px' }}>
            关系: {hoveredLink.relation}
          </div>
        </div>
      )}

      {/* 显示/隐藏关系按钮 - 右上角 */}
      <div style={{
        position: 'absolute',
        top: 20,
        right: 20,
        zIndex: 50
      }}>
        <button
          onClick={toggleLinksVisibility}
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 16px',
            borderRadius: '10px',
            border: 'none',
            background: showAllLinks ? '#3b82f6' : '#94a3b8',
            color: '#fff',
            fontSize: '14px',
            fontWeight: '500',
            cursor: 'pointer',
            boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
            transition: 'all 0.2s ease'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'translateY(-2px)'
            e.currentTarget.style.boxShadow = '0 6px 16px rgba(0,0,0,0.2)'
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'translateY(0)'
            e.currentTarget.style.boxShadow = '0 4px 12px rgba(0,0,0,0.15)'
          }}
        >
          <svg 
            width="16" 
            height="16" 
            viewBox="0 0 24 24" 
            fill="none" 
            stroke="currentColor" 
            strokeWidth="2" 
            strokeLinecap="round" 
            strokeLinejoin="round"
            style={{
              opacity: showAllLinks ? 1 : 0.7,
              transform: showAllLinks ? 'rotate(0deg)' : 'rotate(90deg)',
              transition: 'all 0.3s ease'
            }}
          >
            <line x1="6" y1="12" x2="18" y2="12"></line>
            {showAllLinks && (
              <>
                <line x1="12" y1="6" x2="12" y2="18"></line>
                <circle cx="12" cy="12" r="3"></circle>
              </>
            )}
          </svg>
          {showAllLinks ? '隐藏关系线' : '显示关系线'}
        </button>
      </div>

      {/* 图例 - 调整位置，在按钮下方 */}
      <div style={{
        position: 'absolute',
        top: 70,
        right: 20,
        background: 'rgba(255,255,255,0.95)',
        padding: '16px',
        borderRadius: '12px',
        boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
        zIndex: 40
      }}>
        <div style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px' }}>
          实体类型
        </div>
        {Object.entries(typeColors).filter(([k]) => k !== 'default').map(([type, color]) => (
          <div key={type} style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
            <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: color }} />
            <span style={{ fontSize: '12px', textTransform: 'capitalize' }}>{type}</span>
          </div>
        ))}
      </div>

      {/* 缩放控制 */}
      <div style={{
        position: 'absolute',
        bottom: 20,
        right: 20,
        display: 'flex',
        gap: '8px'
      }}>
        <button
          onClick={() => {
            const svg = d3.select(svgRef.current)
            svg.transition().call(
              (d3.zoom() as any).transform,
              transform.scale(1.2)
            )
          }}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            border: 'none',
            background: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            cursor: 'pointer',
            fontSize: '18px'
          }}
        >
          +
        </button>
        {/* 显示/隐藏所有关系按钮 */}
        <button
          onClick={toggleLinksVisibility}
          title={showAllLinks ? "隐藏所有关系" : "显示所有关系"}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            border: 'none',
            background: showAllLinks ? '#ff6b6b' : '#4CAF50',
            color: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
            cursor: 'pointer',
            fontSize: '20px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          {showAllLinks ? '🔗' : '🔒'}
        </button>
        <button
          onClick={() => {
            const svg = d3.select(svgRef.current)
            svg.transition().call(
              (d3.zoom() as any).transform,
              d3.zoomIdentity
            )
          }}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            border: 'none',
            background: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            cursor: 'pointer',
            fontSize: '14px'
          }}
        >
          ⌂
        </button>
        <button
          onClick={() => {
            const svg = d3.select(svgRef.current)
            svg.transition().call(
              (d3.zoom() as any).transform,
              transform.scale(0.8)
            )
          }}
          style={{
            width: '36px',
            height: '36px',
            borderRadius: '8px',
            border: 'none',
            background: '#fff',
            boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
            cursor: 'pointer',
            fontSize: '18px'
          }}
        >
          −
        </button>
      </div>
    </div>
  )
}
