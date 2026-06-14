"""Routes: cron"""
from flask import Blueprint, jsonify, request
import json
import os
from routes.helpers import get_db, row_to_dict
from datetime import datetime

bp = Blueprint('routes_cron', __name__)

@bp.route('/api/cron/tasks', methods=['GET'])
def get_cron_tasks():
    """获取所有Cron任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, description, schedule, command, status, 
                   last_run, next_run, fail_count, created_at
            FROM cron_tasks 
            ORDER BY created_at DESC
        ''')
        tasks = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/cron/add', methods=['POST'])
def add_cron_task():
    """添加Cron任务"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO cron_tasks (name, description, schedule, command, status, created_at)
            VALUES (%s, %s, %s, %s, 'active', NOW())
        ''', (data.get('name'), data.get('description'), data.get('schedule'), data.get('command')))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/cron/tasks/<int:task_id>', methods=['PUT'])
def update_cron_task(task_id):
    """更新Cron任务"""
    try:
        data = request.get_json()
    
        conn = get_db()
        c = conn.cursor()
    
        # 检查任务是否存在
        c.execute('SELECT id FROM cron_tasks WHERE id = %s', (task_id,))
        if not c.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': '任务不存在'})
    
        # 构建更新字段
        allowed_fields = ['name', 'description', 'schedule', 'command', 'status']
        updates = {k: v for k, v in data.items() if k in allowed_fields}
    
        if not updates:
            conn.close()
            return jsonify({'success': False, 'error': '没有要更新的字段'})
    
        # 构建SQL
        set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
        values = list(updates.values()) + [task_id]
    
        c.execute(f'UPDATE cron_tasks SET {set_clause} WHERE id = %s', values)
        conn.commit()
        conn.close()
    
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})


