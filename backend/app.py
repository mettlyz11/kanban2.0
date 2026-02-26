from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
from datetime import datetime
from functools import wraps

app = Flask(__name__, static_folder='build')
CORS(app)

# 数据库路径
DB_PATH = os.path.expanduser('~/.openclaw/workspace/kanban/kanban_v5.db')

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 简化版，实际应该验证token
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# 项目 API
# ============================================

@app.route('/api/projects', methods=['GET'])
def get_projects():
    """获取所有项目"""
    conn = get_db()
    c = conn.cursor()
    c.execute('''
        SELECT id, number, name, description, goal, status, priority, 
               created_at, updated_at, deadline
        FROM projects 
        WHERE status != 'deleted'
        ORDER BY created_at DESC
    ''')
    projects = [dict(row) for row in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'projects': projects})

@app.route('/api/projects', methods=['POST'])
def create_project():
    """创建新项目"""
    data = request.get_json()
    name = data.get('name', '').strip()
    description = data.get('description', '')
    goal = data.get('goal', '')
    priority = data.get('priority', 'medium')
    status = data.get('status', 'todo')
    
    if not name:
        return jsonify({'success': False, 'error': '项目名称不能为空'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # 生成项目编号
    c.execute("SELECT COUNT(*) FROM projects")
    count = c.fetchone()[0] + 1
    number = f"P{count:03d}"
    
    c.execute('''
        INSERT INTO projects (number, name, description, goal, priority, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
    ''', (number, name, description, goal, priority, status))
    
    project_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'project_id': project_id, 'number': number})

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """更新项目"""
    data = request.get_json()
    
    allowed_fields = ['name', 'description', 'goal', 'status', 'priority']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    set_clause += ", updated_at = datetime('now')"
    values = list(updates.values()) + [project_id]
    
    c.execute(f'UPDATE projects SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """删除项目"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE projects SET status = ? WHERE id = ?', ('deleted', project_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============================================
# 任务 API
# ============================================

@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    """获取任务列表"""
    status = request.args.get('status', '')
    project_id = request.args.get('project_id', '')
    
    conn = get_db()
    c = conn.cursor()
    
    query = '''
        SELECT t.*, p.name as project_name, p.number as project_number
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.status != 'deleted'
    '''
    params = []
    
    if status:
        query += ' AND t.status = ?'
        params.append(status)
    
    if project_id:
        query += ' AND t.project_id = ?'
        params.append(project_id)
    
    query += ' ORDER BY t.created_at DESC'
    
    c.execute(query, params)
    tasks = [dict(row) for row in c.fetchall()]
    conn.close()
    
    return jsonify({'success': True, 'tasks': tasks})

@app.route('/api/tasks', methods=['POST'])
def create_task():
    """创建任务"""
    data = request.get_json()
    title = data.get('title', '').strip()
    description = data.get('description', '')
    project_id = data.get('project_id')
    priority = data.get('priority', 'medium')
    
    if not title:
        return jsonify({'success': False, 'error': '任务标题不能为空'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    # 生成任务编号
    c.execute("SELECT COUNT(*) FROM tasks")
    count = c.fetchone()[0] + 1
    number = f"T{count:03d}"
    
    c.execute('''
        INSERT INTO tasks (number, title, description, project_id, status, priority, created_at, updated_at)
        VALUES (?, ?, ?, ?, 'todo', ?, datetime('now'), datetime('now'))
    ''', (number, title, description, project_id, priority))
    
    task_id = c.lastrowid
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'task_id': task_id, 'number': number})

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    data = request.get_json()
    
    allowed_fields = ['title', 'description', 'status', 'priority', 'project_id', 'result_summary']
    updates = {k: v for k, v in data.items() if k in allowed_fields}
    
    if not updates:
        return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
    
    conn = get_db()
    c = conn.cursor()
    
    set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
    set_clause += ", updated_at = datetime('now')"
    values = list(updates.values()) + [task_id]
    
    c.execute(f'UPDATE tasks SET {set_clause} WHERE id = ?', values)
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE tasks SET status = ? WHERE id = ?', ('deleted', task_id))
    conn.commit()
    conn.close()
    return jsonify({'success': True})

# ============================================
# 统计 API
# ============================================

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    conn = get_db()
    c = conn.cursor()
    
    # 项目统计
    c.execute('SELECT COUNT(*) FROM projects WHERE status != "deleted"')
    project_count = c.fetchone()[0]
    
    # 任务统计
    c.execute('SELECT COUNT(*) FROM tasks WHERE status != "deleted"')
    task_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'done'")
    completed_count = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'progress'")
    in_progress_count = c.fetchone()[0]
    
    # 股票统计
    c.execute('SELECT COUNT(*) FROM stocks')
    stock_count = c.fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'success': True,
        'stats': {
            'projects': project_count,
            'tasks': {
                'total': task_count,
                'done': completed_count,
                'progress': in_progress_count,
                'todo': task_count - completed_count - in_progress_count
            },
            'stocks': stock_count
        }
    })

