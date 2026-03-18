# 看板3.0功能增强集成指南

## 已完成步骤 ✅

### 1. 创建DocumentManager组件
- ✅ 文件: `/opt/kanban-react/frontend/src/components/DocumentManager.tsx`
- ✅ 样式: `/opt/kanban-react/frontend/src/components/DocumentManager.css`
- ✅ 功能: 上传、下载、删除文档

### 2. 修改Projects.tsx
- ✅ 添加导入: `import { DocumentManager } from '../components/DocumentManager'`
- ✅ 添加样式导入: `import '../components/DocumentManager.css'`
- ✅ 添加fullscreen状态: `const [fullscreenProject, setFullscreenProject] = useState<number | null>(null)`

## 待完成步骤 ⏳

### 步骤3: 在展开区域添加DocumentManager组件

找到Projects.tsx中的这一行（约335行附近）：
```tsx
{expandedProjects.has(p.id) && (
  <div className="project-details">
```

在`</div>`之前添加：
```tsx
    {/* 文档管理区域 */}
    <div className="documents-section">
      <h4 style={{ marginBottom: '12px', color: '#374151' }}>📎 重要文档</h4>
      <DocumentManager projectId={p.id} />
    </div>
```

### 步骤4: 添加全屏功能

1. 添加全屏按钮（在项目头部）：
```tsx
<button 
  className="fullscreen-btn"
  onClick={() => setFullscreenProject(p.id)}
  title="全屏展示"
>
  ⛶
</button>
```

2. 添加全屏覆盖层（在项目卡片外部）：
```tsx
{fullscreenProject === p.id && (
  <div 
    className="fullscreen-overlay"
    onClick={() => setFullscreenProject(null)}
  >
    <div className="fullscreen-content" onClick={e => e.stopPropagation()}>
      <button 
        className="close-fullscreen"
        onClick={() => setFullscreenProject(null)}
      >
        <X size={24} />
      </button>
      <h2>{p.name}</h2>
      <p>{p.description}</p>
      <DocumentManager projectId={p.id} />
    </div>
  </div>
)}
```

### 步骤5: 添加样式到Layout.css

```css
.documents-section {
  margin-top: 20px;
  padding: 16px;
  background: #f9fafb;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
}

.fullscreen-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 4px 8px;
  border-radius: 4px;
  transition: background 0.2s;
}

.fullscreen-btn:hover {
  background: #f3f4f6;
}

.fullscreen-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.8);
  z-index: 10000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.fullscreen-content {
  background: white;
  width: 90vw;
  height: 90vh;
  border-radius: 12px;
  padding: 32px;
  overflow: auto;
  position: relative;
}

.close-fullscreen {
  position: absolute;
  top: 16px;
  right: 16px;
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: 50%;
  transition: background 0.2s;
}

.close-fullscreen:hover {
  background: #f3f4f6;
}
```

### 步骤6: 添加X图标导入

在Projects.tsx的import部分添加：
```tsx
import { ChevronDown, ChevronUp, Target, ListTodo, Edit2, X } from 'lucide-react'
```

## 构建和部署

### 构建
```bash
cd /opt/kanban-react/frontend
npm install  # 如果需要
npx vite build
```

### 部署
```bash
# 构建输出在dist/目录
# 重启Nginx
systemctl reload nginx
```

## 回滚方案

如果出现问题，恢复备份：
```bash
cp /opt/kanban-react/frontend/src/pages/Projects.tsx.backup_* \
   /opt/kanban-react/frontend/src/pages/Projects.tsx
rm /opt/kanban-react/frontend/src/components/DocumentManager.tsx
rm /opt/kanban-react/frontend/src/components/DocumentManager.css
systemctl reload nginx
```
