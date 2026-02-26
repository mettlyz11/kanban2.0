# 看板v2.0 功能迁移计划

## 原系统功能清单

### 核心功能 (已完成)
- ✅ Dashboard 总览
- ✅ Projects 项目管理 (列表+创建)
- ✅ Tasks 任务管理 (列表+筛选)

### 需要迁移的功能

#### Phase 1: 基础功能
- [ ] Cron 定时任务管理
- [ ] 资产/股票管理
- [ ] 手动审核任务
- [ ] 技能库管理

#### Phase 2: 高级功能
- [ ] 计算任务管理 (T109)
- [ ] 分子/反应管理
- [ ] 聊天功能 (问Dudu)
- [ ] 邮件管理

#### Phase 3: 系统功能
- [ ] 用户认证/登录
- [ ] 数据统计图表
- [ ] 版本日志
- [ ] 系统状态监控

---

## 实施策略

### 技术架构
- **前端**: React 18 + TypeScript + React Router 6
- **样式**: 自定义CSS (保持与v1一致的视觉风格)
- **API**: 复用v1的Flask后端 (端口8086)
- **状态管理**: React Hooks (useState, useEffect)

### API复用策略
v2.0前端直接调用v1.0的API，无需重写后端：
- 项目: /api/projects
- 任务: /api/tasks
- 统计: /api/stats
- ...等等

### 组件规划
```
src/
├── components/     # 通用组件
│   ├── Layout.tsx
│   ├── Sidebar.tsx
│   ├── Header.tsx
│   └── Modal.tsx
├── pages/          # 页面组件
│   ├── Dashboard.tsx
│   ├── Projects.tsx
│   ├── Tasks.tsx
│   ├── Cron.tsx
│   ├── Stocks.tsx
│   ├── ManualReview.tsx
│   └── Skills.tsx
├── hooks/          # 自定义Hooks
│   └── useApi.ts
└── utils/          # 工具函数
    └── api.ts
```