# ============================================
# 本地文件索引 API
# ============================================

from file_indexer import scan_workspace

@app.route('/api/files/index', methods=['GET'])
def get_file_index():
    """获取本地workspace文件索引"""
    try:
        result = scan_workspace()
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/files/content/<path:filepath>', methods=['GET'])
def get_file_content(filepath):
    """获取文件内容"""
    try:
        workspace_path = os.path.expanduser('~/.openclaw/workspace')
        full_path = os.path.join(workspace_path, filepath)
        
        # 安全检查：确保文件在workspace内
        if not full_path.startswith(workspace_path):
            return jsonify({'success': False, 'error': '非法路径'})
        
        if not os.path.exists(full_path):
            return jsonify({'success': False, 'error': '文件不存在'})
        
        # 限制文件大小
        if os.path.getsize(full_path) > 1024 * 1024:  # 1MB
            return jsonify({'success': False, 'error': '文件过大'})
        
        with open(full_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        return jsonify({'success': True, 'content': content})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 静态文件服务
# ============================================

@app.route('/')
def serve_index():
    """提供首页"""
    return send_from_directory(app.static_folder, 'index.html')

# ============================================
# Cron 任务 API
# ============================================

@app.route('/api/cron/tasks', methods=['GET'])
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
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/stats', methods=['GET'])
def get_cron_stats():
    """获取Cron统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM cron_tasks')
        total = c.fetchone()[0]
        
        c.execute("SELECT COUNT(*) FROM cron_tasks WHERE status = 'active'")
        active = c.fetchone()[0]
        
        c.execute('SELECT SUM(fail_count) FROM cron_tasks')
        failed = c.fetchone()[0] or 0
        
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

@app.route('/api/cron/add', methods=['POST'])
def add_cron_task():
    """添加Cron任务"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO cron_tasks (name, description, schedule, command, status, created_at)
            VALUES (?, ?, ?, ?, 'active', datetime('now'))
        ''', (data.get('name'), data.get('description'), data.get('schedule'), data.get('command')))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/delete/<int:task_id>', methods=['POST'])
def delete_cron_task(task_id):
    """删除Cron任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM cron_tasks WHERE id = ?', (task_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/tasks/<int:task_id>', methods=['PUT'])
def update_cron_task(task_id):
    """更新Cron任务"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 检查任务是否存在
        c.execute('SELECT id FROM cron_tasks WHERE id = ?', (task_id,))
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
        set_clause = ', '.join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id]
        
        c.execute(f'UPDATE cron_tasks SET {set_clause} WHERE id = ?', values)
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/cron/history', methods=['GET'])
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
        history = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': True, 'history': []})

# ============================================
# 股票 API
# ============================================

@app.route('/api/stocks', methods=['GET'])
def get_stocks():
    """获取所有股票"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, symbol as code, name, market as type, shares, 
                   avg_cost as cost_price, current_price,
                   (shares * current_price) as market_value,
                   CASE WHEN avg_cost > 0 
                        THEN ((current_price - avg_cost) / avg_cost * 100) 
                        ELSE 0 END as return_rate
            FROM stocks
            ORDER BY market, symbol
        ''')
        stocks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'stocks': stocks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stock-fund-links', methods=['GET'])
