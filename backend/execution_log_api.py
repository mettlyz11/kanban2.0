#!/usr/bin/env python3
# 添加执行详情记录API

import mysql.connector
from flask import request, jsonify

DB_CONFIG = {
    'host': 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    'user': 'kanban',
    'password': 'Irc210Irc210!',
    'database': 'kanban'
}

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

# 这个函数需要添加到主app中
def register_execution_log_routes(app):
    @app.route('/api/tasks/<int:task_id>/execution-log', methods=['POST'])
    def update_execution_log(task_id):
        try:
            data = request.json
            execution_log = data.get('execution_log', '')
            remaining_issues = data.get('remaining_issues', '')
            improvement_suggestions = data.get('improvement_suggestions', '')
            
            conn = get_db_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE tasks 
                SET execution_log = %s, 
                    remaining_issues = %s, 
                    improvement_suggestions = %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (execution_log, remaining_issues, improvement_suggestions, task_id))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            return jsonify({'success': True, 'message': '执行详情记录已更新'})
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500

    @app.route('/api/tasks/<int:task_id>/execution-log', methods=['GET'])
    def get_execution_log(task_id):
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT execution_log, remaining_issues, improvement_suggestions
                FROM tasks
                WHERE id = %s
            """, (task_id,))
            
            result = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if result:
                return jsonify({'success': True, 'data': result})
            else:
                return jsonify({'success': False, 'error': 'Task not found'}), 404
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
