import React from 'react';

const ROLES = [
  {
    category: '👤 用户',
    items: [
      { name: '刘宇宙', emoji: '👨‍🔬', desc: '系统主人。北航化学教授、和光智成创始人。所有系统最终服务的目标。' },
    ]
  },
  {
    category: '🤖 人类助手',
    items: [
      { name: 'Dudu', emoji: '🐕', desc: '对话助手。负责写代码、改配置、重启服务。平时跟你在QQBot聊天的是我。问题来了就修，修完了告诉你。' },
    ]
  },
  {
    category: '🧠 AI分身',
    items: [
      { name: '扮演者 (Actor)', emoji: '🎭', desc: '你的AI分身，代表你做决策。独立HTTP服务 :18791。每次子代理执行、审计巡检都会问它。"这个要不要修？""按用户的风格应该怎么做？"', port: 18791, code: 'services/actor_service.py', status: 'launchd保活' },
      { name: '扮演者知识库', emoji: '📚', desc: '扮演者的知识支撑。L0核心身份 + L1当前快照 + user_decision_patterns + L2知识树路由。每次决策自动注入。' },
    ]
  },
  {
    category: '⏰ 巡检与修复',
    items: [
      { name: '审计员 (Auditor)', emoji: '🔍', desc: '独立巡检脚本。每6小时起床 → 收集系统快照 → 找扮演者判断 → 发现问题通知Dudu去修 → 修完告知你。', schedule: '每6小时', code: 'services/auditor_service.py', status: 'launchd定时' },
      { name: '审计扮演修复流程', emoji: '🔄', desc: '审计员→扮演者→Dudu→修完告知你+扮演者→扮演者下次复查。完整闭环。' },
    ]
  },
  {
    category: '🛡️ 监控与保活',
    items: [
      { name: 'Watchdog v2', emoji: '🐶', desc: '每5分钟检查所有服务是否活着。发现死了自动重启+通知你。监控6个服务：SDS、扮演者、通知、路由、DeepSeek代理、SSH隧道。', schedule: '每5分钟', code: 'services/watchdog_v2.py', status: 'launchd保活' },
      { name: 'launchd', emoji: '🍎', desc: 'macOS进程管理器。每个独立服务的"保命绳"——死了就重启。不需要人工干预。' },
    ]
  },
  {
    category: '⚙️ 核心系统',
    items: [
      { name: 'SDS 自驱系统', emoji: '🤖', desc: '任务调度引擎。每5分钟一个周期：激活定期任务→派子代理执行→验证结果→生成总结→触发订阅→反哺策略。Mac mini独立进程，launchd保活。', code: 'sds1/sds_main.py', status: '独立进程' },
      { name: '子代理', emoji: '🧩', desc: 'SDS派出的临时任务执行者。每个任务一个独立Python进程，跑完就退出。模板注入Tavily搜索+Houshan搜索+全景上下文。' },
      { name: '订阅引擎', emoji: '📡', desc: '定期任务完成→找扮演者判断→通知下游→下游完成→反哺上游策略。22条活跃订阅关系。' },
      { name: '卡点上报', emoji: '🚨', desc: '子代理卡住了→通过通知服务发QQBot消息给你。任何不确定的事先问，不脑补。' },
    ]
  },
  {
    category: '🌐 独立服务',
    items: [
      { name: '通知服务', emoji: '📬', desc: '统一消息发送。所有子系统发消息都通过它→QQBot或飞书。无法发送时写文件fallback。', port: 18792, code: 'services/notifier_service.py', status: 'launchd保活' },
      { name: '知识树路由', emoji: '🌳', desc: '树形知识体系查询。收到问题→匹配12个烽火台→返回知识上下文。12个第一层+11个子烽火台，39万字知识。', port: 18793, code: 'services/router_service.py', status: 'launchd保活' },
      { name: 'DeepSeek代理', emoji: '🔗', desc: '绕过阿里云ECS地域限制。kanban服务器→SSH隧道→Mac mini→DeepSeek API。', port: 18790, status: 'launchd保活' },
    ]
  },
  {
    category: '📊 展示与数据',
    items: [
      { name: '看板系统前端', emoji: '🖥️', desc: '你现在看到的这个页面。React+TS+Vite，nginx托管在ECS。展示任务、项目、审计历史、知识树配置等。', status: 'nginx静态文件' },
      { name: '看板系统后端', emoji: '🔌', desc: 'Flask API服务。路由任务/项目/审计/配置等所有API请求。ECS独立进程。', status: 'ECS独立进程' },
      { name: 'MySQL RDS', emoji: '🗄️', desc: '阿里云托管数据库。所有系统的数据存储。唯一单点——它挂了全部停。' },
      { name: 'OpenClaw Gateway', emoji: '🌉', desc: '通信通道。你的QQBot消息→LLM处理→回复。独立Node.js进程。SDS和Gateway互相独立，任一崩溃不影响其他。' },
    ]
  },
];

