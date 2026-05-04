import React, { useState, useEffect, useRef } from 'react';
import {
  Rocket, AlertTriangle, AlertCircle, Info, CheckCircle, Send, MessageSquare,
  Clock, User, Bot, RefreshCw, AlertOctagon, TrendingUp, BarChart3, PieChart,
  Activity, FileText, Zap, ChevronRight, Filter, CheckSquare, XCircle, RotateCcw,
  Wifi, WifiOff
} from 'lucide-react';
import { socketIO } from '../utils/socket';
import { Pie, Line } from 'react-chartjs-2';
import {
  Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale,
  LinearScale, PointElement, LineElement, Title, Filler
} from 'chart.js';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title, Filler);

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

interface TaskStats {
  total: number;
  pending: number;
  in_progress: number;
  completed: number;
  pending_review: number;
  failed: number;
}

interface ThroughputData {
  labels: string[];
  completed: number[];
  created: number[];
}

export default function Cockpit() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selectedAlert, setSelectedAlert] = useState<Alert | null>(null);
  const [interactions, setInteractions] = useState<Interaction[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [taskStats, setTaskStats] = useState<TaskStats>({ total: 0, pending: 0, in_progress: 0, completed: 0, pending_review: 0, failed: 0 });
  const [throughput, setThroughput] = useState<ThroughputData>({ labels: [], completed: [], created: [] });
  const [lastUpdated, setLastUpdated] = useState(new Date());
  const [filter, setFilter] = useState<'all' | 'critical' | 'warning' | 'info'>('all');
  const [wsConnected, setWsConnected] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const refreshInterval = useRef<NodeJS.Timeout | null>(null);

  // 获取任务统计
  const fetchTaskStats = async () => {
    try {
      const res = await fetch('/api/tasks/stats');
      const data = await res.json();
      if (data.success) {
        setTaskStats(data.stats);
      }
    } catch (e) { console.error('stats error:', e); }
  };

  // 获取吞吐量数据
  const fetchThroughput = async () => {
    try {
      const res = await fetch('/api/tasks/throughput?days=7');
      const data = await res.json();
      if (data.success) {
        setThroughput(data.data);
      }
    } catch (e) { console.error('throughput error:', e); }
  };

  // 获取警报
  const fetchAlerts = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/cockpit/alerts?status=pending&limit=50');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      if (data.success) {
        setAlerts(data.alerts || []);
      } else {
        setError(data.error || '获取数据失败');
      }
    } catch (e) {
      console.error('alerts error:', e);
      setError('网络错误，无法获取驾驶舱数据');
    } finally {
      setLoading(false);
      setLastUpdated(new Date());
    }
  };

  // 获取交互
  const fetchInteractions = async (taskId: number) => {
    try {
      const res = await fetch(`/api/cockpit/interactions?task_id=${taskId}&limit=50`);
      const data = await res.json();
      if (data.success) {
        setInteractions(data.interactions.reverse());
      }
    } catch (e) { console.error('interactions error:', e); }
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
        fetchTaskStats();
      }
    } catch (e) {
      console.error('send error:', e);
      alert('发送失败');
    } finally {
      setSending(false);
    }
  };

  // 选择警报
  const handleSelectAlert = (alert: Alert) => {
    setSelectedAlert(alert);
    fetchInteractions(alert.task_id);
  };

  // 初始加载 + 定时刷新
  useEffect(() => {
    fetchTaskStats();
    fetchThroughput();
    fetchAlerts();
    refreshInterval.current = setInterval(() => {
      fetchTaskStats();
      fetchAlerts();
    }, 30000);
    return () => {
      if (refreshInterval.current) clearInterval(refreshInterval.current);
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [interactions]);

  // 图表数据
  const pieData = {
    labels: ['待执行', '执行中', '待审核', '已完成', '失败'],
    datasets: [{
      data: [taskStats.pending, taskStats.in_progress, taskStats.pending_review, taskStats.completed, taskStats.failed],
      backgroundColor: ['#fbbf24', '#3b82f6', '#a78bfa', '#10b981', '#ef4444'],
      borderWidth: 2,
      borderColor: '#fff',
    }]
  };

  const lineData = {
    labels: throughput.labels,
    datasets: [
      {
        label: '已完成',
        data: throughput.completed,
        borderColor: '#10b981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#10b981',
      },
      {
        label: '新建',
        data: throughput.created,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
        tension: 0.4,
        pointRadius: 4,
        pointBackgroundColor: '#3b82f6',
      }
    ]
  };

  const filteredAlerts = filter === 'all' ? alerts : alerts.filter(a => a.alert_level === filter);

  const groupedAlerts = {
    critical: alerts.filter(a => a.alert_level === 'critical'),
    warning: alerts.filter(a => a.alert_level === 'warning'),
    info: alerts.filter(a => a.alert_level === 'info')
  };

  const getAlertIcon = (level: string) => {
    switch (level) {
      case 'critical': return <AlertTriangle className="w-5 h-5 text-red-500" />;
      case 'warning': return <AlertCircle className="w-5 h-5 text-amber-500" />;
      case 'info': return <Info className="w-5 h-5 text-blue-500" />;
      default: return <Info className="w-5 h-5 text-gray-500" />;
    }
  };

  const getAlertColor = (level: string) => {
    switch (level) {
      case 'critical': return 'border-red-400 bg-red-50/80 hover:bg-red-100';
      case 'warning': return 'border-amber-400 bg-amber-50/80 hover:bg-amber-100';
      case 'info': return 'border-blue-400 bg-blue-50/80 hover:bg-blue-100';
      default: return 'border-gray-400 bg-gray-50 hover:bg-gray-100';
    }
  };

  const StatCard = ({ icon: Icon, label, value, color, subtext }: any) => (
    <div className="bg-white/70 backdrop-blur-sm rounded-xl p-4 border border-white/50 shadow-sm hover:shadow-md transition-all">
      <div className="flex items-center justify-between mb-2">
        <Icon className={`w-5 h-5 ${color}`} />
        <span className="text-xs text-gray-400">{subtext}</span>
      </div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-sm text-gray-500">{label}</div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 via-gray-50 to-blue-50">
      {/* 顶部标题栏 */}
      <div className="bg-white/80 backdrop-blur-md border-b border-gray-200/50 px-6 py-4 sticky top-0 z-10">
        <div className="flex items-center justify-between max-w-[1800px] mx-auto">
          <div className="flex items-center gap-3">
            {wsConnected ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-600 rounded-full text-xs font-medium border border-emerald-200">
                <Wifi className="w-3.5 h-3.5" /> 实时
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 text-gray-500 rounded-full text-xs font-medium border border-gray-200">
                <WifiOff className="w-3.5 h-3.5" /> 轮询
              </div>
            )}
            <div className="p-2 bg-gradient-to-br from-blue-500 to-indigo-600 rounded-xl shadow-lg shadow-blue-500/25">
              <Rocket className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-xl font-bold bg-gradient-to-r from-gray-900 to-gray-600 bg-clip-text text-transparent">
                SDS 驾驶舱
              </h1>
              <p className="text-xs text-gray-500 flex items-center gap-1">
                <Zap className="w-3 h-3" />
                自动驾驶系统 · 人工接管中心
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            {wsConnected ? (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-emerald-50 text-emerald-600 rounded-full text-xs font-medium border border-emerald-200">
                <Wifi className="w-3.5 h-3.5" /> 实时
              </div>
            ) : (
              <div className="flex items-center gap-1.5 px-2.5 py-1 bg-gray-100 text-gray-500 rounded-full text-xs font-medium border border-gray-200">
                <WifiOff className="w-3.5 h-3.5" /> 轮询
              </div>
            )}
            <div className="flex items-center gap-1.5 text-xs text-gray-400 bg-gray-100/80 px-3 py-1.5 rounded-full">
              <Clock className="w-3 h-3" />
              更新于 {lastUpdated.toLocaleTimeString('zh-CN')}
            </div>
            <button
              onClick={() => { fetchTaskStats(); fetchThroughput(); fetchAlerts(); }}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="刷新"
            >
              <RefreshCw className={`w-4 h-4 text-gray-600 ${loading ? 'animate-spin' : ''}`} />
            </button>
          </div>
        </div>
      </div>

      <div className="max-w-[1800px] mx-auto p-6 space-y-6">
        {/* 统计卡片区域 */}
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
          <StatCard icon={BarChart3} label="总任务" value={taskStats.total} color="text-gray-600" subtext="全部" />
          <StatCard icon={Clock} label="待执行" value={taskStats.pending} color="text-amber-500" subtext="Pending" />
          <StatCard icon={Activity} label="执行中" value={taskStats.in_progress} color="text-blue-500" subtext="Running" />
          <StatCard icon={CheckSquare} label="待审核" value={taskStats.pending_review} color="text-purple-500" subtext="Review" />
          <StatCard icon={CheckCircle} label="已完成" value={taskStats.completed} color="text-emerald-500" subtext="Done" />
          <StatCard icon={XCircle} label="失败" value={taskStats.failed} color="text-red-500" subtext="Failed" />
        </div>

        {/* 图表区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* 任务分布饼图 */}
          <div className="bg-white/70 backdrop-blur-sm rounded-xl p-5 border border-white/50 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <PieChart className="w-4 h-4 text-indigo-500" />
              任务状态分布
            </h3>
            <div className="h-48">
              <Pie
                data={pieData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  plugins: {
                    legend: { position: 'right', labels: { boxWidth: 12, font: { size: 11 } } }
                  }
                }}
              />
            </div>
          </div>

          {/* 吞吐量趋势图 */}
          <div className="lg:col-span-2 bg-white/70 backdrop-blur-sm rounded-xl p-5 border border-white/50 shadow-sm">
            <h3 className="text-sm font-semibold text-gray-700 mb-4 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-emerald-500" />
              7天吞吐量趋势
            </h3>
            <div className="h-48">
              <Line
                data={lineData}
                options={{
                  responsive: true,
                  maintainAspectRatio: false,
                  interaction: { intersect: false, mode: 'index' },
                  plugins: {
                    legend: { position: 'top', align: 'end', labels: { boxWidth: 12, font: { size: 11 }, usePointStyle: true } }
                  },
                  scales: {
                    y: { beginAtZero: true, grid: { color: 'rgba(0,0,0,0.05)' } },
                    x: { grid: { display: false } }
                  }
                }}
              />
            </div>
          </div>
        </div>

        {/* 主内容区：警报 + 聊天 */}
        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 h-[600px]">
          {/* 左侧：警报列表 */}
          <div className="lg:col-span-2 bg-white/70 backdrop-blur-sm rounded-xl border border-white/50 shadow-sm flex flex-col overflow-hidden">
            {/* 过滤器 */}
            <div className="p-4 border-b border-gray-100">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-gray-700 flex items-center gap-2">
                  <AlertTriangle className="w-4 h-4" />
                  警报列表
                </h2>
                <span className="text-xs text-gray-400">{filteredAlerts.length} 条</span>
              </div>
              <div className="flex gap-1.5">
                {(['all', 'critical', 'warning', 'info'] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setFilter(f)}
                    className={`px-2.5 py-1 text-xs rounded-full transition-colors ${
                      filter === f
                        ? f === 'critical' ? 'bg-red-500 text-white' :
                          f === 'warning' ? 'bg-amber-500 text-white' :
                          f === 'info' ? 'bg-blue-500 text-white' :
                          'bg-gray-800 text-white'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {f === 'all' ? '全部' : f === 'critical' ? `紧急(${groupedAlerts.critical.length})` : f === 'warning' ? `警告(${groupedAlerts.warning.length})` : `信息(${groupedAlerts.info.length})`}
                  </button>
                ))}
              </div>
            </div>

            {/* 错误提示 */}
            {error && (
              <div className="mx-4 mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                <div className="flex items-start gap-2">
                  <AlertOctagon className="w-4 h-4 text-red-500 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-red-700">{error}</p>
                    <button onClick={fetchAlerts} className="text-xs text-red-600 underline mt-1">重试</button>
                  </div>
                </div>
              </div>
            )}

            {/* 警报列表 */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2">
              {loading && alerts.length === 0 && (
                <div className="text-center py-8">
                  <RefreshCw className="w-8 h-8 mx-auto mb-2 text-blue-500 animate-spin" />
                  <p className="text-gray-500 text-sm">加载中...</p>
                </div>
              )}

              {filteredAlerts.length === 0 && !loading && (
                <div className="text-center py-8 text-gray-400">
                  <CheckCircle className="w-10 h-10 mx-auto mb-2 text-emerald-400" />
                  <p className="text-sm">暂无警报</p>
                </div>
              )}

              {filteredAlerts.map(alert => (
                <div
                  key={alert.id}
                  onClick={() => handleSelectAlert(alert)}
                  className={`p-3 rounded-lg border-l-4 cursor-pointer transition-all ${
                    selectedAlert?.id === alert.id
                      ? 'ring-2 ring-blue-500 shadow-md bg-white'
                      : getAlertColor(alert.alert_level)
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {getAlertIcon(alert.alert_level)}
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm text-gray-800 truncate">{alert.title}</div>
                      {alert.description && (
                        <div className="text-xs text-gray-500 mt-1 line-clamp-2">{alert.description}</div>
                      )}
                      <div className="flex items-center gap-2 mt-1.5">
                        <span className="text-[10px] px-1.5 py-0.5 bg-gray-200 rounded text-gray-600">#{alert.task_id}</span>
                        <span className="text-[10px] text-gray-400">
                          {new Date(alert.created_at).toLocaleString('zh-CN', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                        </span>
                      </div>
                    </div>
                    <ChevronRight className="w-4 h-4 text-gray-300 flex-shrink-0 mt-1" />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* 右侧：LLM 交互面板 */}
          <div className="lg:col-span-3 bg-white/70 backdrop-blur-sm rounded-xl border border-white/50 shadow-sm flex flex-col overflow-hidden">
            {selectedAlert ? (
              <>
                {/* 选中警报头部 */}
                <div className="p-4 border-b border-gray-100 bg-gradient-to-r from-blue-50/50 to-indigo-50/50">
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        {getAlertIcon(selectedAlert.alert_level)}
                        <h3 className="font-semibold text-gray-800">{selectedAlert.title}</h3>
                      </div>
                      <p className="text-xs text-gray-500">任务 #{selectedAlert.task_id} · {selectedAlert.alert_type}</p>
                    </div>
                    <button
                      onClick={() => setSelectedAlert(null)}
                      className="p-1 hover:bg-gray-200 rounded transition-colors"
                    >
                      <XCircle className="w-4 h-4 text-gray-400" />
                    </button>
                  </div>
                </div>

                {/* 聊天区域 */}
                <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-gray-50/30 to-transparent">
                  {interactions.length === 0 ? (
                    <div className="text-center py-12 text-gray-400">
                      <MessageSquare className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                      <p className="text-sm">暂无交互记录</p>
                      <p className="text-xs mt-1">点击下方输入框开始与 SDS 对话</p>
                    </div>
                  ) : (
                    <>
                      {interactions.map(interaction => (
                        <div
                          key={interaction.id}
                          className={`flex ${interaction.speaker === 'user' ? 'justify-end' : 'justify-start'}`}
                        >
                          <div className={`max-w-[85%] px-4 py-3 rounded-2xl shadow-sm ${
                            interaction.speaker === 'user'
                              ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white rounded-br-md'
                              : interaction.speaker === 'sds'
                              ? 'bg-white border border-gray-200 rounded-bl-md'
                              : 'bg-gray-100 text-gray-600 rounded-bl-md'
                          }`}>
                            <div className="flex items-center gap-1.5 mb-1">
                              {interaction.speaker === 'user' ? (
                                <User className="w-3.5 h-3.5" />
                              ) : (
                                <Bot className="w-3.5 h-3.5" />
                              )}
                              <span className="text-[10px] font-medium opacity-80">
                                {interaction.speaker === 'user' ? '驾驶员' : 'SDS'}
                              </span>
                            </div>
                            <div className="text-sm whitespace-pre-wrap leading-relaxed">{interaction.message}</div>
                            <div className={`text-[10px] mt-1.5 ${interaction.speaker === 'user' ? 'text-blue-200' : 'text-gray-400'}`}>
                              {new Date(interaction.created_at).toLocaleString('zh-CN')}
                            </div>
                          </div>
                        </div>
                      ))}
                      <div ref={messagesEndRef} />
                    </>
                  )}
                </div>

                {/* 输入区域 */}
                <div className="p-4 border-t border-gray-100 bg-white/80">
                  {/* 快捷按钮 */}
                  <div className="flex gap-2 mb-3">
                    <button onClick={() => setInputMessage('通过，任务执行符合预期')} className="px-3 py-1.5 text-xs bg-emerald-50 text-emerald-700 rounded-lg hover:bg-emerald-100 transition-colors flex items-center gap-1 border border-emerald-200">
                      <CheckCircle className="w-3 h-3" /> 通过
                    </button>
                    <button onClick={() => setInputMessage('需要修改：')} className="px-3 py-1.5 text-xs bg-amber-50 text-amber-700 rounded-lg hover:bg-amber-100 transition-colors flex items-center gap-1 border border-amber-200">
                      <RotateCcw className="w-3 h-3" /> 要求修改
                    </button>
                    <button onClick={() => setInputMessage('驳回，请重新评估后执行')} className="px-3 py-1.5 text-xs bg-red-50 text-red-700 rounded-lg hover:bg-red-100 transition-colors flex items-center gap-1 border border-red-200">
                      <XCircle className="w-3 h-3" /> 驳回
                    </button>
                    <button onClick={() => setInputMessage('请提供更多上下文信息')} className="px-3 py-1.5 text-xs bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 transition-colors flex items-center gap-1 border border-blue-200">
                      <FileText className="w-3 h-3" /> 补充信息
                    </button>
                  </div>

                  {/* 输入框 */}
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={inputMessage}
                      onChange={(e) => setInputMessage(e.target.value)}
                      onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
                      placeholder="输入指令或问题...（例如：通过、驳回、需要修改...）"
                      className="flex-1 px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-400 text-sm transition-all"
                      disabled={sending}
                    />
                    <button
                      onClick={sendMessage}
                      disabled={sending || !inputMessage.trim()}
                      className="px-4 py-2.5 bg-gradient-to-r from-blue-500 to-indigo-600 text-white rounded-xl hover:from-blue-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-lg shadow-blue-500/25 transition-all text-sm font-medium"
                    >
                      <Send className="w-4 h-4" />
                      {sending ? '发送中...' : '发送'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="flex-1 flex items-center justify-center">
                <div className="text-center text-gray-400">
                  <div className="w-20 h-20 mx-auto mb-4 bg-gradient-to-br from-blue-100 to-indigo-100 rounded-2xl flex items-center justify-center">
                    <Rocket className="w-10 h-10 text-blue-500" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-700 mb-1">欢迎使用 SDS 驾驶舱</h3>
                  <p className="text-sm text-gray-500 mb-6">点击左侧警报开始与 AI 交互</p>
                  <div className="grid grid-cols-3 gap-3 max-w-sm mx-auto">
                    <div className="p-4 bg-white rounded-xl shadow-sm border border-gray-100">
                      <div className="text-2xl font-bold text-red-500">{groupedAlerts.critical.length}</div>
                      <div className="text-xs text-gray-500 mt-1">紧急决策</div>
                    </div>
                    <div className="p-4 bg-white rounded-xl shadow-sm border border-gray-100">
                      <div className="text-2xl font-bold text-amber-500">{groupedAlerts.warning.length}</div>
                      <div className="text-xs text-gray-500 mt-1">待决策</div>
                    </div>
                    <div className="p-4 bg-white rounded-xl shadow-sm border border-gray-100">
                      <div className="text-2xl font-bold text-blue-500">{groupedAlerts.info.length}</div>
                      <div className="text-xs text-gray-500 mt-1">待补充</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
