"""Routes: cron_api - cron_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_cron_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/cron/stats', methods=['GET'])
def get_cron_stats():
    """获取Cron统计"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        c.execute('SELECT COUNT(*) FROM cron_tasks')
        total = list(c.fetchone().values())[0]
    
        c.execute("SELECT COUNT(*) FROM cron_tasks WHERE status = 'active'")
        active = list(c.fetchone().values())[0]
    
        c.execute('SELECT SUM(fail_count) FROM cron_tasks')
        failed = list(c.fetchone().values())[0] or 0
    
        conn.close()
    
        return jsonify({
            'success': True, 
            'stats': {
                'total': total,
                'active': active,
                'failed': failed,
                'today': 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/cron.py
@bp.route('/api/cron/delete/<int:task_id>', methods=['POST'])
def delete_cron_task(task_id):
    """删除Cron任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM cron_tasks WHERE id = %s', (task_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

    # Routes moved to routes/cron.py
@bp.route('/api/cron/history', methods=['GET'])
def get_cron_history():
    """获取Cron执行历史"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT h.*, t.name as task_name
            FROM cron_execution_history h
            LEFT JOIN cron_tasks t ON h.task_id = t.id
            ORDER BY h.started_at DESC
            LIMIT 100
        ''')
        history = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': True, 'history': []})

