import React, { useState, useEffect } from 'react';
import { Plus, Trash2, Edit, CheckCircle, Clock, Circle } from 'lucide-react';

interface BacklogItem {
  id: number;
  title: string;
  description: string;
  status: 'todo' | 'progress' | 'done';
  priority: number;
  project: string;
  tags: string;
  estimated_hours: number;
  created_at: string;
}

const BacklogPage: React.FC = () => {
  const [items, setItems] = useState<BacklogItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newItem, setNewItem] = useState({
    title: '',
    description: '',
    status: 'todo' as const,
    priority: 3,
    project: '',
    tags: '',
    estimated_hours: 0
  });

  useEffect(() => {
    loadBacklog();
  }, []);

  const loadBacklog = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/backlog');
      const data = await response.json();
      if (data.success) {
        setItems(data.backlog);
      }
    } catch (e) {
      console.error('加载需求池失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!newItem.title.trim()) return;
    try {
      const response = await fetch('/api/backlog', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newItem)
      });
      const data = await response.json();
      if (data.success) {
        setShowCreateModal(false);
        setNewItem({
          title: '',
          description: '',
          status: 'todo',
          priority: 3,
          project: '',
          tags: '',
          estimated_hours: 0
        });
        loadBacklog();
      }
    } catch (e) {
      console.error('创建需求失败:', e);
    }
  };

  const handleUpdateStatus = async (item: BacklogItem, newStatus: BacklogItem['status']) => {
    try {
      await fetch(`/api/backlog/${item.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...item, status: newStatus })
      });
      loadBacklog();
    } catch (e) {
      console.error('更新需求失败:', e);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个需求吗？')) return;
    try {
      await fetch(`/api/backlog/${id}`, { method: 'DELETE' });
      loadBacklog();
    } catch (e) {
      console.error('删除需求失败:', e);
    }
  };

  const getPriorityColor = (priority: number) => {
    if (priority >= 5) return 'bg-red-100 text-red-800';
    if (priority >= 4) return 'bg-orange-100 text-orange-800';
    if (priority >= 3) return 'bg-yellow-100 text-yellow-800';
    if (priority >= 2) return 'bg-blue-100 text-blue-800';
    return 'bg-gray-100 text-gray-800';
  };

  const getStatusIcon = (status: string) => {
    if (status === 'todo') return <Circle size={16} />;
    if (status === 'progress') return <Clock size={16} />;
    if (status === 'done') return <CheckCircle size={16} />;
  };

  const columns = [
    { key: 'todo', title: '待处理', color: 'bg-gray-50' },
    { key: 'progress', title: '进行中', color: 'bg-blue-50' },
    { key: 'done', title: '已完成', color: 'bg-green-50' },
  ];

  const groupedItems = columns.map(col => ({
    ...col,
    items: items.filter(item => item.status === col.key)
  }));

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">需求池</h1>
          <p className="text-gray-600 mt-1">
            共 {items.length} 个需求 · 
            {items.filter(i => i.status === 'todo').length} 待处理 · 
            {items.filter(i => i.status === 'progress').length} 进行中 · 
            {items.filter(i => i.status === 'done').length} 已完成
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          新建需求
        </button>
      </div>

      {loading ? (
        <div className="text-center py-20 text-gray-500">加载中...</div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {groupedItems.map(column => (
            <div key={column.key} className={`rounded-lg p-4 ${column.color} min-h-[400px]`}>
              <h3 className="font-semibold text-lg mb-4 flex items-center justify-between">
                {column.title}
                <span className="bg-white px-2 py-1 rounded text-sm text-gray-600">
                  {column.items.length}
                </span>
              </h3>
              <div className="space-y-3">
                {column.items.map(item => (
                  <div key={item.id} className="bg-white rounded-lg p-4 shadow-sm border border-gray-200">
                    <div className="flex items-start justify-between">
                      <h4 className="font-medium text-gray-900 flex-1">{item.title}</h4>
                      <div className="flex items-center gap-1 ml-2">
                        <span className={`px-2 py-1 rounded text-xs font-medium ${getPriorityColor(item.priority)}`}>
                          P{item.priority}
                        </span>
                        <button
                          onClick={() => handleDelete(item.id)}
                          className="p-1 text-red-600 hover:bg-red-50 rounded"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </div>
                    {item.description && (
                      <p className="text-gray-600 text-sm mt-2 line-clamp-3">
                        {item.description}
                      </p>
                    )}
                    <div className="flex flex-wrap gap-2 mt-3">
                      {item.project && (
                        <span className="text-xs bg-indigo-100 text-indigo-700 px-2 py-1 rounded">
                          {item.project}
                        </span>
                      )}
                      {item.tags && item.tags.split(',').map(tag => (
                        <span key={tag.trim()} className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
                          {tag.trim()}
                        </span>
                      ))}
                      {item.estimated_hours > 0 && (
                        <span className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded">
                          {item.estimated_hours}h
                        </span>
                      )}
                    </div>
                    <div className="flex items-center gap-2 mt-3 pt-3 border-t border-gray-100">
                      {columns.map(col => (
                        <button
                          key={col.key}
                          onClick={() => handleUpdateStatus(item, col.key as any)}
                          className={`p-1 rounded ${item.status === col.key ? 'bg-blue-100 text-blue-600' : 'hover:bg-gray-100 text-gray-400'}`}
                          title={col.title}
                        >
                          {getStatusIcon(col.key)}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* 创建需求弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <h3 className="text-lg font-semibold mb-4">新建需求</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">需求标题 *</label>
                <input
                  type="text"
                  value={newItem.title}
                  onChange={e => setNewItem({...newItem, title: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="输入需求标题"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">需求描述</label>
                <textarea
                  value={newItem.description}
                  onChange={e => setNewItem({...newItem, description: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  rows={3}
                  placeholder="描述需求详情"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">优先级 (1-5，5最高)</label>
                <input
                  type="number"
                  min="1"
                  max="5"
                  value={newItem.priority}
                  onChange={e => setNewItem({...newItem, priority: parseInt(e.target.value)})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">所属项目</label>
                <input
                  type="text"
                  value={newItem.project}
                  onChange={e => setNewItem({...newItem, project: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="输入项目名称"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
                <input
                  type="text"
                  value={newItem.tags}
                  onChange={e => setNewItem({...newItem, tags: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="frontend, bug, feature"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">预计工时 (小时)</label>
                <input
                  type="number"
                  step="0.5"
                  value={newItem.estimated_hours}
                  onChange={e => setNewItem({...newItem, estimated_hours: parseFloat(e.target.value) || 0})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>
            <div className="flex items-center justify-end gap-3 mt-6">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg"
              >
                取消
              </button>
              <button
                onClick={handleCreate}
                className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default BacklogPage;
