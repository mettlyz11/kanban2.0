import React, { useState, useEffect, useRef, useCallback } from 'react'
import { useRealtimeWS } from '../hooks/useRealtimeWS'

// VNC not configured - deploy noVNC to enable
const VNC_ENABLED = true
const VNC_IFRAME_URL = VNC_ENABLED
  ? '/vnc/vnc.html?host=kanbanyun.com&port=443&encrypt=1&path=websockify&autoconnect=1&resize=remote'
  : null

interface Vitals {
  cpu: number; memory: number; disk: number; uptime: number; processes: number; timestamp: string
}

const QUICK_CMDS = [
  { id: 'restart_scheduler', label: '⏩ 重启调度', color: '#3b82f6' },
  { id: 'run_review', label: '🕵️ 触发审核', color: '#8b5cf6' },
  { id: 'flush_cache', label: '🧹 清缓存', color: '#f59e0b' },
  { id: 'batch_rerun_failed', label: '🔄 重跑失败', color: '#22c55e' },
  { id: 'clear_stale_locks', label: '🧹 清锁', color: '#ef4444' },
  { id: 'reload_sds_module', label: '🔄 热重载', color: '#ec4899' },
]

export const RemoteDesktop: React.FC = () => {
  const [vitals, setVitals] = useState<Vitals | null>(null)
  const [panelOpen, setPanelOpen] = useState(true)
  const [activeCmd, setActiveCmd] = useState<string | null>(null)
  const [cmdLog, setCmdLog] = useState<string[]>([])
  const [vncError, setVncError] = useState(false)
  const iframeRef = useRef<HTMLIFrameElement>(null)

  const { isConnected, sendCommand } = useRealtimeWS((evt) => {
    if (evt.event === 'metrics' && evt.data?.metrics) {
      const m = evt.data.metrics
      setVitals({
        cpu: m.cpu?.percent || 0, memory: m.memory?.percent || 0,
        disk: m.disk?.percent || 0, uptime: m.uptime || 0,
        processes: m.processes || 0, timestamp: evt.timestamp,
      })
    }
  })

  const handleCmd = (cmdId: string) => {
    setActiveCmd(cmdId)
    sendCommand(cmdId)
    const t = new Date().toLocaleTimeString('zh-CN', { hour12: false })
    setCmdLog(prev => [`${t} 🎮 ${cmdId}`, ...prev.slice(0, 19)])
    setTimeout(() => setActiveCmd(null), 2000)
  }

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen()
    } else {
      document.exitFullscreen()
    }
  }

  const bg = (pct: number) => pct > 90 ? '#ef4444' : pct > 70 ? '#f59e0b' : '#22c55e'
  const fmtUptime = (s: number) => {
    const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60)
    return `${d}d ${h}h ${m}m`
  }

  return (
    <div style={{
      position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
      background: '#000', overflow: 'hidden',
      marginTop: panelOpen ? 0 : 0,
    }}>
      {/* VNC iframe - conditional on VNC being configured */}
      {VNC_IFRAME_URL ? (
        <iframe ref={iframeRef}
          src={VNC_IFRAME_URL}
          onError={() => setVncError(true)}
          style={{
            width: '100%', height: '100%', border: 'none',
            position: 'absolute', top: 0, left: 0,
          }}
        />
      ) : (
        <div style={{
          width: '100%', height: '100%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: '#0f172a', color: '#94a3b8',
          flexDirection: 'column', gap: 16,
          position: 'absolute', top: 0, left: 0,
        }}>
          <div style={{ fontSize: 48 }}>🖥️</div>
          <h2 style={{ color: '#e2e8f0', margin: 0 }}>远程桌面</h2>
          <p style={{ margin: 0 }}>noVNC 尚未部署</p>
          <p style={{ fontSize: '0.85rem', margin: 0, maxWidth: 400, textAlign: 'center' }}>
            如需启用，请在服务器上安装 noVNC 并配置 nginx websocket 代理
          </p>
          <a href="https://github.com/novnc/noVNC" target="_blank" rel="noopener noreferrer"
             style={{ color: '#60a5fa', fontSize: '0.85rem' }}>
            了解如何配置 noVNC -
          </a>
        </div>
      )}

      {/* 状态浮层 - 右上角 */}
      <div style={{
        position: 'absolute', top: 12, right: panelOpen ? 270 : 12,
        background: 'rgba(15,23,42,0.92)', backdropFilter: 'blur(8px)',
        borderRadius: 12, border: '1px solid rgba(51,65,85,0.5)',
        padding: '10px 14px', minWidth: 200, transition: 'right 0.3s',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8 }}>
          <span style={{ color: isConnected ? '#22c55e' : '#ef4444', fontSize: 10 }}>●</span>
          <span style={{ color: '#e2e8f0', fontSize: 13, fontWeight: 600 }}>Mac mini</span>
          <span style={{ color: '#475569', fontSize: 11, marginLeft: 'auto' }}>{vitals ? fmtUptime(vitals.uptime) : '...'}</span>
        </div>
        {vitals && (
          <>
            {[
              { label: 'CPU', pct: vitals.cpu, value: `${vitals.cpu}%` },
              { label: '内存', pct: vitals.memory, value: `${vitals.memory}%` },
              { label: '磁盘', pct: vitals.disk, value: `${vitals.disk}%` },
            ].map((m, i) => (
              <div key={i} style={{ marginBottom: i < 2 ? 6 : 0 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 11, color: '#94a3b8', marginBottom: 2 }}>
                  <span>{m.label}</span>
                  <span style={{ fontWeight: 600, color: bg(m.pct) }}>{m.value}</span>
                </div>
                <div style={{ height: 3, background: '#1e293b', borderRadius: 2, overflow: 'hidden' }}>
                  <div style={{ width: `${m.pct}%`, height: '100%', background: bg(m.pct), borderRadius: 2, transition: 'width 0.5s ease' }} />
                </div>
              </div>
            ))}
          </>
        )}
        {!vitals && <div style={{ color: '#475569', fontSize: 11 }}>等待数据...</div>}
      </div>

      {/* 控制面板 - 右侧 */}
      <div style={{
        position: 'absolute', top: 0, right: 0, bottom: 0, width: 250,
        background: 'rgba(15,23,42,0.95)', backdropFilter: 'blur(8px)',
        borderLeft: '1px solid rgba(51,65,85,0.4)',
        display: panelOpen ? 'flex' : 'none',
        flexDirection: 'column', padding: 14, transform: panelOpen ? 'none' : 'translateX(100%)',
        transition: 'transform 0.3s',
      }}>
        {/* 面板标题 */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
          <span style={{ color: '#e2e8f0', fontSize: 14, fontWeight: 700 }}>🎮 SDS 遥控</span>
          <button onClick={() => setPanelOpen(false)}
            style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer', fontSize: 18 }}>✕</button>
        </div>

        {/* 快速命令 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginBottom: 16 }}>
          {QUICK_CMDS.map(cmd => (
            <button key={cmd.id} onClick={() => handleCmd(cmd.id)}
              style={{
                padding: '8px 12px', border: 'none', borderRadius: 8, cursor: 'pointer',
                background: activeCmd === cmd.id ? cmd.color : `${cmd.color}18`,
                color: activeCmd === cmd.id ? '#fff' : cmd.color,
                fontSize: 12, fontWeight: 600, textAlign: 'left',
                transition: 'all 0.2s',
              }}>
              {cmd.label}
            </button>
          ))}
        </div>

        {/* 命令日志 */}
        <div style={{ flex: 1, overflow: 'auto', fontSize: 11, fontFamily: 'monospace' }}>
          <div style={{ color: '#475569', fontSize: 11, marginBottom: 6, fontWeight: 600 }}>📋 命令日志</div>
          {cmdLog.length === 0 && (
            <div style={{ color: '#333', fontSize: 11 }}>暂无命令记录</div>
          )}
          {cmdLog.map((line, i) => (
            <div key={i} style={{ color: i === 0 ? '#22c55e' : '#64748b', padding: '2px 0', whiteSpace: 'pre' }}>
              {line}
            </div>
          ))}
        </div>

        {/* 底部按钮 */}
        <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
          <button onClick={() => setPanelOpen(false)}
            style={{ flex: 1, padding: '6px', background: '#334155', border: 'none', borderRadius: 6, color: '#94a3b8', fontSize: 11, cursor: 'pointer' }}>
            ◀ 收起
          </button>
          <button onClick={toggleFullscreen}
            style={{ flex: 1, padding: '6px', background: '#334155', border: 'none', borderRadius: 6, color: '#94a3b8', fontSize: 11, cursor: 'pointer' }}>
            ⛶ 全屏
          </button>
        </div>
      </div>

      {/* 展开按钮 - 面板收起时 */}
      {!panelOpen && (
        <button onClick={() => setPanelOpen(true)}
          style={{
            position: 'absolute', top: 12, right: 12, zIndex: 10,
            padding: '8px 10px', background: 'rgba(15,23,42,0.85)', border: '1px solid #334155',
            borderRadius: 8, color: '#94a3b8', fontSize: 14, cursor: 'pointer',
          }}>
          ◀ 面板
        </button>
      )}
    </div>
  )
}
