import React, { useEffect, useMemo, useRef, useState } from 'react'

type DialogueEvent = {
  id: string
  time: string
  channel: 'agent1' | 'user'
  sender: string
  receiver: string
  event_type: string
  message: string
  meta?: Record<string, any>
}

type Protocol = {
  title: string
  owner: string
  target: string
  purpose: string
  steps: string[]
  template: string
}

const typeStyle: Record<string, { label: string; bg: string; color: string }> = {
  protocol: { label: '方案/协议', bg: '#fef3c7', color: '#92400e' },
  ask: { label: 'Agent2提问', bg: '#dbeafe', color: '#1d4ed8' },
  answer: { label: 'Agent2回答', bg: '#ede9fe', color: '#6d28d9' },
  task_start: { label: '问题开始', bg: '#dcfce7', color: '#166534' },
  problem_summary: { label: '问题总结', bg: '#ccfbf1', color: '#0f766e' },
  summary: { label: '总结', bg: '#ccfbf1', color: '#0f766e' },
  message: { label: '消息', bg: '#f1f5f9', color: '#475569' },
  doctor_report: { label: 'Agent1回复', bg: '#dcfce7', color: '#166534' },
  agent2_followup: { label: '追问', bg: '#dbeafe', color: '#1d4ed8' },
  agent2_decision: { label: '裁决', bg: '#ede9fe', color: '#6d28d9' },
  agent2_to_user: { label: '给用户总结', bg: '#ccfbf1', color: '#0f766e' },
  agent2_user_summary: { label: '给用户总结', bg: '#ccfbf1', color: '#0f766e' },
  agent1_tool_start: { label: '工具开始', bg: '#fef3c7', color: '#92400e' },
  agent1_tool_result: { label: '工具结果', bg: '#dcfce7', color: '#166534' },
  agent1_tool_error: { label: '工具错误', bg: '#fee2e2', color: '#991b1b' },
  agent2_to_user_status: { label: '处理状态', bg: '#e0f2fe', color: '#0369a1' },
}



const noisyTypes = new Set(['protocol', 'queued', 'claimed'])

const agent1ConversationTypes = new Set([
  // Real Agent2 ↔ Agent1 work dialogue
  'ask', 'agent2_ask', 'agent2_to_agent1', 'agent2_instruction', 'agent2_followup',
  'agent1_to_agent2', 'agent1_followup_answer', 'agent1_llm_diagnosis', 'agent1_work_summary',
  'agent1_tool_start', 'agent1_tool_result', 'agent1_tool_error',
  'doctor_report', 'agent1_reply', 'agent2_llm_plan',
  'agent2_decision', 'completed', 'answer'
])
const userConversationTypes = new Set([
  'user_task', 'agent2_ack', 'task_start', 'problem_summary', 'summary', 'agent2_to_user', 'agent2_to_user_status',
  'agent2_user_summary', 'agent2_llm_summary', 'approval_request', 'approval_response', 'message'
])


function isPollutedWorkHealthEvent(ev: DialogueEvent) {
  const report = ev.meta?.report || ev.meta?.report_digest || {}
  const text = String(ev.message || '')
  const evidence = report?.evidence || {}
  const evidenceKeys = Array.isArray(report?.evidence_keys) ? report.evidence_keys : Object.keys(evidence || {})
  const isWorkBrainstorm = report?.tool_group === 'work' || evidenceKeys.includes('brainstorm')
  const hasHealthWords = /pending|in_progress|stale|日志|重复进程|duplicate|错误类型|健康诊断|致命阻塞/.test(text)
  if (!isWorkBrainstorm || ev.event_type === 'agent1_work_summary') return false
  return hasHealthWords && ['agent1_llm_diagnosis', 'agent1_to_agent2', 'doctor_report'].includes(ev.event_type)
}

