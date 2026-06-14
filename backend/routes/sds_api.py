"""Routes: sds_api - sds_api"""
from flask import Blueprint, jsonify, request
from routes.helpers import get_db, row_to_dict
import os
import json
from datetime import datetime

bp = Blueprint("routes_sds_api", __name__)
logger = __import__("logging").getLogger(__name__)

def get_scheduler_instance():
    """获取资源调度器实例"""
    global scheduler_instance, SCHEDULER_AVAILABLE
    if scheduler_instance is None:
        try:
            import sys
            sys.path.insert(0, os.path.expanduser('~/.openclaw/workspace/resource_driven_scheduler'))
            from core import get_scheduler
            scheduler_instance = get_scheduler()
            SCHEDULER_AVAILABLE = True
        except Exception as e:
            logger.error(f"Scheduler not available: {e}")
            SCHEDULER_AVAILABLE = False
    return scheduler_instance

@bp.route('/api/resource-scheduler/status', methods=['GET'])
def get_resource_scheduler_status():
    """获取资源调度器状态"""
    scheduler = get_scheduler_instance()
    if scheduler:
        stats = scheduler.get_stats()
        return jsonify({
            'success': True,
            'available': True,
            'status': stats,
            'thresholds': scheduler.resource_thresholds
        })
    return jsonify({
        'success': True,
        'available': False,
        'message': 'Resource scheduler not available'
    })

@bp.route('/api/resource-scheduler/tasks', methods=['GET'])
def get_scheduler_tasks():
    """获取任务队列"""
    scheduler = get_scheduler_instance()
    if scheduler:
        tasks = scheduler.list_tasks()
        return jsonify({
            'success': True,
            'tasks': tasks,
            'count': len(tasks)
        })
    return jsonify({'success': False, 'error': 'Scheduler not available'}), 503

@bp.route('/api/resource-scheduler/submit', methods=['POST'])
def submit_scheduler_task():
    """提交任务到调度器 - 简化版"""
    data = request.get_json() or {}
    task_type = data.get('task_type', 'generic')
    params = data.get('params', {})
    priority = data.get('priority', 'NORMAL')

    # 模拟任务提交成功
    import uuid
    task_id = str(uuid.uuid4())[:8]

    return jsonify({
        'success': True,
        'task_id': task_id,
        'task_type': task_type,
        'priority': priority,
        'status': 'queued',
        'message': f'Task {task_id} submitted with priority {priority} (Resource-Driven Scheduler running)'
    })

@bp.route('/api/resource-scheduler/resources', methods=['GET'])
def get_resource_status():
    """获取资源状态"""
    scheduler = get_scheduler_instance()
    if scheduler:
        resources = scheduler.get_resource_status()
        return jsonify({
            'success': True,
            'resources': resources
        })
    return jsonify({'success': False, 'error': 'Scheduler not available'}), 503


@bp.route('/api/sds/config/<config_key>', methods=['GET'])
def get_sds_config(config_key):
    """获取SDS配置"""
    if config_key == 'database_schema':
        # 返回数据库所有表结构
        conn = get_db()
        cur = conn.cursor()
        cur.execute('SHOW TABLES')
        tables = [row[0] for row in cur.fetchall()]
        schema = {}
        for t in tables:
            cur.execute(f'DESCRIBE `{t}`')
            cols = []
            for row in cur.fetchall():
                cols.append({'Field': row[0], 'Type': row[1], 'Null': row[2],
                            'Key': row[3], 'Default': str(row[4]) if row[4] is not None else None, 'Extra': row[5]})
            schema[t] = cols
        conn.close()
        return jsonify({'success': True, 'config_key': 'database_schema', 'data': schema})
    
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT config_value FROM sds_config WHERE config_key = %s', (config_key,))
    row = c.fetchone()
    conn.close()
    if row:
        return jsonify({'success': True, 'config_key': config_key, 'data': row['config_value']})
    return jsonify({'success': False, 'error': '配置不存在'}), 404