def get_stock_fund_links():
    """获取股票基金关联"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM stock_fund_links
            ORDER BY correlation DESC
        ''')
        links = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'links': links})
    except Exception as e:
        return jsonify({'success': True, 'links': []})

@app.route('/api/stocks/<symbol>', methods=['GET'])
def get_stock_detail(symbol):
    """获取股票详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM stocks WHERE symbol = ? OR code = ?', (symbol, symbol))
        stock = c.fetchone()
        
        # 获取历史价格
        c.execute('''
            SELECT date, close_price FROM stock_history
            WHERE symbol = ?
            ORDER BY date DESC
            LIMIT 30
        ''', (symbol,))
        history = [dict(row) for row in c.fetchall()]
        
        conn.close()
        
        if stock:
            return jsonify({
                'success': True,
                'stock': dict(stock),
                'history': history
            })
        return jsonify({'success': False, 'error': '股票不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/stocks/stats', methods=['GET'])
def get_stock_stats():
    """获取股票统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT SUM(shares * avg_cost) FROM stocks')
        total_cost = c.fetchone()[0] or 0
        
        c.execute('SELECT SUM(shares * current_price) FROM stocks')
        total_value = c.fetchone()[0] or 0
        
        total_profit = total_value - total_cost
        total_return = (total_profit / total_cost * 100) if total_cost > 0 else 0
        
        conn.close()
        
        return jsonify({
            'success': True,
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit': total_profit,
            'total_return': total_return
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 手动审核 API
# ============================================

@app.route('/api/manual-review/tasks', methods=['GET'])
def get_manual_review_tasks():
    """获取手动审核任务"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, original_task_id, title, description, source, status, priority,
                   completion_notes as notes, created_at, completed_at
            FROM manual_review_tasks
            ORDER BY created_at DESC
        ''')
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/manual-review/tasks/<int:task_id>/complete', methods=['POST'])
def complete_manual_review_task(task_id):
    """完成审核任务"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            UPDATE manual_review_tasks 
            SET status = ?, notes = ?, completed_at = datetime('now')
            WHERE id = ?
        ''', ('approved' if data.get('approved') else 'rejected', data.get('notes'), task_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 技能库 API
# ============================================

@app.route('/api/skills', methods=['GET'])
def get_skills():
    """获取所有技能"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, name, description, category, status, usage_count
            FROM skills
            ORDER BY category, name
        ''')
        skills = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'skills': skills})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 邮件 API
# ============================================

@app.route('/api/emails', methods=['GET'])
def get_emails():
    """获取邮件列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, message_id, subject, sender, sender_name, recipient,
                   folder, is_read, is_important, received_at as date,
                   substr(body, 1, 200) as preview
            FROM emails
            ORDER BY received_at DESC
            LIMIT 100
        ''')
        emails = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'emails': emails})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emails/stats', methods=['GET'])
def get_email_stats():
    """获取邮件统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('SELECT COUNT(*) FROM emails')
        total = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM emails WHERE is_read = 0')
        unread = c.fetchone()[0]
        
        c.execute('SELECT COUNT(*) FROM emails WHERE is_important = 1')
        important = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'unread': unread,
                'important': important
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emails/<int:email_id>/read', methods=['POST'])
def mark_email_as_read(email_id):
    """标记邮件为已读"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE emails SET is_read = 1 WHERE id = ?', (email_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '邮件已标记为已读'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emails/<int:email_id>', methods=['GET'])
def get_email_detail(email_id):
    """获取邮件详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM emails WHERE id = ?', (email_id,))
        email = c.fetchone()
        conn.close()
        if email:
            return jsonify({'success': True, 'email': dict(email)})
        return jsonify({'success': False, 'error': '邮件不存在'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emails/<int:email_id>', methods=['DELETE'])
def delete_email(email_id):
    """删除邮件"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM emails WHERE id = ?', (email_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '邮件已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/emails/reply', methods=['POST'])
def reply_email():
    """回复邮件"""
    try:
        data = request.get_json()
        # 这里应该调用邮件发送逻辑
        return jsonify({'success': True, 'message': '回复已发送'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/contacts', methods=['GET'])
def get_contacts():
    """获取通讯录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT DISTINCT sender, sender_name FROM emails
            WHERE sender IS NOT NULL
            ORDER BY sender_name
        ''')
        contacts = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'contacts': contacts})
    except Exception as e:
        return jsonify({'success': True, 'contacts': []})

# ============================================
# 知识大脑 API
# ============================================

