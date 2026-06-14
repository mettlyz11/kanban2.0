from flask import Blueprint, request, jsonify
from datetime import datetime
import json
from routes.helpers import get_db, row_to_dict

bp = Blueprint('resource_library', __name__, url_prefix='/api/resource-library')

@bp.route('', methods=['GET'])
def get_resource_library():
    """获取资源库所有条目"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取所有条目，按路径排序
        c.execute('''
            SELECT * FROM resource_library_categories
            ORDER BY path
        ''')
        items = [row_to_dict(row, c) for row in c.fetchall()]
        
        # 转换为树形结构
        def build_tree(items, parent_path=''):
            tree = []
            for item in items:
                # 检查是否是当前父路径的直接子项
                item_path = item['path']
                if item_path.startswith(parent_path + '/') or parent_path == '':
                    # 计算层级
                    depth = item_path.count('/')
                    if (parent_path == '' and depth == 0) or (parent_path != '' and depth == parent_path.count('/') + 1):
                        # 递归构建子树
                        children = build_tree(items, item_path)
                        if children:
                            item['children'] = children
                        tree.append(item)
            return tree
        
        tree = build_tree(items)
        
        # 获取最后更新时间
        c.execute('''
            SELECT MAX(updated_at) as last_updated FROM resource_library_categories
        ''')
        last_updated = c.fetchone()['last_updated']
        
        conn.close()
        
        return jsonify({
            'success': True,
            'data': tree,
            'last_updated': last_updated.isoformat() if last_updated else None,
            'count': len(items)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/sync', methods=['POST'])
def sync_resource_library():
    """同步资源库数据（来自Mac mini推送）"""
    try:
        data = request.get_json()
        if not isinstance(data, list):
            return jsonify({'success': False, 'error': '请求体必须是JSON数组'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # 插入或更新数据
        for item in data:
            # 验证必填字段
            if 'path' not in item or 'name' not in item or 'type' not in item:
                continue
            
            # 准备数据
            path = item['path']
            name = item['name']
            type_ = item['type']
            size = item.get('size', 0)
            item_count = item.get('item_count', 0)
            llm_summary = item.get('llm_summary', '')
            tags = item.get('tags', '')
            suggested_use = item.get('suggested_use', '')
            
            # 插入或更新
            c.execute('''
                INSERT INTO resource_library_categories 
                (path, name, type, size, item_count, llm_summary, tags, suggested_use)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    name = VALUES(name),
                    type = VALUES(type),
                    size = VALUES(size),
                    item_count = VALUES(item_count),
                    llm_summary = VALUES(llm_summary),
                    tags = VALUES(tags),
                    suggested_use = VALUES(suggested_use),
                    updated_at = CURRENT_TIMESTAMP
            ''', (path, name, type_, size, item_count, llm_summary, tags, suggested_use))
        
        conn.commit()
        
        # 发送WebSocket通知
        try:
            from src.websocket.index import get_socketio_instance
            socketio = get_socketio_instance()
            if socketio:
                socketio.emit('resource_library_updated', {
                    'timestamp': datetime.now().isoformat()
                })
        except Exception as e:
            print(f"⚠️ WebSocket通知发送失败: {e}")
        
        conn.close()
        
        return jsonify({
            'success': True,
            'message': f'同步成功，共处理{len(data)}条数据',
            'count': len(data)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/search', methods=['GET'])
def search_resource_library():
    """搜索资源库"""
    try:
        keyword = request.args.get('q', '').strip()
        if not keyword:
            return jsonify({'success': False, 'error': '搜索关键词不能为空'}), 400
        
        conn = get_db()
        c = conn.cursor()
        
        # 搜索名称、标签、简介
        search_pattern = f'%{keyword}%'
        c.execute('''
            SELECT * FROM resource_library_categories
            WHERE name LIKE %s OR tags LIKE %s OR llm_summary LIKE %s
            ORDER BY updated_at DESC
            LIMIT 50
        ''', (search_pattern, search_pattern, search_pattern))
        
        items = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        
        return jsonify({
            'success': True,
            'data': items,
            'count': len(items),
            'keyword': keyword
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/project/<int:project_id>', methods=['GET'])
def get_project_resources(project_id):
    """获取项目关联的资源"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT rlc.*, pr.match_type, pr.created_at as linked_at
            FROM project_resources pr
            JOIN resource_library_categories rlc ON pr.resource_path = rlc.path
            WHERE pr.project_id = %s
            ORDER BY rlc.name
        ''', (project_id,))
        items = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'items': items, 'count': len(items)})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/project/<int:project_id>/link', methods=['POST'])
def link_project_resource(project_id):
    """手动关联资源到项目"""
    try:
        data = request.get_json()
        resource_path = data.get('resource_path')
        if not resource_path:
            return jsonify({'success': False, 'error': '需要resource_path'}), 400
        conn = get_db()
        c = conn.cursor()
        c.execute('''INSERT IGNORE INTO project_resources (project_id, resource_path, match_type)
          VALUES (%s, %s, 'manual')''', (project_id, resource_path))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'已关联 {resource_path}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/project/<int:project_id>/unlink', methods=['POST'])
def unlink_project_resource(project_id):
    """解除资源关联"""
    try:
        data = request.get_json()
        resource_path = data.get('resource_path')
        if not resource_path:
            return jsonify({'success': False, 'error': '需要resource_path'}), 400
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM project_resources WHERE project_id = %s AND resource_path = %s',
                  (project_id, resource_path))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'已解除 {resource_path}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/auto-map', methods=['POST'])
def auto_map_resources():
    """自动匹配项目与资源目录（按名称关键词）"""
    try:
        conn = get_db()
        c = conn.cursor()
        # 获取所有项目
        c.execute('SELECT id, name FROM projects WHERE status != "archived"')
        projects = {row['id']: row['name'] for row in c.fetchall()}
        # 获取所有资源目录
        c.execute('SELECT path, name FROM resource_library_categories WHERE type = "dir"')
        resources = [(row['path'], row['name']) for row in c.fetchall()]
        
        linked = 0
        for pid, pname in projects.items():
            pname_lower = pname.lower()
            for rpath, rname in resources:
                rname_lower = rname.lower()
                # 自动匹配：资源名是项目名的一部分，或反之
                if rname_lower in pname_lower or pname_lower in rname_lower:
                    c.execute('''INSERT IGNORE INTO project_resources (project_id, resource_path, match_type)
                      VALUES (%s, %s, 'auto')''', (pid, rpath))
                    if c.rowcount > 0:
                        linked += 1
        
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'自动关联完成，新增{linked}条匹配'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

import os
from flask import send_file

@bp.route('/keys/<filename>', methods=['GET'])
def download_key_file(filename):
    """下载备份的密钥文件"""
    safe_names = ['aliserver1.pem','aliserver2.pem','aliserver3.pem','aliserver4.pem','GPU1.pem']
    if filename not in safe_names:
        return jsonify({'success': False, 'error': '不允许的文件名'}), 403
    key_path = os.path.join('/opt/kanban-react/backend/backup/keys', filename)
    if not os.path.exists(key_path):
        return jsonify({'success': False, 'error': '文件不存在'}), 404
    return send_file(key_path, as_attachment=True, download_name=filename)
