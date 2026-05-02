import React, { useState, useEffect, useMemo } from 'react';
import { Plus, Search, Filter, Save, Star, X, Calendar, Tag, Layout, List } from "lucide-react";
import { TaskAccordion } from '../components/TaskAccordion';

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
  { key: 'all', label: '📊 全部', color: '#6b7280', statuses: [] },
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
  const [savedViews, setSavedViews] = useState<SavedView[]>([]);
  const [showFilters, setShowFilters] = useState(false);
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize] = useState(50);
  const [showSaveViewModal, setShowSaveViewModal] = useState(false);
  const [viewName, setViewName] = useState('');
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [sortField, setSortField] = useState("created_at");
  const [sortOrder, setSortOrder] = useState("desc");
  
  // 视图模式状态
  const [viewMode, setViewMode] = useState<'tab' | 'list'>('tab');
  const [activeStatusTab, setActiveStatusTab] = useState('pending');
  const [tabCurrentPage, setTabCurrentPage] = useState(1);
  
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
      
      params.append('per_page', '2000');
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

  useEffect(() => {
    fetchTasks();
    fetchProjects();
    fetchSavedViews();
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
    if (!tabConfig || activeStatusTab === 'all') return tasks;
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

  // Tab视图：各状态数量统计
  const statusCounts = useMemo(() => {
    const counts: Record<string, number> = statusTabs.reduce(
      (acc, tab) => ({ ...acc, [tab.key]: 0 }),
      {} as Record<string, number>
    );
    counts['all'] = tasks.length;
    tasks.forEach((task) => {
      statusTabs.forEach(tab => {
        if (tab.statuses.includes(task.status)) {
          counts[tab.key] = (counts[tab.key] || 0) + 1;
        }
      });
    });
    return counts;
  }, [tasks]);

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* 头部 - 单行布局 */}
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-bold text-[rgba(0,0,0,0.95)]">任务管理</h1>
        <div className="flex items-center gap-2">
          {/* 视图切换 */}
          <div className="flex items-center bg-gray-100 rounded-lg p-0.5">
            <button
              onClick={() => { setViewMode('tab'); setTabCurrentPage(1); }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'tab'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <Layout size={14} />
              Tab
            </button>
            <button
              onClick={() => { setViewMode('list'); setCurrentPage(1); }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors ${
                viewMode === 'list'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-500 hover:text-gray-700'
              }`}
            >
              <List size={14} />
              列表
            </button>
          </div>

          {/* 分隔线 */}
          <div className="w-px h-6 bg-gray-200" />

          {/* 项目状态筛选 */}
          {Object.entries(projectStatusStats).map(([status, count]) => (
            <button
              key={status}
              onClick={() => setProjectStatusFilter(projectStatusFilter === status ? '' : status)}
              className={`px-2 py-1 rounded-md text-xs font-medium transition-colors ${
                projectStatusFilter === status
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {status === 'active' ? '活跃' : status === 'completed' ? '已完成' : status === 'archived' ? '已归档' : status === 'todo' ? '待办' : status}
              <span className="ml-0.5 opacity-75">({count})</span>
            </button>
          ))}
          {projectStatusFilter && (
            <button
              onClick={() => setProjectStatusFilter('')}
              className="px-2 py-1 rounded-md text-xs text-gray-400 hover:text-gray-600"
            >
              ×
            </button>
          )}

          {/* 分隔线 */}
          <div className="w-px h-6 bg-gray-200" />

          {/* 新建任务 */}
          <button
            onClick={() => setShowAddModal(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-[#0075de] text-white rounded-lg hover:bg-[#005bab] text-xs font-medium"
          >
            <Plus size={14} />
            新建任务
          </button>
        </div>
      </div>

      {/* 搜索和筛选行 */}
      <div className="flex flex-wrap gap-3 items-center mb-4">
        {/* 搜索框 */}
        <div className="relative flex-1 min-w-[300px]">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-[#615d59]" size={20} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="搜索任务标题、描述、标签..."
            className="w-full pl-10 pr-4 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de] focus:border-transparent"
          />
          {search && (
            <button
              onClick={() => setSearch('')}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-[#615d59] hover:text-[#615d59]"
            >
              <X size={16} />
            </button>
          )}
        </div>

        {/* 保存视图按钮 */}
        <button
          onClick={() => setShowSaveViewModal(true)}
          className="flex items-center gap-2 px-4 py-2 border border-white/8 rounded-lg hover:bg-[#f6f5f4]"
        >
          <Save size={18} />
          保存视图
        </button>

        {/* 筛选按钮 */}
        <button
          onClick={() => setShowFilters(!showFilters)}
          className={`flex items-center gap-2 px-4 py-2 border rounded-lg ${
            showFilters ? 'bg-blue-50 border-blue-500' : 'border-white/8 hover:bg-[#f6f5f4]'
          }`}
        >
          <Filter size={18} />
          筛选
        </button>
      </div>

      {/* 激活的筛选条件 */}
      {activeFilters.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3">
          {activeFilters.map((filter, idx) => (
            <span
              key={idx}
              className="inline-flex items-center gap-1 px-3 py-1 bg-[#0075de]/15 text-[#0075de] rounded-full text-sm"
            >
              {filter.label}
              <button
                onClick={() => {
                  if (filter.type === 'search') setSearch('');
                  else if (filter.type === 'tags') setTags('');
                  else if (filter.type === 'quick') setQuickFilter('');
                  else if (filter.type === 'date') { setDateFrom(''); setDateTo(''); }
                }}
                className="hover:text-[#0075de]"
              >
                <X size={14} />
              </button>
            </span>
          ))}
          <button
            onClick={clearFilters}
            className="text-sm text-[#615d59] hover:text-[#31302e] underline"
          >
            清除所有
          </button>
        </div>
      )}

      {/* 高级筛选面板 */}
      {showFilters && (
        <div className="mb-4 p-4 bg-[#f6f5f4] rounded-lg border border-white/8">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 标签筛选 */}
            <div>
              <label className="block text-sm font-medium text-[#31302e] mb-1">
                <Tag size={16} className="inline mr-1" />
                标签
              </label>
              <input
                type="text"
                value={tags}
                onChange={(e) => setTags(e.target.value)}
                placeholder="多个标签用逗号分隔"
                className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
              />
            </div>

            {/* 快捷筛选 */}
            <div>
              <label className="block text-sm font-medium text-[#31302e] mb-1">
                <Calendar size={16} className="inline mr-1" />
                时间范围
              </label>
              <div className="flex gap-2">
                <button
                  onClick={() => setQuickFilter(quickFilter === 'today' ? '' : 'today')}
                  className={`flex-1 px-3 py-2 rounded-lg border ${
                    quickFilter === 'today'
                      ? 'bg-[#0075de] text-white border-blue-600'
                      : 'bg-white text-[#31302e] border-white/8 hover:bg-[#f6f5f4]'
                  }`}
                >
                  今天
                </button>
                <button
                  onClick={() => setQuickFilter(quickFilter === 'this_week' ? '' : 'this_week')}
                  className={`flex-1 px-3 py-2 rounded-lg border ${
                    quickFilter === 'this_week'
                      ? 'bg-[#0075de] text-white border-blue-600'
                      : 'bg-white text-[#31302e] border-white/8 hover:bg-[#f6f5f4]'
                  }`}
                >
                  本周
                </button>
                <button
                  onClick={() => setQuickFilter(quickFilter === 'this_month' ? '' : 'this_month')}
                  className={`flex-1 px-3 py-2 rounded-lg border ${
                    quickFilter === 'this_month'
                      ? 'bg-[#0075de] text-white border-blue-600'
                      : 'bg-white text-[#31302e] border-white/8 hover:bg-[#f6f5f4]'
                  }`}
                >
                  本月
                </button>
              </div>
            </div>

            {/* 自定义日期范围 */}
            <div>
              <label className="block text-sm font-medium text-[#31302e] mb-1">
                自定义日期范围
              </label>
              <div className="flex gap-2">
                <input
                  type="date"
                  value={dateFrom}
                  onChange={(e) => setDateFrom(e.target.value)}
                  className="flex-1 px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                />
                <span className="text-[#615d59]">~</span>
                <input
                  type="date"
                  value={dateTo}
                  onChange={(e) => setDateTo(e.target.value)}
                  className="flex-1 px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                />
              </div>
            </div>
          </div>
        </div>
      )}

      {/* 保存的视图快捷方式 */}
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

      {/* Tab视图 */}
      {viewMode === 'tab' && (
        <div>
          {/* 状态Tab */}
          <div className="flex flex-wrap gap-2 mb-4">
            {statusTabs.map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setActiveStatusTab(tab.key); setTabCurrentPage(1); }}
                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                  activeStatusTab === tab.key
                    ? 'text-white shadow-md'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
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
                        onClick={() => setTabCurrentPage(p => Math.max(1, p - 1))}
                        disabled={tabCurrentPage === 1}
                        className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                      >
                        上一页
                      </button>
                      <button
                        onClick={() => setTabCurrentPage(p => Math.min(tabTotalPages, p + 1))}
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
                      onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                      disabled={currentPage === 1}
                      className="px-4 py-2 bg-white border border-gray-300 rounded-lg text-sm font-medium shadow-sm disabled:opacity-50 disabled:cursor-not-allowed hover:bg-blue-50 hover:border-blue-300 hover:text-blue-600 transition-colors"
                    >
                      上一页
                    </button>
                    <button
                      onClick={() => setCurrentPage(p => Math.min(listTotalPages, p + 1))}
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
      {showEditModal && editingTask && (
        <div style={modalOverlayStyle}>
          <div className="bg-white rounded-xl p-6 w-[48rem] shadow-2xl">
            <h3 className="text-lg font-bold mb-4">编辑任务</h3>
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
                <label className="block text-sm font-medium text-[#31302e] mb-1">状态</label>
                <select
                  id="editTaskStatus"
                  defaultValue={editingTask.status === 'completed' ? 'completed' : editingTask.status === 'in_progress' ? 'in_progress' : 'todo'}
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
                  id="editTaskPriority"
                  defaultValue={editingTask.priority || 'medium'}
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
                  id="editTaskTags"
                  defaultValue={editingTask.tags || ''}
                  className="w-full px-3 py-2 border border-white/8 rounded-lg focus:ring-2 focus:ring-[#0075de]"
                  placeholder="多个标签用逗号分隔"
                />
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
