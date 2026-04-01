import React, { useState, useEffect } from 'react';
import { Search, Plus, BookOpen, Eye, Tag } from 'lucide-react';

interface WikiEntry {
  id: number;
  title: string;
  category: string;
  tags: string;
  author: string;
  status: string;
  views: number;
  created_at: string;
  updated_at: string;
}

interface Category {
  category: string;
  count: number;
}

const WikiPage: React.FC = () => {
  const [entries, setEntries] = useState<WikiEntry[]>([]);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('');
  const [selectedEntry, setSelectedEntry] = useState<WikiEntry | null>(null);
  const [entryContent, setEntryContent] = useState<string>('');
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newEntry, setNewEntry] = useState({
    title: '',
    content: '',
    category: '',
    tags: '',
    author: 'admin',
    status: 'published'
  });

  useEffect(() => {
    loadCategories();
    loadEntries();
  }, [selectedCategory, searchTerm]);

  const loadCategories = async () => {
    try {
      const response = await fetch('/api/wiki/categories');
      const data = await response.json();
      if (data.success) {
        setCategories(data.categories);
      }
    } catch (e) {
      console.error('加载分类失败:', e);
    }
  };

  const loadEntries = async () => {
    try {
      setLoading(true);
      let url = '/api/wiki/entries?';
      if (selectedCategory) {
        url += `category=${encodeURIComponent(selectedCategory)}&`;
      }
      if (searchTerm) {
        url += `search=${encodeURIComponent(searchTerm)}`;
      }
      const response = await fetch(url);
      const data = await response.json();
      if (data.success) {
        setEntries(data.entries);
      }
    } catch (e) {
      console.error('加载词条失败:', e);
    } finally {
      setLoading(false);
    }
  };

  const loadEntryDetail = async (entry: WikiEntry) => {
    try {
      const response = await fetch(`/api/wiki/entries/${entry.id}`);
      const data = await response.json();
      if (data.success) {
        setSelectedEntry(entry);
        setEntryContent(data.entry.content);
      }
    } catch (e) {
      console.error('加载词条详情失败:', e);
    }
  };

  const handleCreate = async () => {
    if (!newEntry.title.trim() || !newEntry.content.trim()) return;
    try {
      const response = await fetch('/api/wiki/entries', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newEntry)
      });
      const data = await response.json();
      if (data.success) {
        setShowCreateModal(false);
        setNewEntry({
          title: '',
          content: '',
          category: '',
          tags: '',
          author: 'admin',
          status: 'published'
        });
        loadEntries();
        loadCategories();
      }
    } catch (e) {
      console.error('创建词条失败:', e);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('确定要删除这个词条吗？')) return;
    try {
      await fetch(`/api/wiki/entries/${id}`, { method: 'DELETE' });
      loadEntries();
      loadCategories();
      if (selectedEntry?.id === id) {
        setSelectedEntry(null);
        setEntryContent('');
      }
    } catch (e) {
      console.error('删除词条失败:', e);
    }
  };

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <BookOpen size={28} />
            产品百科
          </h1>
          <p className="text-gray-600 mt-1">
            共 {entries.length} 个公开词条 · {categories.length} 个分类
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
        >
          <Plus size={20} />
          新建词条
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* 侧边栏 - 分类筛选 */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4">
            <div className="mb-4">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={18} />
                <input
                  type="text"
                  placeholder="搜索词条..."
                  value={searchTerm}
                  onChange={e => setSearchTerm(e.target.value)}
                  className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            <h3 className="font-semibold text-gray-900 mb-3">分类</h3>
            <div className="space-y-1">
              <button
                onClick={() => setSelectedCategory('')}
                className={`w-full text-left px-3 py-2 rounded text-sm ${!selectedCategory ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}
              >
                全部 ({entries.length})
              </button>
              {categories.map(cat => (
                <button
                  key={cat.category}
                  onClick={() => setSelectedCategory(cat.category)}
                  className={`w-full text-left px-3 py-2 rounded text-sm ${selectedCategory === cat.category ? 'bg-blue-100 text-blue-700' : 'text-gray-700 hover:bg-gray-100'}`}
                >
                  {cat.category} ({cat.count})
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 主内容区 */}
        <div className={`lg:col-span-${selectedEntry ? 2 : 3}`}>
          <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
            {loading ? (
              <div className="text-center py-20 text-gray-500">加载中...</div>
            ) : entries.length === 0 ? (
              <div className="text-center py-20 text-gray-500">
                <BookOpen size={48} className="mx-auto mb-4 text-gray-300" />
                <p>暂无词条</p>
                <p className="text-sm">点击右上角 "新建词条" 创建第一个词条</p>
              </div>
            ) : (
              <div className="divide-y divide-gray-100">
                {entries.map(entry => (
                  <div
                    key={entry.id}
                    onClick={() => loadEntryDetail(entry)}
                    className={`p-4 hover:bg-gray-50 cursor-pointer transition-colors ${selectedEntry?.id === entry.id ? 'bg-blue-50' : ''}`}
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1">
                        <h3 className="font-semibold text-lg text-gray-900">{entry.title}</h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-gray-500">
                          {entry.category && (
                            <span className="bg-gray-100 px-2 py-1 rounded text-gray-700">
                              {entry.category}
                            </span>
                          )}
                          <span className="flex items-center gap-1">
                            <Eye size={14} />
                            {entry.views}
                          </span>
                          <span>{new Date(entry.created_at).toLocaleDateString()}</span>
                        </div>
                        {entry.tags && (
                          <div className="flex items-center gap-1 mt-2">
                            <Tag size={14} className="text-gray-400" />
                            {entry.tags.split(',').map(tag => (
                              <span key={tag.trim()} className="text-xs bg-blue-50 text-blue-600 px-2 py-1 rounded">
                                {tag.trim()}
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                      <button
                        onClick={e => {
                          e.stopPropagation();
                          handleDelete(entry.id);
                        }}
                        className="p-2 text-red-600 hover:bg-red-50 rounded opacity-0 group-hover:opacity-100 transition"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* 词条详情 */}
        {selectedEntry && (
          <div className="lg:col-span-1">
            <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sticky top-4">
              <h2 className="text-xl font-bold text-gray-900 mb-2">{selectedEntry.title}</h2>
              <div className="text-sm text-gray-500 mb-4">
                <p>分类: {selectedEntry.category}</p>
                <p>浏览: {selectedEntry.views + (entryContent ? 1 : 0)} 次</p>
                <p>更新: {new Date(selectedEntry.updated_at).toLocaleString()}</p>
              </div>
              <div className="prose prose-sm max-w-none">
                <div dangerouslySetInnerHTML={{ __html: entryContent.replace(/\n/g, '<br />') }} />
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 创建词条弹窗 */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
            <h3 className="text-lg font-semibold mb-4">新建百科词条</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">词条标题 *</label>
                <input
                  type="text"
                  value={newEntry.title}
                  onChange={e => setNewEntry({...newEntry, title: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="输入词条标题"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">分类</label>
                <input
                  type="text"
                  value={newEntry.category}
                  onChange={e => setNewEntry({...newEntry, category: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="例如：技术、产品、方法论"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">标签（逗号分隔）</label>
                <input
                  type="text"
                  value={newEntry.tags}
                  onChange={e => setNewEntry({...newEntry, tags: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="产品,管理,agile"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">词条内容 (支持 Markdown) *</label>
                <textarea
                  value={newEntry.content}
                  onChange={e => setNewEntry({...newEntry, content: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 min-h-[200px]"
                  placeholder="输入词条内容..."
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
                创建词条
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default WikiPage;