function isThinDoctorReport(ev: DialogueEvent) {
  const text = (ev.message || '').trim().toLowerCase()
  if (ev.event_type !== 'doctor_report') return false
  if (text !== 'recent log errors detected') return false
  const report = ev.meta?.report || ev.meta?.report_digest
  const llmAnswer = report?.llm?.json?.agent1_answer || report?.agent1_answer
  const diagnosis = report?.llm_diagnosis || report?.diagnosis
  const evidence = report?.evidence || report?.evidence_keys
  // Hide only the old empty shell events. If there is structured detail, normalizeMessage will show it.
  return !llmAnswer && !diagnosis && !evidence
}

function isDialogueEventForWindow(ev: DialogueEvent, selfName: 'Agent2' | '刘宇宙') {
  if (noisyTypes.has(ev.event_type) || ev.meta?.protocol_key || isThinDoctorReport(ev) || isPollutedWorkHealthEvent(ev)) return false
  const from = shortName(ev.sender)
  const to = shortName(ev.receiver)
  if (selfName === 'Agent2') {
    // Agent2↔Agent1 window: only actual commands/questions/reports between Agent2 and Agent1.
    // Do NOT show task_start/internal user-facing status here.
    const betweenA2A1 = (from === 'Agent2' && to === 'Agent1') || (from === 'Agent1' && to === 'Agent2')
    return betweenA2A1 && agent1ConversationTypes.has(ev.event_type) && ev.event_type !== 'task_start'
  }
  // Agent2↔刘宇宙 window: only messages that actually involve the user.
  // Old scheduled health_scan task_start events were written to channel='user' even though
  // they are Agent2→Agent1/system status; showing them here makes brainstorm tasks look like health checks.
  const involvesUser = from === '刘宇宙' || to === '刘宇宙'
  if (involvesUser) return userConversationTypes.has(ev.event_type) && ev.event_type !== 'protocol'
  return false
}

function shortName(name?: string) {
  if (!name) return '未知'
  if (name === 'YuZhouProxyAgent') return 'Agent2'
  if (name === 'SDSDoctorAgent') return 'Agent1'
  if (name === 'LiuYuZhou' || name === '刘宇宙') return '刘宇宙'
  if (name.includes('Worker')) return '执行器'
  if (name.includes('Queue')) return '队列'
  return name.replace(/Agent$/,'')
}

function normalizeMessage(ev: DialogueEvent) {
  let text = ev.message || ''
  if (ev.event_type === 'doctor_report' && (text || '').trim().toLowerCase() === 'recent log errors detected') {
    const report = ev.meta?.report || ev.meta?.report_digest || {}
    const llmAnswer = report?.llm?.json?.agent1_answer || report?.agent1_answer
    const diagnosis = report?.llm_diagnosis || report?.diagnosis
    const findings = Array.isArray(report?.llm_key_findings) ? report.llm_key_findings.slice(0,3).join('；') : ''
    const evidenceKeys = Array.isArray(report?.evidence_keys) ? report.evidence_keys.join(', ') : (report?.evidence ? Object.keys(report.evidence).slice(0,8).join(', ') : '')
    const parts = [] as string[]
    if (llmAnswer) parts.push(String(llmAnswer))
    if (diagnosis && !String(llmAnswer || '').includes(String(diagnosis))) parts.push('诊断：' + String(diagnosis))
    if (findings) parts.push('关键发现：' + findings)
    if (evidenceKeys) parts.push('证据：' + evidenceKeys)
    if (parts.length) return parts.join('\n')
  }
  text = text.replace(/^Agent2请求Agent1\/Crew开始执行：/g, 'Agent1，请开始执行/检查：')
  text = text.replace(/^Agent2收到Agent1\/Crew执行结果，进入裁决与总结阶段：/g, 'Agent1已完成检查，我开始裁决：')
  text = text.replace(/^Agent2启动问题处理：/g, 'Agent2开始处理：')
  text = text.replace(/^用户发起Agent2任务：/g, '请 Agent2 处理：')
  return text
}

