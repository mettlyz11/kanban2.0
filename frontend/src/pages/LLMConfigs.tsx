import { useState, useEffect } from 'react'

interface LLMConfig {
  id: number
  provider: string
  name: string
  model_name: string
  is_active: number
  is_default: number
  temperature: number
  max_tokens: number
  context_window: number
  model_type: string
  supports_vision: number
  supports_reasoning: number
  description: string
  input_cost: number
  output_cost: number
  tokens_used: number
  last_used_at: string
}

const PROVIDER_COLORS: Record<string, string> = {
  'aliyun': '#FF6A00',
  'aliyun-coding': '#FF8C00',
  'openrouter': '#6366F1',
  'dmxapi': '#10B981',
  'deepseek': '#3B82F6',
  'moonshot': '#8B5CF6',
  'CUSTOM': '#6B7280',
  'ALI': '#FF6A00',
  'OPENAI': '#10A37F',
  'MIDJOURNEY': '#1A1A2E',
  'VERTEX_AI': '#4285F4',
  'KLING': '#FF4757',
  'MINIMAX': '#8B5CF6',
  'ZHIPU': '#4169E1',
  'COZE': '#00D4AA',
  'BAIDU': '#2932E1',
  'XUNFEI': '#FF6B35',
  'LINGYI': '#00C853',
  'VOLCENGINE': '#00D4AA',
  'TENCENT': '#0052D9',
  'SUNO': '#FF006E',
  'DEEPSEEK': '#3B82F6',
  'FLUX': '#FF6B6B',
  'XAI': '#1A1A2E',
}

const PROVIDER_NAMES: Record<string, string> = {
  'aliyun': '阿里云',
  'aliyun-coding': '阿里云Coding',
  'openrouter': 'OpenRouter',
  'dmxapi': 'DMXAPI',
  'deepseek': 'DeepSeek',
  'moonshot': 'Moonshot',
  'CUSTOM': 'CUSTOM',
  'ALI': '阿里',
  'OPENAI': 'OpenAI',
  'MIDJOURNEY': 'Midjourney',
  'VERTEX_AI': 'Vertex AI',
  'KLING': '可灵',
  'MINIMAX': 'MiniMax',
  'ZHIPU': '智谱',
  'COZE': 'Coze',
  'BAIDU': '百度',
  'XUNFEI': '讯飞',
  'LINGYI': '零一万物',
  'VOLCENGINE': '火山引擎',
  'TENCENT': '腾讯',
  'SUNO': 'Suno',
  'DEEPSEEK': 'DeepSeek',
  'FLUX': 'Flux',
  'XAI': 'xAI',
}

const MODEL_TYPE_ICONS: Record<string, string> = {
  'general': '🤖',
  'coding': '💻',
  'vision': '👁️',
  'audio': '🔊',
  'math': '📐',
  'video': '🎬',
  'embedding': '📊',
  'long-context': '📚',
}

// 能力标签配置 (预留)
// @ts-ignore
const _CAPABILITY_CONFIG: Record<string, { icon: string; name: string }> = {
  'chat': { icon: '💬', name: '对话' },
  'vision': { icon: '👁️', name: '视觉' },
  'coding': { icon: '💻', name: '代码' },
  'audio': { icon: '🔊', name: '音频' },
  'video': { icon: '🎬', name: '视频' },
  'reasoning': { icon: '🧠', name: '推理' },
  'embedding': { icon: '📊', name: '嵌入' },
  'search': { icon: '🔍', name: '搜索' },
  'image_gen': { icon: '🎨', name: '生图' },
  'math': { icon: '🔢', name: '数学' },
  'long-context': { icon: '📚', name: '长文本' },
}

