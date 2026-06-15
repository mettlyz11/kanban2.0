"""
变更日志 API — 双向同步桥梁
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
import json
import logging
import pymysql

logger = logging.getLogger(__name__)

changelog_bp = Blueprint('changelog', __name__)


def _get_conn():
    """获取数据库直连（不通过 contextmanager）"""
    from database_config import MYSQL_CONFIG
    import os
    config = MYSQL_CONFIG.copy()
    config['password'] = os.environ.get('MYSQL_PASSWORD', '')
    config['cursorclass'] = pymysql.cursors.DictCursor
    return pymysql.connect(**config)


def _write_log(source, entity_type, entity_id, action, payload=None):
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO system_change_log (source, entity_type, entity_id, action, payload) VALUES (%s, %s, %s, %s, %s)",
                (source, entity_type, entity_id, action, json.dumps(payload or {}, ensure_ascii=False))
            )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"[changelog] write fail: {e}")
        return False


@changelog_bp.route('/api/changelog/consume', methods=['GET'])
def consume():
    source = request.args.get('source', 'sds')
    since = request.args.get('since', 0, type=int)
    limit = request.args.get('limit', 30, type=int)

    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, source, entity_type, entity_id, action, payload, created_at FROM system_change_log WHERE source = %s AND id > %s ORDER BY id ASC LIMIT %s",
                (source, since, limit)
            )
            rows = cur.fetchall() or []
            cur.execute("SELECT MAX(id) as max_id FROM system_change_log WHERE source = 'sds'")
            latest = cur.fetchone()
        conn.close()
        return jsonify({
            'success': True,
            'changes': rows,
            'latest_id': latest['max_id'] if latest else 0
        })
    except Exception as e:
        logger.error(f"[changelog] consume fail: {e}")
        return jsonify({'success': False, 'error': str(e), 'changes': [], 'latest_id': 0})


@changelog_bp.route('/api/changelog/write', methods=['POST'])
def write():
    data = request.get_json() or {}
    ok = _write_log(
        data.get('source', 'kanban'),
        data.get('entity_type', ''),
        data.get('entity_id', 0),
        data.get('action', 'updated'),
        data.get('payload', {})
    )
    return jsonify({'success': ok})