function eventLabel(ev: DialogueEvent) {
  if (ev.event_type === 'ask' || ev.event_type === 'agent2_ask') return '指令'
  if (ev.event_type === 'agent2_followup') return '必要追问'
  if (ev.event_type === 'answer' || ev.event_type === 'agent2_decision') return '回应/裁决'
  if (ev.event_type === 'task_start') return '开始'
  if (ev.event_type === 'problem_summary' || ev.event_type === 'summary') return '总结'
  if (ev.event_type === 'agent1_tool_start') return '工具开始'
  if (ev.event_type === 'agent1_tool_result') return '工具结果'
  if (ev.event_type === 'agent1_tool_error') return '工具错误'
  if (ev.event_type === 'agent1_reply' || ev.event_type === 'doctor_report' || ev.event_type === 'completed') return 'Agent1回复'
  if (ev.event_type === 'user_task') return '用户任务'
  return typeStyle[ev.event_type]?.label || '对话'
}

function ProtocolCard({ proto, compact = false }: { proto: Protocol; compact?: boolean }) {
  return (
    <div style={{ border: '1px solid #c7d2fe', borderRadius: 8, background: '#fff', padding: compact ? 5 : 7, boxShadow: '0 2px 8px rgba(79,70,229,.08)' }}>
      <div style={{ fontWeight: 800, color: '#312e81', fontSize: compact ? 11 : 13 }}>{proto.title}</div>
      <div style={{ color: '#64748b', fontSize: 11, marginTop: 2 }}>{proto.owner} → {proto.target}</div>
      <div style={{ color: '#334155', fontSize: 10, marginTop: 2, lineHeight: 1.25 }}>{proto.purpose}</div>
      {!compact && <ol style={{ margin: '4px 0 0', paddingLeft: 14, color: '#0f172a', fontSize: 10, lineHeight: 1.25 }}>
        {(proto.steps || []).map((s, i) => <li key={i}>{s.replace(/^\d+\.\s*/, '')}</li>)}
      </ol>}
    </div>
  )
}

function avatarFor(name: string) {
  if (name === 'Agent2') return '🐕'
  if (name === 'Agent1') return '🩺'
  if (name === '刘宇宙') return '👤'
  return '⚙️'
}

function EventCard({ ev, selfName }: { ev: DialogueEvent; selfName: 'Agent2' | '刘宇宙' }) {
  const from = shortName(ev.sender)
  const to = shortName(ev.receiver)
  const isSelf = from === selfName
  const isAgent2 = from === 'Agent2'
  const isUser = from === '刘宇宙'
  const isAgent1 = from === 'Agent1'
  const isSummary = ['problem_summary', 'summary', 'agent2_to_user', 'agent2_user_summary'].includes(ev.event_type)
  const align: 'flex-start' | 'flex-end' = isSelf ? 'flex-end' : 'flex-start'
  const bubbleBg = isSelf
    ? selfName === '刘宇宙'
      ? 'linear-gradient(135deg,#22c55e,#059669)'
      : 'linear-gradient(135deg,#4f46e5,#7c3aed)'
    : isAgent2
      ? 'linear-gradient(135deg,#eef2ff,#f5f3ff)'
      : isAgent1
        ? '#ffffff'
        : isUser
          ? 'linear-gradient(135deg,#fef3c7,#fffbeb)'
          : '#ffffff'
  const color = isSelf ? 'white' : '#0f172a'
  const metaColor = isSelf ? 'rgba(255,255,255,.72)' : '#64748b'
  const border = isSelf ? '1px solid rgba(255,255,255,.16)' : isSummary ? '1px solid #99f6e4' : '1px solid #e2e8f0'
  const roleColor = isSelf ? (selfName === '刘宇宙' ? '#059669' : '#4f46e5') : isAgent2 ? '#4f46e5' : isAgent1 ? '#0f766e' : '#b45309'
  return (
    <div style={{ display: 'flex', justifyContent: align, margin: '8px 0' }}>
      <div style={{ display: 'flex', flexDirection: isSelf ? 'row-reverse' : 'row', gap: 7, maxWidth: '88%', alignItems: 'flex-end' }}>
        <div style={{ width: 28, height: 28, flex: '0 0 28px', borderRadius: '50%', background: isSelf ? roleColor : '#e2e8f0', color: isSelf ? 'white' : '#0f172a', display: 'grid', placeItems: 'center', fontSize: 15, boxShadow: '0 5px 14px rgba(15,23,42,.12)' }}>{avatarFor(from)}</div>
        <div style={{ minWidth: 160 }}>
          <div style={{ display: 'flex', justifyContent: isSelf ? 'flex-end' : 'flex-start', gap: 6, alignItems: 'center', marginBottom: 3, color: '#64748b', fontSize: 10 }}>
            <b style={{ color: roleColor }}>{from}</b>
            <span>{ev.time?.replace('T', ' ').slice(5, 19)}</span>
            <span style={{ background: typeStyle[ev.event_type]?.bg || '#f1f5f9', color: typeStyle[ev.event_type]?.color || '#475569', borderRadius: 999, padding: '1px 6px', fontWeight: 800 }}>{eventLabel(ev)}</span>
          </div>
          <div style={{ background: bubbleBg, color, border, borderRadius: isSelf ? '16px 16px 4px 16px' : '16px 16px 16px 4px', padding: '10px 12px', boxShadow: '0 8px 22px rgba(15,23,42,.08)', whiteSpace: 'pre-wrap', lineHeight: 1.48, fontSize: 13 }}>
            {normalizeMessage(ev)}
          </div>
          {ev.meta?.task_id && <div style={{ marginTop: 2, textAlign: isSelf ? 'right' : 'left', color: metaColor, fontSize: 10 }}>task: {String(ev.meta.task_id).slice(0, 28)}</div>}
        </div>
      </div>
    </div>
  )
}

