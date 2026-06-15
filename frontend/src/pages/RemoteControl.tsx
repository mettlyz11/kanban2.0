import React, { useState, useRef } from 'react'
import { useRealtimeWS } from '../hooks/useRealtimeWS'

interface Cmd {
  id: string; label: string; desc: string; needsTaskId: boolean; color: string
}

const CMDS: Cmd[] = [
  {id:'restart_scheduler',label:'🏗️ 重启调度器',desc:'强制调度器重新扫描所有 pending 任务',needsTaskId:false,color:'#3b82f6'},
  {id:'run_review',label:'🕵️ 触发审核',desc:'立即执行审核巡逻，自动审核 pending 任务',needsTaskId:false,color:'#8b5cf6'},
  {id:'run_dependency',label:'🔗 依赖链巡检',desc:'检查任务上下游依赖，激活/阻塞自动处理',needsTaskId:false,color:'#06b6d4'},
  {id:'rerun_task',label:'🔄 重跑任务',desc:'输入 Task ID，重置状态为 pending 重新执行',needsTaskId:true,color:'#f59e0b'},
  {id:'batch_rerun_failed',label:'🔄 重跑所有失败任务',desc:'一键重置所有 failed 状态的子代理任务',needsTaskId:false,color:'#22c55e'},
  {id:'flush_cache',label:'🧹 清空 LLM 黑名单',desc:'LLM 故障已恢复后解除限制',needsTaskId:false,color:'#eab308'},
  {id:'clear_stale_locks',label:'🧹 清理僵尸锁',desc:'清除 DB 中过期死锁',needsTaskId:false,color:'#ef4444'},
  {id:'sync_config',label:'⚙️ 同步配置',desc:'从 system_configs 重新拉取 SDS 配置',needsTaskId:false,color:'#14b8a6'},
  {id:'trigger_patience',label:'🐢 激活耐心模式',desc:'让调度器更耐心等待慢速子代理',needsTaskId:false,color:'#f97316'},
  {id:'push_change_log',label:'📋 同步Changelog',desc:'强制推送 SDS 变更日志到看板',needsTaskId:false,color:'#6366f1'},
  {id:'reload_sds_module',label:'🔄 热重载SDS模块',desc:'不重启服务热更新子代理调度/审核等模块',needsTaskId:false,color:'#ec4899'},
]

const RemoteControl: React.FC = () => {
  const { isConnected, sendCommand } = useRealtimeWS()
  const [taskId, setTaskId] = useState('')
  const [feedback, setFeedback] = useState('')
  const feedbackTimer = useRef<number | null>(null)

  const handleCmd = (cmd: Cmd) => {
    const ok = cmd.needsTaskId ? sendCommand(cmd.id, taskId) : sendCommand(cmd.id)
    setFeedback(ok ? `✅ ${cmd.label} 已发送` : '❌ WS 未连接')
    if (feedbackTimer.current) clearTimeout(feedbackTimer.current)
    feedbackTimer.current = window.setTimeout(() => setFeedback(''), 3000)
  }

  return (
    <div style={{padding:24,color:'#e2e8f0',background:'#0f172a',minHeight:'calc(100vh-64px)'}}>
      <div style={{display:'flex',alignItems:'center',gap:10,marginBottom:4}}>
        <h2 style={{margin:0}}>🎮 SDS 远程控制台</h2>
        <span style={{fontSize:11,padding:'2px 8px',borderRadius:4,
          background:isConnected?'#065f4622':'#7f1d1d22',
          color:isConnected?'#22c55e':'#ef4444'}}>
          {isConnected?'● 已连接':'○ 未连接'}
        </span>
      </div>
      <p style={{color:'#64748b',fontSize:13,margin:'4px 0 16px'}}>
        共 {CMDS.length} 个命令 · 统一 WS · 点击即执行
      </p>

      {feedback && (
        <div style={{padding:'8px 14px',marginBottom:12,borderRadius:8,
          background:feedback.startsWith('✅')?'#065f4622':'#7f1d1d22',
          color:feedback.startsWith('✅')?'#22c55e':'#ef4444',fontSize:13}}>
          {feedback}
        </div>
      )}

      <div style={{display:'flex',flexDirection:'column',gap:8}}>
        {CMDS.map(c=>(
          <div key={c.id} style={{display:'flex',alignItems:'center',gap:12,
            padding:'10px 14px',background:'#1e293b',borderRadius:10,border:'1px solid #334155'}}>
            <div style={{flex:1}}>
              <div style={{fontWeight:600,fontSize:14}}>{c.label}</div>
              <div style={{fontSize:12,color:'#64748b',marginTop:2}}>{c.desc}</div>
            </div>
            {c.needsTaskId && (
              <input value={taskId} onChange={e=>setTaskId(e.target.value)}
                placeholder="Task ID"
                style={{width:80,padding:'6px 8px',background:'#0f172a',border:'1px solid #475569',
                  borderRadius:6,color:'#e2e8f0',fontSize:12}} />
            )}
            <button onClick={()=>handleCmd(c)}
              style={{padding:'6px 16px',border:'none',borderRadius:6,
                background:c.color,color:'#fff',fontSize:12,fontWeight:600,cursor:'pointer'}}>
              ▶ 执行
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
export default RemoteControl
