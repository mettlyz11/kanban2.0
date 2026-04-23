# 🏗️ Dudu 工作流程架构图

可编辑的 Dudu 工作流程架构图系统，支持拖拽编辑、文件同步和版本历史。

## 📋 功能特性

### 1. 可视化编辑
- ✅ 拖拽节点调整位置
- ✅ 双击节点编辑属性（名称、颜色、描述、关联文件）
- ✅ 创建/删除节点连接
- ✅ 缩放画布（50%-200%）
- ✅ 添加/删除节点

### 2. 文件同步
- ✅ 自动读取 SOUL.md、USER.md、AGENTS.md 等文件
- ✅ 提取文件关键信息更新节点描述
- ✅ 支持文件变化自动监听（可选）
- ✅ 手动同步按钮

### 3. 版本历史
- ✅ 每次保存自动创建版本
- ✅ 查看历史版本列表
- ✅ 一键恢复到任意版本
- ✅ 版本描述和创建时间记录

### 4. 后端 API

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/workflow-architecture` | GET | 获取架构图数据 |
| `/api/workflow-architecture` | PUT | 保存架构图修改 |
| `/api/workflow-architecture/sync` | POST | 从文件同步 |
| `/api/workflow-architecture/versions` | GET | 获取版本历史 |
| `/api/workflow-architecture/versions/<id>` | GET | 获取特定版本 |
| `/api/workflow-architecture/versions/<id>/restore` | POST | 恢复版本 |
| `/api/workflow-architecture/node` | POST | 创建节点 |
| `/api/workflow-architecture/node/<id>` | DELETE | 删除节点 |
| `/api/workflow-architecture/connection` | POST | 创建连接 |
| `/api/workflow-architecture/connection/<id>` | DELETE | 删除连接 |
| `/api/workflow-architecture/file/<filename>` | GET | 获取文件内容 |
| `/api/workflow-architecture/file/<filename>` | PUT | 更新文件内容 |

## 🚀 快速开始

### 1. 初始化数据库
```bash
cd /Users/mettlyz/.openclaw/workspace/kanban-react/backend
python3 create_workflow_architecture_db.py
```

### 2. 启动后端服务
```bash
# 确保已安装依赖
pip3 install flask flask-cors watchdog

# 启动后端
python3 app.py
```

### 3. 启动文件监听服务（可选）
```bash
# 在新终端窗口
python3 file_sync_service.py
```

### 4. 访问前端
打开浏览器访问：`http://localhost:5000/architecture-editable`

## 📁 数据库结构

### workflow_architecture 表
```sql
CREATE TABLE workflow_architecture (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,           -- 节点名称
    type TEXT DEFAULT 'node',     -- 节点类型：node | file
    x INTEGER DEFAULT 0,          -- X 坐标
    y INTEGER DEFAULT 0,          -- Y 坐标
    color TEXT DEFAULT '#e3f2fd', -- 背景颜色
    file_path TEXT,               -- 关联文件路径
    description TEXT,             -- 节点描述
    created_at TIMESTAMP,
    updated_at TIMESTAMP
)
```

### workflow_connections 表
```sql
CREATE TABLE workflow_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_node INTEGER NOT NULL,   -- 起始节点 ID
    to_node INTEGER NOT NULL,     -- 目标节点 ID
    created_at TIMESTAMP,
    FOREIGN KEY (from_node) REFERENCES workflow_architecture(id),
    FOREIGN KEY (to_node) REFERENCES workflow_architecture(id)
)
```

### workflow_architecture_versions 表
```sql
CREATE TABLE workflow_architecture_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    version INTEGER NOT NULL,     -- 版本号
    nodes_json TEXT NOT NULL,     -- 节点数据 JSON
    connections_json TEXT NOT NULL, -- 连接数据 JSON
    created_at TIMESTAMP,
    description TEXT              -- 版本描述
)
```

## 🎨 前端组件

### ArchitectureEditableV2.tsx
位置：`/frontend/src/pages/ArchitectureEditableV2.tsx`

**主要功能：**
- SVG 画布渲染
- 节点拖拽
- 连接创建
- 节点编辑弹窗
- 版本历史弹窗
- 缩放控制

**使用方法：**
```tsx
import { ArchitectureEditableV2 } from './pages/ArchitectureEditableV2'

function App() {
  return <ArchitectureEditableV2 />
}
```

## 🔧 配置

### 监听的文件
默认监听以下工作空间文件：
- SOUL.md - 身份定义
- USER.md - 用户档案
- AGENTS.md - 执行准则
- standards.md - 标准规范
- MEMORY.md - 长期记忆
- HEARTBEAT.md - 定时检查
- CHECKLIST.md - 检查清单
- TOOLS.md - 工具配置

### 默认节点
初始化时会自动创建以下节点：
1. 用户输入 → 接收用户指令
2. SOUL.md → 身份定义和人格
3. USER.md → 用户档案和偏好
4. AGENTS.md → 执行准则
5. standards.md → 标准规范
6. 任务执行 → 执行具体任务
7. MEMORY.md → 长期记忆存储
8. 结果输出 → 输出执行结果
9. HEARTBEAT.md → 定时检查

## 📝 使用示例

### 1. 编辑节点
1. 点击"编辑模式"按钮
2. 双击要编辑的节点
3. 修改名称、颜色、描述等
4. 点击"保存"

### 2. 创建连接
1. 进入编辑模式
2. 点击节点右上角的"+"按钮
3. 拖动到目标节点
4. 松开鼠标完成连接

### 3. 同步文件
1. 修改了 SOUL.md 等文件
2. 点击"同步文件"按钮
3. 节点描述自动更新

### 4. 恢复版本
1. 点击"历史版本"按钮
2. 选择要恢复的版本
3. 点击"恢复"按钮

## 🐛 故障排除

### 问题：节点不显示
**解决：** 检查数据库是否正确初始化
```bash
python3 -c "import sqlite3; conn = sqlite3.connect('kanban_v5.db'); c = conn.cursor(); c.execute('SELECT COUNT(*) FROM workflow_architecture'); print(c.fetchone()[0])"
```

### 问题：文件同步失败
**解决：** 确认文件路径和工作空间路径正确
```python
import os
print(os.path.exists('/Users/mettlyz/.openclaw/workspace/SOUL.md'))
```

### 问题：连接无法创建
**解决：** 确保处于编辑模式，并且从"+"按钮开始拖动

## 📊 性能优化

- 使用 SVG 渲染，支持大量节点
- 版本历史限制为最近 50 个版本
- 文件监听使用防抖（1 秒）
- 画布缩放使用 CSS transform

## 🔮 未来计划

- [ ] 支持节点分组
- [ ] 支持节点搜索
- [ ] 导出为图片/PDF
- [ ] 导入/导出 JSON
- [ ] 协作编辑
- [ ] 节点模板
- [ ] 自动布局算法

## 📄 许可证

内部使用