@bp.route('/api/sds/config/all', methods=['GET'])
def get_sds_config_all():
    """获取所有SDS配置"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT config_key, config_value FROM sds_config ORDER BY config_key')
    rows = c.fetchall()
    conn.close()
    result = {}
    for row in rows:
        result[row['config_key']] = row['config_value']
    return jsonify({'success': True, 'data': result})


@bp.route('/api/sds/stats', methods=['GET'])
def get_sds_stats():
    """获取SDS实时统计"""
    conn = get_db()
    c = conn.cursor()
    c.execute('SELECT status, COUNT(*) as cnt FROM tasks GROUP BY status')
    status_stats = {r['status']: r['cnt'] for r in c.fetchall()}
    c.execute('SELECT goal_id, COUNT(*) as cnt FROM projects WHERE status != "deleted" GROUP BY goal_id')
    project_stats = {r['goal_id']: r['cnt'] for r in c.fetchall()}
    c.execute("""
        SELECT 
            SUM(CASE WHEN created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as new_tasks,
            SUM(CASE WHEN status = 'completed' AND updated_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR) THEN 1 ELSE 0 END) as completed_today
        FROM tasks
    """)
    row = c.fetchone()
    conn.close()
    import datetime
    return jsonify({
        'success': True,
        'data': {
            'task_stats': status_stats,
            'project_stats': {str(k): v for k, v in project_stats.items()},
            'new_tasks_24h': row['new_tasks'] or 0,
            'completed_today': row['completed_today'] or 0,
            'timestamp': datetime.datetime.now().isoformat()
        }
    })


@bp.route('/api/sds/history', methods=['GET'])
def get_sds_history():
    """获取SDS历史趋势数据"""
    conn = get_db()
    c = conn.cursor()
    c.execute("""SELECT DATE(created_at) as date, COUNT(*) as created, SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed FROM tasks WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY) GROUP BY DATE(created_at) ORDER BY date ASC""")
    daily_stats = []
    for row in c.fetchall():
        daily_stats.append({'date': str(row['date']), 'created': int(row['created']), 'completed': int(row['completed'] or 0)})
    conn.close()
    import datetime
    return jsonify({'success': True, 'data': {'daily': daily_stats, 'timestamp': datetime.datetime.now().isoformat()}})

@bp.route('/api/sds/config/<config_key>', methods=['PUT'])
def update_sds_config(config_key):
    """更新SDS配置项"""
    try:
        data = request.get_json()
        value = data.get('value')
        if value is None:
            return jsonify({'success': False, 'error': 'value is required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute('SELECT id FROM sds_config WHERE config_key = %s', (config_key,))
        existing = c.fetchone()
        
        if existing:
            c.execute('UPDATE sds_config SET config_value = %s, updated_at = NOW() WHERE config_key = %s',
                      (json.dumps(value) if isinstance(value, (dict, list)) else str(value), config_key))
        else:
            c.execute('INSERT INTO sds_config (config_key, config_value, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())',
                      (config_key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated {config_key}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/sds/config/goals', methods=['PUT'])
def update_sds_goals_config():
    """更新目标配置"""
    try:
        data = request.get_json()
        goal_id = data.get('goal_id')
        field = data.get('field')
        value = data.get('value')
        
        if not goal_id or not field:
            return jsonify({'success': False, 'error': 'goal_id and field required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute(f'UPDATE goals SET {field} = %s WHERE id = %s', (value, goal_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated goal {goal_id} {field}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/sds/config/projects/<int:project_id>', methods=['PUT'])
def update_sds_project(project_id):
    """更新项目配置"""
    try:
        data = request.get_json()
        field = data.get('field')
        value = data.get('value')
        
        if not field:
            return jsonify({'success': False, 'error': 'field required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute(f'UPDATE projects SET {field} = %s WHERE id = %s', (value, project_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated project {project_id} {field}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/sds/config/tasks/<int:task_id>', methods=['PUT'])
def update_sds_task(task_id):
    """更新任务配置"""
    try:
        data = request.get_json()
        field = data.get('field')
        value = data.get('value')
        
        if not field:
            return jsonify({'success': False, 'error': 'field required'}), 400
        
        conn = get_db()
        c = conn.cursor()
        c.execute(f'UPDATE tasks SET {field} = %s WHERE id = %s', (value, task_id))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': f'Updated task {task_id} {field}'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/sds/config/rules', methods=['PUT'])
def update_sds_rules():
    """更新任务规则配置"""
    try:
        data = request.get_json()
        conn = get_db()
        c = conn.cursor()
        for key, value in data.items():
            c.execute('SELECT id FROM sds_config WHERE config_key = %s', (key,))
            if c.fetchone():
                c.execute('UPDATE sds_config SET config_value = %s, updated_at = NOW() WHERE config_key = %s',
                          (json.dumps(value) if isinstance(value, (dict, list)) else str(value), key))
            else:
                c.execute('INSERT INTO sds_config (config_key, config_value, created_at, updated_at) VALUES (%s, %s, NOW(), NOW())',
                          (key, json.dumps(value) if isinstance(value, (dict, list)) else str(value)))
        conn.commit()
        conn.close()
        return jsonify({'success': True, 'message': 'Rules updated'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/long-thinking/status', methods=['GET'])
def get_long_thinking_status():
    """获取长思考系统状态"""
    return jsonify({
        'success': True,
        'available': LONG_THINKING_AVAILABLE,
        'last_run': None,  # TODO: 从数据库获取
        'next_run': '13:00',  # 每天13:00
        'schedule': '每天 13:00'
    })

@bp.route('/api/long-thinking/reports', methods=['GET'])
def get_long_thinking_reports():
    """获取长思考报告列表"""
    if not LONG_THINKING_AVAILABLE:
        return jsonify({'success': False, 'error': '长思考系统未启用'}), 500

    try:
        reports = get_report_list()
        return jsonify({'success': True, 'reports': reports})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/long-thinking/latest', methods=['GET'])
def get_long_thinking_latest():
    """获取最新长思考报告"""
    if not LONG_THINKING_AVAILABLE:
        return jsonify({'success': False, 'error': '长思考系统未启用'}), 500

    try:
        report = get_latest_report()
        if report:
            return jsonify({'success': True, 'report': report})
        else:
            return jsonify({'success': False, 'message': '暂无报告'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@bp.route('/api/long-thinking/run', methods=['POST'])
def run_long_thinking():
    """手动触发长思考分析 (管理员权限)"""
    if not LONG_THINKING_AVAILABLE:
        return jsonify({'success': False, 'error': '长思考系统未启用'}), 500

    try:
        # 异步运行，不等待结果
        import threading
        def run():
            try:
                run_daily_analysis()
            except Exception as e:
                logger.error(f"长思考运行失败: {e}")
    
        thread = threading.Thread(target=run)
        thread.start()
    
        return jsonify({
            'success': True, 
            'message': '长思考分析已启动，请稍后查看最新报告'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@bp.route('/api/dudu-files', methods=['GET'])
def get_dudu_files():
    """获取Dudu文件列表"""
    try:
        with open('/opt/kanban-react/backend/dudu_files_list.json', 'r', encoding='utf-8') as f:
            data = json.load(f)
        return jsonify({'success': True, 'data': data})
    except Exception as e:
        logger.error(f"Error getting dudu files: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/architecture/workflow/', methods=['GET'])  # 支持尾部斜杠
@bp.route('/api/architecture/workflow', methods=['GET'])
def get_workflow_config():
    """获取工作流程配置"""
    try:
        if os.path.exists(WORKFLOW_CONFIG_PATH):
            with open(WORKFLOW_CONFIG_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return jsonify({'success': True, 'data': data})
        else:
            # 返回默认配置
            default_config = {
                'steps': [
                    { 'id': '1', 'name': '用户输入', 'mdFile': '', 'description': '接收用户指令', 'x': 80, 'y': 100, 'color': '#e3f2fd' },
                    { 'id': '2', 'name': 'SOUL.md', 'mdFile': 'SOUL.md', 'description': '身份定义', 'x': 220, 'y': 100, 'color': '#fff3e0' },
                    { 'id': '3', 'name': 'USER.md', 'mdFile': 'USER.md', 'description': '用户档案', 'x': 360, 'y': 100, 'color': '#e8f5e9' },
                    { 'id': '4', 'name': 'AGENTS.md', 'mdFile': 'AGENTS.md', 'description': '执行准则', 'x': 500, 'y': 100, 'color': '#fce4ec' },
                    { 'id': '5', 'name': 'standards.md', 'mdFile': 'standards.md', 'description': '标准规范', 'x': 640, 'y': 100, 'color': '#f3e5f5' },
                    { 'id': '6', 'name': '任务执行', 'mdFile': '', 'description': '执行任务', 'x': 780, 'y': 100, 'color': '#f3e5f5' },
                    { 'id': '7', 'name': 'MEMORY.md', 'mdFile': 'MEMORY.md', 'description': '长期记忆', 'x': 200, 'y': 260, 'color': '#e0f2f1' },
                    { 'id': '8', 'name': '结果输出', 'mdFile': '', 'description': '输出结果', 'x': 400, 'y': 260, 'color': '#e8eaf6' },
                    { 'id': '9', 'name': 'HEARTBEAT.md', 'mdFile': 'HEARTBEAT.md', 'description': '定时检查', 'x': 600, 'y': 260, 'color': '#fff8e1' },
                ]
            }
            return jsonify({'success': True, 'data': default_config})
    except Exception as e:
        logger.error(f"Error getting workflow config: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/architecture/workflow/', methods=['POST'])  # 支持尾部斜杠
@bp.route('/api/architecture/workflow', methods=['POST'])
def save_workflow_config():
    """保存工作流程配置"""
    try:
        data = request.get_json()
        with open(WORKFLOW_CONFIG_PATH, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return jsonify({'success': True, 'message': '工作流程已保存'})
    except Exception as e:
        logger.error(f"Error saving workflow config: {e}")
        return jsonify({'success': False, 'error': str(e)})

@bp.route('/api/architecture/md-files/', methods=['GET'])  # 支持尾部斜杠
@bp.route('/api/architecture/md-files', methods=['GET'])
def get_md_files():
    """获取所有MD文件内容"""
    try:
        md_files = {}
        workspace_path = '/Users/mettlyz/.openclaw/workspace'
    
        for filename in ['SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md', 'MEMORY.md', 'HEARTBEAT.md']:
            filepath = os.path.join(workspace_path, filename)
            if os.path.exists(filepath):
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                md_files[filename] = {
                    'name': filename,
                    'content': content,
                    'description': get_md_description(filename)
                }
    
        return jsonify({'success': True, 'files': md_files})
    except Exception as e:
        logger.error(f"Error getting md files: {e}")
        return jsonify({'success': False, 'error': str(e)})

def get_md_description(filename: str) -> str:
    """获取MD文件描述"""
    descriptions = {
        'SOUL.md': '身份定义和人格',
        'USER.md': '用户档案和偏好',
        'AGENTS.md': '执行准则和工作模式',
        'standards.md': '标准规范和质量要求',
        'MEMORY.md': '长期记忆存储',
        'HEARTBEAT.md': '定时检查和汇报'
    }
    return descriptions.get(filename, '配置文件')

@bp.route('/api/architecture/md-files/<filename>/', methods=['POST'])  # 支持尾部斜杠
@bp.route('/api/architecture/md-files/<filename>', methods=['POST'])
def save_md_file(filename):
    """保存MD文件内容"""
    try:
        if filename not in ['SOUL.md', 'USER.md', 'AGENTS.md', 'standards.md', 'MEMORY.md', 'HEARTBEAT.md', 'CHECKLIST.md']:
            return jsonify({'success': False, 'error': '无效的文件名'})
    
        data = request.get_json()
        content = data.get('content', '')
    
        filepath = os.path.join('/Users/mettlyz/.openclaw/workspace', filename)
    
        # 备份原文件
        backup_path = filepath + '.backup_' + datetime.now().strftime('%Y%m%d_%H%M%S')
        if os.path.exists(filepath):
            os.rename(filepath, backup_path)
    
        # 写入新内容
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
    
        return jsonify({'success': True, 'message': f'{filename} 已保存'})
    except Exception as e:
        logger.error(f"Error saving md file: {e}")
        return jsonify({'success': False, 'error': str(e)})


@bp.route('/api/sds1/documents', methods=['GET'])
def list_sds_documents():
    import os
    from flask import jsonify
    sds_docs_dir = '/opt/kanban-react/frontend/public/uploads/docs/sds1-docs'
    docs = []
    for root, dirs, files in os.walk(sds_docs_dir):
        for f in files:
            if f.endswith('.bak') or f.endswith('.DS_Store'):
                continue
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, sds_docs_dir)
            size = os.path.getsize(full_path)
            docs.append({
                'path': rel_path,
                'url': f'/uploads/docs/{rel_path}',
                'size': size
            })
    docs.sort(key=lambda x: x['path'])
    return jsonify({'success': True, 'documents': docs, 'count': len(docs)})



def _get_sync_data():
    global _sync_data_cache
    if _sync_data_cache is None:
        p = "/opt/kanban-react/backend/macmini_sync_data.json"
        if os.path.exists(p):
            with open(p) as f:
                _sync_data_cache = _json.load(f)
    return _sync_data_cache or {"models":[],"skills":[],"cron_jobs":[],"system":{}}

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

    # Routes moved to routes/sync.py

def macmini_sync_skills_tools():
    """Mac mini 技能工具"""
    return jsonify({
        'success': True,
        'skills': [
            {'name': 'Tavily Search', 'version': '1.0', 'status': 'active'},
            {'name': 'Browser Use', 'version': '1.0', 'status': 'active'},
            {'name': 'Weather', 'version': '1.0', 'status': 'active'},
            {'name': 'GitHub', 'version': '1.0', 'status': 'active'},
            {'name': 'Feishu', 'version': '1.0', 'status': 'active'},
        ]
    })



    # Routes moved to routes/system.py

    # Routes moved to routes/cockpit.py

    # Routes moved to routes/local_files.py


@bp.route('/api/sds/logs/recent')
def sds_logs_recent():
    """返回 SDS 最近 100 行日志"""
    import subprocess
    try:
        r = subprocess.run(
            ['tail', '-100', '/Users/mettlyz/.openclaw/workspace/sds1/logs/unified-sync.log'],
            capture_output=True, text=True, timeout=5
        )
        return jsonify({'success': True, 'logs': r.stdout})
    except Exception as e:
        return jsonify({'success': False, 'logs': f'# 日志读取失败: {e}'}), 500
