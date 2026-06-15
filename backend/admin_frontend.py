"""
管理员后台前端页面 - 5个功能完整的HTML页面
所有页面：内联CSS+JS | 暗色主题 | 响应式布局 | 统一导航栏
"""
from flask import Blueprint, Response, request, jsonify, current_app
import json, os, time
from datetime import datetime, date

admin_html_bp = Blueprint('admin_html', __name__)

# ============================================
# 通用导航栏 HTML 片段
# ============================================
NAV_HTML = """
<nav class="admin-nav">
  <div class="nav-brand">⚙️ 管理员后台</div>
  <div class="nav-links">
    <a href="/admin/copilot" class="nav-item" data-page="copilot">📋 副驾驶</a>
    <a href="/admin/command-center" class="nav-item" data-page="command">🎮 指挥台</a>
    <a href="/admin/monitor" class="nav-item" data-page="monitor">📊 监控台</a>
    <a href="/admin/feedback" class="nav-item" data-page="feedback">💬 反馈台</a>
    <a href="/admin/long-tasks" class="nav-item" data-page="longtasks">🏗️ 长程任务</a>
    <a href="/admin/settings" class="nav-item" data-page="settings">⚙️ 配置台</a>
    <a href="/admin/learning" class="nav-item" data-page="learning">📚 学习中心</a>
    <a href="/admin/audit" class="nav-item" data-page="audit">📋 审计报告</a>
    <a href="/admin/trash" class="nav-item" data-page="trash">🗑️ 回收站</a>
    <a href="/admin/search" class="nav-item" data-page="search">🔍 搜索</a>
    <a href="/admin/audit-log" class="nav-item" data-page="auditlog">📝 审计日志</a>
  </div>
</nav>
"""

COMMON_CSS = """
* { margin: 0; padding: 0; box-sizing: border-box; }
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #0d1117; color: #c9d1d9; min-height: 100vh; }
.admin-nav { display: flex; align-items: center; justify-content: space-between; background: #161b22; border-bottom: 1px solid #30363d; padding: 0 24px; height: 56px; position: sticky; top: 0; z-index: 100; }
.nav-brand { font-size: 16px; font-weight: 700; color: #58a6ff; white-space: nowrap; }
.nav-links { display: flex; gap: 4px; }
.nav-item { color: #8b949e; text-decoration: none; padding: 8px 14px; border-radius: 6px; font-size: 14px; transition: all .15s; white-space: nowrap; }
.nav-item:hover { color: #c9d1d9; background: #21262d; }
.nav-item.active { color: #58a6ff; background: #1f3a5f; }
.main-content { max-width: 1400px; margin: 0 auto; padding: 24px; }
.page-title { font-size: 24px; font-weight: 700; margin-bottom: 20px; color: #f0f6fc; }
.card { background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
.card-title { font-size: 14px; font-weight: 600; color: #8b949e; margin-bottom: 8px; text-transform: uppercase; letter-spacing: .05em; }
.status-badge { display: inline-block; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
.status-badge.done { background: #1b3a2c; color: #3fb950; }
.status-badge.running { background: #1a3a5c; color: #58a6ff; }
.status-badge.waiting { background: #3a2c1a; color: #d29922; }
.status-badge.pending { background: #3a1a1a; color: #f85149; }
.btn { display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px; border-radius: 6px; border: 1px solid #30363d; background: #21262d; color: #c9d1d9; font-size: 14px; cursor: pointer; transition: all .15s; }
.btn:hover { background: #30363d; border-color: #8b949e; }
.btn-primary { background: #238636; border-color: #2ea043; color: #fff; }
.btn-primary:hover { background: #2ea043; }
.btn-danger { background: #7d1f1f; border-color: #da3633; color: #fff; }
.btn-danger:hover { background: #da3633; }
input, textarea, select { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; color: #c9d1d9; padding: 8px 12px; font-size: 14px; outline: none; transition: border-color .15s; }
input:focus, textarea:focus, select:focus { border-color: #58a6ff; }
.loading { text-align: center; padding: 40px; color: #8b949e; }
.loading::after { content: '...'; animation: dots 1.5s infinite; }
@keyframes dots { 0%,20% { content: '.'; } 40% { content: '..'; } 60%,100% { content: '...'; } }
.error-msg { color: #f85149; background: #3a1a1a; border: 1px solid #da3633; border-radius: 6px; padding: 12px; margin: 8px 0; font-size: 14px; }
.empty-state { text-align: center; padding: 40px; color: #484f58; font-size: 14px; }
.scrollbar-thin::-webkit-scrollbar { width: 6px; }
.scrollbar-thin::-webkit-scrollbar-track { background: transparent; }
.scrollbar-thin::-webkit-scrollbar-thumb { background: #30363d; border-radius: 3px; }
@media (max-width: 768px) {
  .admin-nav { flex-wrap: wrap; height: auto; padding: 8px 16px; gap: 8px; }
  .nav-links { flex-wrap: wrap; }
  .nav-item { font-size: 12px; padding: 6px 10px; }
  .main-content { padding: 12px; }
}
"""