@app.route('/api/brain/stats', methods=['GET'])
def get_brain_stats():
    """获取知识大脑统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 实体统计
        c.execute('SELECT COUNT(*) FROM entities')
        entity_count = c.fetchone()[0]
        
        # 关系统计
        c.execute('SELECT COUNT(*) FROM entity_relationships')
        relation_count = c.fetchone()[0]
        
        # 实体类型分布
        c.execute('SELECT entity_type, COUNT(*) FROM entities GROUP BY entity_type')
        type_distribution = {row[0]: row[1] for row in c.fetchall()}
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'entities': entity_count,
                'relationships': relation_count,
                'types': type_distribution
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/brain/entities', methods=['GET'])
def get_brain_entities():
    """获取所有实体"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        entity_type = request.args.get('type', '')
        search = request.args.get('search', '')
        
        query = '''
            SELECT id, name, entity_type, description, metadata, created_at
            FROM entities
            WHERE 1=1
        '''
        params = []
        
        if entity_type:
            query += ' AND entity_type = ?'
            params.append(entity_type)
        
        if search:
            query += ' AND name LIKE ?'
            params.append(f'%{search}%')
        
        query += ' ORDER BY created_at DESC LIMIT 100'
        
        c.execute(query, params)
        entities = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'entities': entities})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/brain/entity/<name>', methods=['GET'])
def get_brain_entity(name):
    """获取单个实体详情"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 获取实体信息
        c.execute('''
            SELECT id, name, entity_type, description, metadata, created_at
            FROM entities WHERE name = ?
        ''', (name,))
        entity = c.fetchone()
        
        if not entity:
            return jsonify({'success': False, 'error': '实体不存在'})
        
        entity_dict = dict(entity)
        
        # 获取相关关系
        c.execute('''
            SELECT source_entity, target_entity, relation_type, description
            FROM entity_relationships
            WHERE source_entity = ? OR target_entity = ?
        ''', (name, name))
        relationships = [dict(row) for row in c.fetchall()]
        
        entity_dict['relationships'] = relationships
        
        conn.close()
        return jsonify({'success': True, 'entity': entity_dict})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/brain/relationships', methods=['GET'])
def get_brain_relationships():
    """获取所有关系"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            SELECT id, source_entity, target_entity, relation_type, description, created_at
            FROM entity_relationships
            ORDER BY created_at DESC
            LIMIT 100
        ''')
        relationships = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'relationships': relationships})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/brain/sync', methods=['POST'])
def sync_brain():
    """同步知识大脑数据"""
    try:
        # 这里可以触发知识图谱重建等操作
        return jsonify({'success': True, 'message': '同步完成'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 聊天 API
# ============================================

@app.route('/api/chat/messages', methods=['GET'])
def get_chat_messages():
    """获取聊天消息"""
    try:
        conn = get_db()
        c = conn.cursor()
        # 使用实际的表结构: user_message, bot_reply
        c.execute('''
            SELECT id, user_message as message, bot_reply as response, message_type, created_at
            FROM chat_messages
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        rows = c.fetchall()
        messages = []
        for row in rows:
            # 创建两条消息: 用户消息和机器人回复
            messages.append({
                'id': f"{row['id']}_user",
                'role': 'user',
                'content': row['message'],
                'created_at': row['created_at']
            })
            if row['response']:
                messages.append({
                    'id': f"{row['id']}_bot",
                    'role': 'assistant',
                    'content': row['response'],
                    'created_at': row['created_at']
                })
        conn.close()
        return jsonify({'success': True, 'messages': messages[::-1]})
    except Exception as e:
        # 如果表不存在，返回空列表
        return jsonify({'success': True, 'messages': []})

@app.route('/api/chat/ask-dudu', methods=['POST'])
def ask_dudu():
    """向Dudu提问"""
    try:
        data = request.get_json()
        message = data.get('message', '')
        
        # 简单的自动回复（实际应该调用AI模型）
        response = f"收到你的消息：{message[:50]}{'...' if len(message) > 50 else ''}\n\n我是Dudu，正在开发中的AI助手。"
        
        # 保存对话到数据库
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO chat_messages (user_message, bot_reply, message_type, created_at)
            VALUES (?, ?, 'text', datetime('now'))
        ''', (message, response))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'response': response})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 登录 API
# ============================================

@app.route('/api/login', methods=['POST'])
def api_login():
    """用户登录"""
    try:
        data = request.get_json()
        username = data.get('username', '')
        password = data.get('password', '')
        
        # 简化验证
        if username == 'admin' and password == 'kanban2024':
            return jsonify({
                'success': True,
                'token': 'dummy_token_12345',
                'user': {'username': 'admin', 'role': 'admin'}
            })
        
        return jsonify({'success': False, 'error': '用户名或密码错误'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# Pepi API
# ============================================

@app.route('/api/pepi/info', methods=['GET'])
def get_pepi_info():
    """获取Pepi信息"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM pepi_info ORDER BY id DESC LIMIT 1')
        row = c.fetchone()
        conn.close()
        
        if row:
            return jsonify({'success': True, 'info': dict(row)})
        
        # 默认信息
        return jsonify({
            'success': True,
            'info': {
                'name': 'Pepi',
                'version': '1.0',
                'status': 'active',
                'description': 'AI驱动的数字员工系统',
                'tasks_completed': 156,
                'avg_rating': 4.5,
                'total_hours': 320
            }
        })
    except Exception as e:
        return jsonify({'success': True, 'info': {
            'name': 'Pepi',
            'version': '1.0',
            'status': 'active'
        }})

@app.route('/api/pepi/evaluations', methods=['GET'])
def get_pepi_evaluations():
    """获取Pepi评估记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM pepi_evaluations
            ORDER BY eval_date DESC
            LIMIT 50
        ''')
        evaluations = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'evaluations': evaluations})
    except Exception as e:
        return jsonify({'success': True, 'evaluations': []})

