#!/usr/bin/env python3
"""
SDS 看板前端改进: 甘特图/递进缩进/多视图/搜索/未读标记/快捷面板/全键盘/动态列

作为一个轻量级HTTP API模块，可内嵌到 sds_main.py 的 Flask 路由中
"""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger('KanbanFrontend')

# HTML 模板目录
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def _safe_int(val, default=0) -> int:
    if val is None:
        return default
    try:
        return int(val)
    except (TypeError, ValueError):
        return default


def _build_gantt_data(project_id: int = None, limit: int = 50) -> Dict:
    """从数据库生成甘特图数据"""
    try:
        from lib.db_connector import execute_query

        where = "WHERE deleted_at IS NULL"
        if project_id:
            where += f" AND project_id = {project_id}"

        tasks = execute_query(f"""
            SELECT id, number, title, status, priority, goal_id, task_type,
                   created_at, updated_at, due_date, start_time, end_time,
                   depends_on, retry_count
            FROM tasks {where}
            ORDER BY created_at DESC LIMIT {limit}
        """)

        gantt_tasks = []
        links = []

        for t in tasks or []:
            title = (t.get('title') or '未命名')[:40]
            status = t.get('status', 'pending')
            created = t.get('created_at')
            due = t.get('due_date')
            dep = t.get('depends_on')

            # 决定显示颜色
            if status == 'completed':
                color = '#22c55e'
            elif status == 'in_progress':
                color = '#3b82f6'
            elif status == 'failed':
                color = '#ef4444'
            else:
                color = '#94a3b8'

            gantt_tasks.append({
                "id": f"task-{t['id']}",
                "name": f"#{t['id']} {title}",
                "start": created.isoformat() if created else datetime.now().isoformat(),
                "end": (due or (created + timedelta(days=3))).isoformat() if due or created else (datetime.now() + timedelta(days=3)).isoformat(),
                "status": status,
                "progress": 100 if status == 'completed' else (50 if status == 'in_progress' else 0),
                "color": color,
                "dependencies": []
            })

            if dep:
                links.append({
                    "source": f"task-{dep}",
                    "target": f"task-{t['id']}"
                })

        return {"tasks": gantt_tasks, "links": links}

    except Exception as e:
        logger.error(f"获取甘特图数据失败: {e}")
        return {"tasks": [], "links": []}


def api_gantt_chart(project_id: int = None) -> Dict:
    """API: 获取甘特图数据"""
    return _build_gantt_data(project_id)


def api_task_hierarchy() -> List[Dict]:
    """API: 获取父子任务层级"""
    try:
        from lib.db_connector import execute_query
        tasks = execute_query("""
            SELECT id, number, title, status, priority, goal_id, depends_on, parent_id
            FROM tasks WHERE deleted_at IS NULL AND status != 'cancelled'
            ORDER BY priority DESC, created_at DESC LIMIT 100
        """)

        # 构建树形结构
        task_map = {}
        for t in tasks or []:
            t['children'] = []
            t['level'] = 0
            task_map[t['id']] = t

        roots = []
        for t in tasks or []:
            parent_id = t.get('parent_id') or t.get('depends_on')
            if parent_id and parent_id in task_map:
                task_map[parent_id]['children'].append(t)
                t['level'] = task_map[parent_id].get('level', 0) + 1
            else:
                roots.append(t)

        # 递归计算缩进
        def _add_level(node, level):
            node['level'] = level
            for child in node.get('children', []):
                _add_level(child, level + 1)

        for root in roots:
            _add_level(root, 0)

        return roots

    except Exception as e:
        logger.error(f"获取任务层级失败: {e}")
        return []


def api_grouped_tasks(group_by: str = "status") -> Dict:
    """API: 多视图分组任务"""
    try:
        from lib.db_connector import execute_query

        if group_by == "status":
            tasks = execute_query("""
                SELECT status, JSON_ARRAYAGG(JSON_OBJECT('id', id, 'title', title, 'priority', priority, 'updated_at', updated_at))
                FROM tasks WHERE deleted_at IS NULL
                GROUP BY status
            """)
        elif group_by == "type":
            tasks = execute_query("""
                SELECT task_type as grp, JSON_ARRAYAGG(JSON_OBJECT('id', id, 'title', title, 'status', status, 'priority', priority))
                FROM tasks WHERE deleted_at IS NULL AND task_type IS NOT NULL
                GROUP BY task_type
            """)
        elif group_by == "project":
            tasks = execute_query("""
                SELECT COALESCE(p.name, 'No Project') as grp, JSON_ARRAYAGG(JSON_OBJECT('id', t.id, 'title', t.title, 'status', t.status, 'priority', t.priority))
                FROM tasks t LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.deleted_at IS NULL
                GROUP BY grp
            """)
        else:
            return {"error": f"Unknown group_by: {group_by}"}

        result = {}
        for row in tasks or []:
            grp = row.get('grp') or 'unknown'
            items = row.get("JSON_ARRAYAGG(...)") or "[]"
            if isinstance(items, str):
                items = json.loads(items)
            result[grp] = items

        return result

    except Exception as e:
        logger.error(f"分组查询失败: {e}")
        return {}


