impor
)t React, { useState, useEffect, useMemo } from 'react';
import { socketIO } from '../utils/socket';
import { Plus, Search, Filter, Save, Star, X, Calendar, Tag, Layout, List, Code, FileCode, Brain, Download } from "lucide-react";
import { TaskAccordion } from '../components/TaskAccordion';
import { TaskAttachments } from '../components/TaskAttachments';
import EditLockIndicator from '../components/EditLockIndicator';

interface Task {
  id: number;
  title: string;
  description: string;
  status: string;
  priority: string;
  tags: string;
  project_id: number;
  project_name: string;
  created_at: string;
  due_date?: string;
  created_date?: string;
}

interface SavedView {
  id: number;
  name: string;
  filters: TaskFilters;
  is_default: boolean;
}

interface TaskFilters {
  search?: string;
  tags?: string;
  date_from?: string;
  date_to?: string;
  quick_filter?: string;
  project_id?: string;
  status?: string;
}

interface Project {
  id: number;
  name: string;
  status?: string;
}

// 状态Tab配置
const statusTabs = [
  { key: 'pending', label: '🔥 待处理', color: '#ef4444', statuses: ['todo', 'pending'] },
  { key: 'in_progress', label: '▶️ 进行中', color: '#3b82f6', statuses: ['in_progress'] },
  { key: 'pending_review', label: '👁️ 待审阅', color: '#f59e0b', statuses: ['pending_review'] },
  { key: 'completed', label: '✅ 已完成', color: '#10b981', statuses: ['completed'] },

];

const modalOverlayStyle: React.CSSProperties = {
  position: "fixed",
  top: 0,
  left: 0,
  right: 0,
  bottom: 0,
  backgroundColor: "#f6f5f4",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 99999,
};

const Tasks: React.FC = () => {
  // 原有状态
  const [tasks, setTasks] = useState<Task[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [projectFilter, setProjectFilter] = useState('');
  const [statusFilter, setStatusFilter] = useState('');
  const [projectStatusFilter, setProjectStatusFilter] = useState('');
  
  // 新增筛选状态
  const [search, setSearch] = useState('');
  const [tags, setTags] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');
  const [quickFilter, setQuickFilter] = useState('');
  const [flashingTab, setFlashingTab] = useState<string | null>(null);
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);
  const [showSaveViewModal, setShowSaveViewModal] = useState(false);
  const [viewName, setViewName] = useState('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [showJsonEditor, setShowJsonEditor] = useState(false);
  const [jsonEditorContent, setJsonEditorContent] = useState('');
  const [showPhaseR, setShowPhaseR] = useState(false);
  const [phaseRData, setPhaseRData] = useState<any>(null);
  const [phaseRLoading, setPhaseRLoading] = useState(false);
  const [showAttachments, setShowAttachments] = useState(false);
  const [detailTab, setDetailTab] = React.useState("detail");
  const [execRecords, setExecRecords] = React.useState([]);
  const [execLoading, setExecLoading] = React.useState(false);
  const loadExecRecords = async (taskId) => {
    setExecLoading(true);
    try {
      const r = await fetch("/api/tasks/" + taskId + "/executions");
      const d = await r.json();
      if (d.success) setExecRecords(d.records);
    } catch(e) {}
    setExecLoading(false);
  };
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  
  // 视图模式状态
  const [viewMode, setViewMode] = useState<'tab' | 'list' | 'kanban'>('tab');
  const [activeStatusTab, setActiveStatusTab] = useState('pending');
  const [tabCurrentPage, setTabCurrentPage] = useState(1);
  
  // 任务统计
  const [taskStats, setTaskStats] = useState<Record<string, number>>({});
  // 防抖搜索
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // 删除任务
  const handleDeleteTask = async (taskId: number) => {
    if (!confirm('确定要删除这个任务吗？')) return;
    try {
      const res = await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        fetchTasks();
      } else {
        alert(data.error || '删除失败');
      }
    } catch (error) {
      console.error('Failed to delete task:', error);
      alert('删除失败');
    }
  }

  // 审核任务
  const handleReviewTask = async (taskId: number, action: 'approve' | 'reject' | 'skip' | 'feedback', feedback?: string) => {
    const actionLabels = { approve: '通过', reject: '驳回', skip: '跳过', feedback: '要求修改' };
    if (action !== 'feedback' && !confirm(`确定要${actionLabels[action]}这个任务吗？`)) return;
    
    try {
      const body: any = { action };
      if (action === 'feedback' && feedback) {
        body.feedback = feedback;
      }
      
      const res = await fetch(`/api/tasks/${taskId}/review`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      });
      const data = await res.json();
      if (data.success) {
        alert(data.message || '操作成功');
        fetchTasks();
      } else {
        alert(data.error || '操作失败');
      }
    } catch (error) {
      console.error('Failed to review task:', error);
      alert('操作失败');
    }
  }
  
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedSearch(search);
    }, 300);
    return () => clearTimeout(timer);
  }, [search]);

  // 获取保存的视图
  const fetchSavedViews = async () => {
    try {
      const res = await fetch('/api/saved-views');
      const data = await res.json();
      if (data.success) {
        setSavedViews(data.views);
      }
    } catch (error) {
      console.error('Failed to fetch saved views:', error);
    }
  };
  // 获取任务统计
  const fetchTaskStats = async () => {
    try {
      const res = await fetch("/api/tasks/stats");
      const data = await res.json();
      if (data.success) {
        setTaskStats(data.stats);
      }
    } catch (error) {
      console.error("Failed to fetch task stats:", error);
    }
  };

  // 获取任务
  const fetchTasks = async () => {
    try {
      const params = new URLSearchParams();
      if (debouncedSearch) params.append('search', debouncedSearch);
      if (tags) params.append('tags', tags);
      if (dateFrom) params.append('date_from', dateFrom);
      if (dateTo) params.append('date_to', dateTo);
      if (quickFilter) params.append('quick_filter', quickFilter);
      if (projectFilter) params.append('project_id', projectFilter);
      if (statusFilter) params.append('status', statusFilter);
      if (projectStatusFilter) params.append('project_status', projectStatusFilter);
      
      
      params.append("per_page", "5000");
      params.append('sort_field', sortField);
      params.append('sort_order', sortOrder);
      const res = await fetch(`/api/tasks?${params}`);
      const data = await res.json();
      if (data.success) {
        setTasks(data.tasks);
      }
    } catch (error) {
      console.error('Failed to fetch tasks:', error);
    }
  };

  // 获取项目
  const fetchProjects = async () => {
    try {
      const res = await fetch('/api/projects');
      const data = await res.json();
      if (data.success) {
        setProjects(data.projects);
      }
    } catch (error) {
      console.error('Failed to fetch projects:', error);
    }
  };