export default function SystemMap() {
  const [expanded, setExpanded] = React.useState<Record<string, boolean>>({});

  return (
    <div style={{ padding: '24px', maxWidth: '1000px', margin: '0 auto', fontSize: '0.9rem' }}>
      <div style={{ textAlign: 'center', marginBottom: '24px', padding: '20px', background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)', borderRadius: '12px', color: '#fff' }}>
        <div style={{ fontSize: '2rem', fontWeight: 700, marginBottom: '8px' }}>🗺️ 系统角色全景图</div>
        <div style={{ fontSize: '0.85rem', opacity: 0.9 }}>了解系统的每一个人和每一个组件</div>
        <div style={{ fontSize: '0.75rem', marginTop: '8px', opacity: 0.7 }}>版本 2026-05-24 | 解耦架构 ✓</div>
      </div>

      <div style={{ fontSize: '0.8rem', color: '#64748b', marginBottom: '16px', padding: '12px', background: '#fef3c7', borderRadius: '8px', border: '1px solid #fde68a' }}>
        💡 任何组件崩溃不影响其他组件。每个独立服务由 launchd 保活，崩溃自动重启。
      </div>

      {ROLES.map(group => (
        <div key={group.category} style={{ marginBottom: '20px' }}>
          <h2 style={{ fontSize: '1rem', fontWeight: 700, color: '#1e293b', marginBottom: '8px', padding: '0 4px' }}>{group.category}</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {group.items.map(item => {
              const key = item.name;
              const isExpanded = expanded[key];
              return (
                <div key={key}
                  onClick={() => setExpanded({ ...expanded, [key]: !isExpanded })}
                  style={{
                    background: '#fff', borderRadius: '8px', border: '1px solid #e2e8f0',
                    padding: '10px 14px', cursor: 'pointer',
                    transition: 'box-shadow 0.15s', 
                  }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '1.2rem' }}>{item.emoji}</span>
                      <div>
                        <span style={{ fontWeight: 600, color: '#1e293b', fontSize: '0.9rem' }}>{item.name}</span>
                        <span style={{ marginLeft: '8px', fontSize: '0.75rem', color: '#94a3b8' }}>{item.desc.slice(0, 60)}{item.desc.length > 60 ? '...' : ''}</span>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
                      {item.port && <span style={{ fontSize: '0.7rem', padding: '1px 6px', background: '#dbeafe', borderRadius: '4px', color: '#2563eb' }}>:{item.port}</span>}
                      {item.schedule && <span style={{ fontSize: '0.7rem', padding: '1px 6px', background: '#fef3c7', borderRadius: '4px', color: '#92400e' }}>{item.schedule}</span>}
                      {item.status && <span style={{ fontSize: '0.7rem', padding: '1px 6px', background: '#dcfce7', borderRadius: '4px', color: '#166534' }}>{item.status}</span>}
                      <span style={{ fontSize: '0.7rem', color: '#94a3b8', marginLeft: '4px' }}>{isExpanded ? '▲' : '▼'}</span>
                    </div>
                  </div>
                  {isExpanded && (
                    <div style={{ marginTop: '8px', paddingTop: '8px', borderTop: '1px solid #f1f5f9' }}>
                      <p style={{ fontSize: '0.85rem', color: '#475569', lineHeight: 1.6, margin: 0 }}>{item.desc}</p>
                      {item.code && (
                        <div style={{ marginTop: '6px', fontSize: '0.75rem', color: '#94a3b8' }}>
                          📁 {item.code}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}

      <div style={{ marginTop: '24px', padding: '16px', background: '#f8fafc', borderRadius: '8px', border: '1px solid #e2e8f0', fontSize: '0.8rem', color: '#64748b' }}>
        <div style={{ fontWeight: 600, color: '#1e293b', marginBottom: '8px' }}>崩溃影响矩阵</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px', fontSize: '0.75rem' }}>
          <div>💀=无法工作 &nbsp; ⚠️=功能受限 &nbsp; ✅=正常运行</div>
        </div>
        <table style={{ width: '100%', marginTop: '8px', borderCollapse: 'collapse', fontSize: '0.7rem' }}>
          <thead>
            <tr style={{ borderBottom: '1px solid #e2e8f0' }}>
              <th style={{ textAlign: 'left', padding: '4px' }}>组件崩溃</th>
              <th style={{ padding: '4px' }}>SDS</th>
              <th style={{ padding: '4px' }}>扮演者</th>
              <th style={{ padding: '4px' }}>审计员</th>
              <th style={{ padding: '4px' }}>通知</th>
              <th style={{ padding: '4px' }}>看板</th>
              <th style={{ padding: '4px' }}>用户</th>
            </tr>
          </thead>
          <tbody>
            {[
              ['SDS', '💀', '✅', '✅', '✅', '✅', '任务停'],
              ['扮演者', '✅', '💀', '✅', '✅', '✅', '判断降级'],
              ['审计员', '✅', '✅', '💀', '✅', '✅', '无人巡检'],
              ['通知服务', '✅', '✅', '✅', '💀', '✅', '消息积压'],
              ['看板后端', '✅', '✅', '✅', '✅', '💀', '网页打不开'],
              ['MySQL', '💀', '💀', '💀', '✅', '💀', '全部停'],
            ].map(row => (
              <tr key={row[0]} style={{ borderBottom: '1px solid #f1f5f9' }}>
                {row.map((cell, i) => (
                  <td key={i} style={{ padding: '4px', textAlign: i === 0 ? 'left' : 'center' }}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div style={{ marginTop: '12px', textAlign: 'center', fontSize: '0.75rem', color: '#94a3b8' }}>
        全部组件共17个 · 解耦架构 · 任一个崩溃不影响其他
      </div>
    </div>
  );
}