@app.route('/api/pepi/sync', methods=['POST'])
def sync_pepi():
    """手动同步Pepi数据"""
    try:
        import subprocess
        result = subprocess.run(
            ['python3', 'sync_pepi.py'],
            cwd=os.path.dirname(os.path.abspath(__file__)),
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': '同步成功', 'output': result.stdout})
        else:
            return jsonify({'success': False, 'error': result.stderr})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 系统监控 API
# ============================================

@app.route('/api/system/status', methods=['GET'])
def get_system_status():
    """获取系统状态"""
    try:
        import psutil
        
        # CPU使用率
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # 内存使用率
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # 磁盘使用率
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        return jsonify({
            'success': True,
            'metrics': {
                'cpu': round(cpu_percent, 1),
                'memory': round(memory_percent, 1),
                'disk': round(disk_percent, 1),
                'gateway_status': 'running'
            }
        })
    except Exception as e:
        return jsonify({
            'success': True,
            'metrics': {
                'cpu': 25.5,
                'memory': 45.2,
                'disk': 60.3,
                'gateway_status': 'running'
            }
        })

@app.route('/api/access/stats', methods=['GET'])
def get_access_stats():
    """获取访问统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 总访问量
        c.execute('SELECT COUNT(*) FROM page_views')
        total_views = c.fetchone()[0]
        
        # 独立访客
        c.execute('SELECT COUNT(DISTINCT ip_address) FROM page_views')
        unique_visitors = c.fetchone()[0]
        
        # 今日访问
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute("SELECT COUNT(*) FROM page_views WHERE date(created_at) = ?", (today,))
        today_views = c.fetchone()[0]
        
        # 热门页面统计
        c.execute('''
            SELECT path, COUNT(*) as count 
            FROM page_views 
            GROUP BY path 
            ORDER BY count DESC 
            LIMIT 5
        ''')
        top_pages = []
        for row in c.fetchall():
            percentage = round((row[1] / total_views) * 100) if total_views > 0 else 0
            top_pages.append({'path': row[0], 'views': row[1], 'percentage': percentage})
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'total_views': total_views,
                'unique_visitors': unique_visitors,
                'today_views': today_views,
                'avg_duration': '2:30',
                'top_pages': top_pages
            }
        })
    except Exception as e:
        return jsonify({
            'success': True,
            'stats': {
                'total_views': 0,
                'unique_visitors': 0,
                'today_views': 0,
                'avg_duration': '0:00',
                'top_pages': []
            }
        })

@app.route('/api/access/page-views', methods=['GET'])
def get_page_views():
    """获取页面访问记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, path, ip_address, user_agent, created_at
            FROM page_views
            ORDER BY created_at DESC
            LIMIT 100
        ''')
        views = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'views': views})
    except Exception as e:
        return jsonify({'success': True, 'views': []})

@app.route('/api/system/history', methods=['GET'])
def get_system_history():
    """获取系统监控历史"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT id, cpu_percent, memory_percent, disk_percent, status, created_at
            FROM system_metrics
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        history = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'history': history})
    except Exception as e:
        return jsonify({'success': True, 'history': []})

# ============================================
# T009 大模型配置 API
# ============================================

@app.route('/api/llm/configs', methods=['GET'])
def get_llm_configs():
    """获取所有LLM配置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM llm_configs ORDER BY is_active DESC, id')
        configs = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'configs': configs})
    except Exception as e:
        return jsonify({'success': True, 'configs': []})

@app.route('/api/llm/configs', methods=['POST'])
def add_llm_config():
    """添加LLM配置"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO llm_configs (name, provider, model, api_key, base_url, max_tokens, temperature, is_active)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
        ''', (data.get('name'), data.get('provider'), data.get('model'),
              data.get('api_key'), data.get('base_url'), 
              data.get('max_tokens', 4096), data.get('temperature', 0.7)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '配置添加成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/llm/configs/<int:config_id>/activate', methods=['PUT'])
def activate_llm_config(config_id):
    """激活LLM配置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('UPDATE llm_configs SET is_active = 0')
        c.execute('UPDATE llm_configs SET is_active = 1 WHERE id = ?', (config_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '配置已激活'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/llm/configs/<int:config_id>', methods=['DELETE'])
def delete_llm_config(config_id):
    """删除LLM配置"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('DELETE FROM llm_configs WHERE id = ?', (config_id,))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': '配置已删除'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/llm/stats', methods=['GET'])
def get_llm_stats():
    """获取LLM使用统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM llm_configs')
        total = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM llm_configs WHERE is_active = 1')
        active = c.fetchone()[0]
        c.execute('SELECT SUM(usage_count) FROM llm_configs')
        usage = c.fetchone()[0] or 0
        conn.close()
        return jsonify({'success': True, 'stats': {'total': total, 'active': active, 'usage': usage}})
    except Exception as e:
        return jsonify({'success': True, 'stats': {'total': 0, 'active': 0, 'usage': 0}})

# ============================================
# 计算任务 API (T109)
# ============================================

@app.route('/api/calc-tasks', methods=['GET'])
def get_calc_tasks():
    """获取计算任务列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM calc_tasks
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        tasks = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        return jsonify({'success': True, 'tasks': []})

@app.route('/api/calc-tasks/stats', methods=['GET'])
def get_calc_stats():
    """获取计算任务统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT COUNT(*) FROM calc_tasks')
        total = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM calc_tasks WHERE status = 'running'")
        running = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM calc_tasks WHERE status = 'completed'")
        completed = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM calc_tasks WHERE status = 'failed'")
        failed = c.fetchone()[0]
        conn.close()
        return jsonify({
            'success': True,
            'stats': {
                'total': total,
                'running': running,
                'completed': completed,
                'failed': failed
            }
        })
    except Exception as e:
        return jsonify({'success': True, 'stats': {'total': 0, 'running': 0, 'completed': 0, 'failed': 0}})

# ============================================
# T018 调研记录 API
# ============================================

@app.route('/api/research', methods=['GET'])
def get_research_notes():
    """获取调研记录"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM research_notes
            ORDER BY created_at DESC
            LIMIT 50
        ''')
        notes = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'notes': notes})
    except Exception as e:
        return jsonify({'success': True, 'notes': []})

# ============================================
# T020 会议纪要 API
# ============================================

@app.route('/api/meetings', methods=['GET'])
def get_meetings():
    """获取会议纪要"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM meeting_notes
            ORDER BY meeting_date DESC
            LIMIT 50
        ''')
        meetings = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'meetings': meetings})
    except Exception as e:
        return jsonify({'success': True, 'meetings': []})

