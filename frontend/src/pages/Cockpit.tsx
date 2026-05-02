import React, { useState, useEffect, useRef } from 'react';
import { Rocket, AlertTriangle, AlertCircle, Info, CheckCircle, Send, MessageSquare, Clock, User, Bot, RefreshCw, AlertOctagon } from 'lucide-react';

interface Alert {
  id: number;
  task_id: number;
  alert_level: 'critical' | 'warning' | 'info';
  alert_type: string;
  title: string;
  description?: string;
  status: string;
  created_at: string;
}

interface Interaction {
  id: number;
  speaker: 'user' | 'sds' | 'system';
  message: string;
  created_at: string;
}

interface CockpitStats {
  critical: number;
  warning: number;
  info: number;
  total_pending: number;
}

export default function Cockpit() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [stats, setStats] = useState<CockpitStats>({ critical: 0, warning: 0, info: 0, total_pending: 0 });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 获取驾驶舱状态
  const fetchStatus = async () => {
    try {
      const res = await fetch('/api/cockpit/status');
      const data = await res.json();
      if (data.success) {
        setStats(data.stats);
      }
    } catch (error) {
      console.error('Failed to fetch cockpit status:', error);
    }
  };

  // 获取警报列表
  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/cockpit/alerts?status=pending&limit=50');
      if (!res.ok) {
        throw new Error(`HTTP error! status: ${res.status}`);
      }
      const data = await res.json();
      if (data.success) {
        setAlerts(data.alerts || []);
      } else {
        setError(data.error || '获取数据失败');
      }
    } catch (error) {
      console.error('Failed to fetch alerts:', error);
      setError('网络错误，无法获取驾驶舱数据');
    } finally {
      setLoading(false);
    }
  };

  // 获取交互历史
  const fetchInteractions = async (taskId: number) => {
    try {
      const res = await fetch(`/api/cockpit/interactions?task_id=${taskId}&limit=50`);
      const data = await res.json();
      if (data.success) {
        setInteractions(data.interactions.reverse());
      }
    } catch (error) {
      console.error('Failed to fetch interactions:', error);
    }
  };

  // 发送消息
  const sendMessage = async () => {
    if (!inputMessage.trim() || !selectedAlert) return;
    
    setSending(true);
    try {
      const res = await fetch('/api/cockpit/interact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          task_id: selectedAlert.task_id,
          alert_id: selectedAlert.id,
          message: inputMessage
        })
      });
      const data = await res.json();
      if (data.success) {
        setInputMessage('');
        fetchInteractions(selectedAlert.task_id);
        fetchAlerts();
        fetchStatus();
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      alert('发送失败，请重试');
    } finally {
      setSending(false);
    }
  };

  // 选择警报
  const handleSelectAlert = (alert: Alert) => {
    setSelectedAlert(alert);
    fetchInteractions(alert.task_id);
  };

  // 初始加载
  useEffect(() => {
    fetchStatus();
    fetchAlerts();
  }, []);

  // 滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [interactions]);

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'critical': return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case 'warning': return <AlertCircle className="w-5 h-5 text-yellow-500" />;
      case 'info': return <Info className="w-5 h-5 text-blue-500" />;
      default: return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const getAlertColor = (level: string) => {
    switch (level) {
      case 'critical': return 'border-red-500 bg-red-50';
      case 'warning': return 'border-yellow-500 bg-yellow-50';
      case 'info': return 'border-blue-500 bg-blue-50';
      default: return 'border-gray-500 bg-gray-50';
    }
  };

  const groupedAlerts = {
    critical: alerts.filter(a => a.alert_level === 'critical'),
    warning: alerts.filter(a => a.alert_level === 'warning'),
    info: alerts.filter(a => a.alert_level === 'info')
  };

  return (
    <div className="min-h-screen bg-gray-100">
      {/* 顶部标题栏 */}
      <div className="bg-white shadow-sm border-b px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Rocket className="w-8 h-8 text-blue-600" />
            <div>
              <h1 className="text-2xl font-bold text-gray-900">SDS驾驶舱</h1>
              <p className="text-sm text-gray-500">自动驾驶系统 · 人工接管中心</p>
            </div>
          </div>
          <div className="flex gap-4">
            <div className="px-4 py-2 bg-red-100 rounded-lg">
              <span className="text-red-700 font-semibold">🚨 {stats.critical}</span>
            </div>
            <div className="px-4 py-2 bg-yellow-100 rounded-lg">
              <span className="text-yellow-700 font-semibold">⚠️ {stats.warning}</span>
            </div>
            <div className="px-4 py-2 bg-blue-100 rounded-lg">
              <span className="text-blue-700 font-semibold">ℹ️ {stats.info}</span>
            </div>
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-80px)]">
        {/* 左侧：警报列表 */}
        <div className="w-1/3 bg-white border-r overflow-y-auto">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                警报列表
              </h2>
              <button 
                onClick={fetchAlerts}
                className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
                title="刷新"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertOctagon className="w-5 h-5 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-red-700">{error}</p>
                    <button 
                      onClick={fetchAlerts}
                      className="text-xs text-red-600 underline mt-1 hover:text-red-800"
                    >
                      点击重试
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* 加载状态 */}
            {loading && alerts.length === 0 && (
              <div className="text-center py-8">
                <RefreshCw className="w-8 h-8 mx-auto mb-2 text-blue-500 animate-spin" />
                <p className="text-gray-500">正在加载驾驶舱数据...</p>
              </div>
            )}

            {/* 紧急决策 */}
            {groupedAlerts.critical.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-red-600 mb-2">🚨 紧急决策 ({groupedAlerts.critical.length})</h3>
                {groupedAlerts.critical.map(alert => (
                  <div
                    key={alert.id}
                    onClick={() => handleSelectAlert(alert)}
                    className={`p-3 mb-2 rounded-lg border-l-4 cursor-pointer hover:shadow-md transition-shadow ${
                      selectedAlert?.id === alert.id ? 'ring-2 ring-blue-500' : ''
                    } ${getAlertColor(alert.alert_level)}`}
                  >
                    <div className="flex items-start gap-2">
                      {getAlertIcon(alert.alert_level)}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{alert.title}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          任务 #{alert.task_id} · {new Date(alert.created_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 待决策 */}
            {groupedAlerts.warning.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-yellow-600 mb-2">⚠️ 待决策 ({groupedAlerts.warning.length})</h3>
                {groupedAlerts.warning.map(alert => (
                  <div
                    key={alert.id}
                    onClick={() => handleSelectAlert(alert)}
                    className={`p-3 mb-2 rounded-lg border-l-4 cursor-pointer hover:shadow-md transition-shadow ${
                      selectedAlert?.id === alert.id ? 'ring-2 ring-blue-500' : ''
                    } ${getAlertColor(alert.alert_level)}`}
                  >
                    <div className="flex items-start gap-2">
                      {getAlertIcon(alert.alert_level)}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{alert.title}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          任务 #{alert.task_id} · {new Date(alert.created_at).toLocaleString('zh-CN')}
                        </div>
                        {alert.description && (
                          <div className="text-xs text-gray-600 mt-1 line-clamp-2">{alert.description}</div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 待补充 */}
            {groupedAlerts.info.length > 0 && (
              <div className="mb-4">
                <h3 className="text-sm font-medium text-blue-600 mb-2">ℹ️ 待补充 ({groupedAlerts.info.length})</h3>
                {groupedAlerts.info.map(alert => (
                  <div
                    key={alert.id}
                    onClick={() => handleSelectAlert(alert)}
                    className={`p-3 mb-2 rounded-lg border-l-4 cursor-pointer hover:shadow-md transition-shadow ${
                      selectedAlert?.id === alert.id ? 'ring-2 ring-blue-500' : ''
                    } ${getAlertColor(alert.alert_level)}`}
                  >
                    <div className="flex items-start gap-2">
                      {getAlertIcon(alert.alert_level)}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-sm truncate">{alert.title}</div>
                        <div className="text-xs text-gray-500 mt-1">
                          任务 #{alert.task_id} · {new Date(alert.created_at).toLocaleString('zh-CN')}
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* 空状态 */}
            {!loading && !error && alerts.length === 0 && (
              <div className="text-center py-8 text-gray-500">
                <CheckCircle className="w-12 h-12 mx-auto mb-2 text-green-500" />
                <p>所有系统正常运行</p>
                <p className="text-sm">暂无需要处理的警报</p>
              </div>
            )}
          </div>
        </div>

        {/* 右侧：交互区 */}
        <div className="flex-1 flex flex-col bg-gray-50">
          {selectedAlert ? (
            <>
              {/* 警报详情头部 */}
              <div className="bg-white border-b px-6 py-4">
                <div className="flex items-center justify-between">
                  <div>
                    <h2 className="text-lg font-semibold">{selectedAlert.title}</h2>
                    <p className="text-sm text-gray-500 mt-1">
                      任务 #{selectedAlert.task_id} · 
                      <span className={`ml-2 px-2 py-0.5 rounded text-xs ${
                        selectedAlert.alert_level === 'critical' ? 'bg-red-100 text-red-700' :
                        selectedAlert.alert_level === 'warning' ? 'bg-yellow-100 text-yellow-700' :
                        'bg-blue-100 text-blue-700'
                      }`}>
                        {selectedAlert.alert_level === 'critical' ? '紧急' :
                         selectedAlert.alert_level === 'warning' ? '警告' : '信息'}
                      </span>
                    </p>
                  </div>
                  <div className="text-sm text-gray-400">
                    <Clock className="w-4 h-4 inline mr-1" />
                    {new Date(selectedAlert.created_at).toLocaleString('zh-CN')}
                  </div>
                </div>
                {selectedAlert.description && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg text-sm text-gray-700 whitespace-pre-line">
                    {selectedAlert.description}
                  </div>
                )}
              </div>

              {/* 消息列表 */}
              <div className="flex-1 overflow-y-auto p-4">
                {interactions.length === 0 ? (
                  <div className="text-center py-8 text-gray-400">
                    <MessageSquare className="w-12 h-12 mx-auto mb-2" />
                    <p>暂无交互记录</p>
                    <p className="text-sm">点击下方输入框开始对话</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {interactions.map(interaction => (
                      <div
                        key={interaction.id}
                        className={`flex ${interaction.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-[80%] px-4 py-2 rounded-lg ${
                          interaction.speaker === 'user'
                            ? 'bg-blue-600 text-white'
                            : interaction.speaker === 'sds'
                            ? 'bg-white border shadow-sm'
                            : 'bg-gray-200 text-gray-700'
                        }`}>
                          <div className="flex items-center gap-2 mb-1">
                            {interaction.speaker === 'user' ? (
                              <User className="w-4 h-4" />
                            ) : (
                              <Bot className="w-4 h-4" />
                            )}
                            <span className="text-xs font-medium">
                              {interaction.speaker === 'user' ? '驾驶员' : 'SDS'}
                            </span>
                          </div>
                          <div className="text-sm whitespace-pre-wrap">{interaction.message}</div>
                          <div className={`text-xs mt-1 ${
                            interaction.speaker === 'user' ? 'text-blue-200' : 'text-gray-400'
                          }`}>
                            {new Date(interaction.created_at).toLocaleString('zh-CN')}
                          </div>
                        </div>
                      </div>
                    ))}
                    <div ref={messagesEndRef} />
                  </div>
                )}
              </div>

              {/* 输入框 */}
              <div className="bg-white border-t p-4">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                    placeholder="输入指令或问题...（例如：通过、驳回、需要修改...）"
                    className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={sending}
                  />
                  <button
                    onClick={sendMessage}
                    disabled={sending || !inputMessage.trim()}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                  >
                    <Send className="w-4 h-4" />
                    {sending ? '发送中...' : '发送'}
                  </button>
                </div>
                <div className="mt-2 flex gap-2">
                  <button
                    onClick={() => { setInputMessage('通过，执行'); }}
                    className="px-3 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                  >
                    ✓ 通过
                  </button>
                  <button
                    onClick={() => { setInputMessage('需要修改：'); }}
                    className="px-3 py-1 text-xs bg-yellow-100 text-yellow-700 rounded hover:bg-yellow-200 transition-colors"
                  >
                    💬 要求修改
                  </button>
                  <button
                    onClick={() => { setInputMessage('驳回，重新执行'); }}
                    className="px-3 py-1 text-xs bg-red-100 text-red-700 rounded hover:bg-red-200 transition-colors"
                  >
                    ✗ 驳回
                  </button>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-gray-400">
                <Rocket className="w-16 h-16 mx-auto mb-4" />
                <h3 className="text-lg font-medium text-gray-600">欢迎使用SDS驾驶舱</h3>
                <p className="mt-2">点击左侧警报开始交互</p>
                <div className="mt-6 grid grid-cols-3 gap-4 text-sm">
                  <div className="p-4 bg-white rounded-lg shadow">
                    <div className="text-2xl font-bold text-red-600">{stats.critical}</div>
                    <div className="text-gray-500">紧急决策</div>
                  </div>
                  <div className="p-4 bg-white rounded-lg shadow">
                    <div className="text-2xl font-bold text-yellow-600">{stats.warning}</div>
                    <div className="text-gray-500">待决策</div>
                  </div>
                  <div className="p-4 bg-white rounded-lg shadow">
                    <div className="text-2xl font-bold text-blue-600">{stats.info}</div>
                    <div className="text-gray-500">待补充</div>
                  </div>
                </div>
                <button 
                  onClick={fetchAlerts}
                  className="mt-6 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 flex items-center gap-2 mx-auto"
                >
                  <RefreshCw className="w-4 h-4" />
                  刷新数据
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