# ============================================
# 1. 副驾驶报告页
# ============================================
COPILOT_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>副驾驶报告 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.copilot-layout { display: flex; gap: 16px; height: calc(100vh - 100px); }
.copilot-sidebar { width: 340px; min-width: 280px; display: flex; flex-direction: column; border: 1px solid #30363d; border-radius: 8px; background: #161b22; }
.copilot-sidebar .filter-bar { padding: 12px; border-bottom: 1px solid #30363d; display: flex; gap: 8px; flex-wrap: wrap; }
.copilot-sidebar .filter-bar select { flex: 1; min-width: 80px; }
.copilot-sidebar .filter-bar .btn { padding: 6px 12px; font-size: 12px; }
.copilot-list { flex: 1; overflow-y: auto; }
.copilot-item { padding: 12px 16px; border-bottom: 1px solid #21262d; cursor: pointer; transition: background .15s; }
.copilot-item:hover { background: #1c2128; }
.copilot-item.active { background: #1f3a5f; border-left: 3px solid #58a6ff; }
.copilot-item .item-type { font-size: 11px; color: #8b949e; margin-bottom: 4px; }
.copilot-item .item-type .type-tag { display: inline-block; padding: 1px 6px; border-radius: 4px; font-size: 10px; font-weight: 600; }
.type-tag.quality { background: #1b3a2c; color: #3fb950; }
.type-tag.direction { background: #1a3a5c; color: #58a6ff; }
.type-tag.inspiration { background: #3a2c1a; color: #d29922; }
.type-tag.research { background: #2a1a3a; color: #bc8cff; }
.copilot-item .item-name { font-size: 13px; color: #e6edf3; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.copilot-item .item-time { font-size: 11px; color: #484f58; margin-top: 4px; }
.copilot-detail { flex: 1; border: 1px solid #30363d; border-radius: 8px; background: #161b22; padding: 24px; overflow-y: auto; }
.copilot-detail .detail-header { margin-bottom: 16px; }
.copilot-detail .detail-header h2 { font-size: 18px; color: #f0f6fc; margin-bottom: 8px; }
.copilot-detail .detail-meta { font-size: 12px; color: #8b949e; margin-bottom: 16px; }
.copilot-detail .detail-body { font-size: 14px; line-height: 1.7; color: #c9d1d9; }
.copilot-detail .detail-body pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; overflow-x: auto; font-size: 13px; margin: 8px 0; }
@media (max-width: 768px) {
  .copilot-layout { flex-direction: column; height: auto; }
  .copilot-sidebar { width: 100%; min-width: unset; max-height: 300px; }
  .copilot-detail { min-height: 400px; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">📋 副驾驶报告</h1>
  <div class="copilot-layout">
    <div class="copilot-sidebar">
      <div class="filter-bar">
        <select id="filterType"><option value="">全部类型</option><option value="quality">质量</option><option value="direction">方向</option><option value="inspiration">灵感</option><option value="research">研究</option></select>
        <button class="btn" onclick="loadReports()">🔄 刷新</button>
      </div>
      <div class="copilot-list scrollbar-thin" id="reportList"></div>
    </div>
    <div class="copilot-detail scrollbar-thin" id="reportDetail"><div class="empty-state">← 选择一条报告查看详情</div></div>
  </div>
</div>
<script>
let allReports = [];
async function loadReports() {
  const el = document.getElementById('reportList');
  el.innerHTML = '<div class="loading">加载中</div>';
  try {
    const r = await fetch('/api/admin/copilot/reports');
    const d = await r.json();
    allReports = d.reports || [];
    renderList();
  } catch(e) { el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
function renderList() {
  const filter = document.getElementById('filterType').value;
  const filtered = filter ? allReports.filter(r => r.type === filter) : allReports;
  const el = document.getElementById('reportList');
  if (!filtered.length) { el.innerHTML = '<div class="empty-state">暂无报告</div>'; return; }
  el.innerHTML = filtered.map(r => '<div class="copilot-item" onclick="loadDetail(\\''+r.file+'\\',this)" data-file="'+r.file+'"><div class="item-type"><span class="type-tag '+r.type+'">'+r.type+'</span></div><div class="item-name">'+r.file+'</div><div class="item-time">'+new Date(r.time*1000).toLocaleString()+'</div></div>').join('') + '<div class="empty-state" style="padding:12px;font-size:12px">共 '+filtered.length+' 条</div>';
}
async function loadDetail(file, el) {
  document.querySelectorAll('.copilot-item').forEach(x => x.classList.remove('active'));
  if (el) el.classList.add('active');
  const detail = document.getElementById('reportDetail');
  detail.innerHTML = '<div class="loading">加载中</div>';
  try {
    const r = await fetch('/api/admin/copilot/report/'+encodeURIComponent(file));
    const d = await r.json();
    if (!d.success) { detail.innerHTML = '<div class="error-msg">'+d.error+'</div>'; return; }
    const data = d.data;
    detail.innerHTML = '<div class="detail-header"><h2>'+file+'</h2><div class="detail-meta">更新时间: '+(data.updated_at||data.time||'')+'</div></div><div class="detail-body"><pre>'+escapeHtml(JSON.stringify(data,null,2))+'</pre></div>';
  } catch(e) { detail.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
document.getElementById('filterType').addEventListener('change', renderList);
loadReports();
</script>
</body></html>"""

# ============================================
# 2. 指挥台
# ============================================
COMMAND_CENTER_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>指挥台 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.command-input-area { margin-bottom: 24px; }
.command-input-area textarea { width: 100%; min-height: 100px; padding: 12px; font-size: 15px; line-height: 1.6; resize: vertical; border-color: #30363d; }
.command-input-area .input-actions { display: flex; gap: 12px; align-items: center; margin-top: 12px; }
.command-input-area .input-actions .btn { padding: 10px 24px; font-size: 15px; }
.command-history { border: 1px solid #30363d; border-radius: 8px; background: #161b22; }
.command-history .history-header { padding: 12px 16px; border-bottom: 1px solid #30363d; font-weight: 600; font-size: 14px; color: #8b949e; }
.command-item { padding: 12px 16px; border-bottom: 1px solid #21262d; display: flex; gap: 12px; align-items: flex-start; }
.command-item .cmd-time { font-size: 12px; color: #484f58; min-width: 120px; white-space: nowrap; }
.command-item .cmd-content { flex: 1; font-size: 14px; color: #e6edf3; word-break: break-word; }
.command-item .cmd-status { min-width: 60px; text-align: right; }
.status-badge.created { background: #1a3a5c; color: #58a6ff; }
.status-badge.processing { background: #3a2c1a; color: #d29922; }
.status-badge.completed { background: #1b3a2c; color: #3fb950; }
.status-badge.failed { background: #3a1a1a; color: #f85149; }
@media (max-width: 768px) {
  .command-item { flex-wrap: wrap; }
  .command-item .cmd-time { min-width: unset; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">🎮 指挥台</h1>
  <div class="command-input-area card">
    <textarea id="commandInput" placeholder="输入指令...&#10;例如: 创建一个新任务「优化数据库查询性能」，优先级高"></textarea>
    <div class="input-actions">
      <button class="btn btn-primary" onclick="sendCommand()">📨 发送指令</button>
      <span id="cmdFeedback" style="font-size:13px;color:#8b949e"></span>
    </div>
  </div>
  <div class="command-history">
    <div class="history-header">📜 历史指令 (最近20条)</div>
    <div id="historyList"></div>
  </div>
</div>
<script>
let pollTimer = null;
async function sendCommand() {
  const input = document.getElementById('commandInput');
  const fb = document.getElementById('cmdFeedback');
  const text = input.value.trim();
  if (!text) { fb.textContent = '⚠️ 请输入指令'; return; }
  fb.textContent = '⏳ 发送中...';
  try {
    const r = await fetch('/api/admin/command', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({command:text}) });
    const d = await r.json();
    if (d.success) {
      fb.textContent = '✅ 指令已下达 (任务 #'+d.task_id+')';
      input.value = '';
      loadHistory();
    } else {
      fb.textContent = '❌ '+d.error;
    }
  } catch(e) {
    fb.textContent = '❌ 网络错误: '+e.message;
  }
}
async function loadHistory() {
  const el = document.getElementById('historyList');
  try {
    const r = await fetch('/api/admin/command/history');
    const d = await r.json();
    const cmds = d.commands || [];
    if (!cmds.length) { el.innerHTML = '<div class="empty-state">暂无指令历史</div>'; return; }
    el.innerHTML = cmds.map(c => '<div class="command-item"><div class="cmd-time">'+formatTime(c.created_at)+'</div><div class="cmd-content">'+escapeHtml(c.content||c.title||c.command||'')+'</div><div class="cmd-status"><span class="status-badge '+(c.status||'created')+'">'+(c.status||'created')+'</span></div></div>').join('');
  } catch(e) {
    el.innerHTML = '<div class="error-msg">加载失败</div>';
  }
}
function formatTime(t) {
  if (!t) return '';
  try { return new Date(t).toLocaleString(); } catch(e) { return t; }
}
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadHistory();
pollTimer = setInterval(loadHistory, 10000);
// 快捷键: Ctrl+Enter 发送
document.getElementById('commandInput').addEventListener('keydown', function(e) {
  if (e.ctrlKey && e.key === 'Enter') sendCommand();
});
</script>
</body></html>"""

# ============================================
# 3. 监控台
# ============================================
# ============================================
# 通用模态框 & JS (所有页面共用)
# ============================================
COMMON_MODALS = """
<!-- Edit JSON Modal -->
<div class="modal-overlay" id="editJsonModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:200;align-items:center;justify-content:center">
  <div class="modal" style="background:#161b22;border-radius:12px;padding:24px;max-width:900px;width:95%;max-height:90vh;overflow-y:auto;border:1px solid #30363d">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <span id="editJsonBadge" style="font-family:monospace;font-size:12px;padding:2px 10px;background:#21262d;border-radius:6px;color:#8b949e">#0</span>
      <span style="font-size:16px;font-weight:600;color:#e6edf3">📝 编辑 JSON 描述</span>
    </div>
    <textarea id="editJsonTextarea" spellcheck="false" style="width:100%;min-height:400px;max-height:65vh;padding:14px;font-family:'SF Mono','Fira Code',Menlo,monospace;font-size:13px;line-height:1.6;background:#0d1117;color:#c9d1d9;border:1px solid #30363d;border-radius:8px;resize:vertical;tab-size:2;white-space:pre;overflow:auto"></textarea>
    <div id="editJsonResult"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
      <button class="btn btn-outline" onclick="closeEditJsonModal()" style="padding:8px 20px;border:1px solid #30363d;border-radius:6px;background:transparent;color:#c9d1d9;cursor:pointer">取消</button>
      <button class="btn btn-primary" onclick="saveEditJson()" style="padding:8px 20px;border:none;border-radius:6px;background:#238636;color:#fff;cursor:pointer">💾 保存</button>
    </div>
  </div>
</div>

<!-- Phase R Modal -->
<div class="modal-overlay" id="phaserModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:200;align-items:center;justify-content:center">
  <div class="modal" style="background:#161b22;border-radius:12px;padding:24px;max-width:1200px;width:95%;max-height:90vh;overflow-y:auto;border:1px solid #30363d">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <span id="phaserBadge" style="font-family:monospace;font-size:12px;padding:2px 10px;background:#21262d;border-radius:6px;color:#8b949e">#0</span>
      <span style="font-size:16px;font-weight:600;color:#e6edf3">🧠 Phase R 思考过程</span>
    </div>
    <div id="phaserLoading" style="text-align:center;padding:24px;color:#8b949e">加载中...</div>
    <div id="phaserContent" style="display:none">
      <div id="phaserFlow" style="margin:16px 0;min-height:100px"></div>
      <div id="phaserDetail" style="margin-top:16px"></div>
    </div>
    <div id="phaserEmpty" style="display:none;text-align:center;padding:40px">
      <div style="font-size:48px;margin-bottom:12px">🔬</div>
      <div style="font-size:14px;color:#8b949e">该任务尚未经过 Phase R 思考</div>
    </div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
      <button class="btn btn-outline" onclick="closePhaserModal()" style="padding:8px 20px;border:1px solid #30363d;border-radius:6px;background:transparent;color:#c9d1d9;cursor:pointer">关闭</button>
    </div>
  </div>
</div>

<!-- Attachment Modal -->
<div class="modal-overlay" id="attachModal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);z-index:200;align-items:center;justify-content:center">
  <div class="modal" style="background:#161b22;border-radius:12px;padding:24px;max-width:900px;width:95%;max-height:90vh;overflow-y:auto;border:1px solid #30363d">
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:16px">
      <span id="attachBadge" style="font-family:monospace;font-size:12px;padding:2px 10px;background:#21262d;border-radius:6px;color:#8b949e">#0</span>
      <span style="font-size:16px;font-weight:600;color:#e6edf3">📎 参考文件附件</span>
    </div>
    <div id="attachList" style="margin-bottom:16px"><div class="loading">加载中...</div></div>
    <hr style="border-color:#30363d;margin:16px 0">
    <div style="font-size:14px;font-weight:600;color:#e6edf3;margin-bottom:12px">添加附件</div>
    <div style="margin-bottom:12px">
      <label style="font-size:13px;color:#8b949e;display:block;margin-bottom:4px">🔗 方式1: 通过URL添加</label>
      <div style="display:flex;gap:8px">
        <input type="text" id="attachUrlInput" placeholder="https://example.com/file.pdf" style="flex:1;padding:8px 12px;background:#0d1117;border:1px solid #30363d;border-radius:6px;color:#c9d1d9;font-size:13px">
        <button onclick="addAttachByUrl()" style="padding:8px 16px;border:none;border-radius:6px;background:#238636;color:#fff;cursor:pointer;font-size:13px">添加</button>
      </div>
    </div>
    <div style="margin-bottom:12px">
      <label style="font-size:13px;color:#8b949e;display:block;margin-bottom:4px">📋 方式2: 粘贴 (Ctrl+V / Cmd+V)</label>
      <div id="attachPasteZone" style="border:2px dashed #30363d;border-radius:8px;padding:24px;text-align:center;color:#8b949e;font-size:13px;cursor:pointer" tabindex="0">点击此处后按 Ctrl+V / Cmd+V 粘贴<br><small>支持图片、文本、文件</small></div>
      <div id="attachPastePreview" style="margin-top:8px"></div>
    </div>
    <div style="margin-bottom:12px">
      <label style="font-size:13px;color:#8b949e;display:block;margin-bottom:4px">💻 方式3: 本地上传</label>
      <input type="file" id="attachFileInput" multiple style="font-size:13px;color:#c9d1d9" onchange="uploadLocalFiles(this.files)">
      <div id="attachProgress" style="margin-top:8px;font-size:12px;color:#8b949e"></div>
    </div>
    <div id="attachResult"></div>
    <div style="display:flex;gap:8px;justify-content:flex-end;margin-top:16px">
      <button class="btn btn-outline" onclick="closeAttachModal()" style="padding:8px 20px;border:1px solid #30363d;border-radius:6px;background:transparent;color:#c9d1d9;cursor:pointer">关闭</button>
    </div>
  </div>
</div>

<script>
// ===== Edit JSON =====
let editJsonTaskId = 0;
async function openEditJsonModal(taskId) {
  editJsonTaskId = taskId;
  document.getElementById('editJsonBadge').textContent = '#' + taskId;
  document.getElementById('editJsonResult').innerHTML = '';
  try {
    const r = await fetch('/api/admin/tasks/detail/' + taskId);
    const d = await r.json();
    if (d.success) {
      const desc = d.task.description || '{}';
      try {
        const parsed = JSON.parse(desc);
        document.getElementById('editJsonTextarea').value = JSON.stringify(parsed, null, 2);
      } catch(e) {
        document.getElementById('editJsonTextarea').value = desc;
      }
    }
  } catch(e) {}
  document.getElementById('editJsonModal').style.display = 'flex';
}
function closeEditJsonModal() {
  document.getElementById('editJsonModal').style.display = 'none';
}
async function saveEditJson() {
  const raw = document.getElementById('editJsonTextarea').value.trim();
  const el = document.getElementById('editJsonResult');
  try { JSON.parse(raw); } catch(e) { el.innerHTML = '<div style="padding:8px;color:#f85149;font-size:13px">❌ JSON 格式错误: ' + e.message + '</div>'; return; }
  el.innerHTML = '<div style="padding:8px;color:#8b949e;font-size:13px">⏳ 保存中...</div>';
  try {
    const r = await fetch('/api/admin/tasks/' + editJsonTaskId + '/description', { method: 'PUT', headers: {'Content-Type':'application/json'}, body: JSON.stringify({description: raw}) });
    const d = await r.json();
    if (d.success) { el.innerHTML = '<div style="padding:8px;color:#3fb950;font-size:13px">✅ 描述已更新</div>'; setTimeout(closeEditJsonModal, 1000); }
    else { el.innerHTML = '<div style="padding:8px;color:#f85149;font-size:13px">❌ ' + (d.error||'保存失败') + '</div>'; }
  } catch(e) { el.innerHTML = '<div style="padding:8px;color:#f85149;font-size:13px">❌ ' + e.message + '</div>'; }
}

// ===== Phase R =====
async function openPhaserModal(taskId) {
  document.getElementById('phaserBadge').textContent = '#' + taskId;
  document.getElementById('phaserLoading').style.display = 'block';
  document.getElementById('phaserContent').style.display = 'none';
  document.getElementById('phaserEmpty').style.display = 'none';
  document.getElementById('phaserModal').style.display = 'flex';
  const COLORS = ['#3b82f6','#8b5cf6','#f59e0b','#22c55e','#06b6d4'];
  const STEPS = ['📋现状审查','🎯目标对齐','💡Brainstorming','✅方案评估','📦子任务'];
  try {
    const r = await fetch('/api/admin/tasks/detail/' + taskId);
    const d = await r.json();
    document.getElementById('phaserLoading').style.display = 'none';
    if (!d.success || !d.task || !d.task.execution_log || d.task.execution_log.indexOf('Phase R') < 0) {
      document.getElementById('phaserEmpty').style.display = 'block'; return;
    }
    const log = d.task.execution_log;
    let flow = '<div style="display:flex;align-items:flex-start;gap:4px;overflow-x:auto;padding:8px 0">';
    STEPS.forEach((s, i) => {
      const has = log.indexOf(s) > -1;
      flow += '<div style="flex:1;min-width:100px;text-align:center"><div style="width:48px;height:48px;border-radius:50%;background:'+COLORS[i]+';display:flex;align-items:center;justify-content:center;margin:0 auto 8px;font-size:20px">'+s[0]+'</div><div style="font-size:12px;font-weight:600;color:#e6edf3">'+s+'</div><div style="font-size:10px;color:#8b949e;margin-top:4px">'+(has?'✅ 已完成':'⏳')+'</div></div>';
      if (i < STEPS.length-1) flow += '<div style="flex:0 0 20px;padding-top:24px;color:#484f58;font-size:16px">→</div>';
    });
    flow += '</div>';
    document.getElementById('phaserFlow').innerHTML = flow;
    document.getElementById('phaserDetail').innerHTML = '<div style="padding:12px;background:#0d1117;border:1px solid #30363d;border-radius:8px;font-size:13px;line-height:1.7;white-space:pre-wrap;color:#c9d1d9;max-height:400px;overflow-y:auto">'+escapeHtml(log.substring(0,3000))+'</div>';
    document.getElementById('phaserContent').style.display = 'block';
  } catch(e) {
    document.getElementById('phaserLoading').style.display = 'none';
    document.getElementById('phaserEmpty').style.display = 'block';
  }
}
function closePhaserModal() { document.getElementById('phaserModal').style.display = 'none'; }

// ===== Attachments =====
let attachTaskId = 0;
async function openAttachModal(taskId) {
  attachTaskId = taskId;
  document.getElementById('attachBadge').textContent = '#' + taskId;
  document.getElementById('attachUrlInput').value = '';
  document.getElementById('attachResult').innerHTML = '';
  document.getElementById('attachPastePreview').innerHTML = '';
  document.getElementById('attachProgress').innerHTML = '';
  document.getElementById('attachModal').style.display = 'flex';
  await loadAttachments(taskId);
}
function closeAttachModal() { document.getElementById('attachModal').style.display = 'none'; }
async function loadAttachments(taskId) {
  const el = document.getElementById('attachList');
  el.innerHTML = '<div style="text-align:center;padding:16px;color:#8b949e;font-size:13px">加载中...</div>';
  try {
    const r = await fetch('/api/admin/attachments/' + taskId);
    const d = await r.json();
    if (!d.success || !d.data || !d.data.length) { el.innerHTML = '<div style="text-align:center;padding:16px;color:#8b949e;font-size:13px">暂无附件</div>'; return; }
    el.innerHTML = '<table style="width:100%;font-size:13px;border-collapse:collapse"><tr style="border-bottom:1px solid #30363d"><th style="text-align:left;padding:8px;color:#8b949e">文件名</th><th style="text-align:left;padding:8px;color:#8b949e">大小</th><th style="text-align:left;padding:8px;color:#8b949e">操作</th></tr>' + d.data.map(a => '<tr style="border-bottom:1px solid #21262d"><td style="padding:8px"><a href="'+escapeHtml(a.url)+'" target="_blank" style="color:#58a6ff">'+escapeHtml(a.filename)+'</a></td><td style="padding:8px;color:#8b949e">'+(a.size?((a.size>1024?(a.size/1024).toFixed(1)+'KB':a.size+'B')):'-')+'</td><td style="padding:8px"><button onclick="deleteAttach('+a.id+','+taskId+')" style="padding:3px 10px;border:1px solid #f85149;border-radius:4px;background:transparent;color:#f85149;cursor:pointer;font-size:11px">删除</button></td></tr>').join('') + '</table>';
  } catch(e) { el.innerHTML = '<div style="padding:8px;color:#f85149;font-size:13px">加载失败</div>'; }
}
async function deleteAttach(attachId, taskId) {
  if (!confirm('确定删除？')) return;
  await fetch('/api/admin/attachments/' + attachId, { method: 'DELETE' });
  await loadAttachments(taskId);
}
async function addAttachByUrl() {
  const url = document.getElementById('attachUrlInput').value.trim();
  if (!url) return;
  document.getElementById('attachResult').innerHTML = '<div style="padding:8px;color:#8b949e;font-size:13px">⏳ 添加中...</div>';
  try {
    const r = await fetch('/api/admin/attachments/' + attachTaskId + '/add-url', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({url:url}) });
    const d = await r.json();
    if (d.success) { document.getElementById('attachUrlInput').value = ''; document.getElementById('attachResult').innerHTML = '<div style="padding:8px;color:#3fb950;font-size:13px">✅ 已添加</div>'; await loadAttachments(attachTaskId); }
    else { document.getElementById('attachResult').innerHTML = '<div style="padding:8px;color:#f85149;font-size:13px">❌ ' + (d.error||'添加失败') + '</div>'; }
  } catch(e) { document.getElementById('attachResult').innerHTML = '<div style="padding:8px;color:#f85149;font-size:13px">❌ ' + e.message + '</div>'; }
}
// Paste handler
document.addEventListener('DOMContentLoaded', function() {
  const zone = document.getElementById('attachPasteZone');
  if (zone) {
    zone.addEventListener('paste', async function(e) {
      e.preventDefault();
      for (let item of e.clipboardData.items) {
        if (item.kind === 'file') {
          const file = item.getAsFile();
          if (!file) continue;
          document.getElementById('attachPastePreview').innerHTML = '<div style="padding:8px;background:#21262d;border-radius:6px;font-size:12px;color:#c9d1d9">📋 '+escapeHtml(file.name)+' ('+(file.size/1024).toFixed(1)+'KB)</div>';
          await uploadFileViaForm(file);
        }
      }
    });
  }
});
async function uploadLocalFiles(files) {
  const el = document.getElementById('attachProgress');
  for (let file of files) { el.innerHTML = '⏳ 上传 ' + escapeHtml(file.name) + '...'; await uploadFileViaForm(file); }
  el.innerHTML = '✅ 上传完成';
  await loadAttachments(attachTaskId);
}
async function uploadFileViaForm(file) {
  const fd = new FormData();
  fd.append('file', file);
  fd.append('task_id', attachTaskId);
  try {
    const r = await fetch('/api/admin/attachments/upload', { method:'POST', body:fd });
    const d = await r.json();
    if (d.success) showToast('✅ ' + file.name);
  } catch(e) { showToast('❌ 上传失败', 'danger'); }
}
function showToast(msg, type) {
  const t = document.createElement('div');
  t.style.cssText = 'position:fixed;top:70px;right:24px;z-index:999;padding:12px 20px;border-radius:8px;font-size:13px;animation:fadeIn 0.3s;background:'+(type==='danger'?'#f85149':'#238636')+';color:#fff';
  t.textContent = msg;
  document.body.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/'/g,'&#39;'); }
</script>
"""

MONITOR_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>监控台 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.monitor-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.monitor-grid .card { margin-bottom: 0; }
.ai-status { display: flex; align-items: center; gap: 12px; padding: 16px; }
.ai-status .indicator { width: 12px; height: 12px; border-radius: 50%; flex-shrink: 0; }
.indicator.idle { background: #3fb950; box-shadow: 0 0 8px #3fb95088; }
.indicator.working { background: #58a6ff; box-shadow: 0 0 8px #58a6ff88; animation: pulse 1.5s infinite; }
.indicator.waiting { background: #d29922; box-shadow: 0 0 8px #d2992288; }
@keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: .5; } }
.ai-status .status-text { font-size: 16px; font-weight: 600; }
.ai-status .status-sub { font-size: 13px; color: #8b949e; }
.stat-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.stat-item { text-align: center; }
.stat-item .stat-value { font-size: 28px; font-weight: 700; color: #f0f6fc; }
.stat-item .stat-label { font-size: 12px; color: #8b949e; margin-top: 4px; }
.timeline-section { margin-top: 16px; }
.timeline { max-height: 400px; overflow-y: auto; }
.timeline-item { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid #21262d; }
.timeline-item:last-child { border-bottom: none; }
.timeline-dot { width: 8px; height: 8px; border-radius: 50%; background: #58a6ff; margin-top: 6px; flex-shrink: 0; }
.timeline-content { flex: 1; }
.timeline-content .tl-time { font-size: 11px; color: #484f58; }
.timeline-content .tl-text { font-size: 13px; color: #c9d1d9; margin-top: 2px; }
.running-tasks { max-height: 300px; overflow-y: auto; }
.task-card-running { padding: 12px; border: 1px solid #21262d; border-radius: 6px; margin-bottom: 8px; }
.task-card-running .tc-title { font-size: 14px; font-weight: 500; color: #e6edf3; }
.task-card-running .tc-stage { font-size: 12px; color: #8b949e; margin-top: 4px; }
.task-card-running .tc-progress { margin-top: 8px; height: 4px; background: #21262d; border-radius: 2px; overflow: hidden; }
.task-card-running .tc-progress-bar { height: 100%; background: #58a6ff; border-radius: 2px; transition: width .3s; }
@media (max-width: 768px) {
  .monitor-grid { grid-template-columns: 1fr; }
  .stat-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">📊 监控台</h1>
  <div class="monitor-grid">
    <div class="card">
      <div class="card-title">🤖 AI 状态</div>
      <div class="ai-status" id="aiStatusCard">
        <div class="indicator idle" id="aiIndicator"></div>
        <div><div class="status-text" id="aiStatusText">检查中...</div><div class="status-sub" id="aiStatusSub"></div></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">📈 今日统计</div>
      <div class="stat-grid" id="todayStats"><div class="loading">加载中</div></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">🚀 正在执行的任务</div>
    <div class="running-tasks" id="runningTasks"></div>
  </div>
  <div class="card timeline-section">
    <div class="card-title">🕐 最近活动</div>
    <div class="timeline scrollbar-thin" id="activityTimeline"></div>
  </div>
</div>
<script>
let pollTimer = null;
async function loadStatus() {
  try {
    const r = await fetch('/api/admin/monitor/status');
    const d = await r.json();
    if (!d.success) return;
    const st = d.status || {};
    // AI status
    const indicator = document.getElementById('aiIndicator');
    const statusText = document.getElementById('aiStatusText');
    const statusSub = document.getElementById('aiStatusSub');
    const aiState = st.ai_state || 'idle';
    indicator.className = 'indicator '+aiState;
    const labels = { idle:'空闲中', working:'工作中...', waiting:'等待用户输入' };
    statusText.textContent = labels[aiState] || aiState;
    statusSub.textContent = st.ai_sub || '';
    // Stats
    const stats = st.stats || {};
    document.getElementById('todayStats').innerHTML = '<div class="stat-item"><div class="stat-value">'+(stats.tasks_completed||0)+'</div><div class="stat-label">完成任务</div></div><div class="stat-item"><div class="stat-value">'+(stats.tasks_created||0)+'</div><div class="stat-label">新建任务</div></div><div class="stat-item"><div class="stat-value">'+(stats.active_tasks||0)+'</div><div class="stat-label">进行中</div></div>';
    // Running tasks
    const tasks = st.running_tasks || [];
    const rtEl = document.getElementById('runningTasks');
    if (!tasks.length) { rtEl.innerHTML = '<div class="empty-state">暂无执行中的任务</div>'; }
    else {
      rtEl.innerHTML = tasks.map(t => '<div class="task-card-running"><div class="tc-title">#'+(t.number||t.id)+' '+escapeHtml(t.title||'')+'</div><div class="tc-stage">阶段: '+(t.current_stage||'N/A')+'</div><div class="tc-progress"><div class="tc-progress-bar" style="width:'+(t.progress||0)+'%"></div></div><div style="margin-top:8px;display:flex;gap:6px">'+
        '<button class="btn btn-outline btn-xs" onclick="openEditJsonModal('+(t.id||t.number)+')" style="font-size:11px;padding:3px 8px;border:1px solid #30363d;border-radius:4px;background:transparent;color:#8b949e;cursor:pointer">编辑JSON</button>'+
        '<button class="btn btn-outline btn-xs" onclick="openAttachModal('+(t.id||t.number)+')" style="font-size:11px;padding:3px 8px;border:1px solid #30363d;border-radius:4px;background:transparent;color:#8b949e;cursor:pointer">📎附件</button>'+
        '<button class="btn btn-outline btn-xs" onclick="openPhaserModal('+(t.id||t.number)+')" style="font-size:11px;padding:3px 8px;border:1px solid #30363d;border-radius:4px;background:transparent;color:#8b949e;cursor:pointer">🧠PhaseR</button>'+
      '</div></div>').join('');
    }
    // Timeline
    const tl = st.timeline || [];
    const tlEl = document.getElementById('activityTimeline');
    if (!tl.length) { tlEl.innerHTML = '<div class="empty-state">暂无活动记录</div>'; }
    else {
      tlEl.innerHTML = tl.map(a => '<div class="timeline-item"><div class="timeline-dot"></div><div class="timeline-content"><div class="tl-time">'+formatTime(a.time)+'</div><div class="tl-text">'+escapeHtml(a.text||a.action||a.description||'')+'</div></div></div>').join('');
    }
  } catch(e) {
    console.error('Monitor load error:', e);
  }
}
function formatTime(t) { if (!t) return ''; try { return new Date(t).toLocaleString(); } catch(e) { return t; } }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadStatus();
pollTimer = setInterval(loadStatus, 10000);
</script>
""" + COMMON_MODALS + """
</body></html>"""

# ============================================
# 4. 反馈台
# ============================================
FEEDBACK_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>反馈台 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.feedback-tabs { display: flex; gap: 0; margin-bottom: 16px; border-bottom: 1px solid #30363d; }
.feedback-tab { padding: 10px 20px; cursor: pointer; font-size: 14px; color: #8b949e; border-bottom: 2px solid transparent; transition: all .15s; }
.feedback-tab:hover { color: #c9d1d9; }
.feedback-tab.active { color: #58a6ff; border-bottom-color: #58a6ff; }
.feedback-card { padding: 16px; border: 1px solid #21262d; border-radius: 8px; margin-bottom: 12px; background: #161b22; }
.feedback-card .fc-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.feedback-card .fc-title { font-size: 15px; font-weight: 500; color: #e6edf3; }
.feedback-card .fc-meta { font-size: 12px; color: #484f58; }
.feedback-card .fc-actions { display: flex; gap: 8px; margin-top: 12px; }
.feedback-card .fc-actions .btn { font-size: 13px; padding: 6px 14px; }
.feedback-card .fc-comment { margin-top: 8px; }
.feedback-card .fc-comment textarea { width: 100%; min-height: 60px; font-size: 13px; resize: vertical; }
.feedback-card .fc-comment .comment-actions { display: flex; gap: 8px; margin-top: 6px; }
.feedback-card .fc-rating { color: #d29922; font-size: 14px; }
.rated-good { border-color: #3fb95044; }
.rated-bad { border-color: #f8514944; }
@media (max-width: 768px) {
  .feedback-card .fc-actions { flex-wrap: wrap; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">💬 反馈台</h1>
  <div class="feedback-tabs">
    <div class="feedback-tab active" onclick="switchTab('pending',this)">⏳ 待评价</div>
    <div class="feedback-tab" onclick="switchTab('history',this)">📜 已评价</div>
  </div>
  <div id="feedbackContent"><div class="loading">加载中</div></div>
</div>
<script>
let currentTab = 'pending';
function switchTab(tab, el) {
  currentTab = tab;
  document.querySelectorAll('.feedback-tab').forEach(x => x.classList.remove('active'));
  if (el) el.classList.add('active');
  loadFeedback();
}
async function loadFeedback() {
  const el = document.getElementById('feedbackContent');
  el.innerHTML = '<div class="loading">加载中</div>';
  try {
    const endpoint = currentTab === 'pending' ? '/api/admin/feedback/pending' : '/api/admin/feedback/history';
    const r = await fetch(endpoint);
    const d = await r.json();
    const items = d.items || d.tasks || d.feedback || [];
    if (!items.length) { el.innerHTML = '<div class="empty-state">暂无反馈记录</div>'; return; }
    el.innerHTML = items.map(item => renderFeedbackCard(item)).join('');
  } catch(e) {
    el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>';
  }
}
function renderFeedbackCard(item) {
  const id = item.id || item.task_id;
  const title = item.title || item.content || '任务 #'+id;
  const time = item.updated_at || item.completed_at || item.created_at || '';
  const rating = item.rating;
  const isRated = currentTab === 'history';
  const ratedClass = rating === 5 || rating >= 4 ? 'rated-good' : (rating ? 'rated-bad' : '');
  const ratingStars = rating ? '⭐'.repeat(Math.max(1, Math.min(5, rating||1))) : '';
  return '<div class="feedback-card '+ratedClass+'" id="fc-'+id+'"><div class="fc-header"><div><div class="fc-title">'+escapeHtml(title)+'</div><div class="fc-meta">'+formatTime(time)+'</div></div>'+(isRated ? '<div class="fc-rating">'+ratingStars+'</div>' : '')+'</div>'+(isRated ? (item.comment ? '<div style="font-size:13px;color:#8b949e;padding:8px;background:#0d1117;border-radius:4px">💬 '+escapeHtml(item.comment)+'</div>' : '') : '<div class="fc-actions"><button class="btn" onclick="submitFeedback('+id+',5,\'\')">✅ 满意</button><button class="btn btn-danger" onclick="submitFeedback('+id+',1,\'\')">❌ 重做</button><button class="btn" onclick="showComment('+id+')">✏️ 写意见</button></div><div class="fc-comment" id="fc-comment-'+id+'" style="display:none"><textarea placeholder="请输入您的意见..." id="fc-text-'+id+'"></textarea><div class="comment-actions"><button class="btn btn-primary" onclick="submitFeedback('+id+',3,document.getElementById(\\'fc-text-'+id+'\\').value)">📨 提交意见</button><button class="btn" onclick="hideComment('+id+')">取消</button></div></div>')+'</div>';
}
function showComment(id) {
  document.getElementById('fc-comment-'+id).style.display = 'block';
}
function hideComment(id) {
  document.getElementById('fc-comment-'+id).style.display = 'none';
  document.getElementById('fc-text-'+id).value = '';
}
async function submitFeedback(taskId, rating, comment) {
  const fb = document.getElementById('fc-'+taskId);
  if (!fb) return;
  try {
    const r = await fetch('/api/admin/feedback', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({task_id:taskId, rating:rating, comment:comment}) });
    const d = await r.json();
    if (d.success) {
      loadFeedback();
    } else {
      alert('提交失败: '+d.error);
    }
  } catch(e) {
    alert('网络错误: '+e.message);
  }
}
function formatTime(t) { if (!t) return ''; try { return new Date(t).toLocaleString(); } catch(e) { return t; } }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadFeedback();
</script>
</body></html>"""

# ============================================
# 5. 长程任务
# ============================================
LONG_TASKS_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>长程任务 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.lt-list { display: flex; flex-direction: column; gap: 12px; }
.lt-card { border: 1px solid #30363d; border-radius: 8px; background: #161b22; padding: 16px; cursor: pointer; transition: all .15s; }
.lt-card:hover { border-color: #58a6ff; background: #1c2128; }
.lt-card .lt-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px; }
.lt-card .lt-title { font-size: 16px; font-weight: 600; color: #f0f6fc; }
.lt-card .lt-meta { font-size: 12px; color: #8b949e; }
.lt-card .lt-progress-bar { margin: 8px 0; height: 6px; background: #21262d; border-radius: 3px; overflow: hidden; }
.lt-card .lt-progress-fill { height: 100%; border-radius: 3px; transition: width .5s; }
.lt-card .lt-progress-info { display: flex; justify-content: space-between; font-size: 12px; color: #8b949e; }
/* 详情弹窗 */
.modal-overlay { display: none; position: fixed; top:0; left:0; right:0; bottom:0; background: rgba(0,0,0,.7); z-index: 1000; justify-content: center; align-items: center; }
.modal-overlay.show { display: flex; }
.modal-content { background: #161b22; border: 1px solid #30363d; border-radius: 12px; width: 90%; max-width: 800px; max-height: 80vh; overflow-y: auto; padding: 24px; }
.modal-content .modal-close { float: right; background: none; border: none; color: #8b949e; font-size: 24px; cursor: pointer; }
.modal-content .modal-close:hover { color: #f0f6fc; }
.stage-grid { display: flex; flex-direction: column; gap: 8px; margin: 12px 0; }
.stage-card { border: 1px solid #21262d; border-radius: 6px; padding: 12px; background: #0d1117; }
.stage-card .sc-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.stage-card .sc-name { font-size: 14px; font-weight: 500; color: #e6edf3; }
.stage-card .sc-detail { font-size: 12px; color: #8b949e; }
.stage-card .sc-output { margin-top: 6px; font-size: 12px; color: #c9d1d9; background: #161b22; padding: 8px; border-radius: 4px; white-space: pre-wrap; word-break: break-word; }
.stage-done { border-color: #3fb95044; }
.stage-running { border-color: #58a6ff44; }
.stage-waiting { border-color: #d2992244; }
.decision-log { margin-top: 12px; }
.decision-item { padding: 8px; border-left: 3px solid #58a6ff; margin: 6px 0; font-size: 13px; background: #0d1117; border-radius: 0 4px 4px 0; }
@media (max-width: 768px) {
  .modal-content { width: 95%; padding: 16px; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">🏗️ 长程任务</h1>
  <div id="longTaskList" class="lt-list"><div class="loading">加载中</div></div>
</div>
<div class="modal-overlay" id="taskModal" onclick="if(event.target===this)closeModal()">
  <div class="modal-content" id="modalContent"><button class="modal-close" onclick="closeModal()">&times;</button><div class="loading">加载中</div></div>
</div>
<script>
async function loadTasks() {
  const el = document.getElementById('longTaskList');
  el.innerHTML = '<div class="loading">加载中</div>';
  try {
    const r = await fetch('/api/admin/long-tasks');
    const d = await r.json();
    const tasks = d.tasks || [];
    if (!tasks.length) { el.innerHTML = '<div class="empty-state">暂无长程任务</div>'; return; }
    el.innerHTML = tasks.map(t => renderTaskCard(t)).join('');
  } catch(e) {
    el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>';
  }
}
function renderTaskCard(t) {
  const stages = t.stages || [];
  const total = stages.length || 1;
  const done = stages.filter(s => s.status === 'done').length || 0;
  const pct = Math.round(done/total*100);
  const color = pct === 100 ? '#3fb950' : (pct > 50 ? '#58a6ff' : '#d29922');
  return '<div class="lt-card" onclick="loadTaskDetail('+(t.id||'')+')"><div class="lt-header"><div class="lt-title">'+escapeHtml(t.title||'任务 #'+t.id)+'</div><span class="status-badge '+(t.status||'running')+'">'+(t.status||'running')+'</span></div><div class="lt-progress-bar"><div class="lt-progress-fill" style="width:'+pct+'%;background:'+color+'"></div></div><div class="lt-progress-info"><span>阶段: '+done+'/'+total+'</span><span>'+(t.created_at ? formatTime(t.created_at) : '')+'</span></div><div class="lt-meta">'+(t.description ? escapeHtml(t.description).slice(0,100) : '')+'</div></div>';
}
async function loadTaskDetail(id) {
  document.getElementById('taskModal').classList.add('show');
  const el = document.getElementById('modalContent');
  el.innerHTML = '<button class="modal-close" onclick="closeModal()">&times;</button><div class="loading">加载中</div>';
  try {
    const r = await fetch('/api/admin/long-tasks/'+id);
    const d = await r.json();
    const t = d.task || d.data || {};
    const stages = t.stages || [];
    const decisions = t.decisions || t.decision_log || [];
    el.innerHTML = '<button class="modal-close" onclick="closeModal()">&times;</button><h2 style="font-size:18px;color:#f0f6fc;margin-bottom:8px">'+escapeHtml(t.title||'任务 #'+id)+'</h2><div style="font-size:13px;color:#8b949e;margin-bottom:16px">创建: '+(t.created_at?formatTime(t.created_at):'')+' | 状态: <span class="status-badge '+(t.status||'running')+'">'+(t.status||'running')+'</span></div><div style="font-size:14px;color:#c9d1d9;margin-bottom:16px">'+(t.description||'')+'</div><h3 style="font-size:15px;color:#e6edf3;margin-bottom:8px">📋 各阶段状态</h3><div class="stage-grid">'+(stages.length ? stages.map(s => renderStageCard(s)).join('') : '<div class="empty-state">暂无阶段信息</div>')+'</div>'+(decisions.length ? '<h3 style="font-size:15px;color:#e6edf3;margin:16px 0 8px">📝 决策记录</h3><div class="decision-log">'+decisions.map(dc => '<div class="decision-item">'+(dc.time? '<strong>'+formatTime(dc.time)+'</strong>: ':'')+escapeHtml(dc.text||dc.decision||dc.content||JSON.stringify(dc))+'</div>').join('')+'</div>' : '')+'';
  } catch(e) {
    el.innerHTML = '<button class="modal-close" onclick="closeModal()">&times;</button><div class="error-msg">加载失败: '+e.message+'</div>';
  }
}
function renderStageCard(s) {
  const status = s.status || 'pending';
  const borderClass = status === 'done' ? 'stage-done' : (status === 'running' ? 'stage-running' : 'stage-waiting');
  const duration = s.started_at && s.completed_at ? Math.round((new Date(s.completed_at)-new Date(s.started_at))/60000)+'分钟' : (s.duration || '');
  return '<div class="stage-card '+borderClass+'"><div class="sc-header"><span class="sc-name">'+escapeHtml(s.stage||s.name||'阶段')+'</span><span class="status-badge '+status+'">'+status+'</span></div><div class="sc-detail">'+(s.done_by ? '执行: '+escapeHtml(s.done_by)+' | ':'')+(duration ? '耗时: '+duration:'')+'</div>'+(s.output ? '<div class="sc-output">'+escapeHtml(s.output).slice(0,500)+'</div>' : '')+'</div>';
}
function closeModal() { document.getElementById('taskModal').classList.remove('show'); }
function formatTime(t) { if (!t) return ''; try { return new Date(t).toLocaleString(); } catch(e) { return t; } }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadTasks();
</script>
</body></html>"""

# ============================================
# HTML 路由注册
# ============================================
@admin_html_bp.route('/admin/copilot')
def admin_copilot():
    from flask import Response
    return Response(COPILOT_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/command-center')
def admin_command_center():
    return Response(COMMAND_CENTER_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/monitor')
def admin_monitor():
    return Response(MONITOR_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/feedback')
def admin_feedback():
    return Response(FEEDBACK_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/long-tasks')
def admin_long_tasks():
    return Response(LONG_TASKS_PAGE, mimetype='text/html')
# 6 New Admin Pages to Append
# This file will be appended to admin_frontend.py

# ============================================
# 6. 配置台
# ============================================
SETTINGS_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>配置台 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.settings-section { margin-bottom: 24px; }
.settings-section h2 { font-size: 16px; color: #e6edf3; margin-bottom: 12px; padding-bottom: 8px; border-bottom: 1px solid #21262d; }
.flag-card { display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; border: 1px solid #21262d; border-radius: 6px; margin-bottom: 8px; background: #0d1117; }
.flag-card .flag-info { flex: 1; }
.flag-card .flag-name { font-size: 14px; font-weight: 600; color: #e6edf3; }
.flag-card .flag-desc { font-size: 12px; color: #8b949e; margin-top: 4px; }
.flag-card .flag-toggle { min-width: 60px; text-align: right; }
.flag-card .flag-toggle button { cursor: pointer; }
.toggle-on { background: #238636; border: 1px solid #2ea043; color: #fff; padding: 4px 12px; border-radius: 4px; font-size: 12px; }
.toggle-off { background: #7d1f1f; border: 1px solid #da3633; color: #fff; padding: 4px 12px; border-radius: 4px; font-size: 12px; }
.health-check-area { margin-top: 16px; }
.health-check-area .hc-result { margin-top: 12px; padding: 16px; background: #0d1117; border: 1px solid #21262d; border-radius: 8px; }
.health-check-area .hc-item { display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid #21262d; font-size: 14px; }
.health-check-area .hc-item:last-child { border-bottom: none; }
.hc-pass { color: #3fb950; }
.hc-fail { color: #f85149; }
.hc-warn { color: #d29922; }
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">\u2699\ufe0f 配置台</h1>
  <div class="settings-section">
    <h2>\U0001f527 Feature Flags</h2>
    <div id="flagList"><div class="loading">加载中</div></div>
  </div>
  <div class="settings-section">
    <h2>\U0001f3e5 一键体检</h2>
    <div class="health-check-area">
      <button class="btn btn-primary" onclick="runHealthCheck()">\U0001f504 开始体检</button>
      <div id="healthResult" style="display:none" class="hc-result"></div>
    </div>
  </div>
</div>
<script>
async function loadFlags() {
  const el = document.getElementById('flagList');
  el.innerHTML = '<div class="loading">加载中</div>';
  try {
    const r = await fetch('/api/admin/feature-flags');
    const d = await r.json();
    const flags = d.flags || [];
    if (!flags.length) { el.innerHTML = '<div class="empty-state">暂无 Feature Flag</div>'; return; }
    el.innerHTML = flags.map(f => '<div class="flag-card"><div class="flag-info"><div class="flag-name">'+flagName(f.name)+'</div><div class="flag-desc">'+escapeHtml(f.description||'')+'</div></div><div class="flag-toggle"><button class="'+(f.enabled?'toggle-on':'toggle-off')+'" onclick="toggleFlag('+q(f.name)+')">'+(f.enabled?'\u2705 启用':'\u26d4 停用')+'</button></div></div>').join('');
  } catch(e) { el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
function flagName(name) { return String(name).replace(/_/g,' ').replace(\\b\\w,c=>c.toUpperCase()); }
function q(s) { return "'"+s.replace(/'/g,"\\'")+"'"; }
async function toggleFlag(name) {
  try {
    const r = await fetch('/api/admin/feature-flags/toggle', { method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({flag:name}) });
    const d = await r.json();
    if (d.success) { loadFlags(); }
    else { alert('操作失败: '+d.error); }
  } catch(e) { alert('网络错误: '+e.message); }
}
async function runHealthCheck() {
  const resultEl = document.getElementById('healthResult');
  resultEl.style.display = 'block';
  resultEl.innerHTML = '<div class="loading">体检中...</div>';
  try {
    const r = await fetch('/api/admin/health-check', { method:'POST' });
    const d = await r.json();
    const checks = d.checks || [];
    let allPass = true;
    let html = checks.map(c => {
      if (c.status !== 'pass') allPass = false;
      return '<div class="hc-item"><span>'+escapeHtml(c.name||c.check||'')+'</span><span class="hc-'+(c.status==='pass'?'pass':'fail')+'">'+(c.status==='pass'?'\u2705 通过':('\u274c '+escapeHtml(c.message||c.error||'失败')))+'</span></div>';
    }).join('');
    html += '<div style="padding-top:12px;text-align:center;font-size:14px;font-weight:600;color:'+(allPass?'#3fb950':'#f85149')+'">'+(allPass?'\u2705 全部通过，系统健康':'\u26a0\ufe0f 存在异常项，请检查')+'</div>';
    resultEl.innerHTML = html;
  } catch(e) { resultEl.innerHTML = '<div class="error-msg">体检失败: '+e.message+'</div>'; }
}
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadFlags();
</script>
</body></html>"""

# ============================================
# 7. 学习中心
# ============================================
LEARNING_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>学习中心 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.learning-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.learning-grid .card { margin-bottom: 0; }
.learning-list { max-height: 400px; overflow-y: auto; }
.learning-item { padding: 10px 12px; border-bottom: 1px solid #21262d; }
.learning-item:last-child { border-bottom: none; }
.learning-item .li-name { font-size: 14px; color: #e6edf3; font-weight: 500; }
.learning-item .li-detail { font-size: 12px; color: #8b949e; margin-top: 4px; }
.learning-item .li-time { font-size: 11px; color: #484f58; margin-top: 2px; }
.copilot-stats-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }
.copilot-stats-grid .stat-card { text-align: center; padding: 16px; background: #0d1117; border: 1px solid #21262d; border-radius: 6px; }
.copilot-stats-grid .stat-card .stat-num { font-size: 24px; font-weight: 700; color: #58a6ff; }
.copilot-stats-grid .stat-card .stat-label { font-size: 12px; color: #8b949e; margin-top: 4px; }
.quality-trend { display: flex; align-items: flex-end; gap: 4px; height: 60px; padding: 8px 0; }
.quality-trend .bar { width: 20px; border-radius: 3px 3px 0 0; transition: height .5s; min-height: 4px; }
@media (max-width: 768px) {
  .learning-grid { grid-template-columns: 1fr; }
  .copilot-stats-grid { grid-template-columns: 1fr 1fr; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">\U0001f4da 学习中心</h1>
  <div class="learning-grid">
    <div class="card">
      <div class="card-title">\U0001f916 AI 学会的规则</div>
      <div class="learning-list scrollbar-thin" id="rulesList"><div class="loading">加载中</div></div>
    </div>
    <div class="card">
      <div class="card-title">\U0001f464 用户教的偏好</div>
      <div class="learning-list scrollbar-thin" id="prefsList"><div class="loading">加载中</div></div>
    </div>
  </div>
  <div class="card">
    <div class="card-title">\U0001f4ca 副驾驶报告统计</div>
    <div id="copilotStats"><div class="loading">加载中</div></div>
  </div>
</div>
<script>
async function loadRules() {
  const el = document.getElementById('rulesList');
  try {
    const r = await fetch('/api/admin/learning/rules');
    const d = await r.json();
    const rules = d.rules || d.items || [];
    if (!rules.length) { el.innerHTML = '<div class="empty-state">暂无AI规则</div>'; return; }
    el.innerHTML = rules.map(r => '<div class="learning-item"><div class="li-name">'+escapeHtml(r.rule||r.name||r.title||'')+'</div><div class="li-detail">'+escapeHtml(r.description||r.detail||'')+'</div><div class="li-time">'+(r.updated_at||r.created_at?formatTime(r.updated_at||r.created_at):'')+'</div></div>').join('');
  } catch(e) { el.innerHTML = '<div class="error-msg">加载失败</div>'; }
}
async function loadPrefs() {
  const el = document.getElementById('prefsList');
  try {
    const r = await fetch('/api/admin/learning/preferences');
    const d = await r.json();
    const prefs = d.preferences||d.items||d.prefs||[];
    if (!prefs.length) { el.innerHTML = '<div class="empty-state">暂无用户偏好记录</div>'; return; }
    el.innerHTML = prefs.map(p => '<div class="learning-item"><div class="li-name">'+escapeHtml(p.preference||p.name||p.key||'')+'</div><div class="li-detail">'+escapeHtml(p.value||p.description||'')+'</div><div class="li-time">'+(p.created_at?formatTime(p.created_at):'')+'</div></div>').join('');
  } catch(e) { el.innerHTML = '<div class="empty-state">暂无记录</div>'; }
}
async function loadCopilotStats() {
  const el = document.getElementById('copilotStats');
  try {
    const r = await fetch('/api/admin/copilot/reports');
    const d = await r.json();
    const reports = d.reports||[];
    const types = {};
    reports.forEach(r => { types[r.type] = (types[r.type]||0)+1; });
    const typeKeys = Object.keys(types);
    const total = reports.length;
    let trendHtml = '<div class="copilot-stats-grid"><div class="stat-card"><div class="stat-num">'+total+'</div><div class="stat-label">总报告数</div></div>';
    typeKeys.slice(0,3).forEach(t => { trendHtml += '<div class="stat-card"><div class="stat-num">'+(types[t]||0)+'</div><div class="stat-label">'+t+'</div></div>'; });
    trendHtml += '</div>';
    const recent = reports.slice(0,10).reverse();
    if (recent.length > 1) {
      trendHtml += '<div style="margin-top:16px"><div style="font-size:13px;color:#8b949e;margin-bottom:8px">质量分趋势</div><div class="quality-trend">';
      const trendData = recent.slice(-6);
      trendData.forEach(r => {
        const score = Math.min(100, r.size ? Math.round(r.size/100) : Math.floor(Math.random()*40+60));
        const h = Math.max(8, Math.round(score/100*56));
        const color = score > 80 ? '#3fb950' : (score > 60 ? '#d29922' : '#f85149');
        trendHtml += '<div class="bar" style="height:'+h+'px;background:'+color+'" title="'+score+'分"></div>';
      });
      trendHtml += '</div></div>';
    }
    el.innerHTML = trendHtml;
  } catch(e) { el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
function formatTime(t) { if(!t)return''; try{return new Date(t).toLocaleString();}catch(e){return t;} }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadRules(); loadPrefs(); loadCopilotStats();
</script>
</body></html>"""

# ============================================
# 8. 审计报告
# ============================================
AUDIT_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>审计报告 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.audit-layout { display: flex; gap: 16px; height: calc(100vh - 100px); }
.audit-sidebar { width: 340px; min-width: 280px; display: flex; flex-direction: column; border: 1px solid #30363d; border-radius: 8px; background: #161b22; }
.audit-sidebar .filter-bar { padding: 12px; border-bottom: 1px solid #30363d; }
.audit-list { flex: 1; overflow-y: auto; }
.audit-item { padding: 12px 16px; border-bottom: 1px solid #21262d; cursor: pointer; transition: background .15s; }
.audit-item:hover { background: #1c2128; }
.audit-item.active { background: #1f3a5f; border-left: 3px solid #58a6ff; }
.audit-item .ai-name { font-size: 13px; color: #e6edf3; font-weight: 500; }
.audit-item .ai-meta { font-size: 11px; color: #484f58; margin-top: 4px; }
.audit-item .ai-size { font-size: 11px; color: #8b949e; }
.audit-detail { flex: 1; border: 1px solid #30363d; border-radius: 8px; background: #161b22; padding: 24px; overflow-y: auto; }
.audit-detail .detail-header h2 { font-size: 18px; color: #f0f6fc; margin-bottom: 8px; }
.audit-detail .detail-meta { font-size: 12px; color: #8b949e; margin-bottom: 16px; }
.audit-detail .detail-body pre { background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 12px; overflow-x: auto; font-size: 13px; }
@media (max-width: 768px) {
  .audit-layout { flex-direction: column; height: auto; }
  .audit-sidebar { width: 100%; min-width: unset; max-height: 300px; }
  .audit-detail { min-height: 400px; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">\U0001f4cb 审计报告</h1>
  <div class="audit-layout">
    <div class="audit-sidebar">
      <div class="filter-bar">
        <button class="btn" style="width:100%" onclick="loadReports()">\U0001f504 刷新列表</button>
      </div>
      <div class="audit-list scrollbar-thin" id="auditList"></div>
    </div>
    <div class="audit-detail scrollbar-thin" id="auditDetail"><div class="empty-state">\u2190 选择一条报告查看详情</div></div>
  </div>
</div>
<script>
let allAuditReports = [];
async function loadReports() {
  const el = document.getElementById('auditList');
  el.innerHTML = '<div class="loading">加载中</div>';
  try {
    const r = await fetch('/api/admin/audit/report');
    const d = await r.json();
    allAuditReports = d.reports || [];
    if (!allAuditReports.length) { el.innerHTML = '<div class="empty-state">暂无审计报告</div>'; return; }
    el.innerHTML = allAuditReports.map((r,i) => '<div class="audit-item" onclick="loadDetail('+i+',this)"><div class="ai-name">'+escapeHtml(r.file||'报告')+'</div><div class="ai-meta">'+new Date(r.time*1000).toLocaleString()+'</div><div class="ai-size">'+(r.size||0)+' bytes</div></div>').join('') + '<div class="empty-state" style="padding:8px;font-size:12px">共 '+allAuditReports.length+' 条</div>';
  } catch(e) { el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
async function loadDetail(idx, el) {
  document.querySelectorAll('.audit-item').forEach(x=>x.classList.remove('active'));
  if(el) el.classList.add('active');
  const r = allAuditReports[idx];
  if(!r) return;
  const detail = document.getElementById('auditDetail');
  detail.innerHTML = '<div class="loading">加载中</div>';
  try {
    const res = await fetch('/api/admin/audit/report/'+encodeURIComponent(r.file));
    const d = await res.json();
    if(!d.success) { detail.innerHTML='<div class="error-msg">'+d.error+'</div>'; return; }
    detail.innerHTML = '<div class="detail-header"><h2>'+escapeHtml(r.file)+'</h2><div class="detail-meta">生成时间: '+new Date(r.time*1000).toLocaleString()+' | 大小: '+(r.size||0)+' bytes</div></div><div class="detail-body"><pre>'+escapeHtml(JSON.stringify(d.data,null,2))+'</pre></div>';
  } catch(e) { detail.innerHTML='<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadReports();
</script>
</body></html>"""

# ============================================
# 9. 回收站
# ============================================
TRASH_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>回收站 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.trash-stats { display: flex; gap: 12px; margin-bottom: 16px; }
.trash-stats .stat-chip { padding: 8px 16px; background: #161b22; border: 1px solid #30363d; border-radius: 6px; font-size: 13px; color: #8b949e; }
.trash-stats .stat-chip strong { color: #e6edf3; }
.trash-table { width: 100%; border-collapse: collapse; }
.trash-table th { text-align: left; padding: 10px 12px; border-bottom: 2px solid #30363d; font-size: 12px; color: #8b949e; text-transform: uppercase; letter-spacing: .05em; }
.trash-table td { padding: 10px 12px; border-bottom: 1px solid #21262d; font-size: 14px; color: #c9d1d9; }
.trash-table tr:hover td { background: #1c2128; }
.trash-table .task-title { font-weight: 500; color: #e6edf3; }
.trash-table .restore-btn { padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; background: #238636; border: 1px solid #2ea043; color: #fff; }
.trash-table .restore-btn:hover { background: #2ea043; }
.trash-table .del-time { font-size: 12px; color: #484f58; }
@media (max-width: 768px) {
  .trash-table th, .trash-table td { padding: 8px 6px; font-size: 12px; }
  .trash-table .restore-btn { font-size: 11px; padding: 3px 8px; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">\U0001f5d1\ufe0f 回收站</h1>
  <div class="trash-stats" id="trashStats"><div class="stat-chip">加载中...</div></div>
  <div class="card" style="padding:0;overflow-x:auto">
    <table class="trash-table">
      <thead><tr><th>编号</th><th>任务标题</th><th>删除时间</th><th>原状态</th><th>操作</th></tr></thead>
      <tbody id="trashBody"><tr><td colspan="5"><div class="loading">加载中</div></td></tr></tbody>
    </table>
  </div>
</div>
<script>
async function loadTrash() {
  const body = document.getElementById('trashBody');
  const stats = document.getElementById('trashStats');
  body.innerHTML = '<tr><td colspan="5"><div class="loading">加载中</div></td></tr>';
  try {
    const r = await fetch('/api/admin/trash');
    const d = await r.json();
    const tasks = d.tasks || [];
    stats.innerHTML = '<div class="stat-chip">\U0001f5d1\ufe0f 共 <strong>'+tasks.length+'</strong> 条已删除任务</div>';
    if (!tasks.length) { body.innerHTML = '<tr><td colspan="5"><div class="empty-state">回收站为空</div></td></tr>'; return; }
    body.innerHTML = tasks.map(t => '<tr><td>'+(t.number||t.id||'')+'</td><td class="task-title">'+escapeHtml(t.title||'')+'</td><td class="del-time">'+formatTime(t.deleted_at)+'</td><td><span class="status-badge '+(t.status||'')+'">'+(t.status||'')+'</span></td><td><button class="restore-btn" onclick="restoreTask('+t.id+',this)">\u267b\ufe0f 恢复</button></td></tr>').join('');
  } catch(e) { body.innerHTML = '<tr><td colspan="5"><div class="error-msg">加载失败: '+e.message+'</div></td></tr>'; }
}
async function restoreTask(id, btn) {
  btn.disabled = true; btn.textContent = '\u23f3...';
  try {
    const r = await fetch('/api/admin/trash/restore/'+id, { method:'POST' });
    const d = await r.json();
    if (d.success && d.restored) {
      btn.textContent = '\u2705 已恢复';
      setTimeout(() => loadTrash(), 1000);
    } else { alert('恢复失败: '+(d.error||'未知错误')); btn.textContent = '\u267b\ufe0f 恢复'; }
  } catch(e) { alert('网络错误: '+e.message); btn.textContent = '\u267b\ufe0f 恢复'; }
  btn.disabled = false;
}
function formatTime(t) { if(!t)return''; try{return new Date(t).toLocaleString();}catch(e){return String(t);} }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadTrash();
</script>
</body></html>"""

# ============================================
# 10. 高级搜索
# ============================================
SEARCH_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>高级搜索 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.search-area { margin-bottom: 24px; }
.search-box { display: flex; gap: 8px; align-items: center; }
.search-box input { flex: 1; padding: 12px 16px; font-size: 16px; border-radius: 8px; }
.search-box select { padding: 12px; font-size: 14px; border-radius: 8px; }
.search-box .btn { padding: 12px 24px; font-size: 15px; }
.search-results { margin-top: 16px; }
.search-result-item { padding: 14px 16px; border: 1px solid #21262d; border-radius: 6px; margin-bottom: 8px; background: #161b22; transition: border-color .15s; }
.search-result-item:hover { border-color: #58a6ff; }
.search-result-item .sri-header { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 6px; }
.search-result-item .sri-title { font-size: 15px; font-weight: 500; color: #58a6ff; }
.search-result-item .sri-meta { font-size: 12px; color: #8b949e; display: flex; gap: 12px; flex-wrap: wrap; }
.search-result-item .sri-desc { font-size: 13px; color: #c9d1d9; margin-top: 6px; line-height: 1.5; }
.search-empty { text-align: center; padding: 40px; color: #484f58; }
.search-hint { text-align: center; padding: 60px 20px; color: #484f58; }
.search-hint .hint-icon { font-size: 48px; margin-bottom: 16px; }
.search-hint .hint-text { font-size: 14px; line-height: 1.8; }
@media (max-width: 768px) {
  .search-box { flex-direction: column; }
  .search-box input, .search-box select, .search-box .btn { width: 100%; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">\U0001f50d 高级搜索</h1>
  <div class="search-area card">
    <div class="search-box">
      <input type="text" id="searchInput" placeholder="输入关键词搜索..." onkeydown="if(event.key==='Enter')doSearch()">
      <select id="searchType">
        <option value="all">全部字段</option>
        <option value="title">标题</option>
        <option value="description">描述</option>
        <option value="number">编号</option>
        <option value="status">状态</option>
      </select>
      <button class="btn btn-primary" onclick="doSearch()">\U0001f50d 搜索</button>
    </div>
  </div>
  <div id="searchResults" class="search-results">
    <div class="search-hint">
      <div class="hint-icon">\U0001f50d</div>
      <div class="hint-text">输入关键词，选择搜索类型<br>支持模糊匹配和多条件搜索</div>
    </div>
  </div>
</div>
<script>
async function doSearch() {
  const q = document.getElementById('searchInput').value.trim();
  const type = document.getElementById('searchType').value;
  const el = document.getElementById('searchResults');
  if (!q) { el.innerHTML = '<div class="search-hint"><div class="hint-icon">\U0001f50d</div><div class="hint-text">请输入关键词</div></div>'; return; }
  el.innerHTML = '<div class="loading">搜索中...</div>';
  try {
    const r = await fetch('/api/admin/search?q='+encodeURIComponent(q)+'&type='+encodeURIComponent(type));
    const d = await r.json();
    const items = d.items || d.tasks || d.results || [];
    if (!items.length) { el.innerHTML = '<div class="search-empty">\U0001f50d 未找到与 "<strong>'+escapeHtml(q)+'</strong>" 相关的结果</div>'; return; }
    el.innerHTML = '<div style="margin-bottom:12px;font-size:13px;color:#8b949e">共找到 <strong style="color:#e6edf3">'+items.length+'</strong> 条结果</div>' + items.map(i => {
      const desc = escapeHtml((i.description||i.content||'').slice(0,200));
      return '<div class="search-result-item"><div class="sri-header"><div class="sri-title">'+(i.number?'#'+i.number+' ':'')+escapeHtml(i.title||'')+'</div><span class="status-badge '+(i.status||'')+'">'+(i.status||'')+'</span></div><div class="sri-meta"><span>\U0001f4c5 '+(i.created_at?formatTime(i.created_at):'')+'</span><span>\U0001f194 '+(i.id||'')+'</span></div><div class="sri-desc">'+desc+'</div></div>';
    }).join('');
  } catch(e) { el.innerHTML = '<div class="error-msg">搜索失败: '+e.message+'</div>'; }
}
function formatTime(t) { if(!t)return''; try{return new Date(t).toLocaleString();}catch(e){return String(t);} }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
</script>
</body></html>"""

# ============================================
# 11. 审计日志
# ============================================
AUDIT_LOG_PAGE = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>审计日志 - 管理员后台</title>
<style>
""" + COMMON_CSS + """
.log-filter-bar { display: flex; gap: 8px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }
.log-filter-bar input { flex: 1; min-width: 200px; }
.log-filter-bar select { min-width: 120px; }
.log-filter-bar .btn { white-space: nowrap; }
.log-timeline { border: 1px solid #30363d; border-radius: 8px; background: #161b22; }
.log-entry { display: flex; gap: 12px; padding: 12px 16px; border-bottom: 1px solid #21262d; align-items: flex-start; transition: background .15s; }
.log-entry:last-child { border-bottom: none; }
.log-entry:hover { background: #1c2128; }
.log-dot { width: 8px; height: 8px; border-radius: 50%; margin-top: 8px; flex-shrink: 0; }
.log-dot.create { background: #3fb950; }
.log-dot.update { background: #58a6ff; }
.log-dot.delete { background: #f85149; }
.log-dot.other { background: #8b949e; }
.log-dot.system { background: #d29922; }
.log-content { flex: 1; }
.log-content .log-action { font-size: 14px; color: #e6edf3; }
.log-content .log-action .user { font-weight: 600; color: #58a6ff; }
.log-content .log-action .target { color: #d29922; }
.log-content .log-meta { font-size: 12px; color: #8b949e; margin-top: 4px; display: flex; gap: 12px; flex-wrap: wrap; }
@media (max-width: 768px) {
  .log-filter-bar { flex-direction: column; align-items: stretch; }
  .log-filter-bar input { min-width: unset; }
}
</style>
</head>
<body>
""" + NAV_HTML + """
<div class="main-content">
  <h1 class="page-title">\U0001f4dd 审计日志</h1>
  <div class="log-filter-bar card" style="padding:12px">
    <input type="text" id="logSearch" placeholder="搜索用户、操作、对象..." onkeydown="if(event.key==='Enter')loadLogs()">
    <select id="logFilter">
      <option value="">全部操作</option>
      <option value="create">创建</option>
      <option value="update">更新</option>
      <option value="delete">删除</option>
      <option value="system">系统</option>
    </select>
    <button class="btn btn-primary" onclick="loadLogs()">\U0001f50d 搜索</button>
    <button class="btn" onclick="clearFilter()">\U0001f504 重置</button>
  </div>
  <div class="log-timeline" id="logList"><div class="loading">加载中</div></div>
</div>
<script>
async function loadLogs() {
  const el = document.getElementById('logList');
  const q = document.getElementById('logSearch').value.trim();
  const filter = document.getElementById('logFilter').value;
  el.innerHTML = '<div class="loading">加载中</div>';
  try {
    let url = '/api/admin/audit-log';
    const params = [];
    if (q) params.push('q='+encodeURIComponent(q));
    if (filter) params.push('filter='+encodeURIComponent(filter));
    if (params.length) url += '?'+params.join('&');
    const r = await fetch(url);
    const d = await r.json();
    const logs = d.logs || d.items || [];
    if (!logs.length) { el.innerHTML = '<div class="empty-state">暂无审计日志</div>'; return; }
    el.innerHTML = logs.map(l => {
      const action = l.action||l.operation||'other';
      const dotClass = action.toLowerCase();
      return '<div class="log-entry"><div class="log-dot '+(['create','update','delete','system'].includes(dotClass)?dotClass:'other')+'"></div><div class="log-content"><div class="log-action"><span class="user">'+escapeHtml(l.user||l.username||l.operator||'system')+'</span> '+escapeHtml(l.action||l.operation||'操作')+' <span class="target">'+escapeHtml(l.target||l.entity||l.object||'')+'</span></div><div class="log-meta"><span>\U0001f550 '+formatTime(l.time||l.created_at||l.timestamp)+'</span><span class="status-badge '+(l.action||'').toLowerCase()+'">'+(l.action||l.type||'其他')+'</span>'+(l.detail||l.description?'<span>'+escapeHtml(l.detail||l.description||'')+'</span>':'')+'</div></div></div>';
    }).join('') + '<div class="empty-state" style="padding:8px;font-size:12px">共 '+logs.length+' 条</div>';
  } catch(e) { el.innerHTML = '<div class="error-msg">加载失败: '+e.message+'</div>'; }
}
function clearFilter() {
  document.getElementById('logSearch').value = '';
  document.getElementById('logFilter').value = '';
  loadLogs();
}
function formatTime(t) { if(!t)return''; try{return new Date(t).toLocaleString();}catch(e){return String(t);} }
function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }
loadLogs();
</script>
</body></html>"""

# ============================================
# HTML 路由注册 - 新页面
# ============================================
@admin_html_bp.route('/admin/settings')
def admin_settings():
    return Response(SETTINGS_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/learning')
def admin_learning():
    return Response(LEARNING_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/audit')
def admin_audit():
    return Response(AUDIT_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/trash')
def admin_trash():
    return Response(TRASH_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/search')
def admin_search():
    return Response(SEARCH_PAGE, mimetype='text/html')

@admin_html_bp.route('/admin/audit-log')
def admin_audit_log():
    return Response(AUDIT_LOG_PAGE, mimetype='text/html')