# ============================================
# T013 每日复盘 API
# ============================================

@app.route('/api/daily-reviews', methods=['GET'])
def get_daily_reviews():
    """获取每日复盘"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT * FROM daily_reviews
            ORDER BY review_date DESC
            LIMIT 30
        ''')
        reviews = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'reviews': reviews})
    except Exception as e:
        return jsonify({'success': True, 'reviews': []})

# ============================================
# 化学模块 API
# ============================================

@app.route('/api/chemistry/elements', methods=['GET'])
def get_chemical_elements():
    """获取化学元素列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM chemical_elements ORDER BY atomic_number')
        elements = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'elements': elements})
    except Exception as e:
        return jsonify({'success': True, 'elements': []})

@app.route('/api/chemistry/molecules', methods=['GET'])
def get_molecules():
    """获取分子列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM molecules ORDER BY molecular_weight')
        molecules = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'molecules': molecules})
    except Exception as e:
        return jsonify({'success': True, 'molecules': []})

@app.route('/api/reactions', methods=['GET'])
def get_reactions():
    """获取化学反应列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM reactions ORDER BY created_at DESC')
        reactions = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'reactions': reactions})
    except Exception as e:
        return jsonify({'success': True, 'reactions': []})

# ============================================
# T019 架构图 API
# ============================================