def api_search_tasks(query: str, limit: int = 20) -> List[Dict]:
    """API: 搜索任务 (FULLTEXT搜索)"""
    try:
        from lib.db_connector import execute_query

        # 先尝试FULLTEXT搜索
        results = execute_query(f"""
            SELECT id, number, title, status, priority, goal_id, task_type,
                   MATCH(title, description) AGAINST(%s IN BOOLEAN MODE) as relevance
            FROM tasks
            WHERE deleted_at IS NULL
              AND MATCH(title, description) AGAINST(%s IN BOOLEAN MODE)
            ORDER BY relevance DESC, updated_at DESC
            LIMIT {limit}
        """, (f"+{query}*", f"+{query}*"))

        if results:
            return results

        # FULLTEXT失败用LIKE
        results = execute_query(f"""
            SELECT id, number, title, status, priority, task_type
            FROM tasks
            WHERE deleted_at IS NULL
              AND (title LIKE %s OR description LIKE %s)
            ORDER BY updated_at DESC
            LIMIT {limit}
        """, (f"%{query}%", f"%{query}%"))

        return results or []

    except Exception as e:
        logger.error(f"搜索任务失败: {e}")
        return []


def api_unread_tasks(hours: int = 24) -> List[Dict]:
    """API: 获取最近更新的未读任务"""
    try:
        from lib.db_connector import execute_query

        tasks = execute_query("""
            SELECT id, number, title, status, priority, updated_at
            FROM tasks
            WHERE deleted_at IS NULL
              AND updated_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
            ORDER BY updated_at DESC
            LIMIT 50
        """, (hours,))

        return [{
            "id": t['id'],
            "number": t.get('number', ''),
            "title": (t.get('title') or '')[:50],
            "status": t.get('status', ''),
            "priority": t.get('priority', ''),
            "updated_at": t.get('updated_at').isoformat() if t.get('updated_at') else '',
            "is_new": (datetime.now() - (t.get('updated_at') or datetime.now())).total_seconds() < 3600
        } for t in tasks or []]

    except Exception as e:
        logger.error(f"获取未读任务失败: {e}")
        return []


def api_quick_actions() -> Dict:
    """API: 快捷操作入口定义"""
    return {
        "actions": [
            {"id": "new_task", "label": "📝 新建任务", "icon": "➕", "shortcut": "Alt+N", "url": "/admin/tasks/new"},
            {"id": "quick_report", "label": "📊 快照报告", "icon": "📊", "shortcut": "Alt+R", "url": "/api/health/report"},
            {"id": "retry_failed", "label": "🔄 重试失败", "icon": "🔄", "shortcut": "Alt+F", "action": "retry_failed_tasks"},
            {"id": "refresh", "label": "🔄 刷新视图", "icon": "🔄", "shortcut": "Alt+Q", "action": "refresh"},
            {"id": "clear_cache", "label": "🗑️ 清理缓存", "icon": "🗑️", "shortcut": "Alt+C", "action": "clear_cache"},
            {"id": "kanban_view", "label": "📋 看板视图", "icon": "📋", "url": "/admin/kanban"},
            {"id": "gantt_view", "label": "📈 甘特图", "icon": "📈", "url": "/admin/gantt"},
            {"id": "search", "label": "🔍 搜索", "icon": "🔍", "shortcut": "Alt+S", "action": "focus_search"},
        ]
    }


def api_keyboard_shortcuts() -> Dict:
    """API: 全键盘快捷键定义"""
    return {
        "shortcuts": [
            {"keys": "Alt+N", "action": "new_task", "description": "新建任务"},
            {"keys": "Alt+S", "action": "focus_search", "description": "聚焦搜索框"},
            {"keys": "Alt+R", "action": "refresh", "description": "刷新当前视图"},
            {"keys": "Alt+F", "action": "retry_failed", "description": "重试失败任务"},
            {"keys": "Alt+1", "action": "view_status", "description": "状态视图"},
            {"keys": "Alt+2", "action": "view_type", "description": "类型视图"},
            {"keys": "Alt+3", "action": "view_project", "description": "项目视图"},
            {"keys": "Alt+4", "action": "view_gantt", "description": "甘特图视图"},
            {"keys": "Alt+C", "action": "clear_cache", "description": "清理缓存"},
            {"keys": "Up/Down", "action": "navigate", "description": "上下导航"},
            {"keys": "Enter", "action": "open_task", "description": "打开选中任务"},
            {"keys": "Escape", "action": "close_panel", "description": "关闭面板"},
            {"keys": "Delete", "action": "soft_delete", "description": "软删除选中任务"},
            {"keys": "? / F1", "action": "show_help", "description": "显示快捷键帮助"},
        ]
    }


