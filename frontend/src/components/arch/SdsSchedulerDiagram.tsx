import React from 'react';

interface SdsSchedulerDiagramProps {
  style?: React.CSSProperties;
}

const SdsSchedulerDiagram: React.FC<SdsSchedulerDiagramProps> = ({ style }) => {
  const [hovered, setHovered] = React.useState<string | null>(null);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 550" style={{ width: '100%', maxWidth: '1000px', height: 'auto', ...style }}>

  <defs>

    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15"/>
    </filter>


    <marker id="arrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#64748b"/>
    </marker>
    <marker id="arrowBlue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#2563eb"/>
    </marker>
    <marker id="arrowGreen" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#059669"/>
    </marker>
    <marker id="arrowPurple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
    </marker>
    <marker id="arrowOrange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#ea580c"/>
    </marker>


    <polygon id="hexagon" points="0,-25 21.65,-12.5 21.65,12.5 0,25 -21.65,12.5 -21.65,-12.5"/>
  </defs>

  <style>{`
text { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    .title { font-size: 22px; font-weight: 700; fill: #1e293b; }
    .layer-label { font-size: 13px; font-weight: 600; fill: #64748b; }
    .node-label { font-size: 12px; font-weight: 600; fill: #1e293b; }
    .sub-label { font-size: 10px; font-weight: 400; fill: #64748b; }
    .arrow-label { font-size: 10px; font-weight: 500; fill: #475569; }
    .legend-label { font-size: 11px; font-weight: 400; fill: #475569; }
`}</style>


  <rect width="1000" height="550" fill="#fafafa"/>


  <text x="500" y="35" textAnchor="middle" className="title">SDS调度 (SdsTab) 系统架构</text>




  <g transform="translate(0, 60)">
    <rect x="20" y="0" width="960" height="75" rx="8" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3"/>
    <text x="35" y="20" className="layer-label">1. 触发层</text>


    <rect x="60" y="35" width="100" height="30" rx="6" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1" filter="url(#shadow)"/>
    <text x="110" y="55" textAnchor="middle" className="node-label">用户触发</text>


    <rect x="200" y="35" width="140" height="30" rx="6" fill="#dcfce7" stroke="#22c55e" strokeWidth="1" filter="url(#shadow)"/>
    <text x="270" y="55" textAnchor="middle" className="node-label">Cron定时</text>
    <text x="270" y="68" textAnchor="middle" className="sub-label">10个cron任务, 每10s扫描</text>


    <rect x="380" y="35" width="100" height="30" rx="6" fill="#fef3c7" stroke="#f59e0b" strokeWidth="1" filter="url(#shadow)"/>
    <text x="430" y="55" textAnchor="middle" className="node-label">事件触发</text>
  </g>


  <g transform="translate(0, 150)">
    <rect x="20" y="0" width="960" height="95" rx="8" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3"/>
    <text x="35" y="20" className="layer-label">2. 调度核心</text>


    <rect x="60" y="35" width="120" height="45" rx="6" fill="#e0e7ff" stroke="#6366f1" strokeWidth="1.5" filter="url(#shadow)"/>
    <text x="120" y="55" textAnchor="middle" className="node-label">任务调度器</text>
    <text x="120" y="70" textAnchor="middle" className="sub-label">orchestrator</text>
    <text x="120" y="82" textAnchor="middle" className="sub-label">优先级 P1→P9</text>


    <rect x="220" y="35" width="120" height="45" rx="6" fill="#fce7f3" stroke="#ec4899" strokeWidth="1" filter="url(#shadow)"/>
    <text x="280" y="55" textAnchor="middle" className="node-label">依赖检查</text>
    <text x="280" y="70" textAnchor="middle" className="sub-label">上下游依赖</text>
    <text x="280" y="82" textAnchor="middle" className="sub-label">自动激活/阻塞</text>


    <g transform="translate(420, 57.5)">
      <polygon points="0,-28 24.25,-14 24.25,14 0,28 -24.25,14 -24.25,-14" fill="#fef3c7" stroke="#d97706" strokeWidth="1.5" filter="url(#shadow)"/>
      <text x="0" y="-5" textAnchor="middle" className="node-label">Guard V48</text>
      <text x="0" y="10" textAnchor="middle" className="sub-label">质量/安全/防循环</text>
    </g>
  </g>


  <g transform="translate(0, 260)">
    <rect x="20" y="0" width="960" height="95" rx="8" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3"/>
    <text x="35" y="20" className="layer-label">3. 执行层</text>


    <rect x="60" y="35" width="130" height="45" rx="6" fill="#dbeafe" stroke="#2563eb" strokeWidth="1" filter="url(#shadow)"/>
    <text x="125" y="55" textAnchor="middle" className="node-label">子代理执行器</text>
    <text x="125" y="70" textAnchor="middle" className="sub-label">isolated会话</text>
    <text x="125" y="82" textAnchor="middle" className="sub-label">互不干扰</text>


    <rect x="230" y="35" width="110" height="45" rx="6" fill="#dcfce7" stroke="#16a34a" strokeWidth="1" filter="url(#shadow)"/>
    <text x="285" y="55" textAnchor="middle" className="node-label">标准评估</text>
    <text x="285" y="70" textAnchor="middle" className="sub-label">13项测试任务</text>
    <text x="285" y="82" textAnchor="middle" className="sub-label">周期评分</text>


    <rect x="380" y="35" width="110" height="45" rx="6" fill="#fef3c7" stroke="#ca8a04" strokeWidth="1" filter="url(#shadow)"/>
    <text x="435" y="55" textAnchor="middle" className="node-label">审核巡逻</text>
    <text x="435" y="70" textAnchor="middle" className="sub-label">自动审核pending</text>
    <text x="435" y="82" textAnchor="middle" className="sub-label">状态一致性</text>
  </g>


  <g transform="translate(0, 370)">
    <rect x="20" y="0" width="960" height="75" rx="8" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3"/>
    <text x="35" y="20" className="layer-label">4. 数据层</text>


    <rect x="60" y="35" width="110" height="30" rx="6" fill="#ede9fe" stroke="#8b5cf6" strokeWidth="1" filter="url(#shadow)"/>
    <text x="115" y="55" textAnchor="middle" className="node-label">看板数据库</text>


    <rect x="210" y="35" width="100" height="30" rx="6" fill="#f3e8ff" stroke="#a855f7" strokeWidth="1" filter="url(#shadow)"/>
    <text x="260" y="55" textAnchor="middle" className="node-label">执行日志</text>
    <text x="260" y="68" textAnchor="middle" className="sub-label">execution_logs</text>


    <rect x="350" y="35" width="100" height="30" rx="6" fill="#fdf4ff" stroke="#c026d3" strokeWidth="1" filter="url(#shadow)"/>
    <text x="400" y="55" textAnchor="middle" className="node-label">结果摘要</text>
    <text x="400" y="68" textAnchor="middle" className="sub-label">result_summary</text>
  </g>


  <g transform="translate(0, 460)">
    <rect x="20" y="0" width="960" height="75" rx="8" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3"/>
    <text x="35" y="20" className="layer-label">5. 结果层</text>


    <rect x="60" y="35" width="110" height="30" rx="6" fill="#ccfbf1" stroke="#14b8a6" strokeWidth="1" filter="url(#shadow)"/>
    <text x="115" y="55" textAnchor="middle" className="node-label">结果验证</text>
    <text x="115" y="68" textAnchor="middle" className="sub-label">ResultCollector</text>


    <rect x="210" y="35" width="100" height="30" rx="6" fill="#cffafe" stroke="#06b6d4" strokeWidth="1" filter="url(#shadow)"/>
    <text x="260" y="55" textAnchor="middle" className="node-label">状态更新</text>
    <text x="260" y="68" textAnchor="middle" className="sub-label">DB入库</text>


    <rect x="350" y="35" width="100" height="30" rx="6" fill="#ecfeff" stroke="#0891b2" strokeWidth="1" filter="url(#shadow)"/>
    <text x="400" y="55" textAnchor="middle" className="node-label">审计追踪</text>
  </g>




  <line x1="270" y1="135" x2="270" y2="150" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arrow)"/>
  <text x="275" y="145" className="arrow-label">每10s</text>


  <line x1="180" y1="200" x2="220" y2="200" stroke="#2563eb" strokeWidth="1.5" markerEnd="url(#arrowBlue)"/>


  <line x1="340" y1="200" x2="396" y2="200" stroke="#7c3aed" strokeWidth="1.5" markerEnd="url(#arrowPurple)"/>


  <line x1="420" y1="245" x2="420" y2="260" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arrow)"/>
  <text x="425" y="255" className="arrow-label">spawn</text>


  <line x1="435" y1="355" x2="435" y2="370" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arrow)"/>
  <text x="440" y="365" className="arrow-label">每300s</text>


  <line x1="260" y1="445" x2="260" y2="460" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arrow)"/>


  <path d="M 460 490 Q 700 490 700 200 Q 700 200 445 200" stroke="#ea580c" strokeWidth="1.5" strokeDasharray="5,3" fill="none" markerEnd="url(#arrowOrange)"/>
  <text x="580" y="485" className="arrow-label" fill="#ea580c">状态反馈</text>


  <text x="520" y="200" className="arrow-label">扫描pending → 优先排序 → 依赖检查</text>
  <text x="560" y="310" className="arrow-label">执行+审计 → DB入库</text>


  <g transform="translate(600, 480)">
    <rect x="0" y="0" width="360" height="55" rx="6" fill="#ffffff" stroke="#e2e8f0" strokeWidth="1" filter="url(#shadow)"/>
    <text x="10" y="18" className="legend-label" fontWeight="600">图例</text>


    <rect x="10" y="28" width="20" height="12" rx="3" fill="#dbeafe" stroke="#3b82f6" strokeWidth="1"/>
    <text x="35" y="38" className="legend-label">组件</text>


    <polygon points="75,28 85,34 85,40 75,46 65,40 65,34" fill="#fef3c7" stroke="#d97706" strokeWidth="1"/>
    <text x="90" y="38" className="legend-label">Guard</text>


    <line x1="130" y1="37" x2="150" y2="37" stroke="#64748b" strokeWidth="1.5" markerEnd="url(#arrow)"/>
    <text x="155" y="40" className="legend-label">数据流</text>


    <line x1="200" y1="37" x2="220" y2="37" stroke="#ea580c" strokeWidth="1.5" strokeDasharray="3,2" markerEnd="url(#arrowOrange)"/>
    <text x="225" y="40" className="legend-label">反馈流</text>


    <rect x="270" y="28" width="20" height="12" rx="2" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="3,2"/>
    <text x="295" y="38" className="legend-label">层级</text>
  </g>


    </svg>
  );
};

export default SdsSchedulerDiagram;
