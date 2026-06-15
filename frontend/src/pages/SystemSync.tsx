import { useState, useEffect, useCallback } from 'react'
import { useChangelog } from '../hooks/useChangelog'
import { useRealtimeWS } from '../hooks/useRealtimeWS'
import { Card, Table, Tag, Spin, Alert, Descriptions, Tabs, Statistic, Row, Col } from 'antd'
import { CheckCircleOutlined, SyncOutlined, ClockCircleOutlined, MonitorOutlined, ToolOutlined, DatabaseOutlined, SettingOutlined } from '@ant-design/icons'
import type { TabsProps } from 'antd'

interface SyncStatus {
  has_data: boolean
  timestamp: string
  received_at: string
}

interface SyncStatusData {
  success: boolean
  sync_status: Record<string, SyncStatus>
  last_update: string
}

const API = '/api'  // 使用相对路径，通过前端nginx代理

export function SystemSync() {
  const [syncStatus, setSyncStatus] = useState<SyncStatusData | null>(null)
  const [cronData, setCronData] = useState<any>(null)
  const [heartbeatData, setHeartbeatData] = useState<any>(null)
  const [llmData, setLlmData] = useState<any>(null)
  const [skillsToolsData, setSkillsToolsData] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const { isConnected } = useRealtimeWS()

  useEffect(() => { loadData() }, [])

  // 🐕 SDS 变更通知：有更新时刷新
  useChangelog((change: any) => {
    loadData()
  })

  useEffect(() => {
    const loadRestData = async () => {
      try {
        const [cronRes, hbRes, llmRes, stRes] = await Promise.all([
          fetch('/api/macmini/sync/cron').then(r => r.json()),
          fetch('/api/macmini/sync/heartbeat').then(r => r.json()),
          fetch('/api/macmini/sync/llm').then(r => r.json()),
          fetch('/api/macmini/sync/skills-tools').then(r => r.json()),
        ])
        if (cronRes.success && !cronData) setCronData(cronRes)
        if (hbRes.success && !heartbeatData) setHeartbeatData(hbRes)
        if (llmRes.success && !llmData) setLlmData(llmRes)
        if (stRes.success && !skillsToolsData) setSkillsToolsData(stRes)
      } catch (e) {
        // silent
      }
    }
    loadRestData()
  }, [cronData, heartbeatData, llmData, skillsToolsData])

  const loadData = async () => {
    try {
      setLoading(true)
      setError(null)
      
      const [statusRes, cronRes, hbRes, llmRes, stRes] = await Promise.all([
        fetch(`${API}/macmini/sync/status`).then(r => r.json()),
        fetch(`${API}/macmini/sync/cron`).then(r => r.json()),
        fetch(`${API}/macmini/sync/heartbeat`).then(r => r.json()),
        fetch(`${API}/macmini/sync/llm`).then(r => r.json()),
        fetch(`${API}/macmini/sync/skills-tools`).then(r => r.json()),
      ])

      if (statusRes.success) setSyncStatus(statusRes)
      if (cronRes.success) setCronData(cronRes)
      if (hbRes.success) setHeartbeatData(hbRes)
      if (llmRes.success) setLlmData(llmRes)
      if (stRes.success) setSkillsToolsData(stRes)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  const formatTime = (iso: string) => {
    if (!iso) return '-'
    try {
      return new Date(iso).toLocaleString('zh-CN', {
        month: 'short', day: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit'
      })
    } catch { return iso }
  }

  const getStatusTag = (status: SyncStatus | undefined) => {
    if (!status || !status.has_data) {
      return <Tag color="default">未同步</Tag>
    }
    const age = Date.now() - new Date(status.received_at).getTime()
    if (age < 120000) {
      return <Tag color="green"><CheckCircleOutlined /> 正常</Tag>
    }
    return <Tag color="orange"><ClockCircleOutlined /> {Math.round(age / 60000)}分钟前</Tag>
  }

  const cronColumns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '调度', dataIndex: 'schedule', key: 'schedule', width: 200 },
    { title: '目标', dataIndex: 'session_target', key: 'session_target', width: 120 },
    { title: '类型', dataIndex: 'payload_kind', key: 'payload_kind', width: 120,
      render: (kind: string) => <Tag color={kind === 'agentTurn' ? 'blue' : 'purple'}>{kind}</Tag>
    },
    { title: '状态', dataIndex: 'enabled', key: 'enabled', width: 80,
      render: (enabled: boolean) => enabled ? <Tag color="green">启用</Tag> : <Tag color="red">禁用</Tag>
    },
    { title: '描述', dataIndex: 'description', key: 'description', ellipsis: true },
  ]

  const skillsColumns = [
    { title: '名称', dataIndex: 'name', key: 'name', width: 200 },
    { title: '位置', dataIndex: 'location', key: 'location', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 100,
      render: (status: string) => <Tag color="green">{status || 'active'}</Tag>
    },
  ]

  const providerColumns = [
    { title: 'Provider', dataIndex: 'name', key: 'name', width: 150 },
    { title: 'Base URL', dataIndex: 'base_url', key: 'base_url', ellipsis: true },
    { title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (status: string) => status && status.includes('✅') ? <Tag color="green">活跃</Tag> : <Tag color="orange">{status || '未知'}</Tag>
    },
    { title: '收费', dataIndex: 'billing', key: 'billing', width: 100 },
  ]

  if (loading) {
    return <div style={{ padding: 40, textAlign: 'center' }}><Spin size="large" tip="正在加载同步数据..." /></div>
  }

  if (error) {
    return <div style={{ padding: 24 }}><Alert message="加载失败" description={error} type="error" showIcon action={<a onClick={loadData}>重新加载</a>} /></div>
  }

  const tabItems: TabsProps['items'] = [
    {
      key: 'cron',
      label: <span><DatabaseOutlined /> Cron 定时任务</span>,
      children: (
        <Card>
          {cronData?.jobs && cronData.jobs.length > 0 ? (
            <Table dataSource={cronData.jobs} columns={cronColumns} rowKey="name" pagination={{ pageSize: 10 }} size="small" />
          ) : <Alert message="暂无同步数据" type="info" />}
        </Card>
      ),
    },
    {
      key: 'heartbeat',
      label: <span>💓 心跳管理</span>,
      children: (
        <Card>
          {heartbeatData ? (
            <Descriptions column={2} bordered>
              <Descriptions.Item label="HEARTBEAT.md 存在">{heartbeatData.file_exists ? '✅' : '❌'}</Descriptions.Item>
              <Descriptions.Item label="文件大小">{heartbeatData.size || 0} 字节</Descriptions.Item>
              <Descriptions.Item label="最后修改">{formatTime(heartbeatData.last_modified)}</Descriptions.Item>
              <Descriptions.Item label="Cron 任务数">{heartbeatData.cron_jobs_count || 0}</Descriptions.Item>
            </Descriptions>
          ) : <Alert message="暂无同步数据" type="info" />}
        </Card>
      ),
    },
    {
      key: 'llm',
      label: <span><SettingOutlined /> 大模型配置</span>,
      children: (
        <Card>
          {llmData?.providers && llmData.providers.length > 0 ? (
            <Table dataSource={llmData.providers} columns={providerColumns} rowKey="name" pagination={false} size="small" />
          ) : <Alert message="暂无同步数据" type="info" />}
        </Card>
      ),
    },
    {
      key: 'skills',
      label: <span><ToolOutlined /> Skills & Tools</span>,
      children: (
        <>
          <Card title="Skills 列表" style={{ marginBottom: 16 }}>
            {skillsToolsData?.skills?.skills && skillsToolsData.skills.skills.length > 0 ? (
              <Table dataSource={skillsToolsData.skills.skills} columns={skillsColumns} rowKey="name" pagination={{ pageSize: 20 }} size="small" />
            ) : <Alert message="暂无同步数据" type="info" />}
          </Card>
          <Card title="Tools 配置">
            {skillsToolsData?.tools?.tools ? (
              <Descriptions column={2} bordered>
                <Descriptions.Item label="TOOLS.md 大小">{skillsToolsData.tools.tools.file_size || 0} 字节</Descriptions.Item>
                <Descriptions.Item label="最后修改">{formatTime(skillsToolsData.tools.tools.last_modified)}</Descriptions.Item>
                <Descriptions.Item label="章节数">{(skillsToolsData.tools.tools.sections || []).length}</Descriptions.Item>
                <Descriptions.Item label="Provider数">{(skillsToolsData.tools.tools.provider_table || []).length}</Descriptions.Item>
              </Descriptions>
            ) : <Alert message="暂无同步数据" type="info" />}
          </Card>
        </>
      ),
    },
  ]

  return (
    <div style={{ padding: 24 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h1 style={{ margin: 0 }}>🖥️ Mac mini 系统同步</h1>
        <Tag icon={<SyncOutlined spin />} color="processing">自动同步中</Tag>
      </div>

      <Card title="同步状态概览" style={{ marginBottom: 16 }}>
        <Row gutter={[16, 16]}>
          <Col span={6}>
            <Statistic title="Cron 定时任务" value={cronData?.count || 0} suffix="个" prefix={getStatusTag(syncStatus?.sync_status?.cron_sync)} />
          </Col>
          <Col span={6}>
            <Statistic title="心跳管理" value={heartbeatData?.cron_jobs_count || 0} suffix="个任务" prefix={getStatusTag(syncStatus?.sync_status?.heartbeat_sync)} />
          </Col>
          <Col span={6}>
            <Statistic title="大模型 Provider" value={llmData?.count || 0} suffix="个" prefix={getStatusTag(syncStatus?.sync_status?.model_config_sync)} />
          </Col>
          <Col span={6}>
            <Statistic title="Skills" value={skillsToolsData?.skills?.count || 0} suffix="个" prefix={getStatusTag(syncStatus?.sync_status?.skills_tools_sync)} />
          </Col>
        </Row>
        <div style={{ marginTop: 12, color: '#888', fontSize: 12 }}>
          最后同步: {formatTime(syncStatus?.last_update || '')}
        </div>
      </Card>

      <Tabs defaultActiveKey="cron" items={tabItems} />
    </div>
  )
}


export default SystemSync;