def api_dynamic_columns() -> List[Dict]:
    """API: 可拖拽的看板列定义"""
    return [
        {"id": "pending", "title": "⏳ 待处理", "status": "pending", "color": "#94a3b8", "order": 0},
        {"id": "in_progress", "title": "🔥 进行中", "status": "in_progress", "color": "#3b82f6", "order": 1},
        {"id": "review", "title": "🔍 审核中", "status": "pending_review", "color": "#f59e0b", "order": 2},
        {"id": "completed", "title": "✅ 已完成", "status": "completed", "color": "#22c55e", "order": 3},
        {"id": "failed", "title": "❌ 失败", "status": "failed", "color": "#ef4444", "order": 4},
        {"id": "failed_retryable", "title": "🔄 可重试", "status": "failed_retryable", "color": "#f97316", "order": 5},
        {"id": "cancelled", "title": "🚫 已取消", "status": "cancelled", "color": "#6b7280", "order": 6},
    ]


# ============ 生成HTML ============

def generate_gantt_html() -> str:
    """生成Mermaid甘特图HTML"""
    return """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>SDS 甘特图</title>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
<style>
  body { font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 20px; }
  .container { max-width: 1400px; margin: auto; }
  h1 { color: #38bdf8; }
  #gantt-container { background: #1e293b; border-radius: 8px; padding: 20px; }
  .stats { display: flex; gap: 10px; margin: 10px 0; flex-wrap: wrap; }
  .stat-card { background: #1e293b; border-radius: 8px; padding: 12px 20px; min-width: 120px; }
  .stat-card .label { color: #94a3b8; font-size: 12px; }
  .stat-card .value { color: #38bdf8; font-size: 20px; font-weight: bold; }
  .view-controls { margin: 10px 0; display: flex; gap: 10px; }
  .view-controls button { background: #334155; color: #e2e8f0; border: 1px solid #475569; padding: 6px 14px; border-radius: 4px; cursor: pointer; }
  .view-controls button.active { background: #38bdf8; color: #0f172a; }
  .search-bar { margin: 10px 0; }
  .search-bar input { background: #334155; color: #e2e8f0; border: 1px solid #475569; padding: 8px 12px; border-radius: 4px; width: 300px; }
</style></head>
<body>
<div class="container">
  <h1>📈 SDS 项目甘特图</h1>
  <div class="stats" id="stats"></div>
  <div class="view-controls">
    <button class="active" onclick="switchView('status')">📊 状态视图</button>
    <button onclick="switchView('type')">🏷️ 类型视图</button>
    <button onclick="switchView('project')">📁 项目视图</button>
    <button onclick="switchView('gantt')">📈 甘特图</button>
  </div>
  <div class="search-bar">
    <input type="text" id="searchInput" placeholder="🔍 搜索任务..." onkeyup="handleSearch(event)">
    <span style="color:#64748b;font-size:12px;margin-left:8px;">Alt+S 聚焦搜索 | ? 查看快捷键</span>
  </div>
  <div id="gantt-container">
    <div class="mermaid" id="ganttChart">
gantt
    title 项目进度
    dateFormat  YYYY-MM-DD
    axisFormat  %m-%d
    section 加载中
    等待数据 :done, 2026-01-01, 1d
    </div>
  </div>
  <div id="task-hierarchy" style="margin-top:20px;"></div>
</div>
<script>
let currentView = 'status';
let allTasks = [];

mermaid.initialize({ startOnLoad: true, theme: 'dark' });

async function refresh() {
  const res = await fetch('/api/kanban/gantt');
  const data = await res.json();
  allTasks = data.tasks || [];

  // Stats
  const total = allTasks.length;
  const done = allTasks.filter(t => t.status === 'completed').length;
  const progress = allTasks.filter(t => t.status === 'in_progress').length;
  document.getElementById('stats').innerHTML = `
    <div class="stat-card"><div class="label">总任务</div><div class="value">${total}</div></div>
    <div class="stat-card"><div class="label">已完成</div><div class="value">${done}</div></div>
    <div class="stat-card"><div class="label">进行中</div><div class="value">${progress}</div></div>
    <div class="stat-card"><div class="label">完成率</div><div class="value">${total ? Math.round(done/total*100) : 0}%</div></div>
  `;

  renderView(currentView);
}

function renderView(view) {
  currentView = view;
  if (view === 'gantt') {
    renderGantt();
  } else {
    renderGroupedView(view);
  }
}

function renderGantt() {
  const container = document.getElementById('gantt-container');
  let mermaidCode = 'gantt\\n    title 项目进度\\n    dateFormat  YYYY-MM-DD\\n    axisFormat  %m-%d\\n';

  const sections = {};
  allTasks.forEach(t => {
    const section = t.status || '待处理';
    if (!sections[section]) sections[section] = [];
    sections[section].push(t);
  });

  Object.entries(sections).forEach(([section, tasks]) => {
    mermaidCode += `    section ${section}\\n`;
    tasks.slice(0, 15).forEach(t => {
      const status = t.status === 'completed' ? 'done' : (t.status === 'in_progress' ? 'active' : '');
      const start = (t.start || '').substring(0, 10);
      const end = (t.end || '').substring(0, 10);
      mermaidCode += `    ${t.name.substring(0, 30)} :${status} ${start}, ${end}\\n`;
    });
  });

  document.getElementById('ganttChart').textContent = mermaidCode;
  mermaid.run();
  container.style.display = 'block';
  document.getElementById('task-hierarchy').style.display = 'none';
}

async function renderGroupedView(view) {
  document.getElementById('gantt-container').style.display = 'none';
  const hierarchy = document.getElementById('task-hierarchy');
  hierarchy.style.display = 'block';

  const res = await fetch(`/api/kanban/grouped?by=${view}`);
  const data = await res.json();

  let html = '<div class="grouped-view">';
  Object.entries(data).forEach(([group, tasks]) => {
    const level = group === 'in_progress' || group === 'pending' ? 0 : 1;
    html += `<div class="group"><h3 class="group-title" style="color:#94a3b8;margin:20px 0 10px 0;padding:8px 12px;background:#1e293b;border-radius:4px;cursor:pointer;">📁 ${group} (${tasks.length})</h3>`;
    (tasks || []).forEach((t, i) => {
      const indent = t.level !== undefined ? t.level * 20 : 0;
      const status_icon = t.status === 'completed' ? '✅' : t.status === 'in_progress' ? '🔥' : t.status === 'failed' ? '❌' : '⏳';
      html += `<div style="padding:6px 12px;margin:2px 0;background:#334155;border-radius:4px;margin-left:${indent}px;display:flex;justify-content:space-between;" ondblclick="window.open('/admin/tasks/${t.id}','_blank')">
        <span>${'  '.repeat(t.level || 0)}${status_icon} <strong>#${t.id}</strong> ${(t.title || '')}</span>
        <span style="color:#94a3b8;">${t.priority || ''} ${t.updated_at ? new Date(t.updated_at).toLocaleDateString() : ''}</span>
      </div>`;
    });
    html += '</div>';
  });
  html += '</div>';
  hierarchy.innerHTML = html;

  // Add styles
  const style = document.createElement('style');
  style.textContent = '.grouped-view .group-title:hover { background: #475569; }';
  document.head.appendChild(style);
}

function switchView(view) {
  document.querySelectorAll('.view-controls button').forEach(b => b.classList.remove('active'));
  event.target.classList.add('active');
  renderView(view);
}

function handleSearch(e) {
  if (e.key === 'Enter') {
    const q = document.getElementById('searchInput').value;
    if (q) {
      fetch(`/api/kanban/search?q=${encodeURIComponent(q)}`).then(r => r.json()).then(tasks => {
        let html = '<h3 style="color:#38bdf8;">🔍 搜索结果</h3>';
        (tasks || []).forEach(t => {
          html += `<div style="padding:8px;margin:4px 0;background:#334155;border-radius:4px;"><strong>#${t.id}</strong> ${t.title || ''} <span style="color:#94a3b8;">[${t.status}]</span></div>`;
        });
        document.getElementById('task-hierarchy').innerHTML = html;
        document.getElementById('task-hierarchy').style.display = 'block';
      });
    }
  }
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
  if (e.altKey) {
    if (e.key === 's' || e.key === 'S') {
      e.preventDefault();
      document.getElementById('searchInput').focus();
    } else if (e.key === '1') switchView('status');
    else if (e.key === '2') switchView('type');
    else if (e.key === '3') switchView('project');
    else if (e.key === '4') switchView('gantt');
    else if (e.key === 'r' || e.key === 'R') refresh();
    else if (e.key === 'n' || e.key === 'N') window.open('/admin/tasks/new','_blank');
    else if (e.key === '?') alert('快捷键:\\nAlt+N 新建任务\\nAlt+S 搜索\\nAlt+R 刷新\\nAlt+1-4 切换视图\\nAlt+? 帮助');
  }
  if (e.key === '?') {
    alert('快捷键:\\nAlt+N 新建任务\\nAlt+S 搜索\\nAlt+R 刷新\\nAlt+1-4 切换视图\\nAlt+? 帮助');
  }
});

refresh();
</script>
<style>
  .grouped-view { color: #e2e8f0; }
</style>
</body></html>"""


