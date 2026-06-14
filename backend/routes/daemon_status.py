"""Routes: evolution_daemon status API"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db
import json
from datetime import datetime

bp = Blueprint('routes_daemon_status', __name__)

@bp.route('/api/evolution-daemon/status', methods=['GET', 'POST'])
def daemon_status():
    if request.method == 'POST':
        data = request.get_json() or {}
        payload = json.dumps(data, ensure_ascii=False)
        conn = get_db()
        cur = conn.cursor()
        cur.execute("SELECT id FROM system_configs WHERE config_type='evolution_daemon_status'")
        row = cur.fetchone()
        if row:
            cur.execute("UPDATE system_configs SET config_data=%s, updated_at=NOW() WHERE id=%s",
                       (payload, row['id']))
        else:
            cur.execute("INSERT INTO system_configs (config_type, config_data, updated_at) VALUES (%s, %s, NOW())",
                       ('evolution_daemon_status', payload))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT config_data, updated_at FROM system_configs WHERE config_type='evolution_daemon_status'")
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({'success': True, 'data': json.loads(row['config_data']), 'updated_at': row['updated_at'].isoformat()})
    return jsonify({'success': True, 'data': None})

@bp.route('/api/evolution-daemon/push', methods=['POST'])
def push_status():
    """简易推送端点，供Mac mini调用"""
    data = request.get_json() or {}
    payload = json.dumps(data, ensure_ascii=False)
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT id FROM system_configs WHERE config_type='evolution_daemon_status'")
    row = cur.fetchone()
    if row:
        cur.execute("UPDATE system_configs SET config_data=%s, updated_at=NOW() WHERE id=%s",
                   (payload, row['id']))
    else:
        cur.execute("INSERT INTO system_configs (config_type, config_data, updated_at) VALUES (%s, %s, NOW())",
                   ('evolution_daemon_status', payload))
    conn.commit()
    conn.close()
    return jsonify({'success': True})
