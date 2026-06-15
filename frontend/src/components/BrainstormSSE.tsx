import React, { useState, useRef, useEffect } from 'react';

interface BrainstormSSEProps {
  q: string;
  setQ: (v: string) => void;
  agentA: string;
  setAgentA: (v: string) => void;
  agentB: string;
  setAgentB: (v: string) => void;
}

const ROLES = [
  { k: 'researcher', n: '子墨', e: '🔬' },
  { k: 'analyst', n: '计然', e: '📊' },
  { k: 'strategist', n: '卧龙', e: '🧠' },
  { k: 'finance', n: '陶朱', e: '💰' },
  { k: 'risk', n: '韩非', e: '⚠️' },
  { k: 'investor', n: '白圭', e: '👀' },
];

export default function BrainstormSSE({ q, setQ, agentA, setAgentA, agentB, setAgentB }: BrainstormSSEProps) {
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<any[]>([]);
  const [conclusion, setConclusion] = useState('');
  const [agents, setAgents] = useState<any>(null);
  const [error, setError] = useState('');
  const abortRef = useRef<AbortController | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const stopStream = () => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
    }
    setLoading(false);
  };

  const startBrainstorm = async () => {
    if (!q.trim()) return;
    
    setMessages([]);
    setConclusion('');
    setAgents(null);
    setError('');
    setLoading(true);
    
    abortRef.current = new AbortController();
    
    try {
      const response = await fetch('/api/actor/brainstorm/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          question: q,
          max_rounds: 2,
          agent_a: agentA,
          agent_b: agentB
        }),
        signal: abortRef.current.signal
      });
      
      if (!response.ok) {
        throw new Error('HTTP ' + response.status);
      }
      
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      
      while (true) {
        const { done, value } = await reader!.read();
        if (done) break;
        
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || '';
        
        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (line.startsWith('data:')) {
            const dataStr = line.slice(5).trim();
            if (!dataStr) continue;
            try {
              const data = JSON.parse(dataStr);
              if (data.agents) {
                setAgents(data.agents);
              } else if (data.type === 'agent_a' || data.type === 'agent_b') {
                setMessages(prev => [...prev, data]);
              } else if (data.conclusion) {
                setConclusion(data.conclusion);
              }
            } catch (e) {
              // ignore parse error
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setError('请求失败: ' + err.message);
      }
    } finally {
      setLoading(false);
      abortRef.current = null;
    }
  };

  return (
    <div style={{ maxWidth: 960, margin: '0 auto', padding: '16px 24px' }}>
      <div style={{ marginBottom: 12 }}>
        <div style={{ fontSize: 14, fontWeight: 500, marginBottom: 8 }}>🧠 双Agent脑风暴（流式）</div>
        <div style={{ fontSize: 12, color: '#888', marginBottom: 12 }}>
          选择两个Agent进行多轮辩论，实时显示对话过程
        </div>
        
        <div style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Agent A</div>
            <select
              style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid #d9d9d9', fontSize: 13 }}
              value={agentA}
              onChange={e => setAgentA(e.target.value)}
            >
              <option value="">🎲 随机</option>
              {ROLES.map(r => (
                <option key={r.k} value={r.k}>{r.e} {r.n}</option>
              ))}
            </select>
          </div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>Agent B</div>
            <select
              style={{ width: '100%', padding: '6px 10px', borderRadius: 8, border: '1px solid #d9d9d9', fontSize: 13 }}
              value={agentB}
              onChange={e => setAgentB(e.target.value)}
            >
              <option value="">🎲 随机</option>
              {ROLES.map(r => (
                <option key={r.k} value={r.k}>{r.e} {r.n}</option>
              ))}
            </select>
          </div>
        </div>
        
        <textarea
          style={{ width: '100%', minHeight: 60, padding: '10px 12px', borderRadius: 10, border: '1px solid #d9d9d9', fontSize: 13, resize: 'vertical', boxSizing: 'border-box' }}
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="输入问题，例如：AI创业应该先技术驱动还是市场驱动？"
        />
        
        <div style={{ margin: '8px 0' }}>
          <button
            onClick={startBrainstorm}
            disabled={loading || !q.trim()}
            style={{
              padding: '8px 24px',
              borderRadius: 20,
              border: 'none',
              background: loading ? '#bbb' : '#1677ff',
              color: '#fff',
              cursor: loading ? 'not-allowed' : 'pointer',
              fontSize: 13
            }}
          >
            {loading ? '脑风暴中...' : '开始脑风暴'}
          </button>
          {loading && (
            <button
              onClick={stopStream}
              style={{
                marginLeft: 8,
                padding: '8px 16px',
                borderRadius: 20,
                border: '1px solid #ff4d4f',
                background: '#fff',
                color: '#ff4d4f',
                cursor: 'pointer',
                fontSize: 13
              }}
            >
              停止
            </button>
          )}
        </div>
      </div>
      
      {agents && (
        <div style={{ marginBottom: 12, padding: '10px 14px', background: '#f0f5ff', borderRadius: 10 }}>
          <div style={{ fontSize: 13, fontWeight: 500, marginBottom: 8 }}>
            {agentA && agentB ? '👥 指定角色' : '🎲 随机角色'}
          </div>
          <div style={{ display: 'flex', gap: 16 }}>
            <div>{agents.agent_a.emoji} {agents.agent_a.name}</div>
            <div style={{ color: '#d9d9d9' }}>VS</div>
            <div>{agents.agent_b.emoji} {agents.agent_b.name}</div>
          </div>
        </div>
      )}
      
      <div ref={scrollRef} style={{ maxHeight: 400, overflow: 'auto' }}>
        {messages.map((msg, idx) => {
          const isAgentA = msg.type === 'agent_a';
          const borderColor = isAgentA ? '#b7eb8f' : '#adc6ff';
          const bgColor = isAgentA ? '#f6ffed' : '#e6f4ff';
          return (
            <div key={idx} style={{ marginBottom: 12 }}>
              <div style={{
                padding: '6px 12px',
                fontSize: 13,
                fontWeight: 600,
                color: '#555',
                background: bgColor,
                borderRadius: '8px 8px 0 0',
                border: '1px solid ' + borderColor
              }}>
                🗣️ 第{msg.round}轮 - {msg.data.emoji} {msg.data.name}
              </div>
              <div style={{
                border: '1px solid ' + borderColor,
                borderTop: 'none',
                borderRadius: '0 0 8px 8px',
                padding: 8
              }}>
                {msg.data.ok ? (
                  <pre style={{ margin: 0, fontSize: 12, whiteSpace: 'pre-wrap', lineHeight: 1.5 }}>
                    {msg.data.reply}
                  </pre>
                ) : (
                  <span style={{ color: '#ff4d4f', fontSize: 12 }}>
                    ⚠️ {msg.data.error || '请求失败'}
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
      
      {conclusion && (
        <div style={{ marginBottom: 12 }}>
          <div style={{
            padding: '6px 12px',
            fontSize: 13,
            fontWeight: 600,
            color: '#555',
            background: '#fff7e6',
            borderRadius: '8px 8px 0 0',
            border: '1px solid #ffd591'
          }}>
            📝 综合结论
          </div>
          <div style={{
            border: '1px solid #ffd591',
            borderTop: 'none',
            borderRadius: '0 0 8px 8px',
            padding: '10px 14px',
            fontSize: 12,
            whiteSpace: 'pre-wrap',
            color: '#333',
            lineHeight: 1.6
          }}>
            {conclusion}
          </div>
        </div>
      )}
      
      {error && (
        <div style={{ padding: 12, background: '#fff2f0', borderRadius: 10, color: '#ff4d4f', fontSize: 13 }}>
          ⚠️ {error}
        </div>
      )}
    </div>
  );
}