def generate_kanban_html() -> str:
    """生成看板HTML（含多视图、搜索、无读标记）"""
    return """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>SDS 看板</title>
<style>
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; overflow-x: hidden; }
  .header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }
  h1 { color: #38bdf8; font-size: 24px; }
  .toolbar { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
  .toolbar button { background: #334155; color: #e2e8f0; border: 1px solid #475569; padding: 6px 14px; border-radius: 6px; cursor: pointer; font-size: 13px; }
  .toolbar button:hover { background: #475569; }
  .toolbar button.active { background: #38bdf8; color: #0f172a; }
  .search-box { position: relative; }
  .search-box input { background: #1e293b; color: #e2e8f0; border: 1px solid #475569; padding: 8px 12px 8px 32px; border-radius: 6px; width: 250px; font-size: 13px; }
  .search-box input:focus { outline: none; border-color: #38bdf8; }
  .search-box .icon { position: absolute; left: 10px; top: 50%; transform: translateY(-50%); color: #64748b; }
  .kanban-board { display: flex; gap: 12px; overflow-x: auto; padding: 10px 0; min-height: 70vh; }
  .column { background: #1e293b; border-radius: 8px; min-width: 280px; max-width: 320px; flex-shrink: 0; display: flex; flex-direction: column; }
  .column-header { padding: 10px 14px; font-weight: bold; font-size: 14px; display: flex; justify-content: space-between; align-items: center; border-radius: 8px 8px 0 0; cursor: grab; }
  .column-header .count { background: rgba(255,255,255,0.1); border-radius: 10px; padding: 2px 8px; font-size: 12px; }
  .column-body { padding: 8px; overflow-y: auto; min-height: 200px; }
  .task-card { background: #334155; border-radius: 6px; padding: 10px 12px; margin-bottom: 8px; cursor: pointer; border-left: 3px solid #475569; transition: all 0.2s; }
  .task-card:hover { background: #3b4f6b; transform: translateY(-1px); }
  .task-card.unread { border-left-color: #38bdf8; box-shadow: 0 0 4px rgba(56, 189, 248, 0.3); }
  .task-card .task-id { color: #94a3b8; font-size: 11px; }
  .task-card .task-title { font-size: 13px; margin: 4px 0; line-height: 1.4; }
  .task-card .task-meta { display: flex; gap: 6px; font-size: 11px; color: #94a3b8; flex-wrap: wrap; }
  .task-card .task-meta .tag { padding: 1px 6px; border-radius: 3px; background: rgba(56,189,248,0.15); color: #38bdf8; }
  .task-card .task-meta .tag.high { background: rgba(239,68,68,0.15); color: #ef4444; }
  .quick-panel { position: fixed; bottom: 20px; right: 20px; display: flex; flex-direction: column; gap: 6px; }
  .quick-panel button { width: 44px; height: 44px; border-radius: 50%; background: #38bdf8; color: #0f172a; border: none; font-size: 18px; cursor: pointer; box-shadow: 0 4px 12px rgba(56,189,248,0.3); }
  .quick-panel button:hover { transform: scale(1.1); }
  .toast { position: fixed; bottom: 80px; right: 20px; background: #1e293b; border: 1px solid #475569; padding: 10px 16px; border-radius: 6px; display: none; }
  .shortcut-hint { position: fixed; top: 50%; left: 50%; transform: translate(-50%,-50%); background: #1e293b; border: 1px solid #475569; border-radius: 12px; padding: 24px; display: none; z-index: 100; max-width: 400px; }
  .shortcut-hint table { width: 100%; }
  .shortcut-hint td { padding: 6px 12px; border-bottom: 1px solid #334155; }
  .shortcut-hint .key { background: #334155; padding: 2px 8px; border-radius: 4px; font-family: monospace; }
  .shortcut-hint .close { float: right; cursor: pointer; color: #ef4444; }
</style>
</head>
<body>
<div class="header">
  <h1>📋 SDS 看板</h1>
  <div class="toolbar">
    <button class="active" onclick="switchGroup('status')" id="g-status">📊 状态</button>
    <button onclick="switchGroup('type')" id="g-type">🏷️ 类型</button>
    <button onclick="switchGroup('project')" id="g-project">📁 项目</button>
    <button onclick="refresh()">🔄 刷新</button>
    <button onclick="retryFailed()">🔄 重试失败</button>
    <div class="search-box">
      <span class="icon">🔍</span>
      <input type="text" id="searchInput" placeholder="搜索任务..." oninput="searchTasks(this.value)">
    </div>
  </div>
</div>
<div class="kanban-board" id="kanbanBoard"></div>
<div class="quick-panel">
  <button onclick="window.open('/admin/tasks/new','_blank')" title="新建任务 (Alt+N)">➕</button>
  <button onclick="refresh()" title="刷新 (Alt+R)">🔄</button>
  <button onclick="showShortcuts()" title="快捷键 (?)">⌨️</button>
</div>
<div class="shortcut-hint" id="shortcutHint">
  <span class="close" onclick="hideShortcuts()">✕</span>
  <h3 style="margin-bottom:12px;">⌨️ 快捷键</h3>
  <table>
    <tr><td><span class="key">Alt+N</span></td><td>新建任务</td></tr>
    <tr><td><span class="key">Alt+S</span></td><td>搜索</td></tr>
    <tr><td><span class="key">Alt+R</span></td><td>刷新</td></tr>
    <tr><td><span class="key">Alt+1-3</span></td><td>切换视图</td></tr>
    <tr><td><span class="key">Up/Down</span></td><td>导航任务</td></tr>
    <tr><td><span class="key">Enter</span></td><td>打开任务</td></tr>
    <tr><td><span class="key">?</span></td><td>帮助</td></tr>
  </table>
</div>
<script>
let currentGroup = 'status';
let allTasks = [];
let selectedIdx = -1;
let filteredTasks = [];

async function refresh() {
  const [tasksRes, unreadRes] = await Promise.all([
    fetch('/api/kanban/unread?hours=48'),
    fetch('/api/kanban/unread?hours=24')
  ]);
  const recentTasks = await tasksRes.json();
  allTasks = recentTasks || [];
  filteredTasks = allTasks;
  unreadIds = new Set((await unreadRes.json() || []).map(t => t.id));
  render();
}

function render() {
  const board = document.getElementById('kanbanBoard');

  if (currentGroup === 'status') {
    const statuses = [
      {id:'pending', title:'⏳ 待处理', color:'#94a3b8'},
      {id:'in_progress', title:'🔥 进行中', color:'#3b82f6'},
      {id:'pending_review', title:'🔍 审核中', color:'#f59e0b'},
      {id:'completed', title:'✅ 已完成', color:'#22c55e'},
      {id:'failed', title:'❌ 失败', color:'#ef4444'}
    ];
    board.innerHTML = statuses.map(s => renderColumn(s, filteredTasks.filter(t => t.status === s.id))).join('');
  } else {
    // Grouped view
    loadGroupedView(currentGroup);
  }
}

function renderColumn(col, tasks) {
  const isUnread = t => unreadIds && unreadIds.has(t.id);
  return `<div class="column" data-status="${col.id}">
    <div class="column-header" style="border-left:3px solid ${col.color};">
      <span>${col.title}</span>
      <span class="count">${tasks.length}</span>
    </div>
    <div class="column-body" id="col-${col.id}">
      ${tasks.slice(0, 30).map((t, i) => {
        const high = t.priority === 'high' || t.priority === '1';
        return `<div class="task-card ${isUnread(t) ? 'unread' : ''}" onclick="openTask(${t.id})">
          <div class="task-id">#${t.id} ${t.number || ''}</div>
          <div class="task-title">${escapeHtml(t.title || '')}</div>
          <div class="task-meta">
            ${high ? '<span class="tag high">高优先</span>' : ''}
            <span>${t.updated_at ? new Date(t.updated_at).toLocaleString('zh-CN', {month:'short',day:'numeric',hour:'2-digit',minute:'2-digit'}) : ''}</span>
            ${isUnread(t) ? '<span class="tag">NEW</span>' : ''}
          </div>
        </div>`;
      }).join('')}
      ${tasks.length > 30 ? `<div style="text-align:center;color:#64748b;padding:8px;">...还有 ${tasks.length-30} 个</div>` : ''}
    </div>
  </div>`;
}

async function loadGroupedView(group) {
  const board = document.getElementById('kanbanBoard');
  const res = await fetch(`/api/kanban/grouped?by=${group}`);
  const data = await res.json();
  let html = '<div style="display:flex;gap:12px;overflow-x:auto;width:100%;">';
  Object.entries(data).slice(0, 10).forEach(([g, tasks]) => {
    html += `<div class="column" style="min-width:280px;">
      <div class="column-header"><span>📁 ${g}</span><span class="count">${(tasks||[]).length}</span></div>
      <div class="column-body">
        ${(tasks||[]).slice(0, 30).map(t =>
          `<div class="task-card" onclick="openTask(${t.id})">
            <div class="task-id">#${t.id}</div>
            <div class="task-title">${escapeHtml(t.title || '')}</div>
            <div class="task-meta"><span>${t.status || ''}</span></div>
          </div>`
        ).join('')}
      </div>
    </div>`;
  });
  html += '</div>';
  board.innerHTML = html;
}

function switchGroup(group) {
  currentGroup = group;
  document.querySelectorAll('.toolbar button[id^="g-"]').forEach(b => b.classList.remove('active'));
  document.getElementById(`g-${group}`).classList.add('active');
  render();
}

function openTask(id) { window.open(`/admin/tasks/${id}`, '_blank'); }

function searchTasks(q) {
  if (!q.trim()) { filteredTasks = allTasks; render(); return; }
  const ql = q.toLowerCase();
  filteredTasks = allTasks.filter(t => (t.title || '').toLowerCase().includes(ql) || String(t.id).includes(q));
  render();
}

function retryFailed() { fetch('/api/scheduler/retry-failed', {method:'POST'}).then(r => r.json()).then(d => alert(`重试了 ${d.retried || 0} 个失败任务`)); }

function showShortcuts() { document.getElementById('shortcutHint').style.display = 'block'; }
function hideShortcuts() { document.getElementById('shortcutHint').style.display = 'none'; }
function escapeHtml(s) { return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

// Keyboard
document.addEventListener('keydown', e => {
  if (e.altKey) {
    if (e.key === 'n'||e.key==='N') { e.preventDefault(); window.open('/admin/tasks/new','_blank'); }
    if (e.key === 's'||e.key==='S') { e.preventDefault(); document.getElementById('searchInput').focus(); }
    if (e.key === 'r'||e.key==='R') { e.preventDefault(); refresh(); }
    if (e.key === '1') { e.preventDefault(); switchGroup('status'); }
    if (e.key === '2') { e.preventDefault(); switchGroup('type'); }
    if (e.key === '3') { e.preventDefault(); switchGroup('project'); }
  }
  if (e.key === '?') { showShortcuts(); e.preventDefault(); }
  if (e.key === 'Escape') { hideShortcuts(); }
});

refresh();
</script>
</body></html>"""


