#!/usr/bin/env python3
"""
更新 app.py - 添加高级筛选和搜索功能
"""

import re

# 读取 app.py
with open('/opt/kanban-react/backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. 增强 get_tasks 函数
old_get_tasks = '''def get_tasks():
    """获取任务列表"""
    status = request.args.get('status', '')
    project_id = request.args.get('project_id', '')

    conn = get_db()
    c = conn.cursor()

    query = \'\'\'
        SELECT t.*, p.name as project_name, p.number as project_number
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.status != 'deleted'
    \'\'\'
    params = []

    if status:
        query += ' AND t.status = ?'
        params.append(status)

    if project_id:
        query += ' AND t.project_id = ?'
        params.append(project_id)

    query += ' ORDER BY t.created_at DESC'

    c.execute(query, params)
    tasks = [row_to_dict(row, c) for row in c.fetchall()]
    conn.close()

    return jsonify({'success': True, 'tasks': tasks})'''

new_get_tasks = '''def get_tasks():
    """获取任务列表（支持高级筛选和搜索）"""
    from datetime import datetime, timedelta
    
    # 原有参数
    status = request.args.get('status', '')
    project_id = request.args.get('project_id', '')
    
    # 新增筛选参数
    search = request.args.get('search', '')
    tags = request.args.get('tags', '')
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    quick_filter = request.args.get('quick_filter', '')

    conn = get_db()
    c = conn.cursor()

    query = \'\'\'
        SELECT t.*, p.name as project_name, p.number as project_number
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.status != 'deleted'
    \'\'\'
    params = []

    # 原有筛选
    if status:
        query += ' AND t.status = ?'
        params.append(status)

    if project_id:
        query += ' AND t.project_id = ?'
        params.append(project_id)
    
    # 全局搜索（标题、描述、标签）
    if search:
        search_term = f'%{search}%'
        query += ' AND (t.title LIKE ? OR t.description LIKE ? OR t.tags LIKE ?)'
        params.extend([search_term, search_term, search_term])
    
    # 标签筛选（支持多标签，逗号分隔）
    if tags:
        tag_list = [t.strip() for t in tags.split(',') if t.strip()]
        tag_conditions = []
        for tag in tag_list:
            tag_conditions.append('t.tags LIKE ?')
            params.append(f'%{tag}%')
        if tag_conditions:
            query += f' AND ({" OR ".join(tag_conditions)})'
    
    # 时间范围筛选
    if date_from:
        query += ' AND DATE(t.created_at) >= ?'
        params.append(date_from)

    if date_to:
        query += ' AND DATE(t.created_at) <= ?'
        params.append(date_to)
    
    # 快捷筛选
    if quick_filter:
        today = datetime.now().date()
        
        if quick_filter == 'today':
            query += ' AND DATE(t.created_at) = ?'
            params.append(today.isoformat())
        elif quick_filter == 'this_week':
            # 本周一
            monday = today - timedelta(days=today.weekday())
            query += ' AND DATE(t.created_at) >= ?'
            params.append(monday.isoformat())
        elif quick_filter == 'this_month':
            # 本月 1 号
            first_day = today.replace(day=1)
            query += ' AND DATE(t.created_at) >= ?'
            params.append(first_day.isoformat())

    query += ' ORDER BY t.created_at DESC'

    c.execute(query, params)
    tasks = [row_to_dict(row, c) for row in c.fetchall()]
    conn.close()

    return jsonify({'success': True, 'tasks': tasks})'''

if old_get_tasks in content:
    content = content.replace(old_get_tasks, new_get_tasks)
    print("✅ 已更新 get_tasks 函数")
else:
    print("⚠️  未找到 get_tasks 函数，可能格式不同")

# 2. 在文件末尾添加保存视图 API
# 找到文件末尾（最后一个路由之后）
saved_views_api = '''
# ============================================
# 保存视图 API
# ============================================

@app.route('/api/saved-views', methods=['GET'])
def get_saved_views():
    """获取所有保存的视图"""
    import json
    
    conn = get_db()
    c = conn.cursor()
    
    c.execute(\'\'\'
        SELECT id, name, filters, is_default, created_at, updated_at
        FROM saved_views
        ORDER BY is_default DESC, created_at ASC
    \'\'\')
    
    views = []
    for row in c.fetchall():
        view_dict = row_to_dict(row, c)
        # 解析 JSON 字段
        if isinstance(view_dict.get('filters'), str):
            view_dict['filters'] = json.loads(view_dict['filters'])
        views.append(view_dict)
    
    conn.close()
    return jsonify({'success': True, 'views': views})

@app.route('/api/saved-views', methods=['POST'])
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
    
    c.execute(\'\'\'
        INSERT INTO saved_views (name, filters, is_default)
        VALUES (?, ?, 0)
    \'\'\', (name, filters_json))
    
    view_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'view_id': view_id,
        'message': '视图已保存'
    })

@app.route('/api/saved-views/<int:view_id>', methods=['PUT'])
def update_saved_view(view_id):
    """更新保存的视图"""
    import json
    
    data = request.get_json()
    
    conn = get_db()
    c = conn.cursor()
    
    # 检查视图是否存在
    c.execute('SELECT id FROM saved_views WHERE id = ?', (view_id,))
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
    
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    values = list(updates.values()) + [view_id]
    
    c.execute(f'UPDATE saved_views SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '视图已更新'
    })

@app.route('/api/saved-views/<int:view_id>', methods=['DELETE'])
def delete_saved_view(view_id):
    """删除保存的视图"""
    conn = get_db()
    c = conn.cursor()
    
    # 检查是否为默认视图
    c.execute('SELECT is_default FROM saved_views WHERE id = ?', (view_id,))
    row = c.fetchone()
    if row and row[0]:
        conn.close()
        return jsonify({'success': False, 'error': '不能删除默认视图'}), 400
    
    c.execute('DELETE FROM saved_views WHERE id = ?', (view_id,))
    conn.commit()
    conn.close()
    
    return jsonify({
        'success': True,
        'message': '视图已删除'
    })

'''

# 在文件末尾添加
content = content.rstrip() + '\n' + saved_views_api
print("✅ 已添加保存视图 API")

# 写回文件
with open('/opt/kanban-react/backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✅ app.py 更新完成！")
print("\n新增功能:")
print("  - GET /api/tasks: 支持 search, tags, date_from, date_to, quick_filter")
print("  - GET /api/saved-views: 获取保存的视图")
print("  - POST /api/saved-views: 创建保存的视图")
print("  - PUT /api/saved-views/<id>: 更新保存的视图")
print("  - DELETE /api/saved-views/<id>: 删除保存的视图")
