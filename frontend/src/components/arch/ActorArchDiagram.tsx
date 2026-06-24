import React from 'react';

interface ActorArchDiagramProps {
  style?: React.CSSProperties;
}

const ActorArchDiagram: React.FC<ActorArchDiagramProps> = ({ style }) => {
  const [hovered, setHovered] = React.useState<string | null>(null);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 520" style={{ width: '100%', maxWidth: '1000px', height: 'auto', ...style }}>

  <defs>

    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15"/>
    </filter>

    <marker id="arrow" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#666"/>
    </marker>
    <marker id="arrow-blue" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#1976d2"/>
    </marker>
    <marker id="arrow-green" markerWidth="10" markerHeight="10" refX="9" refY="3" orient="auto">
      <path d="M0,0 L0,6 L9,3 z" fill="#388e3c"/>
    </marker>
  </defs>


  <rect width="1000" height="520" fill="#fafafa"/>


  <text x="500" y="30" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="18" fontWeight="bold" fill="#333">Actor通道 (ActorTab) 系统架构</text>


  <g id="layer1">
    <rect x="20" y="55" width="960" height="70" fill="none" stroke="#999" strokeWidth="1" strokeDasharray="5,5" rx="8"/>
    <text x="35" y="75" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#666" fontWeight="bold">① 用户端</text>


    <rect x="420" y="85" width="160" height="30" fill="#e3f2fd" stroke="#1976d2" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="500" y="105" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#1565c0" fontWeight="500">🖥️ 浏览器/客户端</text>
  </g>


  <g id="layer2">
    <rect x="20" y="135" width="960" height="90" fill="none" stroke="#999" strokeWidth="1" strokeDasharray="5,5" rx="8"/>
    <text x="35" y="155" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#666" fontWeight="bold">② 双通道架构</text>


    <rect x="280" y="175" width="180" height="40" fill="#e8eaf6" stroke="#5c6bc0" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="370" y="195" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#3f51b5" fontWeight="500">🔄 HTTP轮询</text>
    <text x="370" y="210" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#5c6bc0">传统请求/响应 · 通用性强</text>


    <rect x="540" y="175" width="180" height="40" fill="#e8f5e9" stroke="#43a047" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="630" y="195" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#2e7d32" fontWeight="500">⚡ WebSocket</text>
    <text x="630" y="210" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#43a047">Socket.IO双向 · 评分9.99/10</text>
  </g>


  <g id="layer3">
    <rect x="20" y="235" width="960" height="90" fill="none" stroke="#999" strokeWidth="1" strokeDasharray="5,5" rx="8"/>
    <text x="35" y="255" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#666" fontWeight="bold">③ 通道管理层</text>


    <rect x="80" y="275" width="140" height="40" fill="#fff3e0" stroke="#ff9800" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="150" y="292" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#e65100" fontWeight="500">🧠 自动策略选择</text>
    <text x="150" y="307" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#ff9800">网络条件智能切换</text>


    <rect x="260" y="275" width="140" height="40" fill="#fce4ec" stroke="#e91e63" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="330" y="292" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#c2185b" fontWeight="500">⭐ 质量优化器</text>
    <text x="330" y="307" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#e91e63">Actor评分自动调优</text>


    <rect x="440" y="275" width="140" height="40" fill="#e0f7fa" stroke="#00bcd4" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="510" y="292" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#00838f" fontWeight="500">💓 心跳监控</text>
    <text x="510" y="307" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#00bcd4">30s间隔 · 60s超时</text>


    <rect x="620" y="275" width="140" height="40" fill="#f3e5f5" stroke="#9c27b0" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="690" y="292" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#6a1b9a" fontWeight="500">🧹 僵尸锁清理</text>
    <text x="690" y="307" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#9c27b0">自动清理过期死锁</text>


    <rect x="800" y="275" width="140" height="40" fill="#e8f5e9" stroke="#4caf50" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="870" y="292" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#2e7d32" fontWeight="500">🔌 连接池管理</text>
    <text x="870" y="307" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#4caf50">多实例负载均衡</text>
  </g>


  <g id="layer4">
    <rect x="20" y="335" width="960" height="90" fill="none" stroke="#999" strokeWidth="1" strokeDasharray="5,5" rx="8"/>
    <text x="35" y="355" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#666" fontWeight="bold">④ 事件系统</text>


    <rect x="80" y="375" width="130" height="40" fill="#e8eaf6" stroke="#3f51b5" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="145" y="392" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#283593" fontWeight="500">👥 在线用户通知</text>
    <text x="145" y="407" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#5c6bc0">实时状态同步</text>


    <rect x="240" y="375" width="130" height="40" fill="#e3f2fd" stroke="#2196f3" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="305" y="392" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#1565c0" fontWeight="500">📋 任务事件</text>
    <text x="305" y="407" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#2196f3">created/updated/deleted</text>


    <rect x="400" y="375" width="130" height="40" fill="#fff8e1" stroke="#ffc107" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="465" y="392" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#ff8f00" fontWeight="500">🔒 编辑锁</text>
    <text x="465" y="407" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#ffc107">lock_request/release</text>


    <rect x="560" y="375" width="130" height="40" fill="#f3e5f5" stroke="#9c27b0" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="625" y="392" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#6a1b9a" fontWeight="500">🏠 项目房间</text>
    <text x="625" y="407" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#9c27b0">按项目分组订阅</text>


    <rect x="720" y="375" width="130" height="40" fill="#e0f2f1" stroke="#009688" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="785" y="392" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#00695c" fontWeight="500">📡 广播系统</text>
    <text x="785" y="407" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#009688">Room/Namespace广播</text>


    <rect x="880" y="375" width="80" height="40" fill="#ffebee" stroke="#f44336" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="920" y="392" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#c62828" fontWeight="500">✓ ACK</text>
    <text x="920" y="407" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#f44336">消息确认</text>
  </g>


  <g id="layer5">
    <rect x="20" y="435" width="960" height="70" fill="none" stroke="#999" strokeWidth="1" strokeDasharray="5,5" rx="8"/>
    <text x="35" y="455" fontFamily="system-ui, -apple-system, sans-serif" fontSize="12" fill="#666" fontWeight="bold">⑤ 后端服务</text>


    <rect x="80" y="465" width="140" height="30" fill="#c8e6c9" stroke="#388e3c" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="150" y="484" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#1b5e20" fontWeight="500">🔌 SocketIO Server</text>


    <rect x="250" y="465" width="120" height="30" fill="#ffccbc" stroke="#e64a19" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="310" y="484" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#bf360c" fontWeight="500">🔐 Auth鉴权</text>


    <rect x="400" y="465" width="120" height="30" fill="#b3e5fc" stroke="#0288d1" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="460" y="484" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#01579b" fontWeight="500">📨 Events (12+)</text>


    <rect x="550" y="465" width="120" height="30" fill="#ffebee" stroke="#d32f2f" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="610" y="484" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#b71c1c" fontWeight="500">🔴 Redis Pub/Sub</text>


    <rect x="700" y="465" width="120" height="30" fill="#e1bee7" stroke="#7b1fa2" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="760" y="484" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#4a148c" fontWeight="500">🌐 Nginx代理</text>


    <rect x="850" y="465" width="100" height="30" fill="#d7ccc8" stroke="#5d4037" strokeWidth="1.5" rx="6" filter="url(#shadow)"/>
    <text x="900" y="484" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="11" fill="#3e2723" fontWeight="500">🗄️ PostgreSQL</text>
  </g>



  <line x1="500" y1="115" x2="370" y2="175" stroke="#5c6bc0" strokeWidth="1.5" markerEnd="url(#arrow-blue)"/>
  <line x1="500" y1="115" x2="630" y2="175" stroke="#43a047" strokeWidth="1.5" markerEnd="url(#arrow-green)"/>


  <line x1="370" y1="215" x2="150" y2="275" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="370" y1="215" x2="330" y2="275" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="630" y1="215" x2="510" y2="275" stroke="#00bcd4" strokeWidth="1.5" markerEnd="url(#arrow)"/>
  <line x1="630" y1="215" x2="690" y2="275" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="630" y1="215" x2="870" y2="275" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>


  <line x1="150" y1="315" x2="145" y2="375" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="330" y1="315" x2="305" y2="375" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="510" y1="315" x2="465" y2="375" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="510" y1="315" x2="625" y2="375" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="510" y1="315" x2="785" y2="375" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="690" y1="315" x2="920" y2="375" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>


  <line x1="145" y1="415" x2="150" y2="465" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="305" y1="415" x2="460" y2="465" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="465" y1="415" x2="310" y2="465" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="625" y1="415" x2="610" y2="465" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="785" y1="415" x2="760" y2="465" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>
  <line x1="920" y1="415" x2="900" y2="465" stroke="#999" strokeWidth="1" markerEnd="url(#arrow)"/>


  <text x="430" y="140" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#5c6bc0">HTTP</text>
  <text x="560" y="140" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#43a047">WebSocket</text>


  <g id="legend" transform="translate(20, 515)">
    <text x="0" y="0" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#666" fontWeight="bold">图例:</text>
    <rect x="40" y="-10" width="15" height="10" fill="#e8eaf6" stroke="#5c6bc0" strokeWidth="1" rx="2"/>
    <text x="60" y="-2" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#666">HTTP通道</text>
    <rect x="130" y="-10" width="15" height="10" fill="#e8f5e9" stroke="#43a047" strokeWidth="1" rx="2"/>
    <text x="150" y="-2" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#666">WebSocket通道</text>
    <rect x="240" y="-10" width="15" height="10" fill="#e0f7fa" stroke="#00bcd4" strokeWidth="1" rx="2"/>
    <text x="260" y="-2" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#666">监控组件</text>
    <rect x="330" y="-10" width="15" height="10" fill="#fff3e0" stroke="#ff9800" strokeWidth="1" rx="2"/>
    <text x="350" y="-2" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#666">策略组件</text>
    <rect x="420" y="-10" width="15" height="10" fill="#c8e6c9" stroke="#388e3c" strokeWidth="1" rx="2"/>
    <text x="440" y="-2" fontFamily="system-ui, -apple-system, sans-serif" fontSize="9" fill="#666">服务组件</text>
  </g>


  <text x="500" y="510" textAnchor="middle" fontFamily="system-ui, -apple-system, sans-serif" fontSize="10" fill="#888">
    数据流: SocketIO init → Auth鉴权 → 事件注册 → 心跳+监控 → 实时推送
  </text>


    </svg>
  );
};

export default ActorArchDiagram;