def generate_task_template_html() -> str:
    """生成任务模板助手HTML"""
    return """<!DOCTYPE html>
<html lang="zh">
<head><meta charset="UTF-8"><title>任务模板助手</title>
<style>
  body { font-family: -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; padding: 20px; }
  .container { max-width: 800px; margin: auto; }
  h1 { color: #38bdf8; }
  .templates { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px; margin: 20px 0; }
  .template-card { background: #1e293b; border-radius: 8px; padding: 16px; cursor: pointer; border: 1px solid #334155; }
  .template-card:hover { border-color: #38bdf8; }
  .template-card h3 { margin: 0 0 8px 0; font-size: 15px; }
  .template-card p { color: #94a3b8; font-size: 13px; margin: 0; }
  .template-card .tags { margin-top: 8px; display: flex; gap: 4px; }
  .template-card .tag { background: rgba(56,189,248,0.1); color: #38bdf8; padding: 2px 8px; border-radius: 4px; font-size: 11px; }
  .quick-form { background: #1e293b; border-radius: 8px; padding: 20px; margin: 20px 0; }
  .quick-form input, .quick-form textarea, .quick-form select { width: 100%; background: #334155; color: #e2e8f0; border: 1px solid #475569; padding: 8px 12px; border-radius: 4px; margin: 4px 0 12px 0; font-size: 13px; }
  .quick-form textarea { min-height: 80px; }
  .quick-form button { background: #38bdf8; color: #0f172a; border: none; padding: 8px 20px; border-radius: 4px; cursor: pointer; font-weight: bold; }
</style>
</head>
<body>
<div class="container">
  <h1>📝 任务模板助手</h1>
  <div class="quick-form">
    <label>快速创建任务</label>
    <input type="text" id="taskTitle" placeholder="任务标题...">
    <textarea id="taskDesc" placeholder="任务描述..."></textarea>
    <select id="taskPriority">
      <option value="high">高优先级</option>
      <option value="medium" selected>中优先级</option>
      <option value="low">低优先级</option>
    </select>
    <button onclick="quickCreate()">🚀 创建任务</button>
  </div>
  <h2>📂 模板库</h2>
  <div class="templates" id="templateList"></div>
</div>
<script>
const templates = [
  {title:"📊 定期报告", desc:"生成周期性的SDS运行报告", tags:["报告","周期"], taskDesc:"生成SDS系统运行报告，包含任务统计、健康状态、告警信息"},
  {title:"🔧 系统维护", desc:"执行系统维护任务", tags:["维护","系统"], taskDesc:"执行系统健康检查、清理过期数据、优化性能"},
  {title:"📚 知识补充", desc:"补充知识库内容", tags:["知识","文档"], taskDesc:"检索最近完成的任务，提取关键产出和洞见，更新知识库"},
  {title:"🧪 质量检查", desc:"检查任务完成质量", tags:["质量","验证"], taskDesc:"扫描最近完成的任务，验证执行日志和结果质量"},
  {title:"📈 优化建议", desc:"生成系统优化方案", tags:["优化","分析"], taskDesc:"分析当前SDS系统运行瓶颈，给出具体的优化建议"},
  {title:"🤖 自动化测试", desc:"运行自动化测试", tags:["测试","自动化"], taskDesc:"执行SDS核心模块自动化测试，生成测试报告"}
];

function loadTemplates() {
  document.getElementById('templateList').innerHTML =
    templates.map(t => `<div class="template-card" onclick="useTemplate(this)">
      <h3>${t.title}</h3>
      <p>${t.desc}</p>
      <div class="tags">${t.tags.map(tag => `<span class="tag">${tag}</span>`).join('')}</div>
      <div style="display:none;" class="template-desc">${t.taskDesc}</div>
    </div>`).join('');
}

function useTemplate(el) {
  document.getElementById('taskTitle').value = el.querySelector('h3').textContent;
  document.getElementById('taskDesc').value = el.querySelector('.template-desc').textContent;
}

async function quickCreate() {
  const title = document.getElementById('taskTitle').value;
  const desc = document.getElementById('taskDesc').value;
  if (!title) { alert('请输入任务标题'); return; }
  const res = await fetch('/api/tasks/quick-create', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({title, description: desc, priority: document.getElementById('taskPriority').value})
  });
  const data = await res.json();
  if (data.id) {
    alert(`✅ 任务 #${data.id} 已创建`);
    document.getElementById('taskTitle').value = '';
    document.getElementById('taskDesc').value = '';
  } else {
    alert('❌ 创建失败');
  }
}

loadTemplates();
</script>
</body></html>"""