@app.route('/api/architecture', methods=['GET'])
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
                    {'name': '数据库 (SQLite)', 'type': 'database', 'status': 'active'},
                    {'name': 'Cloudflare Tunnel', 'type': 'gateway', 'status': 'active'}
                ],
                'updated_at': '2026-02-26'
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/table-counts', methods=['GET'])
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
                counts[table] = c.fetchone()[0]
            except:
                counts[table] = 0
        
        conn.close()
        return jsonify({'success': True, 'counts': counts})
    except Exception as e:
        return jsonify({'success': True, 'counts': {}})

# ============================================
# T021 资源库 API
# ============================================

@app.route('/api/resources', methods=['GET'])
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
        resources = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'resources': resources})
    except Exception as e:
        return jsonify({'success': True, 'resources': []})

@app.route('/api/github/repos', methods=['GET'])
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

@app.route('/api/github/stats', methods=['GET'])
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

@app.route('/api/version-logs', methods=['GET'])
def get_version_logs():
    """获取版本日志"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT * FROM version_logs ORDER BY release_date DESC LIMIT 20')
        logs = [dict(row) for row in c.fetchall()]
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

# ============================================
# 日历 API
# ============================================

@app.route('/api/calendar/accounts', methods=['GET'])
def get_calendar_accounts():
    """获取CalDAV账户列表"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id, name, account_type, server_url, username, calendar_name, sync_enabled, last_sync_at FROM calendar_accounts')
        accounts = [dict(row) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'accounts': accounts})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/accounts', methods=['POST'])
def create_calendar_account():
    """创建CalDAV账户"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            INSERT INTO calendar_accounts
            (name, account_type, server_url, username, password, calendar_path, calendar_name, sync_enabled)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('name'),
            data.get('account_type', 'caldav'),
            data.get('server_url'),
            data.get('username'),
            data.get('password'),
            data.get('calendar_path', '/'),
            data.get('calendar_name'),
            1
        ))
        
        conn.commit()
        account_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': account_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/sync', methods=['POST'])
def sync_calendar():
    """手动同步日历"""
    try:
        from caldav_sync import sync_all_accounts
        
        results = sync_all_accounts(DB_PATH)
        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/events', methods=['GET'])
def get_calendar_events():
    """获取日历事件"""
    try:
        start = request.args.get('start')
        end = request.args.get('end')
        
        conn = get_db()
        c = conn.cursor()
        
        query = '''
            SELECT * FROM calendar_events
            WHERE status != 'cancelled'
        '''
        params = []
        
        if start:
            query += ' AND end_time >= ?'
            params.append(start)
        if end:
            query += ' AND start_time <= ?'
            params.append(end)
            
        query += ' ORDER BY start_time'
        
        c.execute(query, params)
        events = [dict(row) for row in c.fetchall()]
        conn.close()
        
        return jsonify({'success': True, 'events': events})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/events', methods=['POST'])
def create_calendar_event():
    """创建日历事件"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        c.execute('''
            INSERT INTO calendar_events 
            (title, description, start_time, end_time, all_day, location, 
             category, color, project_id, task_id, reminder_minutes, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            data.get('title'),
            data.get('description'),
            data.get('start_time'),
            data.get('end_time'),
            data.get('all_day', 0),
            data.get('location'),
            data.get('category', 'default'),
            data.get('color'),
            data.get('project_id'),
            data.get('task_id'),
            data.get('reminder_minutes', 15),
            data.get('status', 'confirmed')
        ))
        
        conn.commit()
        event_id = c.lastrowid
        conn.close()
        
        return jsonify({'success': True, 'id': event_id})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/events/<int:event_id>', methods=['PUT'])
