#!/usr/bin/env python3
"""
公司标签页路由 - 支持动态标签和富文本内容
"""

from flask import Blueprint, request, jsonify
from database_config import get_db_connection
import json

company_tabs_bp = Blueprint('company_tabs', __name__, url_prefix='/api')

@company_tabs_bp.route('/companies/<int:company_id>/tabs', methods=['GET'])
def get_company_tabs(company_id):
    """获取公司的所有标签页"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, name, type, sort_order, created_at, updated_at
                FROM company_tabs
                WHERE company_id = %s
                ORDER BY sort_order, created_at
            ''', (company_id,))
            tabs = cursor.fetchall()
            
            result = []
            for tab in tabs:
                cursor.execute('''
                    SELECT id, title, content, attachments, item_date, sort_order, created_at
                    FROM company_tab_items
                    WHERE tab_id = %s
                    ORDER BY sort_order, created_at DESC
                ''', (tab['id'],))
                items = cursor.fetchall()
                
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

@company_tabs_bp.route('/companies/<int:company_id>/tabs', methods=['POST'])
def create_company_tab(company_id):
    """创建新标签页"""
    data = request.get_json()
    name = data.get('name', '').strip()
    tab_type = data.get('type', 'custom')
    
    if not name:
        return jsonify({'success': False, 'error': '标签名称不能为空'}), 400
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT MAX(sort_order) as max_order FROM company_tabs WHERE company_id = %s', (company_id,))
            result = cursor.fetchone()
            sort_order = (result['max_order'] or 0) + 1
            
            cursor.execute('''
                INSERT INTO company_tabs (company_id, name, type, sort_order)
                VALUES (%s, %s, %s, %s)
            ''', (company_id, name, tab_type, sort_order))
            conn.commit()
            tab_id = cursor.lastrowid
            
            return jsonify({'success': True, 'tab_id': tab_id, 'message': '标签页创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@company_tabs_bp.route('/companies/<int:company_id>/tabs/<int:tab_id>', methods=['PUT'])
def update_company_tab(company_id, tab_id):
    """更新标签页"""
    data = request.get_json()
    name = data.get('name', '').strip()
    sort_order = data.get('sort_order')
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if name:
                cursor.execute('UPDATE company_tabs SET name = %s WHERE id = %s AND company_id = %s',
                             (name, tab_id, company_id))
            if sort_order is not None:
                cursor.execute('UPDATE company_tabs SET sort_order = %s WHERE id = %s AND company_id = %s',
                             (sort_order, tab_id, company_id))
            conn.commit()
            return jsonify({'success': True, 'message': '标签页更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@company_tabs_bp.route('/companies/<int:company_id>/tabs/<int:tab_id>', methods=['DELETE'])
def delete_company_tab(company_id, tab_id):
    """删除标签页"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM company_tabs WHERE id = %s AND company_id = %s', (tab_id, company_id))
            conn.commit()
            return jsonify({'success': True, 'message': '标签页删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@company_tabs_bp.route('/companies/<int:company_id>/tabs/<int:tab_id>/items', methods=['POST'])
def create_company_tab_item(company_id, tab_id):
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
            cursor.execute('SELECT MAX(sort_order) as max_order FROM company_tab_items WHERE tab_id = %s', (tab_id,))
            result = cursor.fetchone()
            sort_order = (result['max_order'] or 0) + 1
            
            cursor.execute('''
                INSERT INTO company_tab_items (tab_id, title, content, attachments, item_date, sort_order)
                VALUES (%s, %s, %s, %s, %s, %s)
            ''', (tab_id, title, content, json.dumps(attachments), item_date, sort_order))
            conn.commit()
            item_id = cursor.lastrowid
            
            return jsonify({'success': True, 'item_id': item_id, 'message': '项目创建成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@company_tabs_bp.route('/companies/<int:company_id>/tabs/<int:tab_id>/items/<int:item_id>', methods=['PUT'])
def update_company_tab_item(company_id, tab_id, item_id):
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
            
            if title is not None:
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
                sql = f"UPDATE company_tab_items SET {', '.join(updates)} WHERE id = %s AND tab_id = %s"
                cursor.execute(sql, params)
                conn.commit()
            
            return jsonify({'success': True, 'message': '项目更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@company_tabs_bp.route('/companies/<int:company_id>/tabs/<int:tab_id>/items/<int:item_id>', methods=['DELETE'])
def delete_company_tab_item(company_id, tab_id, item_id):
    """删除标签页项目"""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM company_tab_items WHERE id = %s AND tab_id = %s', (item_id, tab_id))
            conn.commit()
            return jsonify({'success': True, 'message': '项目删除成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@company_tabs_bp.route('/companies/<int:company_id>/favorite', methods=['PUT'])
def toggle_company_favorite(company_id):
    """切换公司收藏状态"""
    data = request.get_json()
    is_favorite = data.get('is_favorite', False)
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('UPDATE company_info SET is_favorite = %s WHERE id = %s', (is_favorite, company_id))
            conn.commit()
            return jsonify({'success': True, 'message': '收藏状态更新成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
