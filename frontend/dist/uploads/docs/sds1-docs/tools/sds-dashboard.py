#!/usr/bin/env python3
"""SDS Dashboard Generator"""
import json, os, sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))
from config_loader import get_config

LOG_DIR = '/Users/mettlyz/.openclaw/logs/sds'
DASH = get_config('paths.output') + '/task-1570/sds-dashboard.html'
os.makedirs(os.path.dirname(DASH), exist_ok=True)

def read_json(path, default=None):
    try:
        with open(path) as f: return json.load(f)
    except: return default or {}

def gen():
    report = read_json(f'{LOG_DIR}/72h-health-report.json')
    snapshots = read_json(f'{LOG_DIR}/72h-snapshots.json', [])
    alerts = read_json(f'{LOG_DIR}/72h-alerts.json', [])
    if not report: return "No data yet"
    
    uptime = report.get('uptime_hours', 0)
    target = report.get('target_hours', 72)
    progress = report.get('progress_pct', 0)
    healthy = report.get('all_healthy', False)
    restarts = report.get('restart_count', 0)
    total_alerts = report.get('total_alerts', 0)
    checks = report.get('checks', {})
    
    status = "✅ HEALTHY" if healthy else "⚠️ DEGRADED"
    sc = "#00cc44" if healthy else "#ff9900"
    
    comp_html = ""
    for n, c in checks.items():
        ok = c.get('ok', False)
        comp_html += f"<div class='comp {'ok' if ok else 'fail'}'>{'✅' if ok else '❌'} {n}: {c.get('message','')}</div>"
    
    trend_html = ""
    if snapshots:
        trend_html = "<h3>📈 趋势快照</h3><table><tr><th>时间</th><th>运行h</th><th>状态</th></tr>"
        for s in snapshots[-20:]:
            trend_html += f"<tr><td>{s.get('time','')[:19]}</td><td>{s.get('uptime',0)}</td><td>{'✅' if s.get('healthy') else '❌'}</td></tr>"
        trend_html += "</table>"
    
    alert_html = ""
    if alerts:
        alert_html = f"<h3>🚨 告警({len(alerts)})</h3><table><tr><th>时间</th><th>级别</th><th>类别</th><th>详情</th></tr>"
        for a in alerts[-10:]:
            sev = a.get('severity', 'info')
            col = {'warning': '#ff9900', 'critical': '#ff3333', 'info': '#3399ff'}.get(sev, '#999')
            alert_html += f"<tr><td>{a.get('time','')[:19]}</td><td style='color:{col}'>{sev}</td><td>{a.get('category','')}</td><td>{a.get('message','')}</td></tr>"
        alert_html += "</table>"
    
    html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>SDS Dashboard</title><meta http-equiv="refresh" content="300"><style>body{{font-family:-apple-system,sans-serif;max-width:1200px;margin:0 auto;padding:20px;background:#1a1a2e;color:#eee}}h1{{color:#fff;border-bottom:2px solid #333;padding-bottom:10px}}.header{{display:flex;justify-content:space-between;align-items:center}}.status{{font-size:2em;font-weight:bold;color:{sc}}}.progress-bar{{background:#333;height:30px;border-radius:5px;overflow:hidden;margin:10px 0}}.progress-fill{{background:linear-gradient(90deg,#00cc44,#00aa88);height:100%;width:{progress}%;display:flex;align-items:center;justify-content:center;color:#fff;font-weight:bold}}.stats{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin:20px 0}}.stat-card{{background:#16213e;border-radius:10px;padding:20px;text-align:center}}.stat-card .value{{font-size:2.5em;font-weight:bold;color:#00cc44}}.stat-card .label{{color:#999;margin-top:5px}}.comp{{padding:10px 15px;margin:5px 0;background:#16213e;border-radius:5px}}.comp.ok{{border-left:4px solid #00cc44}}.comp.fail{{border-left:4px solid #ff3333}}table{{width:100%;border-collapse:collapse;margin:10px 0}}th,td{{padding:8px 12px;text-align:left;border-bottom:1px solid #333}}th{{background:#16213e}}.footer{{color:#666;text-align:center;margin-top:30px}}</style></head><body><div class="header"><h1>🚀 SDS Dashboard</h1><div class="status">{status}</div></div><p>72h无人值守验证 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p><h2>📊 进度: {progress:.0f}%</h2><div class="progress-bar"><div class="progress-fill">{progress:.1f}%</div></div><div class="stats"><div class="stat-card"><div class="value">{uptime:.1f}h</div><div class="label">运行时间</div></div><div class="stat-card"><div class="value">{target}h</div><div class="label">目标时长</div></div><div class="stat-card"><div class="value">{restarts}</div><div class="label">自愈重启</div></div><div class="stat-card"><div class="value" style="color:{'#ff3333' if total_alerts > 0 else '#00cc44'}">{total_alerts}</div><div class="label">告警次数</div></div></div><h2>🔍 组件健康</h2>{comp_html}{trend_html}{alert_html}<div class="footer">SDS 72h Unattended Validation | Task #1570</div></body></html>"""
    
    with open(DASH, 'w') as f: f.write(html)
    return f"✅ Dashboard updated: {DASH}"

if __name__ == '__main__': print(gen())
