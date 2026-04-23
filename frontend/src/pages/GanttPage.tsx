import React, { useState, useEffect } from 'react';

interface GanttProject {
  id: number;
  name: string;
  start: string;
  end: string;
  progress: number;
  status: string;
  priority: number;
}

const getStatusColor = (status: string) => {
  switch (status) {
    case 'progress': return '#3b82f6';
    case 'done': return '#10b981';
    case 'todo': return '#f59e0b';
    case 'failed': return '#ef4444';
    default: return '#6b7280';
  }
};

const getStatusText = (status: string) => {
  switch (status) {
    case 'progress': return '进行中';
    case 'done': return '已完成';
    case 'todo': return '待开始';
    case 'failed': return '已失败';
    default: return status;
  }
};

const GanttPage: React.FC = () => {
  const [projects, setProjects] = useState<GanttProject[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadGanttData();
  }, []);

  const loadGanttData = async () => {
    try {
      setLoading(true);
      const response = await fetch('/api/projects/gantt');
      const data = await response.json();
      if (data.success) {
        // 填充默认时间（如果没有）
        const today = new Date();
        const processed = data.data.map((p: GanttProject) => {
          if (!p.start) {
            const start = new Date(today);
            p.start = start.toISOString().split('T')[0];
          }
          if (!p.end) {
            const end = new Date(today);
            end.setDate(end.getDate() + 30);
            p.end = end.toISOString().split('T')[0];
          }
          // 计算进度
          if (p.status === 'done') p.progress = 100;
          else if (p.status === 'progress') p.progress = 50;
          else p.progress = 0;
          return p;
        });
        setProjects(processed);
      }
    } catch (e) {
      console.error('加载甘特图数据失败:', e);
    } finally {
      setLoading(false);
    }
  };

  // 计算时间范围
  const allDates = projects.flatMap(p => [new Date(p.start).getTime(), new Date(p.end).getTime()]);
  const minDate = allDates.length > 0 ? new Date(Math.min(...allDates)) : new Date();
  const maxDate = allDates.length > 0 ? new Date(Math.max(...allDates)) : new Date();
  const totalDays = Math.ceil((maxDate.getTime() - minDate.getTime()) / (1000 * 60 * 60 * 24));

  const getXPosition = (dateStr: string) => {
    const date = new Date(dateStr).getTime();
    const percent = ((date - minDate.getTime()) / (maxDate.getTime() - minDate.getTime())) * 100;
    return `${Math.max(0, Math.min(100, percent))}%`;
  };

  const getWidth = (startStr: string, endStr: string) => {
    const start = new Date(startStr).getTime();
    const end = new Date(endStr).getTime();
    const percent = ((end - start) / (maxDate.getTime() - minDate.getTime())) * 100;
    return `${Math.max(5, Math.min(100, percent))}%`;
  };

  const formatDate = (dateStr: string) => {
    return dateStr.split('T')[0];
  };

  return (
    <div className="p-6">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">项目甘特图</h1>
        <p className="text-gray-600 mt-1">
          共 {projects.length} 个项目 · 时间跨度 {formatDate(minDate.toISOString())} 至 {formatDate(maxDate.toISOString())}
        </p>
      </div>

      {loading ? (
        <div className="text-center py-20 text-gray-500">加载中...</div>
      ) : projects.length === 0 ? (
        <div className="text-center py-20 text-gray-500">
          <p>暂无项目数据</p>
        </div>
      ) : (
        <div className="bg-white rounded-lg shadow-sm border border-gray-200 overflow-hidden">
          {/* 时间轴头部 */}
          <div className="border-b border-gray-200 px-4 py-3 bg-gray-50">
            <div className="grid grid-cols-4 gap-4 text-sm font-medium text-gray-700">
              <div className="col-span-1">项目名称</div>
              <div className="col-span-3">时间线</div>
            </div>
          </div>

          {/* 甘特图列表 */}
          <div className="divide-y divide-gray-100">
            {projects.map(project => (
              <div key={project.id} className="grid grid-cols-4 gap-4 p-3 hover:bg-gray-50">
                <div className="col-span-1">
                  <div className="font-medium text-gray-900">{project.name}</div>
                  <div className="flex items-center gap-2 mt-1">
                    <span className={`px-2 py-0.5 rounded-full text-xs text-white bg-${getStatusColor(project.status)}`}>
                      {getStatusText(project.status)}
                    </span>
                    <span className="text-xs text-gray-500">P{project.priority}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {formatDate(project.start)} - {formatDate(project.end)}
                  </div>
                </div>
                <div className="col-span-3 relative flex items-center h-16">
                  <div className="absolute inset-0 bg-gray-100 rounded">
                    <div
                      className="absolute top-1 bottom-1 rounded h-full transition-all"
                      style={{
                        left: getXPosition(project.start),
                        width: getWidth(project.start, project.end),
                        backgroundColor: getStatusColor(project.status),
                        opacity: 0.8
                      }}
                    >
                      {project.progress > 0 && (
                        <div
                          className="absolute top-0 left-0 bottom-0 rounded bg-current opacity-40"
                          style={{ width: `${project.progress}%` }}
                        />
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default GanttPage;
