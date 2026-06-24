import React from 'react';

interface SdsArchDiagramProps {
  style?: React.CSSProperties;
}

const SdsArchDiagram: React.FC<SdsArchDiagramProps> = ({ style }) => {
  const [hovered, setHovered] = React.useState<string | null>(null);

  return (
    <svg
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 1000 520"
      style={{ width: '100%', maxWidth: '1000px', height: 'auto', ...style }}
    >
      <defs>
        <marker id="arrow-blue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#2563eb"/>
        </marker>
        <marker id="arrow-orange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#ea580c"/>
        </marker>
        <marker id="arrow-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#059669"/>
        </marker>
        <marker id="arrow-purple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
        </marker>
        <marker id="arrow-gray" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
          <polygon points="0 0, 10 3.5, 0 7" fill="#6b7280"/>
        </marker>
        <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15"/>
        </filter>
      </defs>

      {/* Background */}
      <rect width="1000" height="520" fill="#fafafa"/>

      {/* Title */}
      <text x="500" y="30" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="20" fontWeight="600" fill="#1f2937">
        SDS 自我驱动系统架构
      </text>

      {/* Container: Core Layer */}
      <rect x="50" y="170" width="900" height="100" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
      <text x="70" y="190" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#6b7280">核心处理层</text>

      {/* Container: Data Layer */}
      <rect x="50" y="370" width="900" height="100" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
      <text x="70" y="390" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#6b7280">数据层</text>

      {/* User */}
      <circle cx="500" cy="60" r="20" fill="#dbeafe" stroke={hovered === 'user' ? '#1d4ed8' : '#3b82f6'} strokeWidth="2" filter="url(#shadow)"
        onMouseEnter={() => setHovered('user')} onMouseLeave={() => setHovered(null)}
        style={{ cursor: 'pointer', transition: 'stroke 0.2s' }}/>
      <text x="500" y="65" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#1e40af">用户</text>

      {/* Main Loop */}
      <rect x="420" y="105" width="160" height="50" rx="8" fill={hovered === 'main' ? '#fde68a' : '#fef3c7'} stroke={hovered === 'main' ? '#d97706' : '#f59e0b'} strokeWidth="2" filter="url(#shadow)"
        onMouseEnter={() => setHovered('main')} onMouseLeave={() => setHovered(null)}
        style={{ cursor: 'pointer', transition: 'fill 0.2s, stroke 0.2s' }}/>
      <text x="500" y="128" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fontWeight="600" fill="#92400e">sds_main.py</text>
      <text x="500" y="142" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#92400e">主循环</text>

      {/* Core Layer Nodes */}
      {[
        { id: 'analyzer', x: 60, y: 200, w: 120, h: 50, name: 'TaskAnalyzer', desc: '任务分析', color: '#e0e7ff', stroke: '#6366f1', text: '#3730a3' },
        { id: 'generator', x: 260, y: 200, w: 120, h: 50, name: 'AutoTaskGenerator', desc: '任务生成', color: '#e0e7ff', stroke: '#6366f1', text: '#3730a3' },
        { id: 'scheduler', x: 620, y: 200, w: 120, h: 50, name: 'SubagentScheduler', desc: '子代理调度', color: '#e0e7ff', stroke: '#6366f1', text: '#3730a3' },
        { id: 'verifier', x: 820, y: 200, w: 120, h: 50, name: 'ResultCollector', desc: '结果验证', color: '#e0e7ff', stroke: '#6366f1', text: '#3730a3' },
      ].map(n => (
        <g key={n.id}
          onMouseEnter={() => setHovered(n.id)}
          onMouseLeave={() => setHovered(null)}
          style={{ cursor: 'pointer' }}
        >
          <rect x={n.x} y={n.y} width={n.w} height={n.h} rx="6"
            fill={hovered === n.id ? '#c7d2fe' : n.color}
            stroke={hovered === n.id ? '#4f46e5' : n.stroke} strokeWidth="2"
            filter="url(#shadow)"
          />
          <text x={n.x + n.w/2} y={n.y + 20} textAnchor="middle" fontFamily="system-ui" fontSize="11" fontWeight="600" fill={n.text}>
            {n.name}
          </text>
          <text x={n.x + n.w/2} y={n.y + 35} textAnchor="middle" fontFamily="system-ui" fontSize="10" fill={n.text}>
            {n.desc}
          </text>
        </g>
      ))}

      {/* Guard (hexagon) */}
      <g onMouseEnter={() => setHovered('guard')} onMouseLeave={() => setHovered(null)} style={{ cursor: 'pointer' }}>
        <polygon points="440,200 500,175 560,200 560,250 500,275 440,250"
          fill={hovered === 'guard' ? '#fde68a' : '#fef3c7'}
          stroke={hovered === 'guard' ? '#d97706' : '#f59e0b'} strokeWidth="2" filter="url(#shadow)"/>
        <text x="500" y="210" textAnchor="middle" fontFamily="system-ui" fontSize="11" fontWeight="600" fill="#92400e">Guard V48</text>
        <text x="500" y="225" textAnchor="middle" fontFamily="system-ui" fontSize="10" fill="#92400e">三重保障</text>
      </g>

      {/* Data Layer Nodes */}
      {/* LLM */}
      <g onMouseEnter={() => setHovered('llm')} onMouseLeave={() => setHovered(null)} style={{ cursor: 'pointer' }}>
        <rect x="260" y="300" width="120" height="50" rx="25"
          fill={hovered === 'llm' ? '#ddd6fe' : '#ede9fe'}
          stroke={hovered === 'llm' ? '#7c3aed' : '#8b5cf6'} strokeWidth="2" filter="url(#shadow)"/>
        <text x="320" y="325" textAnchor="middle" fontFamily="system-ui" fontSize="11" fontWeight="600" fill="#5b21b6">LLM Client</text>
        <text x="320" y="340" textAnchor="middle" fontFamily="system-ui" fontSize="10" fill="#5b21b6">统一调用</text>
      </g>

      {/* Subagent */}
      <g onMouseEnter={() => setHovered('subagent')} onMouseLeave={() => setHovered(null)} style={{ cursor: 'pointer' }}>
        <rect x="620" y="300" width="120" height="50" rx="6"
          fill={hovered === 'subagent' ? '#a7f3d0' : '#d1fae5'}
          stroke={hovered === 'subagent' ? '#059669' : '#10b981'} strokeWidth="2" filter="url(#shadow)"/>
        <text x="680" y="320" textAnchor="middle" fontFamily="system-ui" fontSize="11" fontWeight="600" fill="#065f46">Subagent Executor</text>
        <text x="680" y="335" textAnchor="middle" fontFamily="system-ui" fontSize="10" fill="#065f46">子代理执行器</text>
      </g>

      {/* DB */}
      <g onMouseEnter={() => setHovered('db')} onMouseLeave={() => setHovered(null)} style={{ cursor: 'pointer' }}>
        <ellipse cx="120" cy="400" rx="60" ry="20" fill="#dbeafe" stroke={hovered === 'db' ? '#2563eb' : '#3b82f6'} strokeWidth="2"/>
        <path d="M60,400 L60,440 C60,455 90,460 120,460 C150,460 180,455 180,440 L180,400 C180,415 150,420 120,420 C90,420 60,415 60,400 Z"
          fill={hovered === 'db' ? '#bfdbfe' : '#dbeafe'}
          stroke={hovered === 'db' ? '#2563eb' : '#3b82f6'} strokeWidth="2" filter="url(#shadow)"/>
        <text x="120" y="435" textAnchor="middle" fontFamily="system-ui" fontSize="10" fontWeight="600" fill="#1e40af">看板数据库</text>
      </g>

      {/* Config */}
      <g onMouseEnter={() => setHovered('config')} onMouseLeave={() => setHovered(null)} style={{ cursor: 'pointer' }}>
        <rect x="260" y="400" width="120" height="50" rx="4"
          fill={hovered === 'config' ? '#fbcfe8' : '#fce7f3'}
          stroke={hovered === 'config' ? '#db2777' : '#ec4899'} strokeWidth="2" filter="url(#shadow)"/>
        <path d="M260,405 L270,405 L275,415 L265,415 Z" fill="#ec4899"/>
        <text x="320" y="425" textAnchor="middle" fontFamily="system-ui" fontSize="10" fontWeight="600" fill="#9d174d">配置中心</text>
        <text x="320" y="440" textAnchor="middle" fontFamily="system-ui" fontSize="9" fill="#9d174d">llm_providers.json</text>
      </g>

      {/* Dashboard */}
      <g onMouseEnter={() => setHovered('dashboard')} onMouseLeave={() => setHovered(null)} style={{ cursor: 'pointer' }}>
        <rect x="820" y="400" width="120" height="50" rx="4"
          fill={hovered === 'dashboard' ? '#e9d5ff' : '#f3e8ff'}
          stroke={hovered === 'dashboard' ? '#9333ea' : '#a855f7'} strokeWidth="2" filter="url(#shadow)"/>
        <rect x="830" y="408" width="100" height="6" fill="#a855f7" opacity="0.3" rx="2"/>
        <circle cx="840" cy="411" r="1.5" fill="#a855f7"/>
        <circle cx="847" cy="411" r="1.5" fill="#a855f7"/>
        <circle cx="854" cy="411" r="1.5" fill="#a855f7"/>
        <text x="880" y="430" textAnchor="middle" fontFamily="system-ui" fontSize="11" fontWeight="600" fill="#6b21a8">仪表盘</text>
        <text x="880" y="442" textAnchor="middle" fontFamily="system-ui" fontSize="9" fill="#6b21a8">可观测性</text>
      </g>

      {/* Arrows */}
      <line x1="500" y1="80" x2="500" y2="105" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrow-blue)"/>
      <text x="515" y="95" fontFamily="system-ui" fontSize="9" fill="#2563eb">触发/查询</text>

      <line x1="460" y1="155" x2="120" y2="200" stroke="#ea580c" strokeWidth="1.5" markerEnd="url(#arrow-orange)"/>
      <text x="130" y="180" fontFamily="system-ui" fontSize="8" fill="#ea580c">每3600s</text>
      <line x1="470" y1="155" x2="320" y2="200" stroke="#ea580c" strokeWidth="1.5" markerEnd="url(#arrow-orange)"/>
      <text x="330" y="180" fontFamily="system-ui" fontSize="8" fill="#ea580c">每3600s</text>
      <line x1="500" y1="155" x2="500" y2="175" stroke="#ea580c" strokeWidth="1.5" markerEnd="url(#arrow-orange)"/>
      <text x="510" y="170" fontFamily="system-ui" fontSize="8" fill="#ea580c">每周期</text>
      <line x1="530" y1="155" x2="680" y2="200" stroke="#ea580c" strokeWidth="1.5" markerEnd="url(#arrow-orange)"/>
      <text x="640" y="180" fontFamily="system-ui" fontSize="8" fill="#ea580c">每300s</text>
      <line x1="540" y1="155" x2="880" y2="200" stroke="#ea580c" strokeWidth="1.5" markerEnd="url(#arrow-orange)"/>
      <text x="800" y="180" fontFamily="system-ui" fontSize="8" fill="#ea580c">每300s</text>

      <line x1="120" y1="250" x2="120" y2="380" stroke="#059669" strokeWidth="1.5" markerEnd="url(#arrow-green)"/>
      <text x="85" y="320" fontFamily="system-ui" fontSize="8" fill="#059669">读取/写入</text>

      <line x1="320" y1="250" x2="320" y2="300" stroke="#7c3aed" strokeWidth="1.5" markerEnd="url(#arrow-purple)"/>
      <text x="330" y="278" fontFamily="system-ui" fontSize="8" fill="#7c3aed">生成请求</text>
      <line x1="300" y1="300" x2="300" y2="250" stroke="#7c3aed" strokeWidth="1.5" markerEnd="url(#arrow-purple)"/>
      <text x="260" y="278" fontFamily="system-ui" fontSize="8" fill="#7c3aed">推荐任务</text>

      <line x1="380" y1="225" x2="440" y2="225" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrow-blue)"/>
      <text x="395" y="220" fontFamily="system-ui" fontSize="8" fill="#2563eb">待创建</text>
      <line x1="560" y1="225" x2="620" y2="225" stroke="#059669" strokeWidth="2" markerEnd="url(#arrow-green)"/>
      <text x="580" y="220" fontFamily="system-ui" fontSize="8" fill="#059669">通过</text>

      <line x1="680" y1="250" x2="680" y2="300" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrow-blue)"/>
      <text x="690" y="278" fontFamily="system-ui" fontSize="8" fill="#2563eb">分配任务</text>

      <line x1="620" y1="325" x2="180" y2="420" stroke="#059669" strokeWidth="1.5" strokeDasharray="5,3" markerEnd="url(#arrow-green)"/>
      <text x="380" y="380" fontFamily="system-ui" fontSize="8" fill="#059669">更新状态</text>

      <line x1="180" y1="420" x2="820" y2="225" stroke="#059669" strokeWidth="1.5" markerEnd="url(#arrow-green)"/>
      <text x="500" y="340" fontFamily="system-ui" fontSize="8" fill="#059669">执行结果</text>

      <line x1="880" y1="250" x2="880" y2="400" stroke="#6b7280" strokeWidth="1.5" strokeDasharray="4,2" markerEnd="url(#arrow-gray)"/>
      <text x="890" y="330" fontFamily="system-ui" fontSize="8" fill="#6b7280">更新状态</text>

      <line x1="320" y1="400" x2="320" y2="350" stroke="#6b7280" strokeWidth="1.5" strokeDasharray="4,2" markerEnd="url(#arrow-gray)"/>
      <text x="330" y="380" fontFamily="system-ui" fontSize="8" fill="#6b7280">模型配置</text>

      {/* Legend */}
      <rect x="50" y="480" width="900" height="30" fill="#ffffff" stroke="#e5e7eb" strokeWidth="1" rx="4"/>
      <text x="60" y="498" fontFamily="system-ui" fontSize="10" fontWeight="600" fill="#374151">图例:</text>
      <line x1="100" y1="495" x2="130" y2="495" stroke="#2563eb" strokeWidth="2"/>
      <polygon points="130,492 140,495 130,498" fill="#2563eb"/>
      <text x="145" y="498" fontFamily="system-ui" fontSize="9" fill="#4b5563">主数据流</text>

      <line x1="210" y1="495" x2="240" y2="495" stroke="#ea580c" strokeWidth="1.5"/>
      <polygon points="240,492 250,495 240,498" fill="#ea580c"/>
      <text x="255" y="498" fontFamily="system-ui" fontSize="9" fill="#4b5563">控制/触发</text>

      <line x1="320" y1="495" x2="350" y2="495" stroke="#059669" strokeWidth="1.5"/>
      <polygon points="350,492 360,495 350,498" fill="#059669"/>
      <text x="365" y="498" fontFamily="system-ui" fontSize="9" fill="#4b5563">数据读取</text>

      <line x1="430" y1="495" x2="460" y2="495" stroke="#059669" strokeWidth="1.5" strokeDasharray="5,3"/>
      <polygon points="460,492 470,495 460,498" fill="#059669"/>
      <text x="475" y="498" fontFamily="system-ui" fontSize="9" fill="#4b5563">数据写入</text>

      <line x1="540" y1="495" x2="570" y2="495" stroke="#7c3aed" strokeWidth="1.5"/>
      <polygon points="570,492 580,495 570,498" fill="#7c3aed"/>
      <text x="585" y="498" fontFamily="system-ui" fontSize="9" fill="#4b5563">LLM调用</text>

      <line x1="650" y1="495" x2="680" y2="495" stroke="#6b7280" strokeWidth="1.5" strokeDasharray="4,2"/>
      <polygon points="680,492 690,495 680,498" fill="#6b7280"/>
      <text x="695" y="498" fontFamily="system-ui" fontSize="9" fill="#4b5563">异步事件</text>
    </svg>
  );
};

export default SdsArchDiagram;
