"""Routes: tasks_api - 任务 API + 统计 API + 任务附件"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
from flask import send_file, send_from_directory
from file_indexer import scan_workspace
import os
import json
import re
from datetime import datetime

bp = Blueprint("routes_tasks_api", __name__)
logger = __import__("logging").getLogger(__name__)

# Upload directory config
UPLOAD_DIR = "/opt/kanban-react/backend/uploads"


def _truncate_for_list(value, max_chars=800):
    """Return a safe list-view string while preserving useful context."""
    if value is None:
        return value
    text = str(value)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + f"... [truncated {len(text) - max_chars} chars; use fields=full for complete value]"


def _compact_task_for_list(task):
    """Trim heavy text fields for task-list responses without changing schema."""
    if not isinstance(task, dict):
        return task
    limits = {
        # List cards only need previews; fields=full keeps complete values.
        'description': 240,
        'text_description': 240,
        'notes': 200,
        'execution_log': 240,
        'result_summary': 300,
        'task_summary': 240,
        'acceptance_criteria': 240,
        'review_feedback': 240,
        'remaining_issues': 240,
        'improvement_suggestions': 240,
        'stage_history': 240,
        'user_rules': 200,
        'user_approval_notes': 200,
        'blocked_reason': 160,
        'difficulty_reason': 160,
    }
    out = dict(task)
    for key, max_chars in limits.items():
        if key in out:
            out[key] = _truncate_for_list(out.get(key), max_chars)
    out['_fields'] = 'compact'
    return out

@bp.route('/api/tasks/', methods=['GET'])
@bp.route('/api/tasks', methods=['GET'])
def get_tasks():
    # 添加排序支持
    sort_field = request.args.get('sort_field', 'created_at')
    sort_order = request.args.get('sort_order', 'desc')
    
    # 允许的排序字段
    allowed_sort_fields = ['created_at', 'due_date', 'priority', 'status', 'title']
    if sort_field not in allowed_sort_fields:
        sort_field = 'created_at'
    if sort_order not in ['asc', 'desc']:
        sort_order = 'desc'
    
    # 添加分页支持
    """获取任务列表"""
    status = request.args.get('status', '')
    project_id = request.args.get('project_id', '')

    conn = get_db()
    c = conn.cursor()

    project_status = request.args.get('project_status', '')

    query = '''
        SELECT t.*, p.name as project_name, p.number as project_number, p.status as project_status
        FROM tasks t
        LEFT JOIN projects p ON t.project_id = p.id
        WHERE t.status != 'deleted'
    '''
    params = []

    if status:
        query += ' AND t.status = %s'
        params.append(status)

    if project_id:
        query += ' AND t.project_id = %s'
        params.append(project_id)

    if project_status:
        query += ' AND p.status = %s'
        params.append(project_status)

    # 搜索支持
    search = request.args.get('search', '')
    if search:
        query += ' AND t.title LIKE %s'
        params.append(f'%{search}%')

    # 标签支持
    tags = request.args.get('tags', '')
    if tags:
        for tag in tags.split(','):
            tag = tag.strip()
            if tag:
                query += ' AND t.tags LIKE %s'
                params.append(f'%{tag}%')

    # 日期范围支持
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    if date_from:
        query += ' AND t.created_at >= %s'
        params.append(date_from + ' 00:00:00')
    if date_to:
        query += ' AND t.created_at <= %s'
        params.append(date_to + ' 23:59:59')

    # 快速筛选 (today, this_week, this_month)
    quick_filter = request.args.get('quick_filter', '')
    if quick_filter:
        if quick_filter == 'today':
            query += ' AND (DATE(t.created_at) = CURDATE() OR DATE(t.updated_at) = CURDATE())'
        elif quick_filter == 'this_week':
            query += ' AND (YEARWEEK(t.created_at, 1) = YEARWEEK(CURDATE(), 1) OR YEARWEEK(t.updated_at, 1) = YEARWEEK(CURDATE(), 1))'
        elif quick_filter == 'this_month':
            query += ' AND (YEAR(t.created_at) = YEAR(CURDATE()) AND MONTH(t.created_at) = MONTH(CURDATE()) OR YEAR(t.updated_at) = YEAR(CURDATE()) AND MONTH(t.updated_at) = MONTH(CURDATE()))'

    # 排序与分页
    # 兼容历史前端：仍支持 per_page；新增 limit 别名，避免 /api/tasks?limit=1 被忽略。
    # 原默认 per_page=5000 会导致约 30MB 响应，线上默认降到 50；显式请求最多 1000。
    page = request.args.get('page', 1, type=int) or 1
    requested_per_page = request.args.get('per_page', type=int)
    requested_limit = request.args.get('limit', type=int)
    if requested_limit is not None and requested_per_page is None:
        per_page = requested_limit
    elif requested_per_page is not None:
        per_page = requested_per_page
    else:
        per_page = 50
    page = max(1, page)
    per_page = max(1, min(per_page, 1000))
    offset = (page - 1) * per_page

    # Count uses the same filters without ORDER/LIMIT so clients can page safely.
    count_query = 'SELECT COUNT(*) as total FROM (' + query + ') _tasks_count'
    c.execute(count_query, tuple(params))
    total_row = c.fetchone()
    total = int((total_row or {}).get('total', 0))
    
    query += f' ORDER BY t.{sort_field} {sort_order.upper()} LIMIT {per_page} OFFSET {offset}'

    c.execute(query, tuple(params))
    tasks = [row_to_dict(row, c) for row in c.fetchall()]

    fields = (request.args.get('fields') or request.args.get('view') or 'compact').lower()
    compact = fields not in ['full', 'all', 'raw']
    if compact:
        tasks = [_compact_task_for_list(task) for task in tasks]
    
    # 补充依赖关系（从 task_dependencies 表读取）
    for task in tasks:
        tid = task['id']
        c.execute('SELECT dep_task_id FROM task_dependencies WHERE task_id = %s AND dep_type = "depends_on"', (tid,))
        task['depends_on_list'] = [r['dep_task_id'] for r in c.fetchall()]
        c.execute('SELECT task_id FROM task_dependencies WHERE dep_task_id = %s AND dep_type = "depends_on"', (tid,))
        task['_dependents'] = [r['task_id'] for r in c.fetchall()]
    
    conn.close()

    return jsonify({
        'success': True,
        'tasks': tasks,
        'fields': 'compact' if compact else 'full',
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'has_more': (offset + len(tasks)) < total,
        }
    })

@bp.route('/api/tasks/stats', methods=['GET'])
def get_tasks_stats():
    """获取任务统计"""
    conn = get_db()
    c = conn.cursor()
    
    c.execute("SELECT status, COUNT(*) as count FROM tasks WHERE status != 'deleted' GROUP BY status")
    
    stats = {}
    for row in c.fetchall():
        row_dict = dict(row)
        stats[row_dict['status']] = row_dict['count']
    
    for s in ['todo', 'pending', 'in_progress', 'pending_review', 'completed', 'failed', 'failed_retryable', 'cancelled', 'archived']:
        if s not in stats:
            stats[s] = 0
    
    conn.close()
    return jsonify({"success": True, "stats": stats})

@bp.route('/api/tasks', methods=['POST'])
def create_task():
    """创建任务"""
    data = request.get_json()
    title = data.get('title', '').strip()
    description = data.get('description', '')
    project_id = data.get('project_id')
    priority = data.get('priority', 'medium')

    if not title:
        return jsonify({'success': False, 'error': '任务标题不能为空'}), 400

    if not project_id:
        return jsonify({'success': False, 'error': '所属项目不能为空'}), 400

    conn = get_db()
    c = conn.cursor()

    # 生成任务编号
    c.execute("SELECT COUNT(*) FROM tasks")
    count = list(c.fetchone().values())[0] + 1
    number = f"T{count:03d}"

    c.execute('''
        INSERT INTO tasks (number, title, description, project_id, status, priority, created_at, updated_at)
        VALUES (%s, %s, %s, %s, 'todo', %s, NOW(), NOW())
    ''', (number, title, description, project_id, priority))

    task_id = c.lastrowid
    conn.commit()

    # Fetch the created task for WebSocket emit
    c.execute('SELECT id, number, title, description, project_id, status, priority, assignee, due_date, tags, created_at, updated_at FROM tasks WHERE id = %s', (task_id,))
    task_data = c.fetchone()
    conn.close()

    # WebSocket: emit task_created
    if project_id:
        try:
            from websocket.index import get_socketio_instance
            socketio = get_socketio_instance()
            if socketio:
                task_dict = {
                    'id': task_data['id'],
                    'number': task_data['number'],
                    'title': task_data['title'],
                    'description': task_data['description'],
                    'json_description': (lambda d: (
                        (lambda p: p if isinstance(p, dict) else None)(
                            __import__('json').loads(d)
                        ) if d and d.startswith('{') else None
                    ))(task_data.get('description', '')),
                    'text_description': (lambda d: (
                        (lambda p: (
                            p.get('context', p.get('goal', '')) or d
                        ))(__import__('json').loads(d))
                    ) if d and d.startswith('{') else d or '')(task_data.get('description', '')),
                    'project_id': task_data['project_id'],
                    'status': task_data['status'],
                    'priority': task_data['priority'],
                    'assignee': task_data.get('assignee'),
                    'due_date': str(task_data.get('due_date', '')) if task_data.get('due_date') else None,
                    'tags': task_data.get('tags'),
                    'created_at': str(task_data.get('created_at', '')),
                    'updated_at': str(task_data.get('updated_at', '')),
                }
                socketio.emit('task_created', {
                    'task': task_dict,
                    'project_id': project_id
                }, room=f'project:{project_id}')
                logger.info(f"📡 WebSocket emit: task_created (task_id={task_id}, project_id={project_id})")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket emit failed (task_created): {e}")

    return jsonify({'success': True, 'task_id': task_id, 'number': number})

@bp.route('/api/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """更新任务"""
    data = request.get_json()

    allowed_fields = ['title', 'description', 'status', 'priority', 'project_id', 'due_date', 'tags', 'result_summary', 'result_tag', 'notes', 'requires_audit',
                     'conclusion_type', 'conclusion_passed', 'conclusion_execute', 'conclusion_audit_content']
    updates = {k: v for k, v in data.items() if k in allowed_fields}

    if not updates:
        return jsonify({'success': False, 'error': '没有要更新的字段'}), 400
    
    # 当用户添加备注时，自动标记为需要审计
    if 'notes' in updates and updates['notes']:
        updates['requires_audit'] = 1
        # 同步插入审计记录
        try:
            c.execute('SELECT title, description FROM tasks WHERE id = %s', (task_id,))
            _task = c.fetchone()
            if _task:
                c.execute('''
                    INSERT INTO manual_review_tasks 
                    (original_task_id, review_type, title, description, priority, source, status, created_at, updated_at)
                    VALUES (%s, 'user_note', %s, %s, 'medium', 'user_feedback', 'pending', NOW(), NOW())
                ''', (task_id, _task['title'], updates['notes'][:500]))
        except Exception:
            pass

    conn = get_db()
    c = conn.cursor()

    # Fetch original task state for WebSocket changes diff
    c.execute('SELECT * FROM tasks WHERE id = %s', (task_id,))
    original_task = c.fetchone()
    original_project_id = original_task['project_id'] if original_task else None

    set_clause = ', '.join([f"{k} = %s" for k in updates.keys()])
    set_clause += ", updated_at = NOW()"
    values = list(updates.values()) + [task_id]

    c.execute(f'UPDATE tasks SET {set_clause} WHERE id = %s', values)
    conn.commit()

    # Fetch updated task for WebSocket emit
    c.execute('SELECT id, number, title, description, project_id, status, priority, assignee, due_date, tags, created_at, updated_at FROM tasks WHERE id = %s', (task_id,))
    updated_task = c.fetchone()
    conn.close()

    # Build changes dict
    changes_dict = {k: {'old': str(original_task.get(k)) if original_task and k in original_task else None, 'new': str(v)} for k, v in updates.items()}

    # WebSocket: emit task_updated
    emit_project_id = updates.get('project_id', original_project_id)
    if emit_project_id:
        try:
            from websocket.index import get_socketio_instance
            socketio = get_socketio_instance()
            if socketio:
                task_dict = {
                    'id': updated_task['id'],
                    'number': updated_task['number'],
                    'title': updated_task['title'],
                    'description': updated_task['description'],
                    'project_id': updated_task['project_id'],
                    'status': updated_task['status'],
                    'priority': updated_task['priority'],
                    'assignee': updated_task.get('assignee'),
                    'due_date': str(updated_task.get('due_date', '')) if updated_task.get('due_date') else None,
                    'tags': updated_task.get('tags'),
                    'created_at': str(updated_task.get('created_at', '')),
                    'updated_at': str(updated_task.get('updated_at', '')),
                } if updated_task else None
                socketio.emit('task_updated', {
                    'task': task_dict,
                    'changes': changes_dict,
                    'project_id': emit_project_id
                }, room=f'project:{emit_project_id}')
                logger.info(f"📡 WebSocket emit: task_updated (task_id={task_id}, project_id={emit_project_id})")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket emit failed (task_updated): {e}")

    return jsonify({'success': True})

@bp.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """删除任务"""
    conn = get_db()
    c = conn.cursor()
    
    # Fetch task project_id before soft delete
    c.execute('SELECT project_id FROM tasks WHERE id = %s', (task_id,))
    row = c.fetchone()
    project_id = row['project_id'] if row else None

    c.execute('UPDATE tasks SET status = %s WHERE id = %s', ('deleted', task_id))
    conn.commit()
    conn.close()

    # WebSocket: emit task_deleted
    if project_id:
        try:
            from websocket.index import get_socketio_instance
            socketio = get_socketio_instance()
            if socketio:
                socketio.emit('task_deleted', {
                    'task_id': task_id,
                    'project_id': project_id
                }, room=f'project:{project_id}')
                logger.info(f"📡 WebSocket emit: task_deleted (task_id={task_id}, project_id={project_id})")
        except Exception as e:
            logger.warning(f"⚠️ WebSocket emit failed (task_deleted): {e}")

    return jsonify({'success': True})

@bp.route('/api/tasks/<int:task_id>/review', methods=['POST'])
def review_task(task_id):
    """审核任务 - 通过/驳回/要求修改/跳过"""
    data = request.get_json() or {}
    action = data.get('action')
    feedback = data.get('feedback', '')
    created_by = data.get('created_by', 'user')
    
    if action not in ['approve', 'reject', 'feedback', 'skip']:
        return jsonify({'success': False, 'error': '无效的操作类型'}), 400
    
    # 状态映射
    status_map = {
        'approve': 'completed',
        'reject': 'pending',
        'feedback': 'review_feedback',
        'skip': 'pending_review'
    }
    new_status = status_map[action]
    
    conn = get_db()
    c = conn.cursor()
    
    # 检查任务是否存在
    c.execute('SELECT status, review_round FROM tasks WHERE id = %s', (task_id,))
    task = c.fetchone()
    if not task:
        conn.close()
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 获取当前轮次
    current_round = task.get('review_round', 0) or 0
    new_round = current_round + 1 if action == 'feedback' else current_round
    
    # 更新任务状态
    if action == 'feedback':
        c.execute('''UPDATE tasks 
                     SET status = %s, 
                         review_round = %s,
                         review_feedback = %s,
                         review_status = %s,
                         updated_at = NOW() 
                     WHERE id = %s''', 
                  (new_status, new_round, feedback, 'awaiting_revision', task_id))
    else:
        c.execute('''UPDATE tasks 
                     SET status = %s,
                         review_status = %s,
                         updated_at = NOW() 
                     WHERE id = %s''', 
                  (new_status, action, task_id))
    
    # 记录审核历史
    c.execute('''INSERT INTO task_review_history 
                 (task_id, round_number, action, feedback, created_by, created_at)
                 VALUES (%s, %s, %s, %s, %s, NOW())''',
              (task_id, new_round if action == 'feedback' else current_round, 
               action, feedback, created_by))
    
    conn.commit()
    
    # 获取历史记录
    c.execute('''SELECT id, round_number, action, feedback, created_by, created_at 
                 FROM task_review_history 
                 WHERE task_id = %s 
                 ORDER BY created_at DESC''', (task_id,))
    history = []
    for row in c.fetchall():
        history.append({
            'id': row['id'],
            'round_number': row['round_number'],
            'action': row['action'],
            'feedback': row['feedback'],
            'created_by': row['created_by'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        })
    
    conn.close()
    
    action_labels = {'approve': '通过', 'reject': '驳回', 'feedback': '要求修改', 'skip': '跳过'}
    return jsonify({
        'success': True, 
        'message': f'任务已{action_labels[action]}',
        'task_id': task_id,
        'new_status': new_status,
        'review_round': new_round,
        'history': history
    })

@bp.route('/api/tasks/<int:task_id>/review-history', methods=['GET'])
def get_review_history(task_id):
    """获取任务审核历史"""
    conn = get_db()
    c = conn.cursor()
    
    # 检查任务是否存在
    c.execute('SELECT id FROM tasks WHERE id = %s', (task_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '任务不存在'}), 404
    
    # 获取历史记录
    c.execute('''SELECT id, round_number, action, feedback, created_by, created_at 
                 FROM task_review_history 
                 WHERE task_id = %s 
                 ORDER BY created_at DESC''', (task_id,))
    history = []
    for row in c.fetchall():
        history.append({
            'id': row['id'],
            'round_number': row['round_number'],
            'action': row['action'],
            'feedback': row['feedback'],
            'created_by': row['created_by'],
            'created_at': row['created_at'].isoformat() if row['created_at'] else None
        })
    
    conn.close()
    
    return jsonify({
        'success': True,
        'task_id': task_id,
        'history': history,
        'total': len(history)
    })

@bp.route('/api/tasks/bulk-review', methods=['POST'])
def bulk_review_tasks():
    """批量审核任务"""
    data = request.get_json() or {}
    task_ids = data.get('task_ids', [])
    action = data.get('action')
    
    if not task_ids or action not in ['approve', 'reject']:
        return jsonify({'success': False, 'error': '无效的请求参数'}), 400
    
    status_map = {
        'approve': 'completed',
        'reject': 'pending'
    }
    new_status = status_map[action]
    
    conn = get_db()
    c = conn.cursor()
    
    updated = 0
    failed = 0
    
    for task_id in task_ids:
        try:
            c.execute('UPDATE tasks SET status = %s, updated_at = NOW() WHERE id = %s AND status = "pending_review"', 
                      (new_status, task_id))
            if c.rowcount > 0:
                updated += 1
            else:
                failed += 1
        except Exception:
            failed += 1
    
    conn.commit()
    conn.close()
    
    action_labels = {'approve': '通过', 'reject': '驳回'}
    return jsonify({
        'success': True,
        'message': f'批量{action_labels[action]}完成',
        'updated': updated,
        'failed': failed
    })

@bp.route('/api/tasks/<int:task_id>/history', methods=['GET'])
def get_task_history(task_id):
    """获取任务执行历史和齿轮执行详情"""
    conn = get_db()
    c = conn.cursor()

    # 检查任务是否存在
    c.execute('SELECT id FROM tasks WHERE id = %s AND status != "deleted"', (task_id,))
    if not c.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    # 获取执行历史（从task_history表或类似表）
    # 如果没有专门的表，创建模拟数据
    try:
        c.execute('''
            SELECT id, task_id, action, details, created_at, performed_by
            FROM task_history
            WHERE task_id = %s
            ORDER BY created_at DESC
        ''', (task_id,))
        history = [row_to_dict(row, c) for row in c.fetchall()]
    except:
        history = []

    # 获取齿轮执行详情
    try:
        c.execute('''
            SELECT id, task_id, gear_name, status, output, started_at, completed_at
            FROM gear_executions
            WHERE task_id = %s
            ORDER BY started_at DESC
        ''', (task_id,))
        gear_executions = [row_to_dict(row, c) for row in c.fetchall()]
    except:
        gear_executions = []

    conn.close()

    # 如果没有历史记录，生成一些模拟数据
    if not history and not gear_executions:
        from datetime import timedelta
        now = datetime.now()
        history = [
            {
                'id': 1,
                'task_id': task_id,
                'action': '任务创建',
                'details': '系统自动创建任务',
                'created_at': (now - timedelta(days=2)).isoformat(),
                'performed_by': 'system'
            },
            {
                'id': 2,
                'task_id': task_id,
                'action': '状态更新',
                'details': '任务状态更新为进行中',
                'created_at': (now - timedelta(days=1)).isoformat(),
                'performed_by': 'admin'
            }
        ]

    return jsonify({
        'success': True,
        'history': history,
        'gear_executions': gear_executions
    })

@bp.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@bp.route('/api/projects/<int:project_id>/task', methods=['GET'])
def get_project_tasks(project_id):
    """获取项目关联的任务列表"""
    with get_db() as conn:
        c = conn.cursor()

        # 检查项目是否存在
        c.execute('SELECT id FROM projects WHERE id = %s AND status != "deleted"', (project_id,))
        if not c.fetchone():
            return jsonify({'success': False, 'error': '项目不存在'}), 404

        # 获取项目任务
        c.execute('''
            SELECT id, title, status, priority, created_at, updated_at, task_type, description, details, result_summary, result_tag, task_summary, project_id, (SELECT name FROM projects WHERE projects.id = tasks.project_id) as project_name, (SELECT number FROM projects WHERE projects.id = tasks.project_id) as project_number
            FROM tasks
            WHERE project_id = %s AND status != 'deleted'
            ORDER BY 
                CASE status
                    WHEN 'progress' THEN 1
                    WHEN 'todo' THEN 2
                    WHEN 'done' THEN 3
                    ELSE 4
                END,
                created_at DESC
        ''', (project_id,))

        tasks = [row_to_dict(row, c) for row in c.fetchall()]

    return jsonify({
        'success': True,
        'tasks': tasks,
        'count': len(tasks)
    })

@bp.route('/api/stats/', methods=['GET'])
@bp.route('/api/stats', methods=['GET'])
def get_stats():
    """获取统计数据"""
    conn = get_db()
    c = conn.cursor()

    # 项目统计
    c.execute('SELECT COUNT(*) FROM projects WHERE status != "deleted"')
    project_count = list(c.fetchone().values())[0]

    # 任务统计：兼容历史 done/progress/todo 与当前 completed/in_progress/pending 状态。
    c.execute('''
        SELECT status, COUNT(*) AS count
        FROM tasks
        WHERE status != "deleted"
        GROUP BY status
    ''')
    task_status_counts = {}
    for row in c.fetchall():
        row_dict = row_to_dict(row, c)
        task_status_counts[row_dict['status']] = int(row_dict['count'])
    task_count = sum(task_status_counts.values())
    completed_count = task_status_counts.get('completed', 0) + task_status_counts.get('done', 0)
    in_progress_count = task_status_counts.get('in_progress', 0) + task_status_counts.get('progress', 0)
    todo_count = sum(task_status_counts.get(s, 0) for s in [
        'pending', 'todo', 'pending_review', 'pending_actor_review', 'waiting_for_user', 'needs_human'
    ])

    # 股票统计
    c.execute('SELECT COUNT(*) FROM stocks')
    stock_count = list(c.fetchone().values())[0]

    conn.close()

    return jsonify({
        'success': True,
        'stats': {
            'projects': project_count,
            'tasks': {
                'total': task_count,
                'done': completed_count,
                'progress': in_progress_count,
                'todo': todo_count,
                'by_status': task_status_counts
            },
            'stocks': stock_count
        }
    })

@bp.route('/api/files/index', methods=['GET'])
def get_file_index():
    """获取本地workspace文件索引"""
    try:
        result = scan_workspace()
        return jsonify({'success': True, **result})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/files/content/<path:filepath>', methods=['GET'])
def get_file_content(filepath):
    """获取文件内容"""
    try:
        workspace_path = '/opt/kanban-react/Files'
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

@bp.route('/api/tasks/<int:task_id>/attachments', methods=['GET'])
def get_task_attachments(task_id):
    """获取任务附件列表"""
    try:
        conn = get_db()
        cursor = conn.cursor()
        
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

@bp.route('/api/tasks/<int:task_id>/attachments/upload', methods=['POST'])
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
        file_path = os.path.join(UPLOAD_DIR, "docs", safe_filename)
        
        # 保存文件
        file.save(file_path)
        file_size = os.path.getsize(file_path)
        file_type = ext.lstrip('.').lower() if ext else 'unknown'
        
        # 获取文件URL
        url = f"/uploads/docs/{safe_filename}"
        
        # 写入数据库
        conn = get_db()
        cursor = conn.cursor()
        
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
        logger.error(f"Failed to upload attachment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/tasks/<int:task_id>/attachments/edit', methods=['POST'])
def edit_task_attachment(task_id):
    """编辑任务附件内容"""
    try:
        data = request.json
        filename = data.get('filename')
        content = data.get('content')
        
        if not filename or content is None:
            return jsonify({'success': False, 'error': 'Missing filename or content'}), 400
        
        # 查找附件记录
        conn = get_db()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT url FROM attachments
            WHERE entity_type = 'task' AND entity_id = %s AND filename = %s
        """, (task_id, filename))
        
        attachment = cursor.fetchone()
        if not attachment:
            return jsonify({'success': False, 'error': 'Attachment not found'}), 404
        
        # 提取文件路径
        file_path = attachment['url'].replace('/uploads/', '/opt/kanban-react/frontend/public/uploads/')
        
        # 确保目录存在
        file_dir = os.path.dirname(file_path)
        if not os.path.exists(file_dir):
            os.makedirs(file_dir, exist_ok=True)
        
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
        logger.error(f"Failed to edit attachment: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500



@bp.route('/api/tasks/throughput', methods=['GET'])
def get_task_throughput():
    """获取任务吞吐量统计"""
    try:
        days = request.args.get('days', 7, type=int)
        conn = get_db()
        c = conn.cursor()
        from datetime import datetime, timedelta
        labels = []
        completed = []
        created = []
        for i in range(days - 1, -1, -1):
            day = datetime.now() - timedelta(days=i)
            labels.append(day.strftime('%m-%d'))
            day_start = day.strftime('%Y-%m-%d 00:00:00')
            day_end = day.strftime('%Y-%m-%d 23:59:59')
            c.execute("SELECT COUNT(*) FROM tasks WHERE created_at >= %s AND created_at <= %s", (day_start, day_end))
            created.append(list(c.fetchone().values())[0])
            c.execute("SELECT COUNT(*) FROM tasks WHERE updated_at >= %s AND updated_at <= %s AND status = 'completed'", (day_start, day_end))
            completed.append(list(c.fetchone().values())[0])
        conn.close()
        return jsonify({'success': True, 'data': {'labels': labels, 'completed': completed, 'created': created}})
    except Exception as e:
        logger.error('throughput error: ' + str(e))
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/tasks/quality', methods=['GET'])
def get_task_quality():
    """获取任务质量数据（最近50个完成任务）"""
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute('''
            SELECT t.id, t.number, t.title, t.status, t.task_summary, t.result_tag, t.execution_log, t.created_at, t.updated_at, p.name as project_name
            FROM tasks t
            LEFT JOIN projects p ON t.project_id = p.id
            WHERE t.status = 'completed'
            ORDER BY t.updated_at DESC
            LIMIT 50
        ''')
        tasks = [row_to_dict(row, c) for row in c.fetchall()]
        conn.close()
        return jsonify({'success': True, 'tasks': tasks})
    except Exception as e:
        logger.error(f'Failed to get task quality: {e}')
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/tasks/<int:task_id>/dependencies', methods=['GET'])
def get_task_dependencies(task_id):
    """获取任务依赖关系（前置任务和后续任务）"""
    conn = get_db()
    c = conn.cursor()

    # Check task exists
    c.execute('SELECT id, title, description FROM tasks WHERE id = %s AND (status IS NULL OR status != "deleted")', (task_id,))
    task = c.fetchone()
    if not task:
        conn.close()
        return jsonify({'success': False, 'error': '任务不存在'}), 404

    description = task.get('description', '') or ''
    prereq_ids = set()

    # Helper: extract task IDs from text
    def extract_task_ids(text):
        ids = set()
        if not text:
            return ids
        # Match patterns: #12345, [12345], task ID: 12345, 任务ID：12345
        patterns = [
            r'(?:task|id|任务|ID)\s*[:：]?\s*#?\s*(\d{4,7})',
            r'[##\[]\s*(\d{4,7})\s*[\]#]?'
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, re.IGNORECASE):
                try:
                    pid = int(m.group(1))
                    if pid != task_id:
                        ids.add(pid)
                except:
                    pass
        return ids

    # Parse description JSON
    if description.startswith('{'):
        try:
            desc_obj = json.loads(description)
            for field in ['depends_on', 'input', 'sub_tasks', 'tasks']:
                field_val = desc_obj.get(field, '') or ''
                if isinstance(field_val, str):
                    prereq_ids.update(extract_task_ids(field_val))
                elif isinstance(field_val, list):
                    for item in field_val:
                        if isinstance(item, str):
                            prereq_ids.update(extract_task_ids(item))
            # Check steps
            steps = desc_obj.get('steps', []) or []
            if isinstance(steps, list):
                for step in steps:
                    if isinstance(step, str):
                        prereq_ids.update(extract_task_ids(step))
        except (json.JSONDecodeError, Exception):
            pass

    # Also scan raw description
    prereq_ids.update(extract_task_ids(description))

    # Query prerequisite tasks
    prerequisites = []
    if prereq_ids:
        id_list = list(prereq_ids)
        placeholders = ','.join(['%s'] * len(id_list))
        c.execute('SELECT id, title, status FROM tasks WHERE id IN (' + placeholders + ') AND (status IS NULL OR status != "deleted")', id_list)
        prerequisites = [{'id': r['id'], 'title': r['title'], 'status': r.get('status', 'unknown')} for r in c.fetchall()]

    # Query subsequent tasks - scan all descriptions for references to this task_id
    task_id_str = str(task_id)
    c.execute('SELECT id, title, description FROM tasks WHERE (status IS NULL OR status != "deleted")')
    all_rows = c.fetchall()

    subsequent_ids = []
    for r in all_rows:
        if r['id'] == task_id:
            continue
        desc = r.get('description', '') or ''
        refs_in_desc = extract_task_ids(desc)
        if task_id in refs_in_desc:
            subsequent_ids.append(r['id'])

    subsequents = []
    if subsequent_ids:
        placeholders = ','.join(['%s'] * len(subsequent_ids))
        c.execute('SELECT id, title, status FROM tasks WHERE id IN (' + placeholders + ')', subsequent_ids)
        subsequents = [{'id': r['id'], 'title': r['title'], 'status': r.get('status', 'unknown')} for r in c.fetchall()]

    conn.close()

    return jsonify({
        'success': True,
        'dependencies': {
            'prerequisites': prerequisites,
            'subsequents': subsequents
        }
    })


@bp.route('/api/tasks/depended_by', methods=['GET'])
def get_depended_by():
    """返回每个任务的依赖它的任务列表"""
    task_id = request.args.get('task_id', type=int)
    conn = get_db()
    c = conn.cursor()
    if task_id:
        c.execute('SELECT id, title FROM tasks WHERE depends_on = %s AND deleted_at IS NULL', (task_id,))
    else:
        c.execute('SELECT id, title, depends_on FROM tasks WHERE depends_on IS NOT NULL AND deleted_at IS NULL')
    rows = [row_to_dict(r, c) for r in c.fetchall()]
    conn.close()
    return jsonify({'success': True, 'dependents': rows})
