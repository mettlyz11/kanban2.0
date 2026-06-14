"""System Config Browser"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db
import os, json

bp = Blueprint('routes_config', __name__)
logger = __import__('logging').getLogger(__name__)

SENSITIVE_KEYWORDS = ["key", "password", "secret", "token", "private"]


@bp.route('/api/system/config-browser', methods=['GET'])
def config_browser():
    """浏览 system_configs 表，密钥自动遮罩"""
    search = request.args.get('q', '').strip()
    page = int(request.args.get('page', '1'))
    limit = min(int(request.args.get('limit', '500')), 2000)
    offset = (page - 1) * limit

    try:
        conn = get_db()
        c = conn.cursor()

        if search:
            c.execute("SELECT COUNT(*) FROM system_configs WHERE config_type LIKE %s", (f'%{search}%',))
        else:
            c.execute("SELECT COUNT(*) FROM system_configs")
        total = c.fetchone()['COUNT(*)']

        if search:
            c.execute(
                "SELECT id, config_type, LENGTH(config_data) as dlen, config_data, updated_at FROM system_configs WHERE config_type LIKE %s ORDER BY id DESC LIMIT %s OFFSET %s",
                (f'%{search}%', limit, offset))
        else:
            c.execute(
                "SELECT id, config_type, LENGTH(config_data) as dlen, config_data, updated_at FROM system_configs ORDER BY id DESC LIMIT %s OFFSET %s",
                (limit, offset))
        rows = c.fetchall()
        conn.close()
    except Exception as e:
        logger.warning(f"config_browser query failed: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

    configs = []
    for r in rows:
        is_sensitive = any(k in (r["config_type"] or "").lower() for k in SENSITIVE_KEYWORDS)
        cd = r.get("config_data", "")
        if is_sensitive:
            cd = cd[:6] + "****" + cd[-2:] if len(cd) > 8 else "****"
        configs.append({
            "id": r["id"],
            "config_type": r["config_type"],
            "config_data": cd,
            "dlen": r["dlen"] or 0,
            "updated_at": str(r.get("updated_at", "")) if r.get("updated_at") else "",
            "sensitive": is_sensitive,
        })

    return jsonify({"success": True, "configs": configs, "total": total, "page": page})


@bp.route('/api/system/config-detail', methods=['GET'])
def config_detail():
    """获取某个配置的完整内容（敏感内容需确认）"""
    cid = request.args.get('id', '')
    reveal = request.args.get('reveal', '0') == '1'
    if not cid or not cid.isdigit():
        return jsonify({"success": False, "error": "需要 id 参数"}), 400

    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("SELECT id, config_type, config_data, updated_at FROM system_configs WHERE id = %s", (int(cid),))
        row = c.fetchone()
        conn.close()
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    if not row:
        return jsonify({"success": False, "error": "配置不存在"}), 404

    is_sensitive = any(k in (row["config_type"] or "").lower() for k in SENSITIVE_KEYWORDS)
    cd = row["config_data"]
    if is_sensitive and not reveal:
        cd = cd[:6] + "****" + cd[-2:] if len(cd) > 8 else "****"

    return jsonify({
        "success": True,
        "config": {
            "id": row["id"],
            "config_type": row["config_type"],
            "config_data": cd,
            "sensitive": is_sensitive,
            "revealed": reveal,
            "updated_at": str(row.get("updated_at", "")),
        }
    })