// WebSocket 实时同步
  const [wsConnected, setWsConnected] = useState(false);
  const [highlightedTasks, setHighlightedTasks] = useState<Set<number>>(new Set());

  useEffect(() => {
    const userStr = localStorage.getItem('user');
    const user = userStr ? JSON.parse(userStr) : null;
    
    socketIO.connect({
      url: window.location.origin,
      userId: user?.id?.toString() || "anonymous",
      username: user?.username || "访客",
      onConnect: () => {
        setWsConnected(true);
        if (projectFilter) {
          socketIO.joinProjectRoom(projectFilter);
        }
      },
      onDisconnect: () => setWsConnected(false),
      onTaskCreated: (task) => {
        const matchesFilter = !statusFilter || statusFilter === task.status;
        if (matchesFilter) {
          setTasks(prev => [task, ...prev]);
          setHighlightedTasks(prev => new Set([...prev, task.id]));
          setTimeout(() => setHighlightedTasks(prev => { const n = new Set(prev); n.delete(task.id); return n; }), 3000);
        }
        fetchTaskStats();
      },
      onTaskUpdated: (task) => {
        setTasks(prev => prev.map(t => t.id === task.id ? { ...t, ...task } : t));
        setHighlightedTasks(prev => new Set([...prev, task.id]));
        setTimeout(() => setHighlightedTasks(prev => { const n = new Set(prev); n.delete(task.id); return n; }), 2000);
        fetchTaskStats();
      },
      onTaskDeleted: (taskId) => {
        setTasks(prev => prev.filter(t => t.id !== parseInt(taskId)));
        fetchTaskStats();
      },
    });
    return () => { socketIO.disconnect(); };
  }, [projectFilter, statusFilter]);

  useEffect(() => {
    fetchTasks();
    fetchProjects();
    fetchSavedViews();
    fetchTaskStats();
  }, [debouncedSearch, tags, dateFrom, dateTo, quickFilter, projectFilter, statusFilter, projectStatusFilter, sortField, sortOrder]);

  // 实时刷新 - 每30秒自动刷新
  useEffect(() => {
    const timer = setInterval(() => {
      fetchTasks();
    }, 30000); // 30 seconds

    return () => clearInterval(timer);
  }, [debouncedSearch, tags, dateFrom, dateTo, quickFilter, projectFilter, statusFilter, projectStatusFilter, sortField, sortOrder]);

  // 保存视图
  const handleSaveView = async () => {
    if (!viewName.trim()) {
      alert('请输入视图名称');
      return;
    }
    
    try {
      const filters: TaskFilters = {};
      if (debouncedSearch) filters.search = debouncedSearch;
      if (tags) filters.tags = tags;
      if (dateFrom) filters.date_from = dateFrom;
      if (dateTo) filters.date_to = dateTo;
      if (quickFilter) filters.quick_filter = quickFilter;
      if (projectFilter) filters.project_id = projectFilter;
      if (statusFilter) filters.status = statusFilter;
      
      const res = await fetch('/api/saved-views', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: viewName, filters })
      });
      
      const data = await res.json();
      if (data.success) {
        alert('视图已保存');
        setViewName('');
        setShowSaveViewModal(false);
        fetchSavedViews();
    fetchTaskStats();
      }
    } catch (error) {
      console.error('Failed to save view:', error);
      alert('保存失败');
    }
  };

  // 加载视图
  const loadView = (view: SavedView) => {
    const f = view.filters;
    setSearch(f.search || '');
    setTags(f.tags || '');
    setDateFrom(f.date_from || '');
    setDateTo(f.date_to || '');
    setQuickFilter(f.quick_filter || '');
    setProjectFilter(f.project_id || '');
    setStatusFilter(f.status || '');
  };

  // 删除视图
  const deleteView = async (viewId: number) => {
    if (!confirm('确定要删除这个视图吗？')) return;
    
    try {
      const res = await fetch(`/api/saved-views/${viewId}`, { method: 'DELETE' });
      const data = await res.json();
      if (data.success) {
        fetchSavedViews();
    fetchTaskStats();
      } else {
        alert(data.error || '删除失败');
      }
    } catch (error) {
      console.error('Failed to delete view:', error);
      alert('删除失败');
    }
  };

  // 清除筛选
  const clearFilters = () => {
    setSearch('');
    setTags('');
    setDateFrom('');
    setDateTo('');
    setQuickFilter('');
    setProjectFilter('');
    setStatusFilter('');
    setProjectStatusFilter('');
  };

  // 计算激活的筛选条件
  const activeFilters = useMemo(() => {
    const filters = [];
    if (debouncedSearch) filters.push({ type: 'search', label: `搜索：${debouncedSearch}` });
    if (tags) filters.push({ type: 'tags', label: `标签：${tags}` });
    if (quickFilter) {
      const labels: Record<string, string> = { today: '今天', this_week: '本周', this_month: '本月' };
      filters.push({ type: 'quick', label: labels[quickFilter] || quickFilter });
    }
    if (dateFrom || dateTo) {
      filters.push({ type: 'date', label: `${dateFrom || '...'} ~ ${dateTo || '...'}` });
    }
    return filters;
  }, [debouncedSearch, tags, quickFilter, dateFrom, dateTo]);

  // 按项目状态统计
  const projectStatusStats = useMemo(() => {
    const stats: Record<string, number> = {};
    tasks.forEach((task) => {
      const ps = task.project_status || 'unknown';
      stats[ps] = (stats[ps] || 0) + 1;
    });
    return stats;
  }, [tasks]);

  // Tab视图：按状态过滤任务
  const filteredTasksByTab = useMemo(() => {
    const tabConfig = statusTabs.find(t => t.key === activeStatusTab);
    if (!tabConfig) return tasks;
    return tasks.filter(task => tabConfig.statuses.includes(task.status));
  }, [tasks, activeStatusTab]);

  // Tab视图：分页
  const tabPaginatedTasks = useMemo(() => {
    const start = (tabCurrentPage - 1) * pageSize;
    return filteredTasksByTab.slice(start, start + pageSize);
  }, [filteredTasksByTab, tabCurrentPage, pageSize]);

  const tabTotalPages = Math.ceil(filteredTasksByTab.length / pageSize);

  // 列表视图：分页
  const listPaginatedTasks = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return tasks.slice(start, start + pageSize);
  }, [tasks, currentPage, pageSize]);

  const listTotalPages = Math.ceil(tasks.length / pageSize);

  // Tab视图：各状态数量统计（使用API统计，不是本地已加载的任务）
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = statusTabs.reduce(
      (acc, tab) => ({ ...acc, [tab.key]: 0 }),
      {} as Record<string, number>
    );
    statusTabs.forEach(tab => {
      tab.statuses.forEach(status => {
        counts[tab.key] += taskStats[status] || 0;
      });
    });
    return counts;
  }, [taskStats]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* 顶部工具栏 */}
      <div className="flex flex-col gap-2 mb-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
              {[{k:'tab',l:'分类'},{k:'kanban',l:'汇总'}].map(v => (
                <button key={v.k}
                  onClick={() => { setViewMode(v.k); v.k==='tab' ? setTabCurrentPage(1) : setCurrentPage(1); }}
                  className={'px-3 py-1.5 rounded-md text-sm font-medium transition-colors ' + (viewMode === v.k ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700')}
                >{v.l}</button>
              ))}
            </div>
            <button onClick={() => setShowFilters(!showFilters)}
              className={'flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium border ' + (showFilters ? 'bg-blue-50 border-blue-500 text-blue-600' : 'border-gray-200 text-gray-500 hover:bg-gray-50')}
            ><Filter size={13} /> 筛选</button>
            <button onClick={() => setShowSaveViewModal(true)}
              className="flex items-center gap-1 px-3 py-1.5 rounded-md text-xs font-medium border border-gray-200 text-gray-500 hover:bg-gray-50"
            ><Save size={13} /> 保存</button>
          </div>
          <button onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1 px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
          ><Plus size={14} /> 新建</button>
        </div>
        <div className="relative w-72">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400" size={16} />
          <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索任务..." className="w-full pl-9 pr-4 py-2 border border-gray-200 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-sm"
          />
          {search && (
            <button onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
            ><X size={14} /></button>
          )}
        </div>
      </div>      {/* 保存的视图快捷方式 */}
      {savedViews.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-4">
          {savedViews.map((view) => (
            <div
              key={view.id}
              className="inline-flex items-center gap-2 px-3 py-1.5 bg-white border border-white/8 rounded-lg hover:bg-[#f6f5f4] cursor-pointer group"
              onClick={() => loadView(view)}
            >
              {view.is_default && <Star size={14} className="text-yellow-500 fill-yellow-500" />}
              <span className="text-sm text-[#31302e]">{view.name}</span>
              {!view.is_default && (
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteView(view.id);
                  }}
                  className="opacity-0 group-hover:opacity-100 text-red-500 hover:text-red-700"
                >
                  <X size={14} />
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {/* 筛选面板 */}
      {showFilters && (
        <div className="bg-white rounded-lg shadow border border-white/8 p-4 mb-4">
          <div className="flex flex-wrap items-start gap-6">
            {/* 快速筛选 */}
            <div className="flex flex-col gap-2">
              <span className="text-xs text-gray-500 font-medium">快速筛选</span>
              <div className="flex flex-wrap gap-2">
                {[
                  { key: 'today', label: '今天的任务' },
                  { key: 'this_week', label: '本周的任务' },
                  { key: 'this_month', label: '本月的任务' },
                ].map((item) => (
                  <button
                    key={item.key}
                    onClick={() => setQuickFilter(quickFilter === item.key ? '' : item.key)}
                    className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                      quickFilter === item.key
                        ? 'bg-blue-500 text-white shadow-sm'
                        : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>
            {/* 日期范围 */}
            <div className="flex flex-col gap-2">
              <span className="text-xs text-gray-500 font-medium">日期范围</span>
              <div className="flex items-center gap-2">
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => { setDateFrom(e.target.value); setQuickFilter(''); }}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
                <span className="text-xs text-gray-400">~</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => { setDateTo(e.target.value); setQuickFilter(''); }}
                  className="px-2 py-1.5 border border-gray-200 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>
            {/* 激活的筛选条件 */}
            {activeFilters.length > 0 && (
              <div className="flex flex-col gap-2">
                <span className="text-xs text-gray-500 font-medium">当前筛选</span>
                <div className="flex flex-wrap gap-2">
                  {activeFilters.map((f: { type: string; label: string }, i: number) => (
                    <span
                      key={i}
                      className="inline-flex items-center gap-1 px-2 py-1 bg-blue-50 text-blue-700 rounded-full text-xs font-medium"
                    >
                      {f.label}
                      <button
                        onClick={() => {
                          if (f.type === 'search') setSearch('');
                          else if (f.type === 'tags') setTags('');
                          else if (f.type === 'quick') setQuickFilter('');
                          else if (f.type === 'date') { setDateFrom(''); setDateTo(''); }
                        }}
                        className="hover:text-blue-900"
                      >
                        <X size={12} />
                      </button>
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab视图 */}
      {viewMode === 'tab' && (
        <div>
          {/* 状态Tab */}
          <div className="flex flex-wrap gap-2 mb-4">
            {statusTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setActiveStatusTab(tab.key); setTabCurrentPage(1); window.scrollTo({ top: 0, behavior: "smooth" }); setFlashingTab(tab.key); setTimeout(() => setFlashingTab(null), 600); }}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeStatusTab === tab.key
                    ? 'text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                } ${flashingTab === tab.key ? 'ring-2 ring-offset-1 scale-105 animate-pulse' : ''}`}
                style={activeStatusTab === tab.key ? { backgroundColor: tab.color } : {}}
              >
                <span>{tab.label}</span>
                <span className={`px-2 py-0.5 rounded-full text-xs ${
                  activeStatusTab === tab.key ? 'bg-white/20 text-white' : 'bg-gray-200 text-gray-600'
                }`}>
                  {statusCounts[tab.key] || 0}
                </span>
              </button>
            ))}
          </div>

          {/* Tab视图任务列表 */}
          <div className="bg-white rounded-lg shadow border border-white/8 p-4">
            {filteredTasksByTab.length === 0 ? (
              <div className="px-6 py-12 text-center text-[#615d59]">
                <Search size={48} className="mx-auto mb-4 text-gray-300" />
                <p>该状态下暂无任务</p>
              </div>
            ) : (
              <>
                <TaskAccordion 
                  tasks={tabPaginatedTasks} 
                  onDeleteTask={handleDeleteTask} 
                  onReviewTask={handleReviewTask}
                  showReviewActions={activeStatusTab === 'pending_review'}
                />
                
                {/* 分页控件 */}
                {tabTotalPages > 1 && (
                  <div className="flex items-center justify-between mt-4 pt-4 border-t">
                    <div className="text-sm text-gray-500">
                      共 {filteredTasksByTab.length} 条，第 {tabCurrentPage}/{tabTotalPages} 页
                    </div>
                    <div className="flex items-center gap-3">
                      <div className="flex items-center gap-2">
                        <span className="text-sm text-gray-500">跳转到</span>
                        <input
                          type="number"
                          min={1}
                          max={tabTotalPages}
                          className="w-16 px-2 py-1 border border-gray-300 rounded text-center text-sm"
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              const page = parseInt((e.target as HTMLInputElement).value);
                              if (page >= 1 && page <= tabTotalPages) setTabCurrentPage(page);
                            }
                          }}
                        />
                        <span className="text-sm text-gray-500">页</span>
                      </div>
                      <button
                        onClick={() => { setTabCurrentPage(p => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                        disabled={tabCurrentPage === 1}
                        className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                      >
                        上一页
                      </button>
                      <button
                        onClick={() => { setTabCurrentPage(p => Math.min(tabTotalPages, p + 1)); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                        disabled={tabCurrentPage === tabTotalPages}
                        className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                      >
                        下一页
                      </button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      )}

      {/* 列表视图 */}
      {viewMode === 'list' && (
        <div className="bg-white rounded-lg shadow border border-white/8 p-4">
          {tasks.length === 0 ? (
            <div className="px-6 py-12 text-center text-[#615d59]">
              <Search size={48} className="mx-auto mb-4 text-gray-300" />
              <p>暂无任务</p>
            </div>
          ) : (
            <>
              <TaskAccordion 
                tasks={listPaginatedTasks} 
                onDeleteTask={handleDeleteTask} 
                onReviewTask={handleReviewTask}
                showReviewActions={activeStatusTab === 'pending_review'}
              />

              {/* 分页控件 */}
              {listTotalPages > 1 && (
                <div className="flex items-center justify-between mt-4 pt-4 border-t">
                  <div className="text-sm text-gray-500">
                    共 {tasks.length} 条，第 {currentPage}/{listTotalPages} 页
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2">
                      <span className="text-sm text-gray-500">跳转到</span>
                      <input
                        type="number"
                        min={1}
                        max={listTotalPages}
                        className="w-16 px-2 py-1 border border-gray-300 rounded text-center text-sm"
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            const page = parseInt((e.target as HTMLInputElement).value);
                            if (page >= 1 && page <= listTotalPages) setCurrentPage(page);
                          }
                        }}
                      />
                      <span className="text-sm text-gray-500">页</span>
                    </div>
                    <button
                      onClick={() => { setCurrentPage(p => Math.max(1, p - 1)); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                      disabled={currentPage === 1}
                      className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                    >
                      上一页
                    </button>
                    <button
                      onClick={() => { setCurrentPage(p => Math.min(listTotalPages, p + 1)); window.scrollTo({ top: 0, behavior: "smooth" }); }}
                      disabled={currentPage === listTotalPages}
                      className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                    >
                      下一页
                    </button>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      )}

      {/* 汇总视图 */}
      {viewMode === 'kanban' && (
        <div className="bg-white rounded-lg shadow border border-white/8 p-4">
          {tasks.length === 0 ? (
            <div className="px-6 py-12 text-center text-[#615d59]">
              <Search size={48} className="mx-auto mb-4 text-gray-300" />
              <p>暂无任务</p>
            </div>
          ) : (
            <div className="grid grid-cols-5 gap-4">
              {/* 待处理 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2 cursor-pointer hover:bg-red-50 transition-colors" onClick={() => { setViewMode('tab'); setActiveStatusTab('pending'); setTabCurrentPage(1); }}>
                  <span className="w-2 h-2 rounded-full bg-red-500"></span>
                  待处理
                  <span className="text-xs text-gray-400 ml-auto">
                    {tasks.filter(t => t.status === 'todo' || t.status === 'pending').length}
                  </span>
                </h3>
                <div className="space-y-2">
                  {tasks.filter(t => t.status === 'todo' || t.status === 'pending').map(task => (
                    <div key={task.id} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => { setEditingTask(task); setShowEditModal(true); }}>
                      <div className="text-sm font-medium text-gray-900 line-clamp-2">{task.title}</div>
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-100 text-green-700' :
                          task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          task.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                          task.status === 'todo' || task.status === 'pending' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.status === 'completed' ? '已完成' : task.status === 'in_progress' ? '进行中' : task.status === 'pending_review' ? '待审阅' : task.status === 'todo' ? '待办' : task.status === 'pending' ? '待处理' : task.status}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.priority === 'high' ? 'bg-red-100 text-red-700' :
                          task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          task.priority === 'low' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.priority === 'high' ? '高优先' : task.priority === 'medium' ? '中优先' : task.priority === 'low' ? '低优先' : task.priority}</span>
                        <span className="text-xs text-gray-500">{task.project_name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 进行中 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2 cursor-pointer hover:bg-blue-50 transition-colors" onClick={() => { setViewMode('tab'); setActiveStatusTab('in_progress'); setTabCurrentPage(1); }}>
                  <span className="w-2 h-2 rounded-full bg-blue-500"></span>
                  进行中
                  <span className="text-xs text-gray-400 ml-auto">
                    {tasks.filter(t => t.status === 'in_progress').length}
                  </span>
                </h3>
                <div className="space-y-2">
                  {tasks.filter(t => t.status === 'in_progress').map(task => (
                    <div key={task.id} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => { setEditingTask(task); setShowEditModal(true); }}>
                      <div className="text-sm font-medium text-gray-900 line-clamp-2">{task.title}</div>
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-100 text-green-700' :
                          task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          task.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                          task.status === 'todo' || task.status === 'pending' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.status === 'completed' ? '已完成' : task.status === 'in_progress' ? '进行中' : task.status === 'pending_review' ? '待审阅' : task.status === 'todo' ? '待办' : task.status === 'pending' ? '待处理' : task.status}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.priority === 'high' ? 'bg-red-100 text-red-700' :
                          task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          task.priority === 'low' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.priority === 'high' ? '高优先' : task.priority === 'medium' ? '中优先' : task.priority === 'low' ? '低优先' : task.priority}</span>
                        <span className="text-xs text-gray-500">{task.project_name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 待审阅 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2 cursor-pointer hover:bg-yellow-50 transition-colors" onClick={() => { setViewMode('tab'); setActiveStatusTab('pending_review'); setTabCurrentPage(1); }}>
                  <span className="w-2 h-2 rounded-full bg-yellow-500"></span>
                  待审阅
                  <span className="text-xs text-gray-400 ml-auto">
                    {tasks.filter(t => t.status === 'pending_review').length}
                  </span>
                </h3>
                <div className="space-y-2">
                  {tasks.filter(t => t.status === 'pending_review').map(task => (
                    <div key={task.id} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => { setEditingTask(task); setShowEditModal(true); }}>
                      <div className="text-sm font-medium text-gray-900 line-clamp-2">{task.title}</div>
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-100 text-green-700' :
                          task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          task.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                          task.status === 'todo' || task.status === 'pending' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.status === 'completed' ? '已完成' : task.status === 'in_progress' ? '进行中' : task.status === 'pending_review' ? '待审阅' : task.status === 'todo' ? '待办' : task.status === 'pending' ? '待处理' : task.status}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.priority === 'high' ? 'bg-red-100 text-red-700' :
                          task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          task.priority === 'low' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.priority === 'high' ? '高优先' : task.priority === 'medium' ? '中优先' : task.priority === 'low' ? '低优先' : task.priority}</span>
                        <span className="text-xs text-gray-500">{task.project_name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 已完成 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2 cursor-pointer hover:bg-green-50 transition-colors" onClick={() => { setViewMode('tab'); setActiveStatusTab('completed'); setTabCurrentPage(1); }}>
                  <span className="w-2 h-2 rounded-full bg-green-500"></span>
                  已完成
                  <span className="text-xs text-gray-400 ml-auto">
                    {tasks.filter(t => t.status === 'completed').length}
                  </span>
                </h3>
                <div className="space-y-2">
                  {tasks.filter(t => t.status === 'completed').map(task => (
                    <div key={task.id} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => { setEditingTask(task); setShowEditModal(true); }}>
                      <div className="text-sm font-medium text-gray-900 line-clamp-2">{task.title}</div>
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-100 text-green-700' :
                          task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          task.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                          task.status === 'todo' || task.status === 'pending' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.status === 'completed' ? '已完成' : task.status === 'in_progress' ? '进行中' : task.status === 'pending_review' ? '待审阅' : task.status === 'todo' ? '待办' : task.status === 'pending' ? '待处理' : task.status}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.priority === 'high' ? 'bg-red-100 text-red-700' :
                          task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          task.priority === 'low' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.priority === 'high' ? '高优先' : task.priority === 'medium' ? '中优先' : task.priority === 'low' ? '低优先' : task.priority}</span>
                        <span className="text-xs text-gray-500">{task.project_name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* 失败/阻塞 */}
              <div className="bg-gray-50 rounded-lg p-3">
                <h3 className="font-medium text-sm text-gray-700 mb-3 flex items-center gap-2 cursor-pointer hover:bg-gray-100 transition-colors" onClick={() => { setViewMode('tab'); setActiveStatusTab('pending_review'); setTabCurrentPage(1); }}>
                  <span className="w-2 h-2 rounded-full bg-gray-500"></span>
                  失败/阻塞
                  <span className="text-xs text-gray-400 ml-auto">
                    {tasks.filter(t => t.status === 'failed_retryable' || t.status === 'blocked' || t.status === 'failed').length}
                  </span>
                </h3>
                <div className="space-y-2">
                  {tasks.filter(t => t.status === 'failed_retryable' || t.status === 'blocked' || t.status === 'failed').map(task => (
                    <div key={task.id} className="bg-white p-3 rounded-lg border border-gray-200 shadow-sm cursor-pointer hover:shadow-md transition-shadow" onClick={() => { setEditingTask(task); setShowEditModal(true); }}>
                      <div className="text-sm font-medium text-gray-900 line-clamp-2">{task.title}</div>
                      <div className="flex items-center gap-1 mt-1 flex-wrap">
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.status === 'completed' ? 'bg-green-100 text-green-700' :
                          task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          task.status === 'pending_review' ? 'bg-yellow-100 text-yellow-700' :
                          task.status === 'todo' || task.status === 'pending' ? 'bg-red-100 text-red-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.status === 'completed' ? '已完成' : task.status === 'in_progress' ? '进行中' : task.status === 'pending_review' ? '待审阅' : task.status === 'todo' ? '待办' : task.status === 'pending' ? '待处理' : task.status}</span>
                        <span className={`text-xs px-1.5 py-0.5 rounded ${
                          task.priority === 'high' ? 'bg-red-100 text-red-700' :
                          task.priority === 'medium' ? 'bg-yellow-100 text-yellow-700' :
                          task.priority === 'low' ? 'bg-green-100 text-green-700' :
                          'bg-gray-100 text-gray-600'
                        }`}>{task.priority === 'high' ? '高优先' : task.priority === 'medium' ? '中优先' : task.priority === 'low' ? '低优先' : task.priority}</span>
                        <span className="text-xs text-gray-500">{task.project_name}</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 添加任务弹窗 */}
      {showAddModal && (
        <div style={modalOverlayStyle}>
          <div className="bg-white rounded-xl p-6 w-[48rem] shadow-2xl">
            <h3 className="text-lg font-bold mb-4">新建任务</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">任务标题</label>
                <input
                  type="text"
                  id="newTaskTitle"
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="输入任务标题"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">任务描述</label>
                <textarea
                  id="newTaskDescription"
                  rows={3}
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="输入任务描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">所属项目</label>
                <select
                  id="newTaskProject"
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                >
                  <option value="">请选择项目</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">状态</label>
                <select
                  id="newTaskStatus"
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                >
                  <option value="todo">待办</option>
                  <option value="in_progress">进行中</option>
                  <option value="completed">已完成</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">优先级</label>
                <select
                  id="newTaskPriority"
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                >
                  <option value="low">低</option>
                  <option value="medium">中</option>
                  <option value="high">高</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">标签</label>
                <input
                  type="text"
                  id="newTaskTags"
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="多个标签用逗号分隔"
                />
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="px-4 py-2 text-[#31302e] border border-white/8 rounded-lg hover:bg-[#f6f5f4]"
              >
                取消
              </button>
              <button
                onClick={async () => {
                  const title = (document.getElementById('newTaskTitle') as HTMLInputElement).value;
                  const description = (document.getElementById('newTaskDescription') as HTMLTextAreaElement).value;
                  const project_id = parseInt((document.getElementById('newTaskProject') as HTMLSelectElement).value);
                  const status = (document.getElementById('newTaskStatus') as HTMLSelectElement).value;
                  const priority = (document.getElementById('newTaskPriority') as HTMLSelectElement).value;
                  const tags = (document.getElementById('newTaskTags') as HTMLInputElement).value;
                  
                  if (!title.trim()) {
                    alert('请输入任务标题');
                    return;
                  }
                  if (!project_id) {
                    alert('请选择所属项目');
                    return;
                  }
                  
                  try {
                    const res = await fetch('/api/tasks', {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ title, description, project_id, status, priority, tags })
                    });
                    const data = await res.json();
                    if (data.success) {
                      alert('任务创建成功');
                      setShowAddModal(false);
                      fetchTasks();
                    } else {
                      alert(data.error || '创建失败');
                    }
                  } catch (error) {
                    console.error('Failed to create task:', error);
                    alert('创建失败');
                  }
                }}
                className="px-4 py-2 bg-[#0075de] text-white rounded-lg hover:bg-[#005bab]"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 编辑任务弹窗 */}
      {editingTask && (
        <div style={{...modalOverlayStyle, display: showEditModal ? 'flex' : 'none'}}>
          <div className="bg-white rounded-xl p-6 w-[48rem] shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-bold">编辑任务</h3>
              <EditLockIndicator 
                taskId={editingTask.id.toString()} 
                userId={localStorage.getItem("user") ? JSON.parse(localStorage.getItem("user")!).id?.toString() : "anonymous"}
              />
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">任务标题</label>
                <input
                  type="text"
                  id="editTaskTitle"
                  defaultValue={editingTask.title}
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="输入任务标题"
                />
              </div>
              {/* TABS */}
              <div style={{display:"flex",borderBottom:"2px solid #e5e7eb",marginBottom:"12px",marginTop:"4px"}}>
                <div onClick={()=>setDetailTab("detail")} style={{padding:"8px 16px",cursor:"pointer",fontSize:"14px",fontWeight:detailTab==="detail"?600:400,color:detailTab==="detail"?"#3b82f6":"#666",borderBottom:detailTab==="detail"?"2px solid #3b82f6":"2px solid transparent",marginBottom:"-2px"}}>DETAIL</div>
                <div onClick={()=>{setDetailTab("executions");loadExecRecords(editingTask&&editingTask.id);}} style={{padding:"8px 16px",cursor:"pointer",fontSize:"14px",fontWeight:detailTab==="executions"?600:400,color:detailTab==="executions"?"#3b82f6":"#666",borderBottom:detailTab==="executions"?"2px solid #3b82f6":"2px solid transparent",marginBottom:"-2px"}}>EXECLOG</div>
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">任务描述</label>
                <textarea
                  id="editTaskDescription"
                  rows={3}
                  defaultValue={editingTask.description || ''}
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="输入任务描述"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">所属项目</label>
                <select
                  id="editTaskProject"
                  defaultValue={editingTask.project_id || ''}
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                >
                  <option value="">请选择项目</option>
                  {projects.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-sm font-medium text-[#31302e] mb-1">标签</label>
                <input
                  type="text"
                  id="editTaskTags"
                  defaultValue={editingTask.tags || ''}
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="多个标签用逗号分隔"
                />
              </div>

              {/* JSON 描述编辑器 */}
              <div className="border-t pt-3 mt-2">
                <div className="flex items-center gap-2 mb-2">
                  <button
                    onClick={() => {
                      try {
                        const desc = editingTask.description || '';
                        const formatted = desc ? JSON.stringify(JSON.parse(desc), null, 2) : '';
                        setJsonEditorContent(formatted);
                        setShowJsonEditor(true);
                      } catch (e) {
                        setJsonEditorContent(editingTask.description || '');
                        setShowJsonEditor(true);
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 text-xs font-medium"
                  >
                    <Code size={14} />
                    编辑JSON描述
                  </button>
                  <button
                    onClick={async () => {
                      setPhaseRLoading(true);
                      setShowPhaseR(true);
                      try {
                        const res = await fetch(`/api/admin/tasks/detail/${editingTask.id}`);
                        const data = await res.json();
                        setPhaseRData(data);
                      } catch (err) {
                        console.error('Failed to load task detail:', err);
                        setPhaseRData({ error: '加载失败' });
                      } finally {
                        setPhaseRLoading(false);
                      }
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-50 text-purple-700 rounded-lg hover:bg-purple-100 text-xs font-medium"
                  >
                    <Brain size={14} />
                    🧠PhaseR
                  </button>
                  <button
                    onClick={() => {
                      // Toggle attachments section - using a class-based toggle via state
                      setShowAttachments(!showAttachments);
                    }}
                    className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-50 text-blue-700 rounded-lg hover:bg-blue-100 text-xs font-medium"
                  >
                    <Download size={14} />
                    附件
                  </button>
                </div>

                {/* JSON Editor Modal */}
                {showJsonEditor && (
                  <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', zIndex: 100000
                  }} onClick={() => setShowJsonEditor(false)}>
                    <div className="bg-white rounded-xl p-6 w-[48rem] shadow-2xl"
                         onClick={e => e.stopPropagation()}
                         style={{ maxHeight: '90vh', overflow: 'auto' }}>
                      <h3 className="text-lg font-bold mb-4">编辑 JSON 描述</h3>
                      <div className="mb-2 text-xs text-gray-500">
                        任务 #{editingTask.id}: {editingTask.title}
                      </div>
                      <textarea
                        value={jsonEditorContent}
                        onChange={(e) => setJsonEditorContent(e.target.value)}
                        style={{
                          width: '100%', minHeight: '400px',
                          fontFamily: '"Fira Code", "JetBrains Mono", "Cascadia Code", monospace',
                          fontSize: '13px', lineHeight: '1.6',
                          padding: '12px', borderRadius: '8px', border: '1px solid #d1d5db',
                          resize: 'vertical', tabSize: 2
                        }}
                        placeholder="输入或粘贴 JSON 格式的描述..."
                      />
                      <div className="flex justify-end gap-3 mt-4">
                        <button
                          onClick={() => setShowJsonEditor(false)}
                          className="px-4 py-2 text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-100"
                        >
                          取消
                        </button>
                        <button
                          onClick={async () => {
                            try {
                              // Validate JSON
                              JSON.parse(jsonEditorContent);
                              const res = await fetch(`/api/admin/tasks/${editingTask.id}/description`, {
                                method: 'PUT',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify({ description: jsonEditorContent })
                              });
                              const data = await res.json();
                              if (data.success) {
                                alert('JSON 描述已保存');
                                setShowJsonEditor(false);
                                fetchTasks();
                              } else {
                                alert(data.error || '保存失败');
                              }
                            } catch (e: any) {
                              alert('JSON 格式错误: ' + e.message);
                            }
                          }}
                          className="px-4 py-2 bg-purple-600 text-white rounded-lg hover:bg-purple-700"
                        >
                          保存 JSON 描述
                        </button>
                      </div>
                    </div>
                  </div>
                )}

                {/* Phase R Visualization Modal */}
                {showPhaseR && (
                  <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    backgroundColor: 'rgba(0,0,0,0.5)', display: 'flex',
                    alignItems: 'center', justifyContent: 'center', zIndex: 100000
                  }} onClick={() => { setShowPhaseR(false); setPhaseRData(null); }}>
                    <div className="bg-white rounded-xl p-6 w-[56rem] shadow-2xl"
                         onClick={e => e.stopPropagation()}
                         style={{ maxHeight: '90vh', overflow: 'auto' }}>
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-bold">🧠 Phase R 流程图</h3>
                        <button onClick={() => { setShowPhaseR(false); setPhaseRData(null); }}
                                className="text-gray-400 hover:text-gray-600">
                          <X size={20} />
                        </button>
                      </div>
                      <div className="mb-2 text-xs text-gray-500">
                        任务 #{editingTask.id}: {editingTask.title}
                      </div>
                      {phaseRLoading ? (
                        <div className="text-center py-8 text-gray-500">加载中...</div>
                      ) : phaseRData?.execution_log && phaseRData.execution_log.includes('Phase R') ? (
                        <div>
                          {/* 5步流程图 */}
                          <div className="flex items-center justify-between mb-6">
                            {[
                              { step: 1, label: '现状审查', emoji: '🔍', color: '#3b82f6', iconBg: '#dbeafe' },
                              { step: 2, label: '目标对齐', emoji: '🎯', color: '#10b981', iconBg: '#d1fae5' },
                              { step: 3, label: 'Brainstorming', emoji: '💡', color: '#f59e0b', iconBg: '#fef3c7' },
                              { step: 4, label: '方案评估', emoji: '⚖️', color: '#8b5cf6', iconBg: '#ede9fe' },
                              { step: 5, label: '子任务', emoji: '📋', color: '#ec4899', iconBg: '#fce7f3' },
                            ].map((s, i) => (
                              <React.Fragment key={s.step}>
                                <div className="flex flex-col items-center" style={{ flex: 1, maxWidth: '120px' }}>
                                  <div style={{
                                    width: '48px', height: '48px', borderRadius: '50%',
                                    backgroundColor: s.iconBg, border: `2px solid ${s.color}`,
                                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                                    fontSize: '20px', marginBottom: '6px'
                                  }}>
                                    {s.emoji}
                                  </div>
                                  <div style={{
                                    fontSize: '11px', fontWeight: 600, color: s.color, textAlign: 'center'
                                  }}>
                                    {s.label}
                                  </div>
                                </div>
                                {i < 4 && (
                                  <div style={{
                                    flex: '0 0 24px', height: '2px', backgroundColor: '#d1d5db',
                                    marginTop: '-16px'
                                  }} />
                                )}
                              </React.Fragment>
                            ))}
                          </div>
                          {/* Execution Log Display */}
                          <div className="mt-4 p-4 bg-gray-50 rounded-lg border border-gray-200">
                            <h4 className="text-sm font-semibold text-gray-700 mb-2">执行日志</h4>
                            <pre style={{
                              fontSize: '12px', lineHeight: '1.5', color: '#374151',
                              whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                              maxHeight: '300px', overflow: 'auto',
                              fontFamily: '"Fira Code", "JetBrains Mono", monospace'
                            }}>
                              {phaseRData.execution_log}
                            </pre>
                          </div>
                        </div>
                      ) : (
                        <div className="text-center py-8 text-gray-400">
                          {phaseRData?.error ? `加载错误: ${phaseRData.error}` : '该任务没有 Phase R 执行日志'}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Attachments Section */}
                {showAttachments && (
                  <div className="mt-3 p-3 bg-gray-50 rounded-lg border border-gray-200">
                    <TaskAttachments taskId={editingTask.id} />
                  </div>
                )}
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button
                onClick={() => {
                  setShowEditModal(false);
                  setEditingTask(null);
                }}
                className="px-4 py-2 text-[#31302e] border border-white/8 rounded-lg hover:bg-[#f6f5f4]"
              >
                取消
              </button>
              <button
                onClick={async () => {
                  const title = (document.getElementById('editTaskTitle') as HTMLInputElement).value;
                  const description = (document.getElementById('editTaskDescription') as HTMLTextAreaElement).value;
                  const project_id = parseInt((document.getElementById('editTaskProject') as HTMLSelectElement).value);
                  const status = (document.getElementById('editTaskStatus') as HTMLSelectElement).value;
                  const priority = (document.getElementById('editTaskPriority') as HTMLSelectElement).value;
                  const tags = (document.getElementById('editTaskTags') as HTMLInputElement).value;
                  
                  if (!title.trim()) {
                    alert('请输入任务标题');
                    return;
                  }
                  
                  try {
                    const res = await fetch(`/api/tasks/${editingTask.id}`, {
                      method: 'PUT',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({ title, description, project_id, status, priority, tags })
                    });
                    const data = await res.json();
                    if (data.success) {
                      alert('任务更新成功');
                      setShowEditModal(false);
                      setEditingTask(null);
                      fetchTasks();
                    } else {
                      alert(data.error || '更新失败');
                    }
                  } catch (error) {
                    console.error('Failed to update task:', error);
                    alert('更新失败');
                  }
                }}
                className="px-4 py-2 bg-[#0075de] text-white rounded-lg hover:bg-[#005bab]"
              >
                保存修改
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 保存视图弹窗 */}
      {showSaveViewModal && (
        <div style={modalOverlayStyle}>
          <div className="bg-white rounded-lg p-6 w-[48rem]">
            <h3 className="text-lg font-bold mb-4">保存视图</h3>
            <input
              type="text"
              value={viewName}
              onChange={(e) => setViewName(e.target.value)}
              placeholder="输入视图名称"
              className="w-full px-3 py-2 border border-white/8 rounded-lg mb-4 focus:ring-2 focus:ring-[#0075de]"
              autoFocus
            />
            <div className="flex justify-end gap-3">
              <button
                onClick={() => {
                  setShowSaveViewModal(false);
                  setViewName('');
                }}
                className="px-4 py-2 text-[#31302e] border border-white/8 rounded-lg hover:bg-[#f6f5f4]"
              >
                取消
              </button>
              <button
                onClick={handleSaveView}
                className="px-4 py-2 bg-[#0075de] text-white rounded-lg hover:bg-[#005bab]"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default Tasks;
// build-1778815311
{detailTab === "executions" && (
<div style={{padding:"8px 0px"}}>
<h4>EXEC RECORDS</h4>
{execLoading && <p>loading</p>}
{!execLoading && execRecords.length === 0 && <p>none</p>}
{!execLoading && execRecords.length > 0 && (
<div>
{execRecords.map(function(rec,i){return(
<div key={rec.id||i} style={{padding:"4px 8px",margin:"4px 0",background:"#f8fafc",borderRadius:"4px",fontSize:"13px"}}>
<span>v{rec.version} </span>
<span>{rec.status}</span>
</div>
)})}
</div>
)}
</div>
)}
{detailTab !== "executions" && (
