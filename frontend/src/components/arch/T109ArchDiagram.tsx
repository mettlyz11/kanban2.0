import React from 'react';

interface T109ArchDiagramProps {
  style?: React.CSSProperties;
}

const T109ArchDiagram: React.FC<T109ArchDiagramProps> = ({ style }) => {
  const [hovered, setHovered] = React.useState<string | null>(null);
  return (
    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1000 650" style={{ width: '100%', maxWidth: '1000px', height: 'auto', ...style }}>

<defs>
<marker id="arr-blue" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#2563eb"/></marker>
<marker id="arr-orange" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#ea580c"/></marker>
<marker id="arr-green" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#059669"/></marker>
<marker id="arr-purple" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#7c3aed"/></marker>
<marker id="arr-gray" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto"><polygon points="0 0,10 3.5,0 7" fill="#6b7280"/></marker>
<filter id="shadow"><feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.15"/></filter>
</defs>
<rect width="1000" height="650" fill="#fafafa"/>
<text x="500" y="35" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="20" fontWeight="600" fill="#1f2937">T109 过渡态预测平台架构</text>
<rect x="40" y="100" width="920" height="60" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="55" y="118" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">接入层</text>
<rect x="40" y="180" width="920" height="70" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="55" y="198" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">API服务层</text>
<rect x="40" y="270" width="920" height="70" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="55" y="288" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">任务队列层</text>
<rect x="40" y="360" width="920" height="70" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="55" y="378" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">计算引擎层</text>
<rect x="40" y="450" width="440" height="70" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="55" y="468" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">AI子代理层</text>
<rect x="520" y="450" width="440" height="70" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="535" y="468" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">数据持久化层</text>
<circle cx="500" cy="65" r="18" fill="#dbeafe" stroke="#3b82f6" strokeWidth="2" filter="url(#shadow)"/>
<text x="500" y="70" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="11" fill="#1e40af">用户</text>
<rect x="380" y="112" width="240" height="40" rx="8" fill="#e0e7ff" stroke="#6366f1" strokeWidth="2" filter="url(#shadow)"/>
<text x="500" y="132" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="13" fontWeight="600" fill="#3730a3">nginx 反向代理</text>
<text x="500" y="145" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fill="#3730a3">HTTPS :443 → /api/ → :8000</text>
<rect x="300" y="195" width="400" height="45" rx="8" fill="#fef3c7" stroke="#f59e0b" strokeWidth="2" filter="url(#shadow)"/>
<text x="500" y="215" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="13" fontWeight="600" fill="#92400e">Flask API (:8000)</text>
<text x="500" y="230" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fill="#92400e">RESTful · simple_db_api · pyscf_db_api · simple_async_api</text>
<rect x="50" y="195" width="120" height="45" rx="6" fill="#e0e7ff" stroke="#6366f1" strokeWidth="1.5" filter="url(#shadow)"/>
<text x="110" y="215" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="600" fill="#3730a3">simple_db</text>
<text x="110" y="230" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="9" fill="#3730a3">5,720行</text>
<rect x="780" y="195" width="120" height="45" rx="6" fill="#e0e7ff" stroke="#6366f1" strokeWidth="1.5" filter="url(#shadow)"/>
<text x="840" y="215" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="600" fill="#3730a3">pyscf_db</text>
<text x="840" y="230" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="9" fill="#3730a3">6,725行</text>
<rect x="300" y="285" width="400" height="45" rx="8" fill="#ede9fe" stroke="#8b5cf6" strokeWidth="2" filter="url(#shadow)"/>
<text x="500" y="305" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="13" fontWeight="600" fill="#5b21b6">Celery Workers (2)</text>
<text x="500" y="320" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fill="#5b21b6">qchem_tasks · 异步任务队列</text>
<rect x="300" y="375" width="400" height="45" rx="8" fill="#d1fae5" stroke="#10b981" strokeWidth="2" filter="url(#shadow)"/>
<text x="500" y="395" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="13" fontWeight="600" fill="#065f46">PySCF / Q-Chem 计算引擎</text>
<text x="500" y="410" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fill="#065f46">NEB+CI-NEB · 多基组 · 平行计算</text>
<rect x="110" y="463" width="280" height="45" rx="25" fill="#fce7f3" stroke="#ec4899" strokeWidth="2" filter="url(#shadow)"/>
<text x="250" y="483" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="13" fontWeight="600" fill="#9d174d">Hermes AI Agent</text>
<text x="250" y="498" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fill="#9d174d">过渡态ML预测 · 训练中</text>
<path d="M600,463 L600,503 C600,518 630,523 660,523 C690,523 720,518 720,503 L720,463 C720,478 690,483 660,483 C630,483 600,478 600,463 Z" fill="#dbeafe" stroke="#3b82f6" strokeWidth="2" filter="url(#shadow)"/>
<ellipse cx="660" cy="463" rx="60" ry="20" fill="#dbeafe" stroke="#3b82f6" strokeWidth="2"/>
<text x="660" y="498" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="11" fontWeight="600" fill="#1e40af">MySQL RDS</text>
<text x="660" y="513" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="9" fill="#1e40af">计算结果 · 任务 · 配置</text>
<rect x="850" y="550" width="120" height="45" rx="8" fill="#fff3e0" stroke="#f57c00" strokeWidth="2" filter="url(#shadow)"/>
<text x="910" y="570" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="12" fontWeight="600" fill="#e65100">Supervisor</text>
<text x="910" y="585" textAnchor="middle" fontFamily="system-ui,sans-serif" fontSize="10" fill="#e65100">自动重启守护</text>
<rect x="40" y="540" width="780" height="65" fill="#f3f4f6" stroke="#9ca3af" strokeWidth="1" strokeDasharray="5,3" rx="8"/>
<text x="55" y="558" fontFamily="system-ui,sans-serif" fontSize="12" fill="#6b7280">运维监控层</text>
<line x1="500" y1="83" x2="500" y2="112" stroke="#2563eb" strokeWidth="2" markerEnd="url(#arr-blue)"/>
<text x="510" y="100" fontFamily="system-ui,sans-serif" fontSize="9" fill="#2563eb">请求</text>
<line x1="500" y1="152" x2="500" y2="195" stroke="#ea580c" strokeWidth="1.5" markerEnd="url(#arr-orange)"/>
<text x="510" y="175" fontFamily="system-ui,sans-serif" fontSize="9" fill="#ea580c">反向代理</text>
<line x1="460" y1="152" x2="170" y2="195" stroke="#6b7280" strokeWidth="1.5" strokeDasharray="4,2" markerEnd="url(#arr-gray)"/>
<line x1="540" y1="152" x2="840" y2="195" stroke="#6b7280" strokeWidth="1.5" strokeDasharray="4,2" markerEnd="url(#arr-gray)"/>
<line x1="500" y1="240" x2="500" y2="285" stroke="#7c3aed" strokeWidth="1.5" markerEnd="url(#arr-purple)"/>
<text x="510" y="265" fontFamily="system-ui,sans-serif" fontSize="9" fill="#7c3aed">分发任务</text>
<line x1="500" y1="330" x2="500" y2="375" stroke="#059669" strokeWidth="1.5" markerEnd="url(#arr-green)"/>
<text x="510" y="355" fontFamily="system-ui,sans-serif" fontSize="9" fill="#059669">计算调用</text>
<line x1="700" y1="397" x2="700" y2="445" stroke="#059669" strokeWidth="1.5" markerEnd="url(#arr-green)"/>
<text x="710" y="425" fontFamily="system-ui,sans-serif" fontSize="9" fill="#059669">结果归档</text>
<line x1="390" y1="485" x2="540" y2="475" stroke="#7c3aed" strokeWidth="1.5" strokeDasharray="5,3" markerEnd="url(#arr-purple)"/>
<text x="440" y="475" fontFamily="system-ui,sans-serif" fontSize="9" fill="#7c3aed">训练数据</text>
<line x1="850" y1="572" x2="700" y2="240" stroke="#ea580c" strokeWidth="1.5" strokeDasharray="4,2" markerEnd="url(#arr-orange)"/>
<text x="800" y="380" fontFamily="system-ui,sans-serif" fontSize="9" fill="#ea580c">守护重启</text>
<rect x="40" y="615" width="920" height="25" fill="#fff" stroke="#e5e7eb" strokeWidth="1" rx="4"/>
<text x="55" y="632" fontFamily="system-ui,sans-serif" fontSize="10" fontWeight="600" fill="#374151">图例:</text>
<line x1="90" y1="628" x2="120" y2="628" stroke="#2563eb" strokeWidth="2"/><polygon points="120,625 130,628 120,631" fill="#2563eb"/>
<text x="135" y="632" fontFamily="system-ui,sans-serif" fontSize="9" fill="#4b5563">请求/响应</text>
<line x1="210" y1="628" x2="240" y2="628" stroke="#ea580c" strokeWidth="1.5"/><polygon points="240,625 250,628 240,631" fill="#ea580c"/>
<text x="255" y="632" fontFamily="system-ui,sans-serif" fontSize="9" fill="#4b5563">代理/触发</text>
<line x1="320" y1="628" x2="350" y2="628" stroke="#7c3aed" strokeWidth="1.5"/><polygon points="350,625 360,628 350,631" fill="#7c3aed"/>
<text x="365" y="632" fontFamily="system-ui,sans-serif" fontSize="9" fill="#4b5563">任务/调用</text>
<line x1="430" y1="628" x2="460" y2="628" stroke="#059669" strokeWidth="1.5"/><polygon points="460,625 470,628 460,631" fill="#059669"/>
<text x="475" y="632" fontFamily="system-ui,sans-serif" fontSize="9" fill="#4b5563">数据持久化</text>
<line x1="560" y1="628" x2="590" y2="628" stroke="#6b7280" strokeWidth="1.5" strokeDasharray="4,2"/><polygon points="590,625 600,628 590,631" fill="#6b7280"/>
<text x="605" y="632" fontFamily="system-ui,sans-serif" fontSize="9" fill="#4b5563">守护/异步</text>

    </svg>
  );
};

export default T109ArchDiagram;
