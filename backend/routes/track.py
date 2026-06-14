"""Routes: track"""
from flask import Blueprint, jsonify, request
import json
from routes.helpers import get_db
from datetime import datetime

bp = Blueprint('routes_track', __name__)

@bp.route('/api/track/pageview', methods=['POST'])
def track_pageview():
    """记录页面访问"""
    try:
        data = request.get_json() or {}
        page_path = data.get('path', '/')
        ip = request.headers.get('X-Forwarded-For', request.remote_addr or '0.0.0.0').split(',')[0].strip()
        referrer = data.get('referrer', '')
        user_agent = request.headers.get('User-Agent', '')
        conn = get_db()
        c = conn.cursor()
        c.execute("INSERT INTO page_views (page_path, visitor_ip, referrer, user_agent, created_at) VALUES (%s, %s, %s, %s, NOW())",
                  (page_path, ip, referrer, user_agent))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

