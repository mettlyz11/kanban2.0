#!/usr/bin/env python3
# task_attachments_api.py - 任务附件管理API

import os
import json
import mysql.connector
from datetime import datetime
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# 数据库配置
DB_CONFIG = {
    'host': 'rm-2zew4su9p966e8x2ofo.mysql.rds.aliyuncs.com',
    'user': 'kanban',
    'password': 'Irc210Irc210!',
    'database': 'kanban'
}

UPLOAD_DIR = "/opt/kanban-react/frontend/public/uploads/docs"

def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

@app.route('/api/tasks/<int:task_id>/attachments', methods=['GET'])
def get_task_attachments(task_id):
    """获取任务附件列表"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT id, entity_type, entity_id, filename, url, size, file_type, created_at
            FROM attachments
            WHERE entity_type = 'task' AND entity_id = %s
            ORDER BY created_at DESC
        """, (task_id,))
        
        attachments = cursor.fetchall()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'attachments': attachments})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/attachments/edit', methods=['POST'])
def edit_task_attachment(task_id):
    """编辑任务附件内容"""
    try:
        data = request.json
        filename = data.get('filename')
        content = data.get('content')
        
        if not filename or content is None:
            return jsonify({'success': False, 'error': 'Missing filename or content'}), 400
        
        # 查找附件记录
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            SELECT url FROM attachments
            WHERE entity_type = 'task' AND entity_id = %s AND filename = %s
        """, (task_id, filename))
        
        attachment = cursor.fetchone()
        if not attachment:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404
        
        # 提取文件路径
        file_path = attachment['url'].replace('/uploads/', UPLOAD_DIR + '/')
        
        # 保存文件内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        # 更新文件大小
        new_size = os.path.getsize(file_path)
        cursor.execute("""
            UPDATE attachments SET size = %s
            WHERE entity_type = 'task' AND entity_id = %s AND filename = %s
        """, (new_size, task_id, filename))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return jsonify({'success': True, 'message': 'File saved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/tasks/<int:task_id>/attachments/upload', methods=['POST'])
def upload_task_attachment(task_id):
    """上传任务附件"""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No selected file'}), 400
        
        # 确保上传目录存在
        if not os.path.exists(UPLOAD_DIR):
            os.makedirs(UPLOAD_DIR, exist_ok=True)
        
        # 生成安全的文件名（添加时间戳避免冲突）
        original_filename = file.filename
        name, ext = os.path.splitext(original_filename)
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        safe_filename = f"{timestamp}_{name}{ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)
        
        # 保存文件
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        file_type = ext.lstrip('.').lower() if ext else 'unknown'
        
        # 获取文件URL
        url = f"/uploads/docs/{safe_filename}"
        
        # 写入数据库
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("""
            INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, ('task', task_id, original_filename, url, file_size, file_type, datetime.now()))
        
        conn.commit()
        attachment_id = cursor.lastrowid
        
        cursor.execute("""
            SELECT id, entity_type, entity_id, filename, url, size, file_type, created_at
            FROM attachments WHERE id = %s
        """, (attachment_id,))
        
        attachment = cursor.fetchone()
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'File uploaded successfully',
            'attachment': attachment
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)

@app.route('/api/tasks/<int:task_id>/execution-log', methods=['POST'])
def update_execution_log(task_id):
    更新任务执行详情记录
    try:
        data = request.json
        execution_log = data.get('execution_log', '')
        remaining_issues = data.get('remaining_issues', '')
        improvement_suggestions = data.get('improvement_suggestions', '')
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
