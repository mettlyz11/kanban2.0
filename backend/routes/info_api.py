"""Routes: info_api - info_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_info_api", __name__)
logger = __import__("logging").getLogger(__name__)

@bp.route('/api/architecture', methods=['GET'])
def get_architecture():
    """获取架构图数据"""
    try:
        return jsonify({
            'success': True,
            'architecture': {
                'version': '2.0',
                'components': [
                    {'name': '前端 (React)', 'type': 'frontend', 'status': 'active'},
                    {'name': '后端 (Flask)', 'type': 'backend', 'status': 'active'},
                    {'name': '数据库 (MySQL RDS)', 'type': 'database', 'status': 'active'},
                    {'name': 'Cloudflare Tunnel', 'type': 'gateway', 'status': 'active'}
                ],
                'updated_at': '2026-02-26'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/table-counts', methods=['GET'])
def get_table_counts():
    """获取数据库表记录数"""
    try:
        conn = get_db()
        c = conn.cursor()
    
        tables = ['chat_messages', 'chemical_elements', 'entities', 'emails', 
                  'projects', 'tasks', 'stocks', 'skills', 'llm_configs',
                  'version_logs', 'molecules', 'reactions', 'calc_tasks',
                  'stock_transactions', 'system_metrics']
    
        counts = {}
        for table in tables:
            try:
                c.execute(f'SELECT COUNT(*) FROM {table}')
                counts[table] = list(c.fetchone().values())[0]
            except:
                counts[table] = 0
    
        conn.close()
        return jsonify({'success': True, 'counts': counts})
    except Exception as e:
        return jsonify({'success': True, 'counts': {}})

@bp.route('/api/resources', methods=['GET'])
def get_resources():
    """获取资源库"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM resources
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        resources = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'resources': resources})
    except Exception as e:
        return jsonify({'success': True, 'resources': []})

@bp.route('/api/github/repos', methods=['GET'])
def get_github_repos():
    """获取GitHub仓库列表"""
    try:
        import requests
        # 使用GitHub API获取用户仓库
        # 注意：实际使用需要配置GitHub Token
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'Kanban-System'
        }
    
        # 获取mettlyz11的公开仓库
        response = requests.get(
            'https://api.github.com/users/mettlyz11/repos',
            headers=headers,
            params={'sort': 'updated', 'per_page': 20}
        )
    
        if response.status_code == 200:
            repos = response.json()
            return jsonify({
                'success': True,
                'repos': [{
                    'name': r['name'],
                    'description': r['description'],
                    'url': r['html_url'],
                    'stars': r['stargazers_count'],
                    'language': r['language'],
                    'updated': r['updated_at']
                } for r in repos]
            })
        else:
            # 如果API失败，返回预设的GitHub资源
            return jsonify({
                'success': True,
                'repos': [
                    {'name': 'kanban2.0', 'description': '看板系统v2.0 - React版本', 'url': 'https://github.com/mettlyz11/kanban2.0', 'stars': 0, 'language': 'TypeScript'},
                    {'name': 'kanban-system', 'description': '看板系统v1.0 - Flask版本', 'url': 'https://github.com/mettlyz11/kanban-system', 'stars': 0, 'language': 'Python'}
                ]
            })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/github/stats', methods=['GET'])
def get_github_stats():
    """获取GitHub统计"""
    try:
        return jsonify({
            'success': True,
            'stats': {
                'username': 'mettlyz11',
                'public_repos': 2,
                'followers': 0,
                'following': 0
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/version-logs', methods=['GET'])
def get_version_logs():
    """获取版本日志"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM version_logs ORDER BY release_date DESC LIMIT 20')
        logs = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'logs': logs})
    except Exception as e:
        return jsonify({
            'success': True,
            'logs': [
                {
                    'version': '2.0.0',
                    'release_date': '2026-02-26',
                    'description': 'React版本看板系统正式发布',
                    'changes': ['新增React前端', '新增登录保护', '新增Pepi数字员工', '新增知识大脑']
                },
                {
                    'version': '1.9.0',
                    'release_date': '2026-02-20',
                    'description': '系统功能增强',
                    'changes': ['优化任务管理', '新增资产统计', '修复已知问题']
                }
            ]
        })

@bp.route('/api/saved-views', methods=['GET'])
def get_saved_views():
    """获取所有保存的视图"""
    import json
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute('''
        SELECT id, name, filters, is_default, created_at, updated_at
        FROM saved_views
        ORDER BY is_default DESC, created_at ASC
    ''')
    
    views = []
    for row in c.fetchall():
        view_dict = row_to_dict(row, c)
        # 解析 JSON 字段
        if isinstance(view_dict.get('filters'), str):
            view_dict['filters'] = json.loads(view_dict['filters'])
        views.append(view_dict)
    
    conn.close()
    return jsonify({'success': True, 'views': views})

@bp.route('/api/saved-views', methods=['POST'])
def create_saved_view():
    """创建保存的视图"""
    import json
    
    data = request.get_json()
    name = data.get('name', '').strip()
    filters = data.get('filters', {})
    
    if not name:
        return jsonify({'success': False, 'error': '视图名称不能为空'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    filters_json = json.dumps(filters, ensure_ascii=False)
    
    c.execute('''
        INSERT INTO saved_views (name, filters, is_default)
        VALUES (%s, %s, 0)
    ''', (name, filters_json))
    
    view_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'view_id': view_id,
        'message': '视图已保存'
    })

@bp.route('/api/saved-views/<int:view_id>', methods=['PUT'])
def update_saved_view(view_id):
    """更新保存的视图"""
    import json
    
    data = request.get_json()
    
    conn = get_db()
    c = conn.cursor()
    
    # 检查视图是否存在
    c.execute('SELECT id FROM saved_views WHERE id = %s', (view_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '视图不存在'}), 404
    
    updates = {}
    if 'name' in data:
        updates['name'] = data['name']
    if 'filters' in data:
        updates['filters'] = json.dumps(data['filters'], ensure_ascii=False)
    
    if not updates:
        conn.close()
        return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
    
    set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
    values = list(updates.values()) + [view_id]
    
    c.execute(f'UPDATE saved_views SET {set_clause} WHERE id = %s', values)
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '视图已更新'
    })

@bp.route('/api/saved-views/<int:view_id>', methods=['DELETE'])
def delete_saved_view(view_id):
    """删除保存的视图"""
    conn = get_db()
    c = conn.cursor()
    
    # 检查是否为默认视图
    c.execute('SELECT is_default FROM saved_views WHERE id = %s', (view_id,))
    row = c.fetchone()
    if row and row[0]:
        conn.close()
        return jsonify({'success': False, 'error': '不能删除默认视图'}), 400
    
    c.execute('DELETE FROM saved_views WHERE id = %s', (view_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '视图已删除'
    })


