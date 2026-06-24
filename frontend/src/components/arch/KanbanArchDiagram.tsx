import React from 'react';

interface KanbanArchDiagramProps {
  style?: React.CSSProperties;
}

const KanbanArchDiagram: React.FC<KanbanArchDiagramProps> = ({ style }) => {
  const [hovered, setHovered] = React.useState<string | null>(null);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 600" style={{ width: '100%', maxWidth: '1000px', height: 'auto', ...style }}>

  <defs>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" floodColor="#000000" floodOpacity="0.15"/>
    </filter>
    <marker id="arrowBlue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#2563eb"/>
    </marker>
    <marker id="arrowOrange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#ea580c"/>
    </marker>
    <marker id="arrowGreen" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#059669"/>
    </marker>
    <marker id="arrowPurple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#7c3aed"/>
    </marker>
    <marker id="arrowGray" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
      <polygon points="0 0, 10 3.5, 0 7" fill="#64748b"/>
    </marker>
  </defs>
  <style>{`
text { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }
        .title { font-size: 22px; font-weight: 700; fill: #1e293b; }
        .layer-label { font-size: 14px; font-weight: 600; fill: #475569; }
        .node-label { font-size: 13px; font-weight: 600; fill: #1e293b; }
        .sub-label { font-size: 10px; font-weight: 400; fill: #64748b; }
        .arrow-label { font-size: 10px; font-weight: 400; fill: #475569; }
        .legend-text { font-size: 11px; font-weight: 400; fill: #475569; }
`}</style>
  <rect width="1000" height="600" fill="#fafafa"/>
  <text x="500" y="35" textAnchor="middle" className="title">看板全貌 (KanbanTab) 系统架构</text>
  <rect x="40" y="80" width="920" height="90" fill="#dbeafe" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3" rx="6"/>
  <text x="55" y="72" className="layer-label">前端层</text>
  <rect x="40" y="190" width="920" height="90" fill="#ffedd5" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3" rx="6"/>
  <text x="55" y="182" className="layer-label">后端层</text>
  <rect x="40" y="300" width="920" height="70" fill="#d1fae5" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3" rx="6"/>
  <text x="55" y="292" className="layer-label">通信层</text>
  <rect x="40" y="390" width="920" height="70" fill="#ede9fe" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3" rx="6"/>
  <text x="55" y="382" className="layer-label">数据层</text>
  <rect x="40" y="480" width="920" height="50" fill="#f1f5f9" stroke="#94a3b8" strokeWidth="1" strokeDasharray="5,3" rx="6"/>
  <text x="55" y="472" className="layer-label">守护层</text>
  <rect id="user" x="80" y="105" width="70" height="50" fill="#ffffff" stroke="#2563eb" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="115" y="127" textAnchor="middle" className="node-label">用户</text>
  <text x="115" y="142" textAnchor="middle" className="sub-label">Browser</text>
  <rect id="nginx" x="200" y="105" width="90" height="50" fill="#ffffff" stroke="#2563eb" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="245" y="127" textAnchor="middle" className="node-label">nginx</text>
  <text x="245" y="142" textAnchor="middle" className="sub-label">:443</text>
  <rect id="vite" x="340" y="105" width="100" height="50" fill="#ffffff" stroke="#2563eb" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="390" y="127" textAnchor="middle" className="node-label">Vite</text>
  <text x="390" y="142" textAnchor="middle" className="sub-label">dist/</text>
  <rect id="react" x="490" y="105" width="120" height="50" fill="#ffffff" stroke="#2563eb" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="550" y="127" textAnchor="middle" className="node-label">React SPA</text>
  <text x="550" y="142" textAnchor="middle" className="sub-label">KanbanTab</text>
  <rect id="sentry" x="680" y="105" width="100" height="50" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="730" y="127" textAnchor="middle" className="node-label">Sentry</text>
  <text x="730" y="142" textAnchor="middle" className="sub-label">错误监控</text>
  <rect id="health" x="830" y="105" width="110" height="50" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="885" y="127" textAnchor="middle" className="node-label">健康检查</text>
  <text x="885" y="142" textAnchor="middle" className="sub-label">/health</text>
  <rect id="flask" x="120" y="215" width="140" height="50" fill="#ffffff" stroke="#ea580c" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="190" y="237" textAnchor="middle" className="node-label">Flask API</text>
  <text x="190" y="252" textAnchor="middle" className="sub-label">:8086</text>
  <rect id="gunicorn" x="300" y="215" width="130" height="50" fill="#ffffff" stroke="#ea580c" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="365" y="237" textAnchor="middle" className="node-label">gunicorn</text>
  <text x="365" y="252" textAnchor="middle" className="sub-label">4 workers</text>
  <rect id="routes" x="470" y="215" width="140" height="50" fill="#ffffff" stroke="#ea580c" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="540" y="237" textAnchor="middle" className="node-label">routes/</text>
  <text x="540" y="252" textAnchor="middle" className="sub-label">35+ files</text>
  <rect id="eventlet" x="650" y="215" width="120" height="50" fill="#ffffff" stroke="#ea580c" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="710" y="237" textAnchor="middle" className="node-label">eventlet</text>
  <text x="710" y="252" textAnchor="middle" className="sub-label">async</text>
  <rect id="stats" x="820" y="215" width="120" height="50" fill="#ffffff" stroke="#ea580c" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="880" y="237" textAnchor="middle" className="node-label">9,554</text>
  <text x="880" y="252" textAnchor="middle" className="sub-label">lines</text>
  <rect id="socketio" x="200" y="315" width="130" height="40" fill="#ffffff" stroke="#059669" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="265" y="332" textAnchor="middle" className="node-label">SocketIO</text>
  <text x="265" y="347" textAnchor="middle" className="sub-label">:8085</text>
  <rect id="ws" x="400" y="315" width="140" height="40" fill="#ffffff" stroke="#059669" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="470" y="332" textAnchor="middle" className="node-label">WebSocket</text>
  <text x="470" y="347" textAnchor="middle" className="sub-label">实时推送</text>
  <rect id="eventlet2" x="600" y="315" width="130" height="40" fill="#ffffff" stroke="#059669" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="665" y="332" textAnchor="middle" className="node-label">eventlet</text>
  <text x="665" y="347" textAnchor="middle" className="sub-label">1 worker</text>
  <rect id="mysql" x="180" y="405" width="140" height="40" fill="#ffffff" stroke="#7c3aed" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="250" y="422" textAnchor="middle" className="node-label">MySQL RDS</text>
  <text x="250" y="437" textAnchor="middle" className="sub-label">阿里云</text>
  <rect id="dbconfig" x="380" y="405" width="160" height="40" fill="#ffffff" stroke="#7c3aed" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="460" y="422" textAnchor="middle" className="node-label">database_config</text>
  <text x="460" y="437" textAnchor="middle" className="sub-label">连接池</text>
  <rect id="supervisor" x="150" y="495" width="130" height="35" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="215" y="509" textAnchor="middle" className="node-label">supervisor</text>
  <text x="215" y="524" textAnchor="middle" className="sub-label">进程管理</text>
  <rect id="systemd" x="320" y="495" width="100" height="35" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="370" y="509" textAnchor="middle" className="node-label">systemd</text>
  <text x="370" y="524" textAnchor="middle" className="sub-label">服务</text>
  <rect id="kanban_api" x="460" y="495" width="110" height="35" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="515" y="509" textAnchor="middle" className="node-label">kanban-api</text>
  <text x="515" y="524" textAnchor="middle" className="sub-label">服务</text>
  <rect id="kanban_backend" x="610" y="495" width="130" height="35" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="675" y="509" textAnchor="middle" className="node-label">kanban-backend</text>
  <text x="675" y="524" textAnchor="middle" className="sub-label">服务</text>
  <rect id="monitor" x="780" y="495" width="130" height="35" fill="#ffffff" stroke="#64748b" strokeWidth="2" rx="8" filter="url(#shadow)"/>
  <text x="845" y="509" textAnchor="middle" className="node-label">monitor-relay</text>
  <text x="845" y="524" textAnchor="middle" className="sub-label">服务</text>
  <line x1="150" y1="130" x2="200" y2="130" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrowBlue)"/>
  <text x="175" y="125" textAnchor="middle" className="arrow-label" fill="#2563eb">HTTPS</text>
  <line x1="290" y1="130" x2="340" y2="130" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrowBlue)"/>
  <line x1="440" y1="130" x2="490" y2="130" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrowBlue)"/>
  <line x1="550" y1="155" x2="190" y2="215" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arrowBlue)"/>
  <text x="370" y="180" textAnchor="middle" className="arrow-label" fill="#2563eb">API</text>
  <line x1="260" y1="240" x2="300" y2="240" stroke="#ea580c" strokeWidth="2" markerEnd="url(#arrowOrange)"/>
  <line x1="430" y1="240" x2="470" y2="240" stroke="#ea580c" strokeWidth="2" markerEnd="url(#arrowOrange)"/>
  <line x1="430" y1="225" x2="650" y2="225" stroke="#ea580c" strokeWidth="2" markerEnd="url(#arrowOrange)"/>
  <line x1="610" y1="240" x2="820" y2="240" stroke="#ea580c" strokeWidth="2" markerEnd="url(#arrowOrange)"/>
  <line x1="190" y1="265" x2="265" y2="315" stroke="#059669" strokeWidth="2" markerEnd="url(#arrowGreen)"/>
  <text x="227" y="285" textAnchor="middle" className="arrow-label" fill="#059669">emit</text>
  <line x1="330" y1="335" x2="400" y2="335" stroke="#059669" strokeWidth="2" markerEnd="url(#arrowGreen)"/>
  <line x1="330" y1="320" x2="600" y2="320" stroke="#059669" strokeWidth="2" markerEnd="url(#arrowGreen)"/>
  <line x1="540" y1="325" x2="610" y2="155" stroke="#059669" strokeWidth="2" markerEnd="url(#arrowGreen)"/>
  <text x="575" y="235" textAnchor="middle" className="arrow-label" fill="#059669">push</text>
  <line x1="540" y1="265" x2="250" y2="405" stroke="#7c3aed" strokeWidth="2" markerEnd="url(#arrowPurple)"/>
  <text x="395" y="330" textAnchor="middle" className="arrow-label" fill="#7c3aed">SQL</text>
  <line x1="260" y1="265" x2="460" y2="405" stroke="#7c3aed" strokeWidth="2" markerEnd="url(#arrowPurple)"/>
  <line x1="380" y1="425" x2="320" y2="425" stroke="#7c3aed" strokeWidth="2" markerEnd="url(#arrowPurple)"/>
  <line x1="260" y1="190" x2="715" y2="155" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <text x="487" y="167" textAnchor="middle" className="arrow-label" fill="#64748b">report</text>
  <line x1="610" y1="130" x2="680" y2="130" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <line x1="835" y1="215" x2="835" y2="215" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <text x="835" y="210" textAnchor="middle" className="arrow-label" fill="#64748b">check</text>
  <line x1="880" y1="265" x2="880" y2="315" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <line x1="280" y1="512" x2="460" y2="512" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <line x1="280" y1="505" x2="610" y2="505" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <line x1="420" y1="512" x2="780" y2="512" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <line x1="515" y1="495" x2="190" y2="265" stroke="#64748b" strokeWidth="2" markerEnd="url(#arrowGray)"/>
  <line x1="675" y1="495" x2="330" y2="355" stroke="#059669" strokeWidth="2" markerEnd="url(#arrowGreen)"/>
  <rect x="150" y="545" width="700" height="30" fill="#ffffff" stroke="#94a3b8" strokeWidth="1" rx="4"/>
  <rect x="180" y="552" width="12" height="12" fill="#2563eb" rx="2"/>
  <text x="198" y="562" className="legend-text">请求/响应</text>
  <rect x="300" y="552" width="12" height="12" fill="#ea580c" rx="2"/>
  <text x="318" y="562" className="legend-text">代理/触发</text>
  <rect x="420" y="552" width="12" height="12" fill="#059669" rx="2"/>
  <text x="438" y="562" className="legend-text">WebSocket</text>
  <rect x="540" y="552" width="12" height="12" fill="#7c3aed" rx="2"/>
  <text x="558" y="562" className="legend-text">数据持久化</text>
  <rect x="660" y="552" width="12" height="12" fill="#64748b" rx="2"/>
  <text x="678" y="562" className="legend-text">守护/监控</text>

    </svg>
  );
};

export default KanbanArchDiagram;
