#!/usr/bin/env python3
"""
人员标签页路由 - 支持动态标签和富文本内容
完整功能版本
"""

from flask import Blueprint, request, jsonify, current_app
from database_config import get_db_connection
import json
import os
from werkzeug.utils import secure_filename

person_tabs_bp = Blueprint('person_tabs', __name__, url_prefix='/api')

# 允许的文件类型
ALLOWED_EXTENSIONS = {'pdf', 'doc', 'docx', 'jpg', 'jpeg', 'png', 'gif', 'mp4', 'mp3'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@person_tabs_bp.route('/persons/<int:person_id>/tabs', methods=['GET'])
def get_person_tabs(person_id):
    """获取人员的所有标签页"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, type, sort_order, created_at, updated_at
                FROM person_tabs
                WHERE person_id = %s
                ORDER BY sort_order, created_at
            ''', (person_id,))
            tabs = cursor.fetchall()
            
            result = []
            for tab in tabs:
                # 获取每个标签页的项目
                cursor.execute('''
                    SELECT id, title, content, attachments, item_date, sort_order, created_at
                    FROM person_tab_items
                    WHERE tab_id = %s
                    ORDER BY sort_order, created_at DESC
                ''', (tab['id'],))
                items = cursor.fetchall()
                
                # 解析 JSON 附件
                for item in items:
                    if item['attachments']:
                        try:
                            item['attachments'] = json.loads(item['attachments'])
                        except:
                            item['attachments'] = []
                    else:
                        item['attachments'] = []
                
                result.append({
                    'id': tab['id'],
                    'name': tab['name'],
                    'type': tab['type'],
                    'sort_order': tab['sort_order'],
                    'items': items,
                    'created_at': tab['created_at'].isoformat() if tab['created_at'] else None,
                    'updated_at': tab['updated_at'].isoformat() if tab['updated_at'] else None
                })
            
            return jsonify({'success': True, 'tabs': result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/tabs', methods=['POST'])
def create_person_tab(person_id):
    """创建新标签页"""
    data = request.get_json()
    name = data.get('name', '').strip()
    tab_type = data.get('type', 'custom')
    
    if not name:
        return jsonify({'success': False, 'error': '标签名称不能为空'}), 400
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 获取当前最大排序
            cursor.execute('SELECT MAX(sort_order) as max_order FROM person_tabs WHERE person_id = %s', (person_id,))
            result = cursor.fetchone()
            sort_order = (result['max_order'] or 0) + 1
            
            cursor.execute('''
                INSERT INTO person_tabs (person_id, name, type, sort_order)
                VALUES (%s, %s, %s, %s)
            ''', (person_id, name, tab_type, sort_order))
            conn.commit()
            tab_id = cursor.lastrowid
            
            return jsonify({'success': True, 'tab_id': tab_id, 'message': '标签页创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/tabs/<int:tab_id>', methods=['PUT'])
def update_person_tab(person_id, tab_id):
    """更新标签页"""
    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order')
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if name:
                cursor.execute('UPDATE person_tabs SET name = %s WHERE id = %s AND person_id = %s',
                             (name, tab_id, person_id))
            if sort_order is not None:
                cursor.execute('UPDATE person_tabs SET sort_order = %s WHERE id = %s AND person_id = %s',
                             (sort_order, tab_id, person_id))
            conn.commit()
            return jsonify({'success': True, 'message': '标签页更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/tabs/<int:tab_id>', methods=['DELETE'])
def delete_person_tab(person_id, tab_id):
    """删除标签页"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM person_tabs WHERE id = %s AND person_id = %s', (tab_id, person_id))
            conn.commit()
            return jsonify({'success': True, 'message': '标签页删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/tabs/<int:tab_id>/items', methods=['POST'])
def create_tab_item(person_id, tab_id):
    """创建标签页项目"""
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '')
    attachments = data.get('attachments', [])
    item_date = data.get('item_date')
    
    if not title:
        return jsonify({'success': False, 'error': '标题不能为空'}), 400
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            # 获取当前最大排序
            cursor.execute('SELECT MAX(sort_order) as max_order FROM person_tab_items WHERE tab_id = %s', (tab_id,))
            result = cursor.fetchone()
            sort_order = (result['max_order'] or 0) + 1
            
            cursor.execute('''
                INSERT INTO person_tab_items (tab_id, title, content, attachments, item_date, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (tab_id, title, content, json.dumps(attachments), item_date, sort_order))
            conn.commit()
            item_id = cursor.lastrowid
            
            return jsonify({'success': True, 'item_id': item_id, 'message': '项目创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/tabs/<int:tab_id>/items/<int:item_id>', methods=['PUT'])
def update_tab_item(person_id, tab_id, item_id):
    """更新标签页项目"""
    data = request.get_json()
    title = data.get('title', '').strip()
    content = data.get('content', '')
    attachments = data.get('attachments', [])
    item_date = data.get('item_date')
    sort_order = data.get('sort_order')
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            updates = []
            params = []
            
            if title:
                updates.append('title = %s')
                params.append(title)
            if content is not None:
                updates.append('content = %s')
                params.append(content)
            if attachments is not None:
                updates.append('attachments = %s')
                params.append(json.dumps(attachments))
            if item_date:
                updates.append('item_date = %s')
                params.append(item_date)
            if sort_order is not None:
                updates.append('sort_order = %s')
                params.append(sort_order)
            
            if updates:
                params.extend([item_id, tab_id])
                sql = f"UPDATE person_tab_items SET {', '.join(updates)} WHERE id = %s AND tab_id = %s"
                cursor.execute(sql, params)
                conn.commit()
            
            return jsonify({'success': True, 'message': '项目更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/tabs/<int:tab_id>/items/<int:item_id>', methods=['DELETE'])
def delete_tab_item(person_id, tab_id, item_id):
    """删除标签页项目"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM person_tab_items WHERE id = %s AND tab_id = %s', (item_id, tab_id))
            conn.commit()
            return jsonify({'success': True, 'message': '项目删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/upload', methods=['POST'])
def upload_file():
    """上传附件"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': '没有文件'}), 400
    
    file = request.files['file']
    entity_type = request.form.get('entity_type', 'person')
    entity_id = request.form.get('entity_id', 0)
    
    if file.filename == '':
        return jsonify({'success': False, 'error': '文件名为空'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': '不支持的文件类型'}), 400
    
    try:
        # 确保上传目录存在
        upload_dir = '/opt/kanban-react/backend/uploads'
        os.makedirs(upload_dir, exist_ok=True)
        
        filename = secure_filename(file.filename)
        # 添加时间戳避免重名
        import time
        name, ext = os.path.splitext(filename)
        filename = f"{name}_{int(time.time())}{ext}"
        file_path = os.path.join(upload_dir, filename)
        file.save(file_path)
        
        # 获取文件大小
        file_size = os.path.getsize(file_path)
        file_type = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # 保存到数据库
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO attachments (entity_type, entity_id, filename, url, size, file_type)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (entity_type, entity_id, filename, f'/uploads/{filename}', file_size, file_type))
            conn.commit()
            attachment_id = cursor.lastrowid
        
        return jsonify({
            'success': True,
            'attachment_id': attachment_id,
            'filename': filename,
            'url': f'/uploads/{filename}',
            'size': file_size,
            'type': file_type
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@person_tabs_bp.route('/persons/<int:person_id>/favorite', methods=['PUT'])
def toggle_person_favorite(person_id):
    """切换人员收藏状态"""
    data = request.get_json()
    is_favorite = data.get('is_favorite', False)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE persons SET is_favorite = %s WHERE id = %s', (is_favorite, person_id))
            conn.commit()
            return jsonify({'success': True, 'message': '收藏状态更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