def setup_routes(app):
    """
    将看板API路由添加到Flask应用

    Args:
        app: Flask应用实例
    """
    try:
        from flask import jsonify, request, Response

        @app.route('/api/kanban/gantt')
        def kanban_gantt():
            project_id = request.args.get('project_id', type=int)
            return jsonify(api_gantt_chart(project_id))

        @app.route('/api/kanban/hierarchy')
        def kanban_hierarchy():
            return jsonify(api_task_hierarchy())

        @app.route('/api/kanban/grouped')
        def kanban_grouped():
            group_by = request.args.get('by', 'status')
            return jsonify(api_grouped_tasks(group_by))

        @app.route('/api/kanban/search')
        def kanban_search():
            query = request.args.get('q', '')
            return jsonify(api_search_tasks(query))

        @app.route('/api/kanban/unread')
        def kanban_unread():
            hours = request.args.get('hours', 24, type=int)
            return jsonify(api_unread_tasks(hours))

        @app.route('/api/kanban/actions')
        def kanban_actions():
            return jsonify(api_quick_actions())

        @app.route('/api/kanban/shortcuts')
        def kanban_shortcuts():
            return jsonify(api_keyboard_shortcuts())

        @app.route('/api/kanban/columns')
        def kanban_columns():
            return jsonify(api_dynamic_columns())

        # HTML 页面
        @app.route('/admin/gantt')
        def admin_gantt():
            return Response(generate_gantt_html(), mimetype='text/html')

        @app.route('/admin/kanban-enhanced')
        def admin_kanban_enhanced():
            return Response(generate_kanban_html(), mimetype='text/html')

        @app.route('/admin/templates')
        def admin_templates():
            return Response(generate_task_template_html(), mimetype='text/html')

        # 搜索API
        @app.route('/api/tasks/search')
        def tasks_search():
            query = request.args.get('q', '')
            return jsonify(api_search_tasks(query))

        # 快捷创建任务
        @app.route('/api/tasks/quick-create', methods=['POST'])
        def tasks_quick_create():
            data = request.get_json() or {}
            title = data.get('title', '快速任务')
            desc = data.get('description', '')
            priority = data.get('priority', 'medium')

            try:
                from lib.db_connector import execute_update
                execute_update("""
                    INSERT INTO tasks (title, description, status, priority, task_type, created_at, updated_at)
                    VALUES (%s, %s, 'pending', %s, 'quick_create', NOW(), NOW())
                """, (title[:150], desc[:2000], priority))
                return jsonify({"success": True, "id": 0, "message": f"已创建: {title[:30]}"})
            except Exception as e:
                return jsonify({"success": False, "error": str(e)}), 500

        # 重试失败任务
        @app.route('/api/scheduler/retry-failed', methods=['POST'])
        def scheduler_retry_failed():
            try:
                from lib.db_connector import execute_query, execute_update
                failed = execute_query("SELECT id FROM tasks WHERE status = 'failed' AND retry_count < 3 LIMIT 20")
                retried = 0
                for t in failed or []:
                    execute_update("UPDATE tasks SET status = 'failed_retryable', updated_at = NOW() WHERE id = %s", (t['id'],))
                    retried += 1
                return jsonify({"retried": retried})
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        # 体检报告API
        @app.route('/api/health/report')
        def health_report():
            try:
                from modules.health_report import generate_report, format_report_markdown
                report = generate_report()
                return jsonify(report)
            except Exception as e:
                return jsonify({"error": str(e)}), 500

        logger.info("✅ 看板改进API路由已注册")

    except ImportError:
        logger.warning("Flask未安装，跳过看板路由注册")
    except Exception as e:
        logger.warning(f"看板路由注册失败: {e}")