function DialogueColumn({ title, subtitle, events, accent, selfName, emptyText }: { title: string; subtitle: string; events: DialogueEvent[]; accent: string; selfName: 'Agent2' | '刘宇宙'; emptyText: string }) {
  const visibleEvents = events
    .filter(e => isDialogueEventForWindow(e, selfName))
    .slice()
    .sort((a, b) => String(b.time || '').localeCompare(String(a.time || '')))
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.scrollTop = 0
  }, [visibleEvents])
  return (
    <section style={{ flex: 1, minWidth: 0, minHeight: 0, borderRadius: 16, background: 'rgba(248,250,252,.94)', border: '1px solid rgba(226,232,240,.9)', overflow: 'hidden', boxShadow: '0 10px 30px rgba(15,23,42,.08)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ padding: '10px 14px', background: accent, color: 'white', display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'center' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: 16, letterSpacing: '.2px' }}>{title}</h2>
          <div style={{ opacity: .9, fontSize: 11, marginTop: 2 }}>{subtitle}</div>
        </div>
        <div style={{ opacity: .9, fontSize: 11, background: 'rgba(255,255,255,.14)', border: '1px solid rgba(255,255,255,.18)', borderRadius: 999, padding: '3px 8px' }}>{visibleEvents.length} 条 · 最新置顶</div>
      </div>
      <div ref={ref} style={{ flex: 1, minHeight: 0, overflowY: 'auto', padding: 10, background: 'linear-gradient(180deg,rgba(255,255,255,.65),rgba(241,245,249,.7))' }}>
        {visibleEvents.length === 0 ? <div style={{ color: '#64748b', textAlign: 'center', marginTop: 60 }}>{emptyText}</div> : visibleEvents.map(ev => <EventCard key={ev.id + ev.time + ev.event_type} ev={ev} selfName={selfName} />)}
      </div>
    </section>
  )
}


export default function SDSCrewDialogue() {
  const [agent1, setAgent1] = useState<DialogueEvent[]>([])
  const [user, setUser] = useState<DialogueEvent[]>([])
  const [protocols, setProtocols] = useState<Record<string, Protocol>>({})
  const [status, setStatus] = useState('connecting')
  const [lastUpdated, setLastUpdated] = useState('')
  const [transport, setTransport] = useState('polling')
  const [question, setQuestion] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [taskHint, setTaskHint] = useState('')

  async function submitUserTask() {
    const q = question.trim()
    if (!q) return
    setSubmitting(true)
    setTaskHint('正在提交给 Agent2...')
    try {
      const res = await fetch('/api/sds-crew/user-task', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: q })
      })
      const data = await res.json()
      if (data.success) {
        setTaskHint(`已发送给 Agent2：${data.task_id}`)
        setQuestion('')
        setTimeout(load, 800)
      } else {
        setTaskHint(`提交失败：${data.error || 'unknown'}`)
      }
    } catch (e) {
      setTaskHint('提交失败：网络或后端错误')
    } finally {
      setSubmitting(false)
    }
  }

  async function load() {
    try {
      const res = await fetch('/api/sds-crew/dialogue-events?limit=500&include_protocols=0', { cache: 'no-store' })
      const data = await res.json()
      if (data.success) {
        setAgent1(data.agent1 || [])
        setUser(data.user || [])
        setProtocols(data.protocols || {})
        setStatus('online')
        setLastUpdated(new Date().toLocaleTimeString())
      } else {
        setStatus('api_error')
      }
    } catch (e) {
      setStatus('offline')
    }
  }

  useEffect(() => {
    load()
    let timer: ReturnType<typeof setInterval> | undefined
    let es: EventSource | undefined
    try {
      es = new EventSource('/api/sds-crew/dialogue-events/stream?limit=500')
      es.onopen = () => { setTransport('sse'); setStatus('online') }
      es.onmessage = (msg) => {
        const data = JSON.parse(msg.data)
        if (data.success) {
          setAgent1(data.agent1 || [])
          setUser(data.user || [])
          setStatus('online')
          setLastUpdated(new Date().toLocaleTimeString())
        }
      }
      es.onerror = () => {
        setTransport('polling')
        es?.close()
        timer = setInterval(load, 2000)
      }
    } catch {
      timer = setInterval(load, 2000)
    }
    return () => { es?.close(); if (timer) clearInterval(timer) }
  }, [])

  const stats = useMemo(() => ({
    agent1: agent1.length,
    user: user.length,
    summaries: user.filter(e => ['problem_summary', 'summary'].includes(e.event_type)).length,
    protocols: Object.keys(protocols).length,
  }), [agent1, user, protocols])

  const protoList = ['agent2_ask_agent1', 'agent2_answer_agent1'].map(k => protocols[k]).filter(Boolean)

  return (
    <div style={{ margin: -20, padding: 10, height: 'calc(100vh - 60px)', boxSizing: 'border-box', background: 'radial-gradient(circle at top left,#dbeafe 0,#eef2ff 34%,#f8fafc 72%)', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(210px,.62fr) minmax(420px,1.35fr) minmax(330px,1fr)', gap: 10, alignItems: 'stretch', marginBottom: 10 }}>
        <div style={{ background: 'linear-gradient(135deg,rgba(15,23,42,.96),rgba(49,46,129,.92))', color: 'white', borderRadius: 16, padding: '11px 14px', boxShadow: '0 14px 34px rgba(49,46,129,.18)', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 9, minWidth: 0 }}>
            <div style={{ width: 30, height: 30, borderRadius: 10, background: 'rgba(255,255,255,.14)', display: 'grid', placeItems: 'center', fontSize: 17 }}>🐕</div>
            <div style={{ minWidth: 0 }}>
              <h1 style={{ margin: 0, fontSize: 18, lineHeight: 1.1 }}>SDS Crew</h1>
              <div style={{ marginTop: 3, color: 'rgba(255,255,255,.72)', fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>Agent2 双通道实时对话</div>
            </div>
          </div>
          <div style={{ display: 'flex', gap: 7, alignItems: 'center', marginTop: 9, fontSize: 11, flexWrap: 'wrap' }}>
            <span style={{ background: status === 'online' ? 'rgba(34,197,94,.18)' : 'rgba(239,68,68,.18)', color: status === 'online' ? '#86efac' : '#fecaca', border: '1px solid rgba(255,255,255,.16)', borderRadius: 999, padding: '2px 7px', fontWeight: 800 }}>{status}</span>
            <span style={{ color: 'rgba(255,255,255,.72)' }}>{transport}</span>
            <span style={{ color: 'rgba(255,255,255,.72)' }}>{lastUpdated || '-'}</span>
            <button onClick={load} style={{ border: '1px solid rgba(255,255,255,.18)', background: 'rgba(255,255,255,.12)', color: 'white', borderRadius: 8, padding: '3px 8px', fontSize: 11, cursor: 'pointer' }}>刷新</button>
          </div>
        </div>

        <div style={{ background: 'rgba(255,255,255,.92)', border: '1px solid rgba(199,210,254,.9)', borderRadius: 16, padding: 10, boxShadow: '0 12px 30px rgba(79,70,229,.10)', minWidth: 0 }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'stretch' }}>
            <textarea
              value={question}
              onChange={e => setQuestion(e.target.value)}
              onKeyDown={e => { if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') submitUserTask() }}
              placeholder="输入任务即可，Agent2 会自动判断是否派给 Agent1；需要追问才追问，不需要就一轮结束。Ctrl/Cmd+Enter"
              style={{ flex: 1, minHeight: 50, maxHeight: 92, resize: 'vertical', borderRadius: 11, border: '1px solid #cbd5e1', padding: '8px 10px', fontSize: 13, outline: 'none', boxSizing: 'border-box', background: '#f8fafc' }}
            />
            <button disabled={submitting || !question.trim()} onClick={submitUserTask} style={{ border: 0, background: submitting || !question.trim() ? '#94a3b8' : 'linear-gradient(135deg,#4f46e5,#7c3aed)', color: 'white', borderRadius: 11, padding: '0 16px', minWidth: 72, fontSize: 13, cursor: submitting || !question.trim() ? 'not-allowed' : 'pointer', fontWeight: 900, boxShadow: submitting || !question.trim() ? 'none' : '0 10px 18px rgba(79,70,229,.22)' }}>
              {submitting ? '提交中' : '启动'}
            </button>
          </div>
          {taskHint && <div style={{ marginTop: 5, color: taskHint.includes('失败') ? '#dc2626' : '#475569', fontSize: 11, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>{taskHint}</div>}
        </div>

        <div style={{ background: 'rgba(255,255,255,.92)', border: '1px solid rgba(226,232,240,.95)', borderRadius: 16, padding: '10px 12px', boxShadow: '0 12px 30px rgba(15,23,42,.07)', minWidth: 0 }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,minmax(0,1fr))', gap: 6, marginBottom: 8 }}>
            {[['A1对话', stats.agent1], ['用户对话', stats.user], ['总结', stats.summaries], ['协议', stats.protocols]].map(([k, v]) => (
              <div key={String(k)} style={{ background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 11, padding: '5px 6px', textAlign: 'center' }}>
                <div style={{ fontSize: 16, fontWeight: 900, lineHeight: 1, color: '#0f172a' }}>{v}</div>
                <div style={{ fontSize: 10, color: '#64748b', marginTop: 2 }}>{k}</div>
              </div>
            ))}
          </div>
          <div style={{ display: 'flex', gap: 5, color: '#475569', fontSize: 10, alignItems: 'center', flexWrap: 'wrap' }}>
            {protoList.map((p, i) => <span key={i} style={{ background: '#eef2ff', border: '1px solid #c7d2fe', borderRadius: 999, padding: '2px 7px', color: '#3730a3', whiteSpace: 'nowrap' }}>{p.title}</span>)}
          </div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1fr) minmax(0,1fr)', gap: 12, flex: 1, minHeight: 0 }}>
        <DialogueColumn title="Agent2 ↔ Agent1" subtitle="Agent2 在右侧指挥；只有证据不够时才追问，Agent1 在左侧干活/给证据" events={agent1} accent="linear-gradient(135deg,#2563eb,#7c3aed)" selfName="Agent2" emptyText="暂无 Agent2 和 Agent1 的真实对话" />
        <DialogueColumn title="Agent2 ↔ 刘宇宙" subtitle="你在右侧发起/确认，Agent2 在左侧汇报/请示" events={user} accent="linear-gradient(135deg,#059669,#0f766e)" selfName="刘宇宙" emptyText="暂无你和 Agent2 的对话" />
      </div>
    </div>
  )
}