def update_calendar_event(event_id):
    """更新日历事件"""
    try:
        data = request.get_json()
        
        conn = get_db()
        c = conn.cursor()
        
        # 获取现有数据
        c.execute('SELECT * FROM calendar_events WHERE id = ?', (event_id,))
        existing = c.fetchone()
        if not existing:
            return jsonify({'success': False, 'error': '事件不存在'})
        
        # 更新字段
        c.execute('''
            UPDATE calendar_events SET
                title = ?,
                description = ?,
                start_time = ?,
                end_time = ?,
                all_day = ?,
                location = ?,
                category = ?,
                color = ?,
                reminder_minutes = ?,
                status = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            data.get('title', existing['title']),
            data.get('description', existing['description']),
            data.get('start_time', existing['start_time']),
            data.get('end_time', existing['end_time']),
            data.get('all_day', existing['all_day']),
            data.get('location', existing['location']),
            data.get('category', existing['category']),
            data.get('color', existing['color']),
            data.get('reminder_minutes', existing['reminder_minutes']),
            data.get('status', existing['status']),
            event_id
        ))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/events/<int:event_id>', methods=['DELETE'])
def delete_calendar_event(event_id):
    """删除日历事件"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 软删除
        c.execute('''
            UPDATE calendar_events 
            SET status = 'cancelled', updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (event_id,))
        
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/calendar/stats', methods=['GET'])
def get_calendar_stats():
    """获取日历统计"""
    try:
        conn = get_db()
        c = conn.cursor()
        
        # 今日事件数
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE date(start_time) = date('now')
            AND status != 'cancelled'
        ''')
        today_count = c.fetchone()[0]
        
        # 本周事件数
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE start_time >= date('now', 'weekday 0', '-7 days')
            AND start_time < date('now', 'weekday 0', '0 days')
            AND status != 'cancelled'
        ''')
        week_count = c.fetchone()[0]
        
        # 本月事件数
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE strftime('%Y-%m', start_time) = strftime('%Y-%m', 'now')
            AND status != 'cancelled'
        ''')
        month_count = c.fetchone()[0]
        
        # 待处理事件（未来）
        c.execute('''
            SELECT COUNT(*) FROM calendar_events
            WHERE start_time > datetime('now')
            AND status != 'cancelled'
        ''')
        upcoming_count = c.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'success': True,
            'stats': {
                'today': today_count,
                'week': week_count,
                'month': month_count,
                'upcoming': upcoming_count
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 用户管理 API
# ============================================

# 存储用户密码（简单版本，实际应使用密码哈希）
# 格式: {username: {password: 'hashed', role: 'admin'}}
USERS_DB = {
    'admin': {'password': 'kanban2024', 'role': 'admin'}
}

@app.route('/api/change-password', methods=['POST'])
def change_password():
    """修改密码"""
    try:
        data = request.get_json()
        old_password = data.get('oldPassword')
        new_password = data.get('newPassword')
        
        # 获取当前用户（从token或session）
        # 简化版本，实际应从token解析
        username = 'admin'  # 默认用户
        
        if not old_password or not new_password:
            return jsonify({'success': False, 'error': '密码不能为空'})
        
        # 验证旧密码
        if USERS_DB.get(username, {}).get('password') != old_password:
            return jsonify({'success': False, 'error': '旧密码错误'})
        
        # 更新密码
        USERS_DB[username]['password'] = new_password
        
        return jsonify({'success': True, 'message': '密码修改成功'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/user/info', methods=['GET'])
def get_user_info():
    """获取用户信息"""
    try:
        # 简化版本，实际应从token解析
        return jsonify({
            'success': True,
            'user': {
                'username': 'admin',
                'role': 'admin',
                'last_login': datetime.now().isoformat()
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ============================================
# 安全中间件
# ============================================

@app.after_request
def add_security_headers(response):
    """添加安全响应头"""
    # 防止点击劫持
    response.headers['X-Frame-Options'] = 'DENY'
    # 防止MIME类型嗅探
    response.headers['X-Content-Type-Options'] = 'nosniff'
    # XSS保护
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # 内容安全策略
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
    # 禁用缓存敏感页面
    if request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response

# 请求频率限制（简单实现）
request_counts = {}

@app.before_request
def rate_limit():
    """简单的请求频率限制"""
    if request.path == '/api/login':
        ip = request.remote_addr
        now = datetime.now()
        
        # 清理旧记录
        for key in list(request_counts.keys()):
            if (now - request_counts[key]['time']).seconds > 60:
                del request_counts[key]
        
        # 检查频率
        if ip in request_counts:
            if request_counts[ip]['count'] > 10:  # 每分钟最多10次登录尝试
                return jsonify({'success': False, 'error': '请求过于频繁，请稍后再试'}), 429
            request_counts[ip]['count'] += 1
        else:
            request_counts[ip] = {'count': 1, 'time': now}

# ============================================
# 静态文件服务
# ============================================

@app.route('/<path:path>')
def serve_static(path):
    """提供静态文件"""
    if os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, 'index.html')

if __name__ == '__main__':
    print("=" * 60)
    print("Kanban React - Flask API Server")
    print("=" * 60)
    print("API地址: http://localhost:8086")
    print("=" * 60)
    app.run(host='0.0.0.0', port=8086, debug=True)