export function LLMConfigs() {
  const [configs, setConfigs] = useState<LLMConfig[]>([])
  const [stats, setStats] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [selectedProvider, setSelectedProvider] = useState<string>('all')

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [configsRes, statsRes] = await Promise.all([
        fetch('/api/llm/configs').then(r => r.json()),
        fetch('/api/llm/stats').then(r => r.json())
      ])
      if (configsRes.success) setConfigs(configsRes.configs || [])
      if (statsRes.success) setStats(statsRes.stats)
    } catch (e) {
      console.error(e)
    } finally {
      setLoading(false)
    }
  }

  const handleActivate = async (id: number) => {
    try {
      await fetch(`/api/llm/configs/${id}/activate`, { method: 'PUT' })
      loadData()
    } catch (e) {
      console.error(e)
    }
  }

  const getProviders = () => {
    const providers = new Set(configs.map(c => c.provider))
    return ['all', ...Array.from(providers).sort()]
  }

  const filteredConfigs = selectedProvider === 'all' 
    ? configs 
    : configs.filter(c => c.provider === selectedProvider)

  // 按提供商分组统计
  const providerStats = configs.reduce((acc, config) => {
    acc[config.provider] = (acc[config.provider] || 0) + 1
    return acc
  }, {} as Record<string, number>)

  // 按厂商分组的模型
  const groupedByProvider = configs.reduce((acc, config) => {
    const p = config.provider
    if (!acc[p]) acc[p] = []
    acc[p].push(config)
    return acc
  }, {} as Record<string, LLMConfig[]>)

  if (loading) return <div className="loading">加载中...</div>

  return (
    <div>
      <div className="page-header">
        <h2 className="page-title">🤖 大模型配置 (725+ 模型)</h2>
      </div>

      {stats && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))', gap: '12px', marginBottom: '20px' }}>
          <div className="stat-card blue" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>🔧</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.total || 0}</h3>
              <p style={{ fontSize: '0.75rem' }}>配置总数</p>
            </div>
          </div>
          <div className="stat-card green" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>✅</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.active || 0}</h3>
              <p style={{ fontSize: '0.75rem' }}>活跃配置</p>
            </div>
          </div>
          <div className="stat-card purple" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>📊</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{stats.usage || 0}</h3>
              <p style={{ fontSize: '0.75rem' }}>使用次数</p>
            </div>
          </div>
          <div className="stat-card orange" style={{ padding: '12px' }}>
            <div className="stat-icon" style={{ width: '40px', height: '40px', fontSize: '1.1rem' }}>🏢</div>
            <div className="stat-info">
              <h3 style={{ fontSize: '1.3rem' }}>{Object.keys(providerStats).length}</h3>
              <p style={{ fontSize: '0.75rem' }}>提供商</p>
            </div>
          </div>
        </div>
      )}

      {/* 提供商统计 */}
      <div className="card" style={{ marginBottom: '20px' }}>
        <div className="card-header">
          <h5>📊 提供商分布</h5>
        </div>
        <div style={{ padding: '16px', display: 'flex', flexWrap: 'wrap', gap: '10px' }}>
          {Object.entries(providerStats).map(([provider, count]) => (
            <div 
              key={provider}
              style={{
                padding: '8px 16px',
                borderRadius: '20px',
                background: `${PROVIDER_COLORS[provider] || '#6B7280'}20`,
                border: `1px solid ${PROVIDER_COLORS[provider] || '#6B7280'}`,
                display: 'flex',
                alignItems: 'center',
                gap: '8px'
              }}
            >
              <span style={{ 
                width: '10px', 
                height: '10px', 
                borderRadius: '50%', 
                background: PROVIDER_COLORS[provider] || '#6B7280' 
              }} />
              <span style={{ fontWeight: 500 }}>{provider}</span>
              <span style={{ 
                background: PROVIDER_COLORS[provider] || '#6B7280', 
                color: 'white',
                padding: '2px 8px',
                borderRadius: '10px',
                fontSize: '0.8rem'
              }}>{count}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 过滤器 */}
      <div style={{ marginBottom: '16px', display: 'flex', gap: '10px', alignItems: 'center' }}>
        <span style={{ fontWeight: 500 }}>筛选:</span>
        <select 
          value={selectedProvider}
          onChange={(e) => setSelectedProvider(e.target.value)}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: '1px solid var(--border)',
            background: 'var(--card-bg)',
            color: 'var(--text)',
            cursor: 'pointer'
          }}
        >
          <option value="all">全部提供商</option>
          {getProviders().filter(p => p !== 'all').map(provider => (
            <option key={provider} value={provider}>{provider}</option>
          ))}
        </select>
        <button 
          onClick={loadData}
          style={{
            padding: '8px 16px',
            borderRadius: '6px',
            border: 'none',
            background: '#3B82F6',
            color: 'white',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px'
          }}
        >
          🔄 刷新
        </button>
      </div>

      <div className="card">
        <div className="card-header">
          <h5>模型配置列表 ({filteredConfigs.length}个)</h5>
        </div>
        <div className="table-container">
          <table className="data-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>提供商</th>
                <th>模型ID</th>
                <th>类型</th>
                <th>上下文</th>
                <th>能力</th>
                <th>状态</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {filteredConfigs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="empty-state">暂无模型配置</td>
                </tr>
              ) : (
                filteredConfigs.map((config) => (
                  <tr key={config.id} style={{ opacity: config.is_active ? 1 : 0.7 }}>
                    <td>
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <strong>{config.name}</strong>
                        {config.description && (
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                            {config.description.length > 40 ? config.description.slice(0, 40) + '...' : config.description}
                          </span>
                        )}
                      </div>
                    </td>
                    <td>
                      <span style={{
                        padding: '4px 10px',
                        borderRadius: '12px',
                        fontSize: '0.8rem',
                        fontWeight: 500,
                        background: `${PROVIDER_COLORS[config.provider] || '#6B7280'}20`,
                        color: PROVIDER_COLORS[config.provider] || '#6B7280',
                        border: `1px solid ${PROVIDER_COLORS[config.provider] || '#6B7280'}`
                      }}>
                        {config.provider}
                      </span>
                    </td>
                    <td><code style={{ fontSize: '0.85rem' }}>{config.model_name}</code></td>
                    <td>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <span>{MODEL_TYPE_ICONS[config.model_type] || '📦'}</span>
                        <span>{config.model_type}</span>
                      </span>
                    </td>
                    <td>
                      <span style={{ fontFamily: 'monospace', fontSize: '0.9rem' }}>
                        {config.context_window >= 1000000 
                          ? `${(config.context_window / 1000000).toFixed(1)}M` 
                          : config.context_window >= 1000 
                            ? `${(config.context_window / 1000).toFixed(0)}K` 
                            : config.context_window}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
                        {config.supports_vision ? (
                          <span title="视觉理解" style={{ 
                            fontSize: '0.75rem', 
                            padding: '2px 6px', 
                            background: '#ECFDF5', 
                            borderRadius: '4px',
                            color: '#059669'
                          }}>👁️ 视觉</span>
                        ) : null}
                        {config.supports_reasoning ? (
                          <span title="推理能力" style={{ 
                            fontSize: '0.75rem', 
                            padding: '2px 6px', 
                            background: '#EEF2FF', 
                            borderRadius: '4px',
                            color: '#6366F1'
                          }}>🧠 推理</span>
                        ) : null}
                        {config.model_type === 'coding' ? (
                          <span title="代码生成" style={{ 
                            fontSize: '0.75rem', 
                            padding: '2px 6px', 
                            background: '#F0FDF4', 
                            borderRadius: '4px',
                            color: '#16A34A'
                          }}>💻 代码</span>
                        ) : null}
                        {config.model_type === 'audio' ? (
                          <span title="音频处理" style={{ 
                            fontSize: '0.75rem', 
                            padding: '2px 6px', 
                            background: '#FEF3C7', 
                            borderRadius: '4px',
                            color: '#D97706'
                          }}>🔊 音频</span>
                        ) : null}
                        {config.model_type === 'video' ? (
                          <span title="视频生成" style={{ 
                            fontSize: '0.75rem', 
                            padding: '2px 6px', 
                            background: '#FEE2E2', 
                            borderRadius: '4px',
                            color: '#DC2626'
                          }}>🎬 视频</span>
                        ) : null}
                      </div>
                    </td>
                    <td>
                      <span className={`badge ${config.is_active ? 'badge-green' : 'badge-gray'}`}>
                        {config.is_active ? '活跃' : '停用'}
                      </span>
                      {config.is_default ? (
                        <span className="badge badge-blue" style={{ marginLeft: '6px' }}>默认</span>
                      ) : null}
                    </td>
                    <td>
                      {!config.is_active && (
                        <button
                          onClick={() => handleActivate(config.id)}
                          style={{
                            padding: '6px 12px',
                            borderRadius: '4px',
                            border: 'none',
                            background: '#10B981',
                            color: 'white',
                            cursor: 'pointer',
                            fontSize: '0.85rem'
                          }}
                        >
                          激活
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* 厂商分组展示 */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <h5>🏢 按厂商分类 ({Object.keys(groupedByProvider).length} 个厂商, {configs.length} 个模型)</h5>
        </div>
        <div style={{ padding: '16px' }}>
          {Object.entries(groupedByProvider)
            .sort((a, b) => b[1].length - a[1].length)
            .map(([provider, models]) => (
            <div key={provider} style={{ marginBottom: '20px' }}>
              <div style={{ 
                display: 'flex', 
                alignItems: 'center', 
                gap: '10px', 
                marginBottom: '10px',
                padding: '8px 12px',
                background: `${PROVIDER_COLORS[provider] || '#6B7280'}10`,
                borderRadius: '8px',
                borderLeft: `4px solid ${PROVIDER_COLORS[provider] || '#6B7280'}`
              }}>
                <span style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                  {PROVIDER_NAMES[provider] || provider}
                </span>
                <span style={{ 
                  background: PROVIDER_COLORS[provider] || '#6B7280', 
                  color: 'white',
                  padding: '2px 10px',
                  borderRadius: '12px',
                  fontSize: '0.85rem'
                }}>
                  {models.length} 个模型
                </span>
              </div>
              <div style={{ 
                display: 'flex', 
                flexWrap: 'wrap', 
                gap: '8px',
                paddingLeft: '16px'
              }}>
                {models.slice(0, 20).map(m => (
                  <span key={m.id} style={{
                    padding: '4px 10px',
                    background: 'var(--bg-secondary)',
                    borderRadius: '6px',
                    fontSize: '0.8rem',
                    border: '1px solid var(--border)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '4px'
                  }}>
                    {MODEL_TYPE_ICONS[m.model_type] || '📦'}
                    {m.name}
                    {m.supports_vision && <span title="视觉">👁️</span>}
                    {m.supports_reasoning && <span title="推理">🧠</span>}
                  </span>
                ))}
                {models.length > 20 && (
                  <span style={{
                    padding: '4px 10px',
                    color: 'var(--text-secondary)',
                    fontSize: '0.8rem'
                  }}>+{models.length - 20} 更多...</span>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* 模型调用示例 */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <h5>💻 模型调用示例 (DMXAPI)</h5>
        </div>
        <div style={{ padding: '16px' }}>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontWeight: 500, marginBottom: '8px', color: 'var(--text-secondary)' }}>Python:</div>
            <pre style={{ 
              background: '#1F2937', 
              color: '#E5E7EB',
              padding: '16px', 
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.85rem'
            }}>{`import openai

client = openai.OpenAI(
    api_key='your-dmxapi-key',
    base_url='https://www.dmxapi.cn/v1'
)

response = client.chat.completions.create(
    model='gpt-4o',  # 或其他模型如 claude-3-5-sonnet, gemini-1.5-pro
    messages=[{'role': 'user', 'content': '你好'}]
)

print(response.choices[0].message.content)`}</pre>
          </div>
          <div style={{ marginBottom: '16px' }}>
            <div style={{ fontWeight: 500, marginBottom: '8px', color: 'var(--text-secondary)' }}>cURL:</div>
            <pre style={{ 
              background: '#1F2937', 
              color: '#E5E7EB',
              padding: '16px', 
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.85rem'
            }}>{`curl https://www.dmxapi.cn/v1/chat/completions \\
  -H "Content-Type: application/json" \\
  -H "Authorization: Bearer your-dmxapi-key" \\
  -d '{
    "model": "gpt-4o",
    "messages": [{"role": "user", "content": "你好"}]
  }'`}</pre>
          </div>
          <div>
            <div style={{ fontWeight: 500, marginBottom: '8px', color: 'var(--text-secondary)' }}>列出所有可用模型:</div>
            <pre style={{ 
              background: '#1F2937', 
              color: '#E5E7EB',
              padding: '16px', 
              borderRadius: '8px',
              overflow: 'auto',
              fontSize: '0.85rem'
            }}>{`curl https://www.dmxapi.cn/v1/models \\
  -H "Authorization: Bearer your-dmxapi-key"`}</pre>
          </div>
        </div>
      </div>

      {/* 模型说明卡片 */}
      <div className="card" style={{ marginTop: '20px' }}>
        <div className="card-header">
          <h5>📖 模型类型说明</h5>
        </div>
        <div style={{ padding: '16px' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px' }}>
            <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🤖</div>
              <div style={{ fontWeight: 600 }}>General</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>通用对话模型</div>
            </div>
            <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>💻</div>
              <div style={{ fontWeight: 600 }}>Coding</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>代码生成优化</div>
            </div>
            <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>👁️</div>
              <div style={{ fontWeight: 600 }}>Vision</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>视觉理解模型</div>
            </div>
            <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🔊</div>
              <div style={{ fontWeight: 600 }}>Audio</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>音频处理模型</div>
            </div>
            <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>🎬</div>
              <div style={{ fontWeight: 600 }}>Video</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>视频生成模型</div>
            </div>
            <div style={{ padding: '12px', background: 'var(--bg-secondary)', borderRadius: '8px' }}>
              <div style={{ fontSize: '1.5rem', marginBottom: '8px' }}>📊</div>
              <div style={{ fontWeight: 600 }}>Embedding</div>
              <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>文本嵌入模型</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
