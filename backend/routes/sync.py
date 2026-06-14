"""Routes: sync"""
from flask import Blueprint, jsonify, request
import json as _json
import os
from datetime import datetime

_sync_data_cache = None
def _get_sync_data():
    global _sync_data_cache
    if _sync_data_cache is None:
        p = "/opt/kanban-react/backend/macmini_sync_data.json"
        if os.path.exists(p):
            with open(p) as f:
                _sync_data_cache = _json.load(f)
    return _sync_data_cache or {}

bp = Blueprint('routes_sync', __name__)

@bp.route('/api/macmini/sync/cron', methods=['GET'])
def macmini_sync_cron():
    d = _get_sync_data()
    jobs = d.get("_cron", {}).get("jobs", [])
    if not jobs:
        raw = d.get("cron_jobs", [])
        jobs = [{"name": j.get("name","?"), "schedule": j.get("schedule","?"), "session_target":"main","payload_kind":"agentTurn","enabled":j.get("status")=="running","description":j.get("status","?")} for j in raw]
    return jsonify({"success": True, "jobs": jobs, "count": len(jobs)})

@bp.route('/api/macmini/sync/heartbeat', methods=['GET'])
def macmini_sync_heartbeat():
    d = _get_sync_data()
    hb = d.get("_heartbeat", {})
    now = datetime.now().isoformat()
    return jsonify({
        "success": True,
        "file_exists": hb.get("file_exists", True),
        "size": hb.get("size", 1024),
        "last_modified": hb.get("last_modified", now),
        "cron_jobs_count": hb.get("cron_jobs_count", 0),
        "connected": hb.get("connected", True),
        "last_heartbeat": hb.get("last_heartbeat", now),
        "uptime": hb.get("uptime", 0)
    })

@bp.route('/api/macmini/sync/llm', methods=['GET'])
def macmini_sync_llm():
    d = _get_sync_data()
    llm = d.get("_llm", {})
    providers = llm.get("providers", [])
    return jsonify({"success": True, "providers": providers, "count": len(providers)})

@bp.route('/api/macmini/sync/skills-tools', methods=['GET'])
def macmini_sync_skills_tools():
    d = _get_sync_data()
    st = d.get("_skills_tools", {})
    return jsonify(st)

@bp.route('/api/macmini/sync/skills_tools', methods=['GET'])
def macmini_sync_skills_tools_v2():
    return macmini_sync_skills_tools()

@bp.route('/api/macmini/sync/status', methods=['GET'])
def macmini_sync_status():
    d = _get_sync_data()
    st = d.get("_status", {})
    # Fallback to dynamic status
    if not st.get("sync_status"):
        sys = d.get("system", {})
        monitor = d.get("monitor", {}).get("data", {})
        h = monitor.get("hostname", sys.get("hostname", "macmini"))
        n = "running" if sys.get("sds_processes", 0) > 0 else "stopped"
        now = datetime.now().isoformat()
        status = {"has_data": True, "timestamp": now, "received_at": now}
        st = {
            "success": True,
            "sync_status": {
                "cron_sync": status,
                "heartbeat_sync": status,
                "model_config_sync": status,
                "skills_tools_sync": status
            },
            "last_update": d.get("updated_at", now)
        }
    return jsonify(st)

@bp.route('/api/macmini/sync/push-monitor', methods=['POST'])
def macmini_push_monitor():
    """接收 Mac mini 推送的监控数据（WebSocket）"""
    global _sync_data_cache
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'error': 'No data'}), 400

        p = '/opt/kanban-react/backend/macmini_sync_data.json'
        sync_data = {}
        if os.path.exists(p):
            with open(p) as f:
                sync_data = _json.load(f)

        sync_data['monitor'] = {
            'data': data.get('data', {}),
            'timestamp': data.get('timestamp', datetime.now().isoformat())
        }
        sync_data['updated_at'] = datetime.now().isoformat()
        _sync_data_cache = None

        with open(p, 'w') as f:
            _json.dump(sync_data, f, indent=2, ensure_ascii=False)

        _sync_data_cache = None
        return jsonify({'success': True, 'message': 'Monitor data received'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
